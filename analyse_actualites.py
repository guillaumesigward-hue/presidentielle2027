"""Lecture thématique transparente des actualités déjà retenues.

Cette couche ne juge pas un candidat. Elle indique ce qu'une actualité permet
ou ne permet pas de conclure au regard des sujets suivis par le site.
"""
import re
import unicodedata

VERSION = 'lecture-thematique-v2'

THEMES = {
    'École et jeunesse': ('ecole', 'education', 'enseignant', 'eleve', 'college', 'lycee', 'aesh', 'scolaire', 'cantine', 'enfant'),
    'Finances publiques et financement': ('budget', 'cout', 'financement', 'depense', 'economie', 'deficit', 'dette', 'milliard', 'million', 'aide publique', 'aides publiques', 'epargne'),
    'Santé et protection sociale': ('sante', 'hopital', 'medecin', 'soin', 'securite sociale', 'medicament', 'retraite', 'protection sociale'),
    'Travail, retraites et pouvoir d’achat': ('travail', 'emploi', 'salaire', 'smic', 'retraite', 'prix', 'pouvoir d achat', 'carburant', 'syndicat'),
    'Fiscalité': ('impot', 'fiscalite', 'taxe', 'tva', 'cotisation', 'prelevement'),
    'Énergie et industrie': ('energie', 'electricite', 'nucleaire', 'gaz', 'carburant', 'industrie', 'industriel'),
    'Écologie et climat': ('ecologie', 'climat', 'environnement', 'pollution', 'biodiversite', 'renouvelable', 'adaptation climatique'),
    'Institutions, libertés et souveraineté': ('etat', 'institution', 'justice', 'police', 'liberte', 'constitution', 'service public', 'souverainete', 'intelligence artificielle'),
    'Immigration': ('immigration', 'migrant', 'asile', 'oqtf', 'frontiere', 'expulsion'),
    'International et défense': ('otan', 'ukraine', 'russie', 'guerre', 'defense', 'diplomatie', 'international', 'etrangere'),
    'Handicap et AESH': ('handicap', 'aesh', 'inclusion scolaire'),
}

QUESTIONS = {
    'École et jeunesse': 'Quels moyens humains, quel calendrier et quels effets sur les inégalités scolaires sont documentés ?',
    'Finances publiques et financement': 'Quel coût complet, quelles recettes ou économies et quel effet sur le déficit sont documentés ?',
    'Santé et protection sociale': 'Quels moyens, quelle couverture, quelle gouvernance et quel effet sur l’accès aux soins sont précisés ?',
    'Travail, retraites et pouvoir d’achat': 'Qui gagne ou perd, selon quel calendrier et avec quel effet sur l’emploi et le pouvoir d’achat ?',
    'Fiscalité': 'Quels contribuables sont concernés, pour quel rendement et avec quels effets redistributifs ?',
    'Énergie et industrie': 'Quels coûts, capacités, délais, dépendances et effets sur les prix et les émissions sont établis ?',
    'Écologie et climat': 'Quels objectifs mesurables, contraintes, financements et effets sociaux accompagnent l’annonce ?',
    'Institutions, libertés et souveraineté': 'Quelles garanties juridiques, quels contrôles et quelles conséquences pour les libertés publiques sont prévus ?',
    'Immigration': 'Quels fondements juridiques, moyens d’exécution et effets humains ou budgétaires sont explicités ?',
    'International et défense': 'Quels partenaires, moyens, risques et conséquences diplomatiques ou budgétaires sont évalués ?',
    'Handicap et AESH': 'Quels droits effectifs, effectifs, formations, délais et financements sont garantis ?',
}

PRIORITAIRES = ('École et jeunesse', 'Finances publiques et financement',
                'Santé et protection sociale', 'Énergie et industrie',
                'Fiscalité', 'Écologie et climat')
THEMES_PROGRAMME = {
    'École et jeunesse': 'ecole', 'Santé et protection sociale': 'sante',
    'Énergie et industrie': 'energie', 'Fiscalité': 'fiscalite',
    'Écologie et climat': 'ecologie',
}

def normaliser(texte):
    texte = unicodedata.normalize('NFKD', str(texte).casefold())
    return ''.join(c for c in texte if not unicodedata.combining(c))

def contient(texte, terme):
    # Accepter pluriels et flexions simples : « financer », « financée »,
    # « milliards » ou « enseignants » doivent rejoindre leur notion.
    return bool(re.search(r'(?<!\w)' + re.escape(terme) + r'\w*(?!\w)', texte))

def _themes(texte, existants=()):
    texte = normaliser(texte)
    resultat = []
    correspondances = {
        'École': 'École et jeunesse', 'Santé': 'Santé et protection sociale',
        'Énergie': 'Énergie et industrie', 'Fiscalité': 'Fiscalité',
        'Écologie': 'Écologie et climat', 'Handicap / AESH': 'Handicap et AESH',
        'Institutions / libertés publiques': 'Institutions, libertés et souveraineté',
        'Immigration': 'Immigration', 'Travail': 'Travail, retraites et pouvoir d’achat',
        'Finances publiques': 'Finances publiques et financement',
    }
    forces = {correspondances[x] for x in existants if x in correspondances}
    for theme, mots in THEMES.items():
        if theme in forces or any(contient(texte, mot) for mot in mots):
            resultat.append(theme)
    return resultat

def _nature(texte):
    texte = normaliser(texte)
    if any(contient(texte, x) for x in ('candidature', 'candidat', 'candidate')) and not any(
            contient(texte, x) for x in ('propose', 'proposition', 'mesure', 'reforme')):
        return 'Statut ou stratégie de candidature'
    if any(contient(texte, x) for x in ('propose', 'proposition', 'mesure', 'reforme',
                                        'veut', 'souhaite', 'defend', 'programme', 'projet', 'axe')):
        return 'Proposition ou orientation de programme'
    return 'Prise de position ou élément de contexte'

def _elements_theme(texte, theme):
    """Retient jusqu'à deux éléments courts, sans commentaire ajouté."""
    phrases = [re.sub(r'\s+', ' ', x).strip(' -•\t') for x in
               re.split(r'(?<=[.!?])\s+|[\r\n]+', str(texte))]
    mots = THEMES[theme]
    candidats = []
    for phrase in phrases:
        segments = re.split(r'[,;]|\s+ainsi que\s+|\s+et\s+(?=(?:un|une|des|le|la|les)\b)',
                            phrase, flags=re.I)
        precis = [segment.strip() for segment in segments
                  if len(segment.strip()) >= 20
                  and any(contient(normaliser(segment), mot) for mot in mots)]
        candidats.extend(precis or ([phrase] if len(phrase) >= 20
                           and any(contient(normaliser(phrase), mot) for mot in mots) else []))
    retenues = []
    for element in candidats:
        element = element.strip()
        element = element[:1].upper() + element[1:]
        if element and element[-1] not in '.!?…':
            element += '.'
        if element not in retenues:
            retenues.append(element)
    elements = []
    for phrase in retenues[:2]:
        if len(phrase) > 360:
            phrase = phrase[:357].rsplit(' ', 1)[0] + '…'
        elements.append(phrase)
    return elements

def _grille_thematique(texte, themes):
    grille = []
    for theme in THEMES:
        if theme in themes:
            elements = _elements_theme(texte, theme)
            constat = (' '.join(elements) if elements else
                       'Aucun élément précis disponible dans le texte accessible.')
            grille.append({'theme': theme, 'statut': 'aborde', 'libelle_statut': 'Sujet abordé',
                            'constat': constat, 'elements': elements, 'question': QUESTIONS[theme]})
        else:
            grille.append({'theme': theme, 'statut': 'non_aborde',
                            'libelle_statut': 'Sujet non abordé',
                            'constat': 'Sujet non abordé dans cette information.',
                            'elements': [],
                            'question': QUESTIONS[theme]})
    return grille

def analyser_actualite(item, programmes=None):
    texte = '. '.join(str(item.get(k, '')).strip().rstrip('.')
                      for k in ('titre', 'description', 'resume') if item.get(k))
    themes = _themes(texte, item.get('themes', []))
    nature = _nature(texte)
    # Une date de publication ne rend pas une mesure « chiffrée ».
    chiffres = re.findall(r'\b\d+(?:[,.]\d+)?\s*(?:%|euros?|milliards?|millions?|ans?|'
                          r'postes?|places?|emplois?|classes?|élèves?|enseignants?)\b', texte, re.I)
    financement = any(x in themes for x in ('Finances publiques et financement', 'Fiscalité'))
    proposition = nature == 'Proposition ou orientation de programme'
    candidat = (item.get('candidats_mentions') or ['la personne concernée'])[0]
    if proposition and chiffres and financement:
        avis = ('Actualité très utile pour engager la comparaison : elle contient une orientation, '
                'des éléments chiffrés et un enjeu de financement. Elle ne suffit toutefois pas à '
                'établir le coût complet, les effets attendus ni la faisabilité de la mesure.')
        niveau = 'Utile et relativement documentée, à confronter au chiffrage complet'
    elif proposition and chiffres:
        avis = ('Actualité utile pour comparer les programmes : elle présente une mesure avec au moins '
                'un repère chiffré. Le financement, les modalités d’application et les effets indirects '
                'restent à vérifier dans les documents complets.')
        niveau = 'Utile, mais documentation incomplète'
    elif proposition:
        avis = ('Actualité pertinente pour identifier une orientation de programme. Elle reste '
                'insuffisante pour apprécier sa faisabilité : coût, financement, calendrier, bénéficiaires '
                'et indicateurs de résultat doivent encore être documentés.')
        niveau = 'Pertinente pour l’orientation, insuffisante pour conclure'
    else:
        avis = ('Actualité utile comme contexte ou prise de position, mais trop peu opérationnelle pour '
                'évaluer un programme. Elle doit être complétée par une mesure précise, son calendrier, '
                'son financement et des critères permettant d’en mesurer les effets.')
        niveau = 'Contexte à suivre, portée programmatique limitée'
    if themes:
        liste_themes = themes[0] if len(themes) == 1 else ', '.join(themes[:-1]) + ' et ' + themes[-1]
        apport = (f'Cette actualité concernant {candidat} éclaire ' + liste_themes
                  + '. Elle aide à repérer le sujet politique traité, sans valider les résultats annoncés.')
    else:
        apport = (f'Cette actualité concernant {candidat} ne documente directement aucun des sujets '
                  'de réflexion suivis. Elle reste affichée pour son lien avec la candidature.')
    finance = ('Un élément financier ou fiscal est repéré, mais l’article seul ne permet pas de vérifier '
               'le coût net, la recette, les économies, le calendrier budgétaire et l’effet sur le déficit.'
               if financement else
               'Aucun chiffrage ou financement suffisamment identifiable n’apparaît dans le texte résumé. '
               'Ce silence ne signifie pas que la proposition serait sans coût.')
    questions = [QUESTIONS[t] for t in themes]
    if not financement:
        questions.append(QUESTIONS['Finances publiques et financement'])
    if not questions:
        questions = [QUESTIONS['Finances publiques et financement'],
                     'Quelle mesure précise cette actualité permet-elle de comparer au programme du candidat ?']
    non_documentes = [x for x in PRIORITAIRES if x not in themes]
    dossier = None
    if isinstance(programmes, dict):
        dossier = next((x for x in programmes.get('pretendants', []) if x.get('nom') == candidat), None)
    fiches = [theme for theme in themes if theme in THEMES_PROGRAMME and dossier
              and dossier.get('themes', {}).get(THEMES_PROGRAMME[theme])]
    if fiches:
        comparaison = (f'À rapprocher de la fiche programme « {fiches[0]} » de {candidat}. '
                       'L’actualité constitue un complément daté ; la fiche programme reste la référence '
                       'pour le détail des mesures, les sources et le financement disponible.')
    elif themes:
        comparaison = ('Aucune comparaison directe n’est disponible dans les cinq fiches programme '
                       'prioritaires pour ce sujet. Cela ne signifie pas que le candidat n’a pas de proposition.')
    else:
        comparaison = ('Cette actualité ne permet pas de rapprochement avec les cinq fiches programme '
                       'prioritaires actuellement affichées.')
    return {'version': VERSION, 'nature': nature, 'niveau': niveau,
            'themes_concernes': themes, 'apport': apport, 'avis': avis,
            'finances_publiques': finance, 'questions': questions,
            'comparaison_programme': comparaison,
            'themes_non_documentes': non_documentes,
            'analyse_par_sujet': _grille_thematique(texte, themes)}

def enrichir_actualites(actualites, programmes=None):
    for item in actualites:
        item['point_reflexion'] = analyser_actualite(item, programmes)
    return actualites

def enrichir_syntheses(syntheses, programmes=None):
    """Applique la même grille aux discours, congrès et programmes résumés."""
    for item in syntheses:
        paragraphes = '. '.join(
            str(paragraphe.get('texte', '')).strip().rstrip('.')
            for paragraphe in item.get('paragraphes', []) if isinstance(paragraphe, dict)
        )
        document = {
            'titre': item.get('titre', ''),
            'description': paragraphes,
            'resume': item.get('evolution', ''),
            'candidats_mentions': [item.get('candidat')] if item.get('candidat') else [],
            'themes': item.get('themes', []),
        }
        point = analyser_actualite(document, programmes)
        point['nature'] = item.get('nature') or point['nature']
        point['apport'] = point['apport'].replace('Cette actualité', 'Cette synthèse', 1)
        point['avis'] = point['avis'].replace('Actualité', 'Synthèse', 1)
        point['finances_publiques'] = point['finances_publiques'].replace("l’article seul", 'le document seul')
        item['point_reflexion'] = point
    return syntheses
