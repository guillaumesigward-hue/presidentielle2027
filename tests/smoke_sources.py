"""Essai réseau volontaire et limité, dans .preview ; jamais exécuté par la CI."""
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

data = update.ROOT / '.preview' / 'data'
data.mkdir(parents=True, exist_ok=True)
for file in update.DATA_DIR.glob('*.json'):
    shutil.copy2(file, data / file.name)
with patch.object(update, 'DATA_DIR', data), patch.object(veille, 'MAX_ARTICLES_PAR_SOURCE', 2), contextlib.redirect_stdout(io.StringIO()):
    update.main()
status = json.loads((data / 'status.json').read_text(encoding='utf-8'))
for nom, source in status['sources'].items():
    print(nom, json.dumps({key: value for key, value in source.items()
                           if key in ('ok', 'erreur', 'liens_trouves', 'liens_examines', 'extractions_vides', 'detections', 'notices_detectees')}, ensure_ascii=False))
