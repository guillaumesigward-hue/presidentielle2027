from pathlib import Path
from datetime import datetime, timezone
import html
import json
import re
import urllib.request

ROOT = Path(__file__).resolve().parent

COMMISSION_URL = (
    "https://www.commission-des-sondages.fr/notices/medias/"
    "fichiers/bytag/14/2027-Presidentielle"
)

VERIAN_URL = "https://www.veriangroup.com/fr/news-and-insights"


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Presidentielle2027SourceMonitor/4.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


now = datetime.now(timezone.utc)

months = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

date_fr = f"{now.day} {months[now.month - 1]} {now.year}"

data_dir = ROOT / "data"
data_dir.mkdir(exist_ok=True)

election_file = data_dir / "election.json"

if election_file.exists():
    election = json.loads(
        election_file.read_text(encoding="utf-8")
    )
else:
    election = {
        "titre": "Présidentielle française 2027",
        "candidatures": [],
        "sondages": [],
        "programmes": [],
        "actualites": [],
        "sources": []
    }

election["derniere_mise_a_jour"] = date_fr

status = {
    "last_checked_utc": now.isoformat(),
    "last_checked_fr": date_fr,
    "sources": {}
}


# --------------------------------------------------
# COMMISSION DES SONDAGES
# --------------------------------------------------

try:
    body = fetch(COMMISSION_URL)

    notices = []
    seen = set()

    pattern = re.compile(
        r"(102\d{2})\s+([^<\r\n]+)",
        re.IGNORECASE
    )

    for match in pattern.finditer(body):
        notice_id = match.group(1)
        title = clean_text(match.group(2))

        if notice_id not in seen:
            seen.add(notice_id)
            notices.append({
                "id": notice_id,
                "titre": title
            })

    notices.sort(
        key=lambda item: item["id"],
        reverse=True
    )

    status["sources"]["commission_sondages"] = {
        "ok": True,
        "url": COMMISSION_URL,
        "notices_trouvees": len(notices),
        "latest_notice_id": (
            notices[0]["id"] if notices else None
        ),
        "publication_automatique": False,
        "raison": (
            "La rubrique présidentielle contient aussi "
            "des enquêtes thématiques. Une notice n'est "
            "donc pas automatiquement une intention de vote."
        )
    }

except Exception as exc:
    status["sources"]["commission_sondages"] = {
        "ok": False,
        "url": COMMISSION_URL,
        "error": str(exc)[:180]
    }


# --------------------------------------------------
# INTENTIONS DE VOTE
# --------------------------------------------------
#
# Aucune enquête n'est ajoutée automatiquement ici
# tant qu'elle n'est pas explicitement identifiée
# comme une intention de vote présidentielle.
#

election.setdefault("sondages", [])


# --------------------------------------------------
# VERIAN
# --------------------------------------------------

try:
    verian_body = fetch(VERIAN_URL)

    status["sources"]["verian"] = {
        "ok": True,
        "url": VERIAN_URL,
        "bytes": len(verian_body)
    }

except Exception as exc:
    verian_body = ""

    status["sources"]["verian"] = {
        "ok": False,
        "url": VERIAN_URL,
        "error": str(exc)[:180]
    }


# --------------------------------------------------
# ACTUALITES / ETUDES RECENTES
# --------------------------------------------------
#
# On publie ici uniquement des intitulés descriptifs
# accompagnés d'un lien vers la source.
#

actualites = []

if verian_body:
    verian_lower = clean_text(verian_body).lower()

    if (
        "stature présidentielle" in verian_lower
        and "vague 5" in verian_lower
    ):
        actualites.append({
            "titre": (
                "Baromètre de la stature présidentielle "
                "des candidats potentiels — vague 5"
            ),
            "description": (
                "Étude Verian publiée en septembre 2026 "
                "sur la perception de candidats potentiels "
                "à l'élection présidentielle."
            ),
            "source": "Verian",
            "url": (
                "https://www.veriangroup.com/fr/news-and-insights/"
                "la-stature-pr%C3%A9sidentielle-de-candidats-"
                "potentiels-%C3%A0-la-prochaine-%C3%A9lection-"
                "pr%C3%A9sidentielle-vague-5"
            )
        })

    if (
        "baromètre politique verian" in verian_lower
        and "septembre 2026" in verian_lower
    ):
        actualites.append({
            "titre": (
                "Baromètre politique Verian — septembre 2026"
            ),
            "description": (
                "Baromètre mensuel de Verian. "
                "Il ne doit pas être confondu avec un "
                "sondage d'intentions de vote."
            ),
            "source": "Verian",
            "url": (
                "https://www.veriangroup.com/fr/news-and-insights/"
                "barom%C3%A8tre-politique-verian-pour-le-"
                "figaro-magazine-septembre-2026"
            )
        })

election.setdefault("actualites", [])

urls_existantes = {
    item.get("url")
    for item in election["actualites"]
    if item.get("url")
}

for actualite in actualites:
    if actualite.get("url") not in urls_existantes:
        election["actualites"].append(actualite)
        urls_existantes.add(actualite.get("url"))


# --------------------------------------------------
# CANDIDATURES
# --------------------------------------------------
#
# Cette rubrique reste vide tant qu'une collecte
# spécifique de déclarations de candidature,
# avec sources individualisées, n'est pas mise
# en place.
#

election.setdefault("candidatures", [])


# --------------------------------------------------
# SOURCES
# --------------------------------------------------

election["sources"] = [
    {
        "nom": "Commission des sondages",
        "url": COMMISSION_URL,
        "type": "contrôle et notices de sondages"
    },
    {
        "nom": "Verian",
        "url": VERIAN_URL,
        "type": "études d'opinion"
    }
]


# --------------------------------------------------
# ENREGISTREMENT
# --------------------------------------------------

election_file.write_text(
    json.dumps(
        election,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

(data_dir / "status.json").write_text(
    json.dumps(
        status,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(json.dumps(status, ensure_ascii=False))
