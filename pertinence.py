"""Périmètre commun à la collecte, au repli et à la publication hors réseau."""
import re
import unicodedata

def normaliser(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold())
                   if not unicodedata.combining(c)).replace('‑', '-').replace('–', '-')

NOMS = ('Nicolas Dupont-Aignan', 'Édouard Philippe', 'Gabriel Attal',
        'Bruno Retailleau', 'Jean-Luc Mélenchon', 'Marine Le Pen',
        'Fabien Roussel', 'Éric Zemmour', 'Jordan Bardella',
        'Raphaël Glucksmann', 'Marine Tondelier', 'Olivier Faure',
        'François Ruffin', 'François Hollande', 'Nathalie Arthaud',
        'Philippe Poutou', 'François Asselineau', 'David Lisnard',
        'Xavier Bertrand', 'Valérie Pécresse', 'Bernard Cazeneuve')

def aliases(nom):
    value = normaliser(nom)
    return (value, ' '.join(value.split()[1:]))

def mentions(texte):
    texte = normaliser(texte)
    return [nom for nom in NOMS if any(re.search(r'(?<!\w)' + re.escape(a) + r'(?!\w)', texte)
                                     for a in aliases(nom))]

def candidats_centraux(titre, corps=''):
    """Un nom dans le titre, ou dans le début du texte avec un sujet de campagne.

    Une mention en fin d'article ou des mots génériques « président / ministre »
    ne suffisent jamais. Les noms sont un périmètre de veille, pas une déclaration
    de candidature : les statuts continuent de venir des fiches sourcées.
    """
    directs = mentions(titre)
    if directs:
        return directs
    debut = str(corps)[:1200]
    sujets = re.search(r'\b(propos\w*|programm\w*|mesur\w*|reform\w*|annonc\w*|'
                       r'presidentielle|candidature|campagne|meeting|congres|convention|discours)\b',
                       normaliser(debut))
    return mentions(debut) if sujets else []

def actualite_candidat(item):
    # Ne jamais croire une ancienne liste de mentions calculée sur toute la page.
    return bool(candidats_centraux(item.get('titre', ''),
                item.get('resume', '') or item.get('description', '')))
