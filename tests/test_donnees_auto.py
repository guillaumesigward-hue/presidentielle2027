import copy
import unittest
from officiel_auto import analyser_publication, lien_officiel, actualiser_officiel
from sondages_auto import tableau_resultats, methodologie, actualiser_sondages, enrichir_personnes
from resumes_auto import resumer_publications, VERSION
from veille import extraire_html


class DonneesAutomatiques(unittest.TestCase):
    def test_personne_testee_ne_devient_pas_candidature_declaree(self):
        election = {'candidatures': [], 'sondages': [{'controle':'automatique',
            'resultats':[{'nom':'Anne Martin'}], 'source':'Notice Test', 'url':'https://exemple.fr/notice'}]}
        programmes = {'pretendants': []}
        self.assertEqual(enrichir_personnes(election, programmes), 1)
        self.assertEqual(enrichir_personnes(election, programmes), 0)
        self.assertEqual(election['candidatures'][0]['nature'], 'personne_testee')
        self.assertIn('n’établit pas', election['candidatures'][0]['description'])
        self.assertEqual(len(programmes['pretendants']), 1)

    def test_resultats_publies_uniquement(self):
        table = [['', 'Résultats publiés'], ['', '(%)'],
                 ['Anne Martin', '42'], ['Paul Durand', '33,5'], ['Marie Dupont', '24,5'], ['TOTAL', '100']]
        self.assertEqual([x['pourcentage'] for x in tableau_resultats(table)], [42, 33.5, 24.5])
        brut = copy.deepcopy(table); brut[0][1] = 'Résultats bruts'
        self.assertIsNone(tableau_resultats(brut))
        mauvais = copy.deepcopy(table); mauvais[2][1] = '142'
        self.assertIsNone(tableau_resultats(mauvais))
        incomplet = copy.deepcopy(table); incomplet[4][1] = '4,5'
        self.assertIsNone(tableau_resultats(incomplet))

    def test_methodologie_et_conservation_en_panne(self):
        texte = 'Étude réalisée par Institut Test pour Journal Test Echantillon de 1 200 personnes inscrites sur les listes électorales. Du 1 au 3 septembre 2026. Méthode des quotas.'
        meta = methodologie(texte)
        self.assertEqual(meta['date_fin'], '2026-09-03')
        self.assertIn('1 200', meta['echantillon'])
        self.assertIsNone(methodologie('Enquête de popularité sans méthode'))
        existant = [{'id': 'ancien', 'controle': 'automatique', 'date_fin': '2026-09-03'}]
        result, report = actualiser_sondages([{'titre':'IV', 'url':'https://test/1'}], existant, lambda _: b'bad')
        self.assertEqual(result, existant)
        self.assertEqual(report['scenarios_extraits'], 0)

    def test_programme_date_et_provenance(self):
        url = 'https://www.edouardphilippe.fr/projet'
        body = '<article>Présidentielle 2027. Je propose de renforcer les moyens de l’école publique.</article>'
        result = analyser_publication('Édouard Philippe', url, body)
        self.assertEqual(result['propositions'][0]['themes'], ['ecole'])
        self.assertIsNone(lien_officiel('https://fraude.fr/projet', url))
        self.assertIsNone(analyser_publication('Édouard Philippe', url, body.replace('2027', '2022')))
        old = '<meta property="article:published_time" content="2022-01-01">' + body
        self.assertIsNone(analyser_publication('Édouard Philippe', url, old))

    def test_campagne_ne_devine_pas_candidature(self):
        result = analyser_publication('Édouard Philippe', 'https://www.edouardphilippe.fr/',
                    '<article>Élection 2027. Certains disent que je pourrais être candidat.</article>')
        self.assertIsNone(result['statut'])


class Resumes(unittest.TestCase):
    def test_recommandations_ne_sont_pas_resumees(self):
        contenu = 'Les écoles sont rénovées après une décision municipale. ' * 5
        self.assertEqual(extraire_html('<article>'+contenu+'</article><article>Une autre enquête sans rapport.</article>'), contenu.strip())

    def setUp(self):
        self.article = '<article>' + ' '.join(['La mairie annonce une rénovation des écoles. Les travaux concernent cinq établissements et débuteront en septembre. Les familles demandent un calendrier précis et les enseignants souhaitent connaître les modalités.']*7) + '</article>'
        self.texte = 'La rénovation annoncée concerne les écoles de la commune. Les familles et les enseignants demandent des précisions sur le calendrier et les modalités des travaux.'

    def test_resume_et_cache_sans_recalcul(self):
        items = [{'url':'https://exemple.fr/article'}]
        report = resumer_publications(items, lambda _: self.article, generate=lambda _: self.texte)
        self.assertEqual(report['resumes'], 1)
        self.assertEqual(items[0]['resume_statut'], 'disponible')
        nouveau = [{'url':items[0]['url']}]
        def interdit(_): raise AssertionError('Le cache doit éviter un nouveau calcul')
        report = resumer_publications(nouveau, lambda _: self.article, items, generate=interdit)
        self.assertEqual(report['reutilises'], 1)
        self.assertEqual(nouveau[0]['resume'], items[0]['resume'])

    def test_article_ferme_et_chiffres_inventes(self):
        items = [{'url':'https://exemple.fr/article'}]
        resumer_publications(items, lambda _: '<meta property="og:description" content="Bref chapeau"><article>Abonnez-vous</article>', generate=lambda _: self.texte)
        self.assertEqual(items[0]['resume_statut'], 'indisponible')
        resumer_publications(items, lambda _: self.article, generate=lambda _: self.texte + ' Le budget est de 987654 euros.')
        self.assertEqual(items[0]['resume_statut'], 'indisponible')
        self.assertNotIn('resume', items[0])


if __name__ == '__main__':
    unittest.main()
