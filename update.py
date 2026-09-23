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

ecrire_json(
    election_file,
    election
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
