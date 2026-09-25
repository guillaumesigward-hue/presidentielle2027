from pathlib import Path
from datetime import datetime, timezone
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
    Une détection n'est jamais publiée automatiquement.
    """
    cle = (
        detection.get("type"),
        detection.get("titre"),
        detection.get("url")
    )

    for element in collection:
        cle_existante = (
            element.get("type"),
            element.get("titre"),
            element.get("url")
        )

        if cle_existante == cle:
            return

    collection.append(detection)


DATA_DIR.mkdir(exist_ok=True)

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
                if domaine:
                    url_article = (
                        domaine.group(1) + url_article
                    )

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
                "/contact",
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
            ajouter_detection(
                detections,
                   {
                    "type": source_journalistique["type"],
                    "source": nom_source,
                    "nature": nature,
                    "themes": themes,
                    "candidats_mentions": candidats_mentions,
                    "titre": titre_article,
                    "url": url_article,
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
                },
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

    except Exception as exc:
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
        "publication_automatique": False,
    }

    a_valider.append(entree_validation)

# Les détections les plus récentes sont placées en premier
# pour faciliter la vérification éditoriale.
a_valider.reverse()

# Limite raisonnable pour garder le fichier lisible.
a_valider = a_valider[:100]

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
