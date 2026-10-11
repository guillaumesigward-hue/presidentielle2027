import json
import unittest
from veille import PageArticle

class BlastPublic(unittest.TestCase):
    def page(self, scope='PUBLIC', host='www.blast-info.fr'):
        texte = '<p>La commune annonce des travaux dans les écoles et présente le calendrier aux familles.</p>' * 12
        valeurs = [['ShallowReactive', 1], {'data': 2}, ['ShallowReactive', 3], {'story:principal': 4},
                   {'scope': 5, 'canonical_url': 6, 'content_blocks': 7}, scope,
                   'https://' + host + '/articles/2026/exemple', {'blocks': 8}, [9],
                   {'scheme': 10, 'attributes': 11}, 'text', {'source': 12}, texte,
                   {'story:recommandation': 14}, '<p>RECOMMANDATION A EXCLURE</p>']
        return '<meta name="description" content="Description publique suffisamment longue pour être affichée."><script type="application/json" id="__NUXT_DATA__">' + json.dumps(valeurs) + '</script>'

    def test_corps_public_sans_recommandations(self):
        p = PageArticle(); p.feed(self.page())
        self.assertGreater(len(p.texte().split()), 120)
        self.assertNotIn('RECOMMANDATION', p.texte())

    def test_donnees_non_publiques_ou_autre_domaine_ignorees(self):
        for args in [('PRIVATE', 'www.blast-info.fr'), ('PUBLIC', 'exemple.fr')]:
            p = PageArticle(); p.feed(self.page(*args))
            self.assertNotIn('La commune', p.texte())

    def test_json_invalide_ne_casse_pas_extraction(self):
        p = PageArticle(); p.feed('<script type="application/json" id="__NUXT_DATA__">invalide</script><article><p>Texte public. </p></article>')
        self.assertIn('Texte public.', p.texte())
