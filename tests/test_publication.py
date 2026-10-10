import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from construire_site import preparer_site
import update


class PublicationTests(unittest.TestCase):
    def test_public_package_excludes_unreviewed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            data.mkdir()
            for file in update.DATA_DIR.glob('*.json'):
                (data / file.name).write_bytes(file.read_bytes())
            status = json.loads((data / 'status.json').read_text(encoding='utf-8'))
            status['sources']['blast'] = {'ok': True, 'etat_extraction': 'partielle',
                'extractions_vides': 6, 'mise_a_jour': {'articles': [{'titre': 'NON VALIDE'}]}}
            (data / 'status.json').write_text(json.dumps(status), encoding='utf-8')
            output = Path(directory) / 'site'
            suivi = preparer_site(output, data)
            self.assertEqual(set(str(p.relative_to(output)).replace('\\', '/') for p in output.rglob('*') if p.is_file()),
                {'index.html', 'data/election.json', 'data/programmes.json', 'data/suivi.json'})
            self.assertNotIn('NON VALIDE', (output / 'data/suivi.json').read_text())
            self.assertNotIn('mise_a_jour', suivi['sources']['blast'])
            self.assertFalse(suivi['publication_automatique'])
            self.assertEqual((output / 'data/programmes.json').read_bytes(), (data / 'programmes.json').read_bytes())

    def test_publication_rejects_disabled_safeguard(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            data.mkdir()
            for file in update.DATA_DIR.glob('*.json'):
                (data / file.name).write_bytes(file.read_bytes())
            status = json.loads((data / 'status.json').read_text(encoding='utf-8'))
            status['publication_automatique'] = True
            (data / 'status.json').write_text(json.dumps(status), encoding='utf-8')
            with self.assertRaises(ValueError):
                preparer_site(Path(directory) / 'site', data)

    def test_two_runs_do_not_duplicate_articles_or_change_human_review(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            for file in update.DATA_DIR.glob('*.json'):
                (data / file.name).write_bytes(file.read_bytes())
            def fetch(url):
                if url == update.SOURCES_JOURNALISTIQUES[0]['url']:
                    return '<a href="/journal/politique/101026/test-veille">Gabriel Attal et la présidentielle</a>'
                return '<article>' + 'Gabriel Attal présente des propositions pour l’école. ' * 8 + '</article>'
            with patch.object(update, 'DATA_DIR', data), patch.object(update, 'fetch', fetch), patch('builtins.print'):
                update.main()
                queue = json.loads((data / 'a_valider.json').read_text(encoding='utf-8'))
                item = next(x for x in queue if x['url'].endswith('/test-veille'))
                item.update(statut='Retenu', resume='Résumé validé humainement')
                (data / 'a_valider.json').write_text(json.dumps(queue), encoding='utf-8')
                update.main()
            result = json.loads((data / 'a_valider.json').read_text(encoding='utf-8'))
            matches = [x for x in result if x['url'].endswith('/test-veille')]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]['resume'], 'Résumé validé humainement')
            self.assertEqual(matches[0]['statut'], 'Retenu')
            self.assertFalse(matches[0]['publication_automatique'])
