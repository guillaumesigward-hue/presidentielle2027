from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin
from veille import extraire_html, surveiller_source, construire_validation
import html
import json
import re
import urllib.request
from functools import lru_cache

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


@lru_cache(maxsize=128)
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
    try:
        return extraire_html(fetch(url))
    except Exception as erreur:
        print(f"Extraction impossible {url}: {type(erreur).__name__}: {erreur}")
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
        raise FileNotFoundError(f"Fichier requis absent : {path}")
    contenu = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(contenu, type(valeur_defaut)):
        raise ValueError(f"Structure JSON inattendue : {path}")
    if isinstance(contenu, list) and any(not isinstance(item, dict) for item in contenu):
        raise ValueError(f"Entrée JSON inattendue : {path}")
    return contenu


def ecrire_json(path, contenu):
    texte = json.dumps(contenu, ensure_ascii=False, indent=2) + "\n"
    json.loads(texte)
    temporaire = path.with_suffix(path.suffix + ".tmp")
    temporaire.write_text(texte, encoding="utf-8")
    temporaire.replace(path)


def ajouter_detection(collection, detection):
    """
    Évite les doublons dans la file de détection.
    Si une détection existe déjà, ses nouvelles informations
    sont ajoutées ou mises à jour.
    """
    cle = (
        detection.get("type"),
        detection.get("source") or detection.get("titre"),
        detection.get("url"),
    )

    for element in collection:
        cle_existante = (
            element.get("type"),
            element.get("source") or element.get("titre"),
            element.get("url"),
        )

        if cle_existante == cle:
            for champ, valeur in detection.items():
                if valeur not in (None, "", [], {}):
                    if champ not in ("date_detection", "statut", "publication_automatique"):
                        element[champ] = valeur
            return
    collection.append(detection)
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

candidats_recherches.update({
    'Jordan Bardella': ['jordan bardella', 'bardella'],
    'Raphaël Glucksmann': ['raphaël glucksmann', 'glucksmann'],
    'Marine Tondelier': ['marine tondelier', 'tondelier'],
    'Olivier Faure': ['olivier faure'],
})


def main():
    if hasattr(fetch, 'cache_clear'):
        fetch.cache_clear()
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
        "publication_automatique": True,
        "sources": {}
    }

    # On conserve l'historique des détections déjà enregistrées.
    detections = charger_json(detections_file, [])
    validations_existantes = charger_json(validation_file, [])
    for champ in ("candidatures", "sondages", "programmes", "actualites", "sources"):
        if not isinstance(election.get(champ), list):
            raise ValueError(f"election.json : {champ} doit être une liste")

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

    for source in SOURCES_JOURNALISTIQUES:
        status["sources"][source["nom"].lower().replace(" ", "_")] = surveiller_source(
            source, fetch, extraire_texte_article, creer_resume_article,
            candidats_recherches, date_fr, ajouter_detection, detections,
        )

    # ------------------------------------------------------------
    # SOURCES AFFICHÉES SUR LE SITE
    # ------------------------------------------------------------

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
    a_valider = construire_validation(
        detections, validations_existantes, SOURCES_JOURNALISTIQUES
    )

    # Les pages déjà collectées sont réutilisées grâce au cache du passage courant.
    # La publication devient une construction locale reproductible, sans réseau.
    from automatisation import selectionner_articles
    exclusions = {item['url'] for item in a_valider if item.get('url') and item.get('statut') in ('Rejeté', 'Rejetée', 'Refusé')}
    articles = selectionner_articles(detections, SOURCES_JOURNALISTIQUES, fetch, now, exclusions)
    ecrire_json(DATA_DIR / 'publications_auto.json', {'last_checked_utc': status['last_checked_utc'], 'articles': articles})
    status['publications_par_media'] = {source['nom']: sum(x['source'] == source['nom'] for x in articles) for source in SOURCES_JOURNALISTIQUES}

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
        status_file,
        status
    )

    print(
        json.dumps(
            status,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
