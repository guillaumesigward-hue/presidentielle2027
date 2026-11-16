"""Suivi des supports primaires : texte seulement, aucune vidéo embarquée."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
import hashlib
import os
import re
import time
from automatisation import Metadonnees, donnees_article
from delais import delai_reel, DelaiDepasse
from officiel_auto import CAMPAGNES, TextePrincipal, lien_officiel
from pertinence import normaliser, mentions
from resumes_auto import moteur, raison_rejet, extrait_pertinent

VERSION = 'synthese-campagne-v1'
SUPPORTS = [
    ('Jean-Luc Mélenchon', 'https://melenchon.fr/2026/11/07/grand-meeting-du-bourget-notre-programme-de-gouvernement/'),
    ('Édouard Philippe', 'https://www.edouardphilippe.fr/programme/retraites'),
    ('Bruno Retailleau', 'https://www.avecretailleau.fr/projet/theme/logement'),
]

def lire_support(nom, url, body):
    racines = [(n, r) for n, r in CAMPAGNES.items()] + [('Jean-Luc Mélenchon', 'https://melenchon.fr/')]
    if not any(n == nom and lien_officiel(url, root) for n, root in racines):
        raise ValueError('Domaine primaire non autorisé pour cette personne')
    parser = TextePrincipal(); parser.feed(body)
    texte = parser.texte()
    # Certains programmes composent leur <main> de dizaines de petites fiches
    # <article>. Le premier encadré n'est alors pas le document complet.
    if parser.nombre_articles > 1 and re.search(r'/(programme|projet)/', url):
        texte = re.sub(r'\s+', ' ', ' '.join(parser.main)).strip()
        texte = re.split(r'Vos avis\s*[.]?', texte, maxsplit=1, flags=re.I)[0].strip()
    if len(texte.split()) < 200:
        raise ValueError('Texte intégral ou transcription insuffisante')
    meta = Metadonnees(); meta.feed(body)
    article = donnees_article(meta, url)
    titre = meta.meta.get('og:title') or article.get('headline') or ''
    if nom in ('Marine Le Pen', 'Fabien Roussel'):
        author = article.get('author', {})
        author = author.get('name', '') if isinstance(author, dict) else ''
        if nom not in mentions(titre + ' ' + str(author)):
            raise ValueError('Auteur personnel non établi sur le site du parti')
    # Un espace de campagne est autorisé pour son titulaire, sans attribuer
    # les propos d'un invité ou d'un adversaire au candidat.
    if normaliser(nom) not in normaliser(texte + ' ' + titre):
        raise ValueError('Auteur du document non établi')
    date = meta.meta.get('article:published_time') or article.get('datePublished')
    if date:
        parsed = datetime.fromisoformat(date.replace('Z', '+00:00'))
        if parsed.year < 2026 or parsed.date() > datetime.now(timezone.utc).date():
            raise ValueError('Date hors campagne')
    reference = texte + ' ' + url + ' ' + titre
    campagne_courante = nom in CAMPAGNES and lien_officiel(url, CAMPAGNES[nom]) and re.search(r'/(programme|projet)/', url)
    if re.search(r'(?:programme|presidentielle).{0,30}2022', normaliser(reference[:1200])):
        raise ValueError('Ancien programme')
    if not re.search(r'\b2027\b', reference) and not campagne_courante:
        raise ValueError('Document non rattaché à la campagne 2027')
    return {'candidat': nom, 'url': url, 'titre': titre or 'Publication de campagne',
            'empreinte': hashlib.sha256(texte.encode()).hexdigest(),
            'date_publication': date, 'texte': texte}

def actualiser_syntheses(anciennes, fetch, generate=None):
    maintenant = datetime.now(timezone.utc).isoformat()
    precedentes = {x['url']: x for x in anciennes}
    urls = dict((url, nom) for nom, url in SUPPORTS)
    racines = list(CAMPAGNES.items()) + [('Jean-Luc Mélenchon', 'https://melenchon.fr/')]
    urls.update({url: x['candidat'] for url, x in precedentes.items()
                 if any(nom == x['candidat'] and lien_officiel(url, root) for nom, root in racines)})
    bilan = {'documents_examines': 0, 'accessibles': 0, 'syntheses': 0, 'reportes': 0, 'sources': {}}
    # Découverte bornée, sur les seuls domaines primaires autorisés.
    def decouvrir(item):
        nom, root = item
        liens = []
        try:
            body = fetch(root)
            for href, titre in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
                if not re.search(r'meeting|congr[eè]s|convention|discours|programme|projet', unescape(re.sub('<[^>]+>', ' ', titre)) + href, re.I):
                    continue
                url = lien_officiel(href, root)
                if url and url.rstrip('/') != root.rstrip('/'):
                    liens.append((url, nom))
                if len(liens) >= 3: break
        except Exception: pass
        return liens
    with ThreadPoolExecutor(max_workers=6) as pool:
        for liens in pool.map(decouvrir, racines):
            for url, nom in liens: urls.setdefault(url, nom)
    def lire(item):
        url, nom = item
        try:
            with delai_reel(35):
                return url, lire_support(nom, url, fetch(url)), None
        except (Exception, DelaiDepasse) as exc:
            return url, None, type(exc).__name__
    rediger = generate
    limite = time.monotonic() + 600
    limite_lecture = time.monotonic() + 180
    resultat = []
    try:
        # Ne pas placer delai_reel (signal POSIX) dans un worker.
        for entree in list(urls.items())[:32]:
            if time.monotonic() >= limite_lecture:
                break
            url, support, erreur = lire(entree)
            bilan['documents_examines'] += 1
            old = precedentes.get(url)
            if not support:
                bilan['sources'][url] = {'ok': False, 'erreur': erreur}
                if old:
                    resultat.append(dict(old, verification_differee=True,
                        limite='Source momentanément inaccessible ; synthèse conservée avec sa date de vérification antérieure.'))
                continue
            bilan['accessibles'] += 1
            bilan['sources'][url] = {'ok': True}
            if old and old.get('empreinte') == support['empreinte'] and old.get('paragraphes'):
                resultat.append(dict(old, dernier_controle_utc=maintenant, verification_differee=False))
                continue
            # Un programme sans date n'est pas transformé en annonce nouvelle.
            connu = url in dict((u, n) for n, u in SUPPORTS) or bool(old)
            if not support['date_publication'] and not connu:
                bilan['reportes'] += 1
                continue
            if (generate is None and os.environ.get('RESUMES_LOCAUX') != '1') or time.monotonic() >= limite:
                bilan['reportes'] += 1
                continue
            texte, partiel = extrait_pertinent(support['titre'], support['texte'])
            preuve = support['candidat'] + '\n' + support['titre'] + '\n' + texte
            try:
                with delai_reel(max(1, limite-time.monotonic())):
                    if rediger is None: rediger = moteur(campagne=True)
                    resume = rediger(preuve)
                if raison_rejet(resume, preuve) or not resume.rstrip().endswith(('.', '!', '?')):
                    raise ValueError('Résumé incohérent')
                support.pop('texte')
                support.update(paragraphes=[{'titre': 'Propositions présentées', 'texte': resume}],
                    nature='Synthèse automatique de source primaire', version=VERSION,
                    dernier_controle_utc=maintenant, date_evenement=support['date_publication'],
                    evolution='Document nouveau ou modifié dans la veille ; nouveauté politique non établie.',
                    limite='Propositions du candidat, sans validation indépendante de leur faisabilité.' +
                    (' Source longue : seuls des passages ont été traités.' if partiel else ''))
                if old:
                    support['evolution'] = ('Texte de campagne modifié depuis le contrôle du '
                        + str(old.get('dernier_controle_utc', 'passage précédent'))[:10]
                        + '. Synthèse actualisée ; la nouveauté de chaque proposition reste à établir.')
                resultat.append(support)
            except (Exception, DelaiDepasse):
                bilan['reportes'] += 1
                # Ne jamais publier l'ancien résumé comme celui d'un texte modifié.
                if rediger is not None and hasattr(rediger, 'close'):
                    rediger.close(); moteur.cache_clear(); rediger = None
    finally:
        if generate is None and rediger is not None and hasattr(rediger, 'close'):
            rediger.close(); moteur.cache_clear()
    visites = set(bilan['sources'])
    resultat.extend(dict(x, verification_differee=True) for url, x in precedentes.items()
                    if url in urls and url not in visites)
    bilan['syntheses'] = len(resultat)
    return resultat, bilan
