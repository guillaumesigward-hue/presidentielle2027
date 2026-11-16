import json
from pathlib import Path
import tempfile
import unittest

from analyse_actualites import analyser_actualite, enrichir_actualites, VERSION
from construire_site import preparer_site
import update


class AnalyseActualitesTests(unittest.TestCase):
    def setUp(self):
        self.programmes = {'pretendants': [{'nom': 'Gabriel Attal', 'themes': {
            'ecole': {'statut': 'Propositions documentées'},
            'sante': {}, 'energie': {}, 'fiscalite': {}, 'ecologie': {}}}]}

    def test_proposition_ecole_chiffree_et_financee(self):
        item = {'titre': 'Gabriel Attal propose 200 euros pour les enseignants',
                'description': 'La mesure coûterait 2,5 milliards et serait financée par des économies budgétaires.',
                'candidats_mentions': ['Gabriel Attal'], 'themes': ['École']}
        point = analyser_actualite(item, self.programmes)
        self.assertEqual(point['version'], VERSION)
        self.assertIn('École et jeunesse', point['themes_concernes'])
        self.assertIn('Finances publiques et financement', point['themes_concernes'])
        self.assertIn('fiche programme', point['comparaison_programme'])
        self.assertIn('coût net', point['finances_publiques'])
        self.assertTrue(any('déficit' in question for question in point['questions']))
        self.assertNotIn('École et jeunesse', point['themes_non_documentes'])

    def test_prise_de_position_signale_les_limites(self):
        point = analyser_actualite({'titre': 'Marine Le Pen prend position sur la Russie et l’Ukraine',
            'description': 'Elle réagit à une réunion diplomatique.',
            'candidats_mentions': ['Marine Le Pen']}, {'pretendants': []})
        self.assertEqual(point['nature'], 'Prise de position ou élément de contexte')
        self.assertIn('portée programmatique limitée', point['niveau'])
        self.assertIn('International et défense', point['themes_concernes'])
        self.assertIn('Aucun chiffrage', point['finances_publiques'])
        self.assertEqual(set(point['themes_non_documentes']), set([
            'École et jeunesse', 'Finances publiques et financement',
            'Santé et protection sociale', 'Énergie et industrie',
            'Fiscalité', 'Écologie et climat']))

    def test_enrichissement_remplace_une_ancienne_analyse(self):
        items = [{'titre': 'Éric Zemmour confirme sa candidature',
                  'description': 'Déclaration pour 2027.',
                  'candidats_mentions': ['Éric Zemmour'],
                  'point_reflexion': {'version': 'ancienne'}}]
        enrichir_actualites(items, {'pretendants': []})
        self.assertEqual(items[0]['point_reflexion']['version'], VERSION)
        self.assertIn('déficit', items[0]['point_reflexion']['questions'][0].casefold())

    def test_paquet_public_enrichit_toutes_les_actualites(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'; data.mkdir()
            for file in update.DATA_DIR.glob('*.json'):
                (data / file.name).write_bytes(file.read_bytes())
            output = Path(directory) / 'site'
            preparer_site(output, data)
            election = json.loads((output / 'data/election.json').read_text(encoding='utf-8'))
            self.assertTrue(election['actualites'])
            self.assertTrue(all(x.get('point_reflexion', {}).get('version') == VERSION
                                for x in election['actualites']))
            self.assertTrue(all(x['point_reflexion'].get('avis') for x in election['actualites']))


if __name__ == '__main__':
    unittest.main()
