"""Extraction et filtrage de veille, sans publication éditoriale."""
from html.parser import HTMLParser
from html import unescape
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

MAX_ARTICLES_PAR_SOURCE = 20
CHEMINS_EXCLUS = (
    '/tag/', '/tags/', '/categorie/', '/category/', '/auteur/', '/author/',
    '/recherche/', '/search/', '/newsletter', '/podcasts', '/mentions-legales',
    '/mentions_legales', '/contact', '/confidentialite', '/confidentiality',
    '/politique-de-confidentialite', '/privacy', '/cookies', '/cookie',
    '/abonnement', '/abonnements', '/abonner', '/subscribe', '/subscription',
    '/connexion', '/login', '/compte', '/account', '/faq', '/qui-sommes-nous',
    '/a-propos', '/about', '/mot-cle/', '/mot-cles/', '/club/',
)
THEMES = {
    'École': ['école', 'éducation', 'enseignant', 'élève', 'collège', 'lycée', 'lycéen', 'lycéenne', 'scolaire'],
    'Santé': ['santé', 'hôpital', 'médecin', 'soins', 'sécurité sociale'],
    'Énergie': ['énergie', 'électricité', 'nucléaire', 'gaz', 'énergétique'],
    'Fiscalité': ['impôt', 'fiscalité', 'taxe'],
    'Écologie': ['écologie', 'écologique', 'climat', 'environnement', 'pollution', 'pollueur', 'pollueurs', 'biodiversité'],
    'Handicap / AESH': ['handicap', 'aesh', 'inclusion scolaire', 'école inclusive'],
}


def url_article_valide(url, source_url):
    """Résout les liens relatifs et écarte navigation et domaines externes."""
    parsed = urlsplit(urljoin(source_url, url))
    source = urlsplit(source_url)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        return None
    if (parsed.hostname or '').lower().removeprefix('www.') != (
        source.hostname or ''
    ).lower().removeprefix('www.'):
        return None
    path = parsed.path.lower()
    if any(part in path for part in CHEMINS_EXCLUS):
        return None
    if path.rstrip('/') in ('', source.path.lower().rstrip('/')):
        return None
    host = (parsed.hostname or '').removeprefix('www.')
    if host == 'mediapart.fr' and not re.fullmatch(r'/journal/[^/]+/\d{6}/[^/]+/?', path):
        return None
    if host == 'blast-info.fr' and not re.fullmatch(r'/(emissions|articles)/\d{4}/[^/]+/?', path):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))


def contient_expression(texte, expression):
    return bool(re.search(r'(?<!\w)' + re.escape(expression) + r'(?!\w)', texte, re.I))


class PageArticle(HTMLParser):
    """Ne mélange pas un article court avec les paragraphes hors article."""
    IGNORES = {'script', 'style', 'noscript', 'svg', 'form', 'nav', 'footer', 'header', 'aside'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.article = []
        self.paragraphes = []
        self.description = ''
        self.a_article = False
        self.nombre_articles = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and (attrs.get('property') == 'og:description' or attrs.get('name') == 'description'):
            self.description = attrs.get('content', '')
        if tag in {'meta', 'img', 'br', 'hr', 'input', 'link', 'source', 'wbr', 'embed', 'area', 'base', 'col', 'param', 'track'}:
            if tag == 'br':
                self.handle_data(' ')
            return
        self.stack.append(tag)
        if tag == 'article':
            self.a_article = True
            self.nombre_articles += 1

    def handle_endtag(self, tag):
        self.handle_data(' ')
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]

    def handle_data(self, data):
        if any(tag in self.IGNORES for tag in self.stack):
            return
        if 'article' in self.stack and self.nombre_articles == 1:
            self.article.append(data)
        if 'p' in self.stack:
            self.paragraphes.append(data)

    def texte(self):
        normalize = lambda parts: re.sub(r'\s+', ' ', ' '.join(parts)).strip()
        article = normalize(self.article)
        if len(article) >= 200:
            return article
        # Une page avec article court/fermé ne doit pas récupérer les recommandations.
        if not self.a_article:
            paragraphs = normalize(self.paragraphes)
            if len(paragraphs) >= 200:
                return paragraphs
        description = normalize([self.description])
        return description if len(description) >= 40 else article


def extraire_html(body):
    parser = PageArticle()
    parser.feed(body)
    return parser.texte()


def surveiller_source(source, fetch, extraire, resume, candidats, date_fr, ajouter, detections):
    nom, source_url = source['nom'], source['url']
    resultat = {'ok': True, 'url': source_url, 'publication_automatique': False,
                'raison': 'Détections soumises aux contrôles automatiques de publication.'}
    articles = []
    examines = 0
    erreurs = 0
    try:
        body = fetch(source_url)
        liens = re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S)
        vus = set()
        for href, titre_html in liens:
            url = url_article_valide(href, source_url)
            titre = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', titre_html)).strip()
            titre = unescape(titre)
            if not url or not titre or url in vus:
                continue
            vus.add(url)
            if examines >= MAX_ARTICLES_PAR_SOURCE:
                break
            examines += 1
            texte = extraire(url)
            if not texte:
                erreurs += 1
            analyse = (titre + ' ' + texte).lower()
            mentions = [nom for nom, variantes in candidats.items()
                        if any(contient_expression(analyse, variante) for variante in variantes)]
            contexte = any(contient_expression(analyse, mot) for mot in
                           ['présidentielle', 'présidentiel', 'candidat', 'candidate', 'candidature'])
            themes = [theme for theme, mots in THEMES.items()
                      if any(contient_expression(analyse, mot) for mot in mots)]
            institutions = any(contient_expression(analyse, mot) for mot in
                               ['gouvernement', 'ministre', 'matignon', 'bercy', 'argent public', 'politique publique'])
            if not contexte and not mentions and not (themes and institutions):
                continue
            detection = {
                'type': source['type'], 'source': nom, 'titre': titre, 'url': url,
                'resume': resume(texte), 'date_detection': date_fr,
                'nature': 'actualité à qualifier',
                'themes': themes,
                'candidats_mentions': mentions, 'statut': 'À vérifier manuellement',
                'publication_automatique': False,
                'note': 'Extrait automatique incomplet possible. Vérifier la source, les chiffres et le contexte avant publication.',
            }
            ajouter(detections, detection)
            articles.append(detection)
        resultat.update(detections=len(articles), liens_examines=examines,
                        extractions_vides=erreurs, liens_trouves=len(liens),
                        etat_extraction='partielle' if erreurs else ('aucun_article' if not examines else 'ok'),
                        mise_a_jour={'nombre': len(articles), 'articles': articles[-5:]})
    except Exception as exc:
        resultat.update(ok=False, erreur=f'{type(exc).__name__}: {exc}')
    return resultat


def construire_validation(detections, existantes, sources):
    """Les décisions et textes humains restent intacts, même hors de la veille récente."""
    par_url = {item['url']: dict(item) for item in existantes if item.get('url')}
    urls_sources = {source['nom']: source['url'] for source in sources}
    for detection in detections:
        nom = detection.get('source')
        url = detection.get('url')
        if nom not in urls_sources or not detection.get('titre'):
            continue
        if not url_article_valide(url or '', urls_sources[nom]):
            continue
        if url in par_url:
            continue
        entree = {key: detection.get(key, '') for key in
                  ('source', 'titre', 'url', 'resume', 'date_detection', 'nature', 'themes', 'candidats_mentions')}
        entree.update(statut='À vérifier manuellement', publication_automatique=False)
        par_url[url] = entree
    for item in par_url.values():
        item['publication_automatique'] = False
    return list(par_url.values())
