import json
from pathlib import Path
import tempfile
import unittest

from analyse_actualites import analyser_actualite, enrichir_actualites, enrichir_syntheses, VERSION
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
        self.assertEqual(len(point['analyse_par_sujet']), 11)
        ecole = next(x for x in point['analyse_par_sujet'] if x['theme'] == 'École et jeunesse')
        immigration = next(x for x in point['analyse_par_sujet'] if x['theme'] == 'Immigration')
        self.assertEqual(ecole['statut'], 'aborde')
        self.assertIn('enseignants', ecole['constat'])
        self.assertTrue(ecole['elements'])
        self.assertTrue(all('Information relevée' not in x for x in ecole['elements']))
        self.assertEqual(immigration['statut'], 'non_aborde')
        self.assertEqual(immigration['elements'], [])
        self.assertEqual(immigration['constat'], 'Sujet non abordé dans cette information.')

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
            self.assertTrue(all(len(x['point_reflexion'].get('analyse_par_sujet', [])) == 11
                                for x in election['actualites']))
            self.assertTrue(election['syntheses_campagne'])
            self.assertTrue(all(x.get('point_reflexion', {}).get('version') == VERSION
                                for x in election['syntheses_campagne']))
            self.assertTrue(all(len(x['point_reflexion'].get('analyse_par_sujet', [])) == 11
                                for x in election['syntheses_campagne']))

    def test_bourget_recoit_une_analyse_complete(self):
        syntheses = json.loads((update.DATA_DIR / 'syntheses_campagne.json').read_text(encoding='utf-8'))
        bourget = next(x for x in syntheses if 'Bourget' in x.get('titre', ''))
        enrichir_syntheses([bourget], self.programmes)
        point = bourget['point_reflexion']
        self.assertEqual(point['version'], VERSION)
        for theme in ('École et jeunesse', 'Finances publiques et financement',
                      'Santé et protection sociale', 'Travail, retraites et pouvoir d’achat',
                      'Énergie et industrie', 'Écologie et climat', 'International et défense'):
            self.assertIn(theme, point['themes_concernes'])
        self.assertIn('Cette synthèse', point['apport'])
        self.assertTrue(point['questions'])
        self.assertEqual(len(point['analyse_par_sujet']), 11)
        fiscalite = next(x for x in point['analyse_par_sujet'] if x['theme'] == 'Fiscalité')
        self.assertEqual(fiscalite['libelle_statut'], 'Sujet non abordé')
        finances = next(x for x in point['analyse_par_sujet']
                        if x['theme'] == 'Finances publiques et financement')
        ecole = next(x for x in point['analyse_par_sujet'] if x['theme'] == 'École et jeunesse')
        self.assertTrue(finances['elements'])
        self.assertTrue(all('Le projet présenté' not in x and 'Les mesures concrètes' not in x
                            for x in finances['elements']))
        self.assertTrue(any('cantines biologiques gratuites' in x for x in ecole['elements']))
        self.assertTrue(all('médicament' not in x for x in ecole['elements']))


if __name__ == '__main__':
    unittest.main()
