"""Contrôles de provenance et de fraîcheur pour des liens de presse attribués."""
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json
import re
from veille import url_article_valide, contient_expression, THEMES

class Metadonnees(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.scripts = []
        self.script = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property') or attrs.get('name')] = attrs.get('content', '')
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.script = []
        if tag == 'script' and attrs.get('id') == '__NUXT_DATA__':
            self.script = []
    def handle_data(self, value):
        if self.script is not None:
            self.script.append(value)
    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            try:
                self.scripts.append(json.loads(''.join(self.script)))
            except (ValueError, TypeError):
                pass
            self.script = None

def donnees_article(parser, url):
    """Associe la date au bon article, jamais à une recommandation voisine."""
    for data in parser.scripts:
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict) or 'canonical_url' not in item:
                    continue
                def lire(key):
                    value = item.get(key)
                    return data[value] if type(value) is int and 0 <= value < len(data) else value
                if str(lire('canonical_url')).rstrip('/') == url.rstrip('/'):
                    return {'datePublished': lire('published_at'), 'headline': lire('title'), 'description': lire('headline')}
        nodes = data.get('@graph', [data]) if isinstance(data, dict) else []
        for item in nodes:
            if not isinstance(item, dict) or item.get('@type') not in ('NewsArticle', 'Article', 'ReportageNewsArticle'):
                continue
            entity = item.get('mainEntityOfPage', item.get('url', ''))
            if isinstance(entity, dict):
                entity = entity.get('@id', '')
            if entity and str(entity).rstrip('/') == url.rstrip('/'):
                return item
    return {}

def controler_article(item, source, body, now=None):
    now = now or datetime.now(timezone.utc)
    url = url_article_valide(item.get('url', ''), source['url'])
    if not url or not url.startswith('https://'):
        return None
    parser = Metadonnees()
    parser.feed(body)
    meta = parser.meta
    article = donnees_article(parser, url)
    titre = re.sub(r'\s+', ' ', meta.get('og:title') or article.get('headline') or '').strip()
    try:
        date = datetime.fromisoformat((meta.get('article:published_time') or meta.get('og:article:published_time') or article.get('datePublished') or '').replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if not 15 <= len(titre) <= 250 or not now - timedelta(days=180) <= date <= now + timedelta(minutes=5):
        return None
    analyse = titre + ' ' + str(meta.get('og:description') or article.get('description') or '')
    themes = [theme for theme, mots in THEMES.items() if any(contient_expression(analyse, mot) for mot in mots)]
    contexte = any(contient_expression(analyse, mot) for mot in
                   ('présidentielle', 'présidentiel', 'candidature'))
    aliases = {'Jordan Bardella': ['jordan bardella', 'bardella'], 'Marine Le Pen': ['marine le pen'],
               'Jean-Luc Mélenchon': ['jean-luc mélenchon', 'mélenchon', 'melenchon'],
               'Gabriel Attal': ['gabriel attal', 'attal'], 'Bruno Retailleau': ['bruno retailleau', 'retailleau']}
    personnes = list(dict.fromkeys(item.get('candidats_mentions', []) + list(aliases)))
    mentions = [nom for nom in personnes if nom and any(contient_expression(analyse, variante) for variante in aliases.get(nom, [nom]))]
    institutions = any(contient_expression(analyse, mot) for mot in ('gouvernement', 'ministre', 'matignon', 'bercy', 'argent public', 'politique publique'))
    if not contexte and not mentions and not (themes and institutions):
        return None
    # Aucun résumé factuel synthétisé : le titre reste attribué au média.
    return {'titre': titre, 'source': source['nom'], 'url': url,
            'description': 'Lien de presse sélectionné automatiquement. Les informations et analyses sont celles du média cité.',
            'date_publication': date.isoformat(), 'controle': 'automatique',
            'themes': themes, 'candidats_mentions': mentions,
            'enquete_anterieure': date < now - timedelta(days=30),
            'nature': 'Lien de presse — contrôle automatique'}

def selectionner_articles(detections, sources, fetch, now=None, exclusions=()):
    sources = {source['nom']: source for source in sources}
    resultats, vus = [], set(exclusions)
    lots = {nom: [] for nom in sources}
    for item in reversed(detections):
        source = sources.get(item.get('source'))
        url = item.get('url')
        if not source or not url or url in vus or not url_article_valide(url, source['url']):
            continue
        vus.add(url)
        if len(lots[source['nom']]) < 20:
            lots[source['nom']].append(item)
    def verifier(item):
        try:
            return controler_article(item, sources[item['source']], fetch(item['url']), now)
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        for nom, lot in lots.items():
            articles = [x for x in pool.map(verifier, lot) if x]
            resultats.extend(sorted(articles, key=lambda x: datetime.fromisoformat(x['date_publication']), reverse=True)[:7])
    return sorted(resultats, key=lambda item: datetime.fromisoformat(item['date_publication']), reverse=True)
