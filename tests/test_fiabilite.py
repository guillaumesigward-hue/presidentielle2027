import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from delais import delai_reel, DelaiDepasse
import enregistrer_veille
from resumes_auto import resumer_publications


class Echeances(unittest.TestCase):
    def test_interruption_reelle_et_restauration_du_signal(self):
        precedent = signal.getsignal(signal.SIGALRM)
        debut = time.monotonic()
        with self.assertRaises(DelaiDepasse), delai_reel(0.03):
            time.sleep(1)
        self.assertLess(time.monotonic() - debut, 0.8)
        self.assertEqual(signal.getsignal(signal.SIGALRM), precedent)

    def test_budget_epuise_ne_lance_pas_de_generation(self):
        articles = [{'url': 'https://exemple.fr/test'}]
        with patch.dict(os.environ, {'RESUMES_BUDGET_SECONDES': '0'}):
            bilan = resumer_publications(articles, lambda _: '<article>' + 'Texte accessible. ' * 80 + '</article>',
                                        generate=lambda _: self.fail('Budget déjà épuisé'))
        self.assertEqual(bilan['indisponibles'], 1)
        self.assertIn('reporté', articles[0]['resume_limite'])

    def test_article_interrompu_ne_bloque_pas_les_suivants(self):
        articles = [{'url': 'a'}, {'url': 'b'}]
        appels = []
        def rediger(_):
            appels.append(True)
            if len(appels) == 1:
                raise DelaiDepasse()
            return 'La commune prépare des travaux dans les établissements scolaires. Les familles attendent encore des précisions sur le calendrier annoncé.'
        bilan = resumer_publications(articles, lambda _: '<article>' + 'La mairie rénove les écoles et informe les familles. ' * 20 + '</article>', generate=rediger)
        self.assertEqual(bilan['resumes'], 1)
        self.assertEqual(bilan['indisponibles'], 1)
        self.assertEqual(articles[1]['resume_statut'], 'disponible')

    def test_articles_reportes_prioritaires_sans_changer_ordre_public(self):
        articles = [{'url': 'a'}, {'url': 'b'}]
        ordre = []
        def fetch(url):
            ordre.append(url)
            return ''
        resumer_publications(articles, fetch, [{'url': 'a', 'resume_tente_utc': '2026-10-11'}])
        self.assertEqual(ordre, ['b', 'a'])
        self.assertEqual([x['url'] for x in articles], ['a', 'b'])


class PublicationConcurrente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.remote = root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.local = root / 'local'
        subprocess.run(['git', 'clone', str(self.remote), str(self.local)], check=True, capture_output=True)
        ancien = Path.cwd()
        os.chdir(self.local)
        self.addCleanup(os.chdir, ancien)
        self.git('checkout', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        Path('data').mkdir()
        for fichier in enregistrer_veille.FICHIERS:
            Path(fichier).write_text('{}\n')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')
        self.git('push', '-u', 'origin', 'main')
        self.initial = self.git('rev-parse', 'HEAD')
        self.output = root / 'output'

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True, capture_output=True).stdout.strip()

    def avancer_main(self, path):
        Path(path).write_text('{"manuel": true}\n')
        self.git('add', path)
        self.git('commit', '-m', 'correction humaine')
        self.git('push', 'origin', 'main')
        revision = self.git('rev-parse', 'HEAD')
        self.git('reset', '--hard', self.initial)
        Path('data/status.json').write_text('{"nouveau": true}\n')
        return revision

    def test_rebase_preserve_modification_independante(self):
        self.avancer_main('README.md')
        with patch.object(enregistrer_veille, 'valider') as validation, patch.dict(os.environ, {'GITHUB_OUTPUT': str(self.output)}):
            enregistrer_veille.enregistrer()
        self.assertEqual(Path('README.md').read_text(), '{"manuel": true}\n')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'origin/main'))
        self.assertIn('revision=', self.output.read_text())
        self.assertGreaterEqual(validation.call_count, 2)

    def test_donnees_concurrentes_jamais_ecrasees(self):
        distant = self.avancer_main('data/election.json')
        with patch.object(enregistrer_veille, 'valider'), patch.dict(os.environ, {'GITHUB_OUTPUT': str(self.output)}):
            with self.assertRaisesRegex(RuntimeError, 'Données modifiées'):
                enregistrer_veille.enregistrer()
        self.assertEqual(self.git('rev-parse', 'origin/main'), distant)
        self.assertFalse(self.output.exists())

    def test_validation_echouee_ne_pousse_rien(self):
        Path('data/status.json').write_text('invalide')
        with patch.object(enregistrer_veille, 'valider', side_effect=ValueError('invalide')):
            with self.assertRaises(ValueError):
                enregistrer_veille.enregistrer()
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.initial)
