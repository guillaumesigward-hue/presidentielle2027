import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import update
from veille import construire_validation, extraire_html, surveiller_source, url_article_valide


class VeilleTests(unittest.TestCase):
    def test_urls(self):
        source = 'https://www.mediapart.fr/journal/politique'
        valid = '/journal/politique/101026/un-article#section'
        self.assertEqual(url_article_valide(valid, source), source.split('/journal')[0] + valid.split('#')[0])
        for url in ['/confidentialite', '/journal/politique', '/journal/mot-cle/2027',
                    'https://blogs.mediapart.fr/article', '//evil.test/article', 'javascript:alert(1)']:
            self.assertIsNone(url_article_valide(url, source), url)

    def test_extraction_and_metadata_quotes(self):
        text = 'Une proposition concernant les écoles et leur financement est présentée. ' * 5
        self.assertEqual(extraire_html(f'<nav>Marine Le Pen</nav><article><p>{text}</p><script>bad</script></article>'), text.strip())
        html = '<meta content="L\'école et le financement font l\'objet de précisions." property="og:description"><article>Abonnez-vous</article><p>' + text + '</p>'
        self.assertEqual(extraire_html(html), "L'école et le financement font l'objet de précisions.")

    def test_each_article_processed_once_and_source_failure_reported(self):
        source = update.SOURCES_JOURNALISTIQUES[0]
        body = ''.join(f'<a href="/journal/politique/101026/article-{i}">Titre {i}</a>' for i in range(25))
        body += '<a href="/journal/politique/101026/article-0">Doublon</a><a href="/confidentialite">Confidentialité</a>'
        calls, detections = [], []
        def extract(url):
            calls.append(url)
            return 'Gabriel Attal parle du financement de l’école.'
        result = surveiller_source(source, lambda url: body, extract, update.creer_resume_article,
                                  update.candidats_recherches, '10 octobre 2026', update.ajouter_detection, detections)
        self.assertEqual(len(calls), 20)
        self.assertEqual(len(detections), 20)
        self.assertEqual(result['liens_examines'], 20)
        self.assertIn('École', detections[0]['themes'])
        self.assertTrue(all(item['publication_automatique'] is False for item in detections))
        def failed(url):
            raise OSError('indisponible')
        result = surveiller_source(source, failed, extract, str, {}, '', update.ajouter_detection, [])
        self.assertFalse(result['ok'])

    def test_manual_decisions_survive_and_not_automatically_published(self):
        existing = [{'url': 'https://www.blast-info.fr/emissions/2026/ancien', 'statut': 'Retenu',
                     'resume': 'Texte corrigé humainement', 'publication_automatique': False}]
        result = construire_validation([], existing, update.SOURCES_JOURNALISTIQUES)
        self.assertEqual(result, existing)
        duplicate = dict(existing[0], source='Blast', titre='Titre', resume='Robot')
        result = construire_validation([duplicate, duplicate], existing, update.SOURCES_JOURNALISTIQUES)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['resume'], 'Texte corrigé humainement')

    def test_bad_json_is_never_replaced_by_empty_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                update.charger_json(path, [])
            self.assertEqual(path.read_text(), '{broken')

    def test_complete_run_preserves_editorial_content(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            election = json.loads((update.DATA_DIR / 'election.json').read_text(encoding='utf-8'))
            original = copy.deepcopy(election)
            for filename in ['election.json', 'a_valider.json', 'actualites_detectees.json', 'programmes.json']:
                (data / filename).write_bytes((update.DATA_DIR / filename).read_bytes())
            programmes = json.loads((data / 'programmes.json').read_text(encoding='utf-8'))
            with patch.object(update, 'DATA_DIR', data), patch.object(update, 'fetch', return_value=''), contextlib.redirect_stdout(io.StringIO()):
                update.main()
            result = json.loads((data / 'election.json').read_text(encoding='utf-8'))
            result.pop('derniere_mise_a_jour', None)
            original.pop('derniere_mise_a_jour', None)
            for document in (result, original):
                for candidat in document['candidatures']:
                    candidat.pop('dernier_controle_sources', None)
            self.assertEqual(result, original)
            programmes_actualises = json.loads((data / 'programmes.json').read_text(encoding='utf-8'))
            for document in (programmes_actualises, programmes):
                document.pop('dernier_controle_automatique', None)
                for personne in document['pretendants']:
                    for theme in personne.get('themes', {}).values():
                        theme.pop('dernier_controle_sources', None)
            self.assertEqual(programmes_actualises, programmes)
            status = json.loads((data / 'status.json').read_text(encoding='utf-8'))
            self.assertEqual(len(status['sources']), 5)
            self.assertTrue(status['publication_automatique'])
            self.assertTrue(all(not item['publication_automatique'] for item in status['sources'].values()))

    def test_repository_json(self):
        for path in update.DATA_DIR.glob('*.json'):
            json.loads(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
