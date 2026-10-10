"""Contrôles de provenance et de fraîcheur pour des liens de presse attribués."""
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import re
from veille import url_article_valide, contient_expression

class Metadonnees(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property') or attrs.get('name')] = attrs.get('content', '')

def controler_article(item, source, body, now=None):
    now = now or datetime.now(timezone.utc)
    url = url_article_valide(item.get('url', ''), source['url'])
    if not url or not url.startswith('https://'):
        return None
    parser = Metadonnees()
    parser.feed(body)
    meta = parser.meta
    titre = re.sub(r'\s+', ' ', meta.get('og:title', '')).strip()
    try:
        date = datetime.fromisoformat(meta.get('article:published_time', '').replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if not 15 <= len(titre) <= 250 or not now - timedelta(days=30) <= date <= now + timedelta(minutes=5):
        return None
    analyse = titre + ' ' + meta.get('og:description', '')
    contexte = any(contient_expression(analyse, mot) for mot in
                   ('présidentielle', 'présidentiel', 'candidature'))
    mentions = any(contient_expression(analyse, nom) for nom in item.get('candidats_mentions', []) if nom)
    if not contexte and not mentions:
        return None
    # Aucun résumé factuel synthétisé : le titre reste attribué au média.
    return {'titre': titre, 'source': source['nom'], 'url': url,
            'description': 'Lien de presse sélectionné automatiquement. Les informations et analyses sont celles du média cité.',
            'date_publication': date.isoformat(), 'controle': 'automatique',
            'nature': 'Lien de presse — contrôle automatique'}

def selectionner_articles(detections, sources, fetch, now=None, exclusions=()):
    sources = {source['nom']: source for source in sources}
    resultats, vus = [], set(exclusions)
    for item in reversed(detections):
        source = sources.get(item.get('source'))
        url = item.get('url')
        if not source or not url or url in vus or not url_article_valide(url, source['url']):
            continue
        vus.add(url)
        try:
            article = controler_article(item, source, fetch(url), now)
        except Exception:
            article = None
        if article:
            resultats.append(article)
        if len(vus) >= len(exclusions) + 60:
            break
    return sorted(resultats, key=lambda item: item['date_publication'], reverse=True)[:20]
