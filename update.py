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
        headers={"User-Agent": "Presidentielle2027SourceMonitor/3.0"}
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
    election = json.loads(election_file.read_text(encoding="utf-8"))
else:
    election = {
        "titre": "Présidentielle française 2027",
        "candidatures": [],
        "sondages": [],
        "actualites": [],
        "sources": []
    }

election["derniere_mise_a_jour"] = date_fr

status = {
    "last_checked_utc": now.isoformat(),
    "last_checked_fr": date_fr,
    "sources": {}
}

# Commission des sondages
#
# La rubrique "2027 - Présidentielle" contient aussi des enquêtes
# thématiques. Elles ne doivent pas être présentées automatiquement
# comme des intentions de vote.
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
                "titre": title,
                "source": "Commission des sondages",
                "url": COMMISSION_URL
            })

    notices.sort(key=lambda item: item["id"], reverse=True)

    # On conserve les notices comme éléments de contrôle de la source.
    # On ne les publie PAS comme intentions de vote.
    election["sondages"] = []

    status["sources"]["commission_sondages"] = {
        "ok": True,
        "url": COMMISSION_URL,
        "notices_trouvees": len(notices),
        "latest_notice_id": notices[0]["id"] if notices else None,
        "publication_automatique": False,
        "raison": (
            "La rubrique contient aussi des enquêtes thématiques ; "
            "les intentions de vote doivent être identifiées séparément."
        )
    }

except Exception as exc:
    election["sondages"] = []

    status["sources"]["commission_sondages"] = {
        "ok": False,
        "url": COMMISSION_URL,
        "error": str(exc)[:180]
    }


# Vérification de la source Verian
try:
    body = fetch(VERIAN_URL)

    status["sources"]["verian"] = {
        "ok": True,
        "url": VERIAN_URL,
        "bytes": len(body)
    }

except Exception as exc:
    status["sources"]["verian"] = {
        "ok": False,
        "url": VERIAN_URL,
        "error": str(exc)[:180]
    }


election["sources"] = [
    {
        "nom": "Commission des sondages",
        "url": COMMISSION_URL,
        "type": "contrôle et notices de sondages"
    },
    {
        "nom": "Verian",
        "url": VERIAN_URL,
        "type": "études et sondages"
    }
]

election_file.write_text(
    json.dumps(election, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

(data_dir / "status.json").write_text(
    json.dumps(status, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(status, ensure_ascii=False))
