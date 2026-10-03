from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin
import html
import json
import re
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

COMMISSION_URL = (
    "https://www.commission-des-sondages.fr/notices/medias/"
    "fichiers/bytag/14/2027-Presidentielle"
)

VERIAN_URL = "https://www.veriangroup.com/fr/news-and-insights"
# Sources journalistiques indépendantes / investigation.
# Leur présence dans la veille ne vaut ni validation ni publication automatique.
SOURCES_JOURNALISTIQUES = [
    {
        "nom": "Mediapart",
        "url": "https://www.mediapart.fr/journal/politique",
        "type": "media_independant_investigation",
    },
    {
        "nom": "Blast",
        "url": "https://www.blast-info.fr/",
        "type": "media_independant_investigation",
    },
    {
        "nom": "Disclose",
        "url": "https://disclose.ngo/fr",
        "type": "media_investigation",
    },
]

MOTS_CLES_POLITIQUES = [
    # Élection présidentielle
    "présidentielle",
    "2027",
    "candidat",
    "candidate",
    "campagne",
    "élection",

    # École
    "école",
    "éducation",
    "enseignant",
    "enseignante",
    "aesh",
    "handicap",
    "inclusion scolaire",

    # Santé
    "santé",
    "hôpital",
    "médecin",
    "soins",
    "sécurité sociale",

    # Énergie
    "énergie",
    "électricité",
    "nucléaire",
    "gaz",

    # Fiscalité
    "impôt",
    "impôts",
    "fiscalité",
    "taxe",
    "taxes",

    # Écologie
    "écologie",
    "climat",
    "environnement",
    "pollution",
]
USER_AGENT = "Presidentielle2027SourceMonitor/5.0"


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()
def extraire_texte_article(url):
    """
    Récupère le contenu textuel utile d'un article.
    Essaie d'abord le contenu de l'article, puis les métadonnées
    de description si le corps de page n'est pas exploitable.
    """
    try:
        body = fetch(url)

        if not body:
            return ""

        # 1. Supprimer les blocs non éditoriaux.
        contenu = re.sub(
            r"<(script|style|noscript|svg|form|nav|footer|header)[^>]*>"
            r".*?</\1>",
            " ",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 2. Essayer de récupérer spécifiquement le contenu <article>.
        article_match = re.search(
            r"<article[^>]*>(.*?)</article>",
            contenu,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if article_match:
            texte = clean_text(article_match.group(1))

            if len(texte) >= 200:
                return texte

        # 3. Sinon récupérer les paragraphes de la page.
        paragraphes = re.findall(
            r"<p[^>]*>(.*?)</p>",
            contenu,
            flags=re.IGNORECASE | re.DOTALL,
        )

        textes = []

        for paragraphe in paragraphes:
            texte = clean_text(paragraphe)

            # Élimine les petits éléments de navigation ou légendes.
            if len(texte) >= 40:
                textes.append(texte)

        texte_paragraphes = " ".join(textes).strip()

        if len(texte_paragraphes) >= 200:
            return texte_paragraphes

        # 4. Solution de repli :
        # description OpenGraph utilisée par de nombreux médias.
        meta_patterns = [
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        ]

        for pattern in meta_patterns:
            match = re.search(
                pattern,
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if match:
                description = clean_text(match.group(1))

                if len(description) >= 40:
                    return description

        return ""

    except Exception as erreur:
        print(
            f"Impossible d'extraire l'article {url}: "
            f"{type(erreur).__name__}: {erreur}"
        )
        return ""
def creer_resume_article(texte, longueur_max=650):
    """
    Produit un résumé extractif court à partir du texte de l'article.
    """
    if not texte:
        return ""

    texte = re.sub(r"\s+", " ", texte).strip()
    phrases = re.split(r"(?<=[.!?])\s+", texte)

    phrases_utiles = []

    for phrase in phrases:
        phrase = phrase.strip()

        if len(phrase) < 40:
            continue

        phrases_utiles.append(phrase)

        if len(phrases_utiles) >= 3:
            break

        if len(" ".join(phrases_utiles)) >= longueur_max:
            break

    resume = " ".join(phrases_utiles)

    if len(resume) > longueur_max:
        resume = resume[:longueur_max].rsplit(" ", 1)[0] + "…"

    return resume

def charger_json(path, valeur_defaut):
    if not path.exists():
        return valeur_defaut

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return valeur_defaut


def ecrire_json(path, contenu):
    texte = json.dumps(
        contenu,
        ensure_ascii=False,
        indent=2
    )

    # Vérification avant écriture.
    json.loads(texte)

    path.write_text(
        texte + "\n",
        encoding="utf-8"
    )


def ajouter_detection(collection, detection):
    """
    Évite les doublons dans la file de détection.
    Si une détection existe déjà, ses nouvelles informations
    sont ajoutées ou mises à jour.
    """
    cle = (
        detection.get("type"),
        detection.get("titre"),
        detection.get("url"),
    )

    for element in collection:
        cle_existante = (
            element.get("type"),
            element.get("titre"),
            element.get("url"),
        )

        if cle_existante == cle:
            for champ, valeur in detection.items():
                if valeur not in (None, "", [], {}):
                    element[champ] = valeur
            return
    collection.append(detection)
now = datetime.now(timezone.utc)

months = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre"
]

date_fr = (
    f"{now.day} {months[now.month - 1]} {now.year}"
)

election_file = DATA_DIR / "election.json"
status_file = DATA_DIR / "status.json"
detections_file = DATA_DIR / "actualites_detectees.json"
validation_file = DATA_DIR / "a_valider.json"

# IMPORTANT :
# data/programmes.json est volontairement absent de ce script.
# Les fiches politiques validées manuellement ne sont donc jamais
# modifiées, complétées ou écrasées par l'automatisation.

election = charger_json(
    election_file,
    {
        "titre": "Présidentielle française 2027",
        "candidatures": [],
        "sondages": [],
        "programmes": [],
        "actualites": [],
        "sources": []
    }
)

# On préserve toujours les contenus éditoriaux existants.
election.setdefault("candidatures", [])
election.setdefault("sondages", [])
election.setdefault("programmes", [])
election.setdefault("actualites", [])
election.setdefault("sources", [])

# Cette date signifie désormais :
# dernière vérification du robot, et non dernière modification
# du contenu politique.
election["derniere_mise_a_jour"] = date_fr

status = {
    "last_checked_utc": now.isoformat(),
    "last_checked_fr": date_fr,
    "publication_automatique": False,
    "sources": {}
}

# On conserve l'historique des détections déjà enregistrées.
detections = charger_json(detections_file, [])

# Sécurité : si le fichier est endommagé ou ne contient plus une liste,
# on repart d'une liste vide sans interrompre le robot.
if not isinstance(detections, list):
    detections = []

# ------------------------------------------------------------
# COMMISSION DES SONDAGES
# ------------------------------------------------------------

try:
    commission_body = fetch(COMMISSION_URL)

    notices = []

    for match in re.finditer(
        r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        commission_body,
        flags=re.IGNORECASE | re.DOTALL
    ):
        url = match.group(1)
        if url.startswith("/"):
            url = "https://www.commission-des-sondages.fr" + url
        titre = clean_text(match.group(2))

        if not titre:
            continue

        if "pres" not in titre.lower() and "prés" not in titre.lower():
            continue

        id_match = re.search(r"(\d{4,})", url + " " + titre)

        notice_id = (
            int(id_match.group(1))
            if id_match
            else None
        )

        notices.append(
            {
                "id": notice_id,
                "titre": titre,
                "url": url
            }
        )

    # Déduplication.
    notices_uniques = []
    deja_vues = set()

    for notice in notices:
        cle = (
            notice.get("id"),
            notice.get("titre")
        )

        if cle in deja_vues:
            continue

        deja_vues.add(cle)
        notices_uniques.append(notice)

    notices = notices_uniques

    ids = [
        notice["id"]
        for notice in notices
        if notice["id"] is not None
    ]

    dernier_id = max(ids) if ids else None

    status["sources"]["commission_sondages"] = {
        "ok": True,
        "url": COMMISSION_URL,
        "notices_detectees": len(notices),
        "dernier_id_detecte": dernier_id,
        "publication_automatique": False,
        "raison": (
            "La rubrique présidentielle de la Commission peut contenir "
            "des enquêtes thématiques qui ne sont pas des intentions "
            "de vote. Une vérification humaine est requise avant publication."
        )
    }

    # On ne publie AUCUN résultat automatiquement.
    # On signale seulement les notices les plus récentes.
    notices_avec_id = [
        n for n in notices
        if n.get("id") is not None
    ]

    notices_avec_id.sort(
        key=lambda n: n["id"],
        reverse=True
    )

    for notice in notices_avec_id[:10]:
        ajouter_detection(
            detections,
            {
                "type": "commission_sondages",
                "titre": notice["titre"],
                "url": notice["url"],
                "date_detection": date_fr,
                "statut": "À vérifier manuellement",
                "publication_automatique": False,
                "note": (
                    "Cette notice peut être une intention de vote, "
                    "une enquête thématique ou une autre question "
                    "d'opinion. Ne pas publier comme sondage électoral "
                    "sans vérification du document."
                )
            }
        )

except Exception as exc:
    status["sources"]["commission_sondages"] = {
        "ok": False,
        "url": COMMISSION_URL,
        "erreur": str(exc),
        "publication_automatique": False
    }


# ------------------------------------------------------------
# VERIAN
# ------------------------------------------------------------

try:
    verian_body = fetch(VERIAN_URL)
    verian_text = clean_text(verian_body)

    status["sources"]["verian"] = {
        "ok": True,
        "url": VERIAN_URL,
        "publication_automatique": False,
        "raison": (
            "Les nouvelles publications sont détectées pour examen. "
            "Le robot ne transforme pas automatiquement une publication "
            "Verian en sondage présidentiel ou en contenu politique."
        )
    }

    recherches_verian = [
        {
            "expression": "stature présidentielle",
            "titre": (
                "Publication Verian détectée — "
                "stature présidentielle"
            )
        },
        {
            "expression": "baromètre politique",
            "titre": (
                "Publication Verian détectée — "
                "baromètre politique"
            )
        },
        {
            "expression": "présidentielle 2027",
            "titre": (
                "Publication Verian détectée — "
                "présidentielle 2027"
            )
        }
    ]

    texte_minuscule = verian_text.lower()

    for recherche in recherches_verian:
        if recherche["expression"].lower() in texte_minuscule:
            ajouter_detection(
                detections,
                {
                    "type": "verian",
                    "titre": recherche["titre"],
                    "url": VERIAN_URL,
                    "date_detection": date_fr,
                    "statut": "À vérifier manuellement",
                    "publication_automatique": False,
                    "note": (
                        "Vérifier la publication originale, "
                        "les dates de terrain, l'échantillon "
                        "et la nature exacte de l'enquête "
                        "avant toute publication sur le site."
                    )
                }
            )

except Exception as exc:
    status["sources"]["verian"] = {
        "ok": False,
        "url": VERIAN_URL,
        "erreur": str(exc),
        "publication_automatique": False
    }

# ------------------------------------------------------------
# Veille journalistique indépendante / investigation
# ------------------------------------------------------------
# --------------------------------------------------
# PERSONNES POLITIQUES RECHERCHEES DANS LES ARTICLES
# --------------------------------------------------

candidats_recherches = {
    "Nicolas Dupont-Aignan": [
        "nicolas dupont-aignan",
        "dupont-aignan",
    ],
    "Édouard Philippe": [
        "édouard philippe",
        "edouard philippe",
    ],
    "Gabriel Attal": [
        "gabriel attal",
        "attal",
    ],
    "Bruno Retailleau": [
        "bruno retailleau",
        "retailleau",
    ],
    "Jean-Luc Mélenchon": [
        "jean-luc mélenchon",
        "jean-luc melenchon",
        "mélenchon",
        "melenchon",
    ],
    "Marine Le Pen": [
        "marine le pen",
        "le pen",
    ],
    "Fabien Roussel": [
        "fabien roussel",
    ],
    "Éric Zemmour": [
        "éric zemmour",
        "eric zemmour",
        "zemmour",
    ],
}
for source_journalistique in SOURCES_JOURNALISTIQUES:
    nom_source = source_journalistique["nom"]
    url_source = source_journalistique["url"]

    try:
        body_source = fetch(url_source)

        liens = re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            body_source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        nombre_detecte = 0
        # Articles réellement retenus pendant CETTE mise à jour.
        nouvelles_detections_source = []
        for url_article, titre_html in liens:
            titre_article = clean_text(titre_html).strip()

            if not titre_article:
                continue

            texte_test = titre_article.lower()

            if not any(
                mot.lower() in texte_test
                for mot in MOTS_CLES_POLITIQUES
            ):
                continue

            if url_article.startswith("/"):
                domaine = re.match(
                    r"(https?://[^/]+)",
                    url_source
                )
            url_article = urljoin(url_source, url_article)
        # --------------------------------------------------
        # FILTRE GLOBAL DES URL NON EDITORIALES
        # --------------------------------------------------
        
        url_minuscule = url_article.lower()
        
        chemins_non_editoriaux = [
            "/tag/",
            "/tags/",
            "/categorie/",
            "/category/",
            "/auteur/",
            "/author/",
            "/recherche/",
            "/search/",
            "/newsletter",
            "/podcasts",
            "/mentions-legales",
            "/mentions_legales",
            "/contact",
            "/confidentialite",
            "/confidentiality",
            "/politique-de-confidentialite",
            "/privacy",
            "/cookies",
            "/cookie",
            "/abonnement",
            "/abonnements",
            "/abonner",
            "/subscribe",
            "/subscription",
            "/connexion",
            "/login",
            "/compte",
            "/account",
            "/faq",
            "/qui-sommes-nous",
            "/a-propos",
        ]
        
        if any(
            chemin in url_minuscule
            for chemin in chemins_non_editoriaux
        ):
            continue
                        # --------------------------------------------------
            # Filtrage des URL : on privilégie les vrais articles
            # et on écarte les pages techniques ou de navigation.
            # --------------------------------------------------

            if not url_article.startswith("http"):
                continue

            url_minuscule = url_article.lower()

            # Pages génériques qui ne correspondent normalement
            # pas à un article journalistique individuel.
            chemins_exclus = [
            "/tag/",
            "/tags/",
            "/categorie/",
            "/category/",
            "/auteur/",
            "/author/",
            "/recherche/",
            "/search/",
            "/newsletter",
            "/podcasts",
            "/mentions-legales",
            "/mentions_legales",
            "/contact",
            "/confidentialite",
            "/confidentiality",
            "/politique-de-confidentialite",
            "/privacy",
            "/cookies",
            "/cookie",
            "/abonnement",
            "/abonnements",
            "/abonner",
            "/subscribe",
            "/subscription",
            "/connexion",
            "/login",
            "/compte",
            "/account",
            "/faq",
            "/qui-sommes-nous",
            "/a-propos",
            "/about",
            "/mot-cle/",
            "/mot-cles/",
        ]

            if any(
                chemin in url_minuscule
                for chemin in chemins_exclus
            ):
                continue

            # Mediapart : le Club et les blogs sont des espaces
            # de contribution distincts des articles du Journal.
            if (
                nom_source == "Mediapart"
                and (
                    "/blogs.mediapart.fr/" in url_minuscule
                    or "/club/" in url_minuscule
                )
            ):
                continue

            # Disclose : exclusion supplémentaire de ses pages
            # d'index thématiques.
            if (
                nom_source == "Disclose"
                and "/news/tag/" in url_minuscule
            ):
                continue
                        # --------------------------------------------------
        # ANALYSE DU CONTENU DE L'ARTICLE
        # --------------------------------------------------

            texte_article = extraire_texte_article(url_article)
            if "blast-info.fr" in url_article:
                print("DEBUG ETAPE BLAST: extraction OK")
            if "blast-info.fr" in url_article:
                print(
                    "DEBUG BLAST:",
                    url_article,
                    "LONGUEUR TEXTE:",
                    len(texte_article),
                    "DEBUT:",
                    repr(texte_article[:500])
                )
            
            # Le titre reste pris en compte, mais l'analyse porte
            # également sur le contenu de l'article.
            texte_analyse = (
                titre_article + " " + texte_article
            ).lower()
            if "blast-info.fr" in url_article:
                print("DEBUG ETAPE BLAST: texte_analyse OK")
            # Indices explicites de contexte électoral.
            mots_contexte_electoral = [
            "présidentielle",
            "présidentiel",
            "présidentielle 2027",
            "élection présidentielle",
            "candidat",
            "candidate",
            "candidature",
            "campagne présidentielle",
        ]

            contexte_electoral = any(
            mot in texte_analyse
            for mot in mots_contexte_electoral
        )

            if "blast-info.fr" in url_article:
                print(
                    "DEBUG ETAPE BLAST: contexte OK",
                    contexte_electoral
                )
        
            # Personnes explicitement mentionnées.
            if "blast-info.fr" in url_article:
                print("DEBUG ETAPE BLAST: AVANT dictionnaire")
            print("DEBUG ABSOLU: JUSTE AVANT AFFECTATION", url_article)                
            candidats_recherches = {
            "Nicolas Dupont-Aignan": [
                "nicolas dupont-aignan",
                "dupont-aignan",
            ],
            "Édouard Philippe": [
                "édouard philippe",
                "edouard philippe",
            ],
            "Gabriel Attal": [
                "gabriel attal",
                "attal",
            ],
            "Bruno Retailleau": [
                "bruno retailleau",
                "retailleau",
            ],
            "Jean-Luc Mélenchon": [
                "jean-luc mélenchon",
                "jean-luc melenchon",
                "mélenchon",
                "melenchon",
            ],
            "Marine Le Pen": [
                "marine le pen",
                "le pen",
            ],
            "Fabien Roussel": [
                "fabien roussel",
            ],
            "Éric Zemmour": [
                "éric zemmour",
                "eric zemmour",
                "zemmour",
            ],
        }
        print("DEBUG ABSOLU: APRES DICTIONNAIRE", url_article)

        if "blast-info.fr" in url_article:
            print("DEBUG ETAPE BLAST: APRES dictionnaire")
        if "blast-info.fr" in url_article:
            print("DEBUG ETAPE BLAST: dictionnaire candidats OK")
        candidats_mentions = []
        if "blast-info.fr" in url_article:
            print("DEBUG ETAPE BLAST: candidats_mentions OK")
        if "blast-info.fr" in url_article:
            print("DEBUG ETAPE BLAST: candidats initialisés")

        for candidat, variantes in candidats_recherches.items():
            if any(
                variante in texte_analyse
                for variante in variantes
            ):
                candidats_mentions.append(candidat)
            if "blast-info.fr" in url_article:
                print(
            "DEBUG FILTRE BLAST:",
            "TITRE:", titre_article,
            "CONTEXTE:", contexte_electoral,
            "CANDIDATS:", candidats_mentions,
            "MOTS_ELECTORAUX:",
            [
                mot for mot in mots_contexte_electoral
                if mot in texte_analyse
            ],
        )
        # On conserve uniquement les articles présentant
        # un contexte électoral explicite ou mentionnant
        # explicitement une personne surveillée.
        #
        # Il s'agit uniquement d'une détection destinée
        # à la validation humaine.
        if not contexte_electoral and not candidats_mentions:
            if "blast-info.fr" in url_article:
                print(
                    "DEBUG BLAST REJETE:",
                    titre_article,
                    "CONTEXTE ELECTORAL:",
                    contexte_electoral,
                    "CANDIDATS:",
                    candidats_mentions,
                )
            continue
        # Pré-classement indicatif pour faciliter la vérification humaine.
        # Cette qualification n'est jamais publiée automatiquement.
        themes = []

        mots_cles_themes = {
                "École": [
                    "école", "éducation", "enseignant",
                    "enseignante", "élève", "collège", "lycée",
                ],
                "Santé": [
                    "santé", "hôpital", "médecin",
                    "soins", "sécurité sociale",
                ],
                "Énergie": [
                    "énergie", "électricité", "nucléaire",
                    "gaz", "énergétique",
                ],
                "Fiscalité": [
                    "impôt", "impôts", "fiscalité",
                    "taxe", "taxes",
                ],
                "Écologie": [
                    "écologie", "climat", "environnement",
                    "pollution", "biodiversité",
                ],
                "Handicap / AESH": [
                    "handicap", "aesh", "inclusion scolaire",
                    "école inclusive",
                ],
            }

        titre_pour_themes = titre_article.lower()

        for theme, mots_cles in mots_cles_themes.items():
            if any(
                mot in titre_pour_themes
                for mot in mots_cles
            ):
                themes.append(theme)
        titre_minuscule = titre_article.lower()

        if any(
            mot in titre_minuscule
            for mot in [
                "enquête",
                "investigation",
                "révélations",
                "révélation",
            ]
        ):
            nature = "enquête potentielle"
        
        elif any(
            mot in titre_minuscule
            for mot in [
                "entretien",
                "interview",
                "déclare",
                "affirme",
                "estime",
            ]
        ):
            nature = "déclaration ou entretien potentiel"
        
        elif any(
            mot in titre_minuscule
            for mot in [
                "analyse",
                "décryptage",
                "décryptons",
            ]
        ):
            nature = "analyse potentielle"
        
        else:
            nature = "actualité à qualifier"
                            # Identification indicative des candidats mentionnés
            # dans le titre. Aucun nom n'est ajouté par déduction.
            candidats_mentions = []

            candidats_recherches = {
                "Nicolas Dupont-Aignan": [
                    "nicolas dupont-aignan",
                    "dupont-aignan",
                ],
                "Édouard Philippe": [
                    "édouard philippe",
                    "edouard philippe",
                ],
                "Gabriel Attal": [
                    "gabriel attal",
                    "attal",
                ],
                "Bruno Retailleau": [
                    "bruno retailleau",
                    "retailleau",
                ],
                "Jean-Luc Mélenchon": [
                    "jean-luc mélenchon",
                    "jean-luc melenchon",
                    "mélenchon",
                    "melenchon",
                ],
                "Marine Le Pen": [
                    "marine le pen",
                    "le pen",
                ],
                "Fabien Roussel": [
                    "fabien roussel",
                ],
                "Éric Zemmour": [
                    "éric zemmour",
                    "eric zemmour",
                    "zemmour",
                ],
            }

            titre_pour_candidats = titre_article.lower()

            for candidat, variantes in candidats_recherches.items():
                if any(
                    variante in titre_pour_candidats
                    for variante in variantes
                ):
                    candidats_mentions.append(candidat)
        resume_article = creer_resume_article(texte_article)

        if "blast-info.fr" in url_article:
            print(
                "DEBUG RESUME BLAST:",
                "LONGUEUR:",
                len(resume_article or ""),
                "RESUME:",
                repr(resume_article)
            )

        nouvelle_detection = {
            "type": source_journalistique["type"],
            "source": nom_source,
            "nature": nature,
            "themes": themes,
            "candidats_mentions": candidats_mentions,
            "titre": titre_article,
            "url": url_article,
            "resume": resume_article,
            "date_detection": date_fr,
            "statut": "À vérifier manuellement",
            "publication_automatique": False,
            "note": (
                "Détection provenant d'une source "
                "journalistique indépendante ou "
                "d'investigation. Vérifier le contenu, "
                "la nature de l'article (information, "
                "enquête, analyse, entretien ou opinion) "
                "et recouper les affirmations sensibles "
                "avant toute publication."
            ),
        }

        ajouter_detection(
            detections,
            nouvelle_detection,
        )

        nouvelles_detections_source.append(
            nouvelle_detection
        )

        nombre_detecte += 1

        # Évite qu'une page très chargée produise
        # trop de détections lors d'une seule exécution.
        if nombre_detecte >= 20:
            break
    
        status["sources"][
            nom_source.lower().replace(" ", "_")
        ] = {
                "ok": True,
                "url": url_source,
                "detections": nombre_detecte,
                "publication_automatique": False,
                "raison": (
                    "Veille journalistique uniquement. "
                    "Validation humaine obligatoire."
                ),
            }
        

        status["sources"][
            nom_source.lower().replace(" ", "_")
        ]["mise_a_jour"] = {
            "nombre": len(nouvelles_detections_source),
            "articles": [
                {
                    "titre": detection.get("titre", ""),
                    "resume": detection.get("resume", ""),
                    "nature": detection.get(
                        "nature",
                        "actualité à qualifier"
                    ),
                    "themes": detection.get("themes", []),
                    "candidats_mentions": detection.get(
                        "candidats_mentions",
                        []
                    ),
                    "url": detection.get("url", ""),
                }
                for detection in nouvelles_detections_source[-5:]
            ],
        }
    except Exception as exc:
        print("DEBUG ERREUR SOURCE:", nom_source, repr(exc))
        status["sources"][
            nom_source.lower().replace(" ", "_")
        ] = {
            "ok": False,
            "url": url_source,
            "publication_automatique": False,
            "erreur": str(exc),
        }


# ------------------------------------------------------------
# SOURCES AFFICHÉES SUR LE SITE
# ------------------------------------------------------------

election["sources"] = [
    {
        "nom": "Commission des sondages",
        "description": (
            "Notices officielles relatives aux sondages. "
            "La rubrique 2027 peut aussi contenir des enquêtes "
            "thématiques : elles sont vérifiées avant publication."
        ),
        "url": COMMISSION_URL
    },
    {
        "nom": "Verian",
        "description": (
            "Publications et études de Verian. "
            "Les nouvelles études détectées sont placées "
            "en attente de vérification."
        ),
        "url": VERIAN_URL
    }
]


# ------------------------------------------------------------
# ÉCRITURE DES FICHIERS
# ------------------------------------------------------------
# On conserve l'historique, tout en évitant que le fichier
# ne grossisse indéfiniment. On garde les 500 détections
# les plus récentes.
detections = detections[-500:]
# ------------------------------------------------------------
# File de validation éditoriale
# ------------------------------------------------------------
# Cette file est uniquement une aide au contrôle humain.
# Elle ne modifie jamais les programmes ni les actualités publiées.

# On recharge la file existante afin de préserver
# les décisions éditoriales prises manuellement.
validations_existantes = charger_json(
    validation_file,
    []
)

if not isinstance(validations_existantes, list):
    validations_existantes = []

validations_par_url = {}

for validation in validations_existantes:
    url_validation = validation.get("url")

    if url_validation:
        validations_par_url[url_validation] = validation

a_valider = []

for detection in detections:
    url_detection = detection.get("url", "").lower()

    # Nettoyage de la file éditoriale.
    chemins_exclus_validation = [
        "/tag/",
        "/tags/",
        "/categorie/",
        "/category/",
        "/auteur/",
        "/author/",
        "/recherche/",
        "/search/",
        "/newsletter",
        "/mentions-legales",
        "/contact",
        "/blogs.mediapart.fr/",
        "/club/",
    ]

    if any(
        chemin in url_detection
        for chemin in chemins_exclus_validation
    ):
        continue

    # Les rubriques Mediapart ne sont pas des articles individuels.
    if (
        detection.get("source") == "Mediapart"
        and re.fullmatch(
            r"https?://(www\.)?mediapart\.fr/journal/[^/]+/?",
            url_detection
        )
    ):
        continue

    if detection.get("publication_automatique") is not False:
        continue

    if not detection.get("source"):
        continue

    if not detection.get("titre"):
        continue

    if not detection.get("url"):
        continue

    validation_precedente = validations_par_url.get(
        detection.get("url"),
        {}
    )

    statut_precedent = validation_precedente.get(
        "statut",
        "À vérifier manuellement"
    )

    # Seuls ces statuts éditoriaux sont conservés.
    statuts_autorises = [
        "À vérifier manuellement",
        "Retenu",
        "Écarté",
    ]

    if statut_precedent not in statuts_autorises:
        statut_precedent = "À vérifier manuellement"

    entree_validation = {
        "source": detection.get("source"),
        "titre": detection.get("titre"),
        "url": detection.get("url"),
        "resume": detection.get("resume", ""),
        "date_detection": detection.get("date_detection"),
        "nature": detection.get(
            "nature",
            "actualité à qualifier"
        ),
        "themes": detection.get("themes", []),
        "candidats_mentions": detection.get(
            "candidats_mentions",
            []
        ),
        "statut": statut_precedent,
        "publication_automatique": statut_precedent == "Retenu",
    }

    a_valider.append(entree_validation)

# Les détections les plus récentes sont placées en premier
# pour faciliter la vérification éditoriale.
a_valider.reverse()

# Limite raisonnable pour garder le fichier lisible.
a_valider = a_valider[:100]
ecrire_json(
    election_file,
    election
)
ecrire_json(
    validation_file,
    a_valider
)

ecrire_json(
    detections_file,
    detections
)

ecrire_json(
    detections_file,
    detections
)

ecrire_json(
    status_file,
    status
)

print(
    json.dumps(
        status,
        ensure_ascii=False
    )
)
