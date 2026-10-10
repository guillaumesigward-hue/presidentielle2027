"""Essai réseau isolé, jamais exécuté par la CI de contrôle."""
import argparse
import hashlib
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import update
import veille

parser = argparse.ArgumentParser()
parser.add_argument('--max-articles', type=int, default=20)
args = parser.parse_args()

data = update.ROOT / '.preview' / 'data'
data.mkdir(parents=True, exist_ok=True)
for file in update.DATA_DIR.glob('*.json'):
    shutil.copy2(file, data / file.name)
pages = update.ROOT / '.preview' / 'pages'
pages.mkdir(parents=True, exist_ok=True)
original_fetch = update.fetch
index = []
def fetch_snapshot(url):
    body = original_fetch(url)
    filename = hashlib.sha256(url.encode()).hexdigest() + '.html'
    (pages / filename).write_text(body, encoding='utf-8')
    index.append({'url': url, 'file': filename})
    return body

with patch.object(update, 'DATA_DIR', data), patch.object(veille, 'MAX_ARTICLES_PAR_SOURCE', args.max_articles), patch.object(update, 'fetch', fetch_snapshot), contextlib.redirect_stdout(io.StringIO()):
    update.main()
(pages / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
status = json.loads((data / 'status.json').read_text(encoding='utf-8'))
for nom, source in status['sources'].items():
    print(nom, json.dumps({key: value for key, value in source.items()
                           if key in ('ok', 'erreur', 'liens_trouves', 'liens_examines', 'extractions_vides', 'detections', 'notices_detectees')}, ensure_ascii=False))
