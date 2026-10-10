"""Prépare un site public sans exposer la file éditoriale ni les extraits de veille."""
import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CHAMPS_SUIVI = ('ok', 'url', 'notices_detectees', 'detections', 'liens_examines',
                'extractions_vides', 'etat_extraction')


def preparer_site(output, data_dir=None):
    data_dir = Path(data_dir or ROOT / 'data')
    election = json.loads((data_dir / 'election.json').read_text(encoding='utf-8'))
    programmes = json.loads((data_dir / 'programmes.json').read_text(encoding='utf-8'))
    status = json.loads((data_dir / 'status.json').read_text(encoding='utf-8'))
    for champ in ('candidatures', 'sondages', 'actualites', 'sources'):
        if not isinstance(election.get(champ), list) or any(not isinstance(x, dict) for x in election[champ]):
            raise ValueError(f'election.json : structure incorrecte pour {champ}')
    if not isinstance(programmes.get('pretendants'), list):
        raise ValueError('programmes.json : prétendants manquants')
    if status.get('publication_automatique') is not False or not isinstance(status.get('sources'), dict):
        raise ValueError('status.json : garanties de veille absentes')
    suivi = {key: status.get(key) for key in ('last_checked_utc', 'last_checked_fr')}
    suivi['publication_automatique'] = False
    suivi['sources'] = {nom: {key: source[key] for key in CHAMPS_SUIVI if key in source}
                        for nom, source in status['sources'].items()}
    output = Path(output)
    # Un dossier existant pourrait exposer des anciens fichiers non prévus.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'data').mkdir()
    shutil.copy2(ROOT / 'index.html', output / 'index.html')
    for name in ('election.json', 'programmes.json'):
        shutil.copy2(data_dir / name, output / 'data' / name)
    (output / 'data' / 'suivi.json').write_text(
        json.dumps(suivi, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return suivi


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    parser.add_argument('--data-dir', default=str(ROOT / 'data'))
    args = parser.parse_args()
    preparer_site(args.output, args.data_dir)
