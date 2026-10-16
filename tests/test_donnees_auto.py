import copy
import unittest
import hashlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from officiel_auto import analyser_publication, lien_officiel, actualiser_officiel
from sondages_auto import tableau_resultats, methodologie, actualiser_sondages, enrichir_personnes
from resumes_auto import resumer_publications, VERSION, sortie_coherente, titre_coherent, extrait_pertinent
from veille import extraire_html
from preparer_resumes import telecharger


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

    def test_extrait_enrichit_sans_remplacer_la_fiche_detaillee(self):
        theme = {'resume': 'Explication détaillée existante', 'financement': 'Budget documenté',
                 'population_concernee': 'Élèves et familles', 'sources': []}
        programmes = {'pretendants':[{'nom':'Édouard Philippe','themes':{'ecole':copy.deepcopy(theme)}}]}
        election = {'candidatures':[{'nom':'Édouard Philippe'}]}
        body = '<article>Présidentielle 2027. Je propose de renforcer les moyens de l’école publique.</article>'
        actualiser_officiel(election, programmes, lambda url: body if 'edouardphilippe.fr' in url else '', '10 octobre 2026')
        actualise = programmes['pretendants'][0]['themes']['ecole']
        self.assertTrue(actualise['propositions_automatiques'])
        for key,value in theme.items():
            self.assertEqual(actualise[key], value)


class Resumes(unittest.TestCase):
    def test_cache_corrompu_est_retelecharge_avant_utilisation(self):
        contenu = b'contenu officiel verifie'
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / 'runtime.bin'
            fichier.write_bytes(b'cache corrompu')
            with patch('preparer_resumes.urllib.request.urlopen', return_value=io.BytesIO(contenu)):
                telecharger('https://exemple.fr/runtime.bin', fichier, hashlib.sha256(contenu).hexdigest())
            self.assertEqual(fichier.read_bytes(), contenu)

    def test_attribution_ne_devient_pas_un_nom_propre_invente(self):
        source = 'Disclose examine un financement public. Les autorités répondent que le dossier reste en discussion.'
        texte = 'Selon Disclose, le financement étudié soulève des interrogations. La décision définitive demeure attendue et les autorités apportent une réponse.'
        self.assertTrue(sortie_coherente(texte, source))
        self.assertFalse(sortie_coherente(texte.replace('Disclose', 'Paul Martin'), source))

    def test_resume_doit_couvrir_le_sujet_du_titre(self):
        titre = 'Mensonges et désaveux : Laurent Nuñez face à sa démission'
        hors_sujet = 'Selon Blast, les lycéens ont été blessés pendant des manifestations. Laurent Nuñez a répondu aux syndicats.'
        pertinent = 'Selon Blast, Laurent Nuñez est confronté à des demandes de démission après les révélations sur ses déclarations. Les réponses officielles restent attendues.'
        self.assertFalse(titre_coherent(titre, hors_sujet))
        self.assertTrue(titre_coherent(titre, pertinent))

    def test_nom_et_sigle_ne_remplacent_pas_le_sujet_du_titre(self):
        titre = 'Bardella : l’antisémitisme, un vivier du RN'
        hors_sujet = 'Selon Blast, Jordan Bardella a été porte-parole du Front national à Brachay.'
        pertinent = ('Selon Blast, l’enquête examine des propos antisémites attribués à Jordan Bardella '
                     'et leur place dans le Rassemblement national.')
        self.assertFalse(titre_coherent(titre, hors_sujet))
        self.assertTrue(titre_coherent(titre, pertinent))

    def test_extrait_long_recherche_les_passages_centraux_lies_au_titre(self):
        titre = 'Enquête sur les messages antisémites attribués à Bardella'
        texte = ('Présentation générale de la politique française et contexte du débat public. ' * 8
                 + 'Au cœur de l’enquête, les messages antisémites attribués à Jordan Bardella sont examinés. '
                 + 'Contexte et éléments complémentaires sur les personnes concernées. ' * 8
                 + 'La rédaction indique les réponses reçues et les suites attendues de cette enquête. ' * 8)
        extrait, partiel = extrait_pertinent(titre, texte, limite_mots=55)
        self.assertTrue(partiel)
        self.assertIn('Au cœur de l’enquête', extrait)
        self.assertIn('réponses reçues', extrait)

    def test_copies_longues_et_repetitions_rejetees(self):
        original = ' '.join('mot'+str(i) for i in range(40))
        self.assertFalse(sortie_coherente(original + '.', original))
        boucle = 'La transition concerne les collectivités. ' * 5
        self.assertFalse(sortie_coherente(boucle, boucle))
        original = 'Aucune aide n’a encore été versée. Les contrats sont en discussion.'
        resume = 'L’entreprise a reçu une subvention publique pour lancer son projet industriel, alors que les modalités du contrat restent en discussion.'
        self.assertFalse(sortie_coherente(resume, original))

    def test_negation_du_versement_acceptee(self):
        original = 'Aucune aide n’a encore été versée. Les contrats sont en discussion.'
        for apostrophe in ("'", '’'):
            resume = 'L’entreprise n' + apostrophe + 'a reçu aucune subvention à ce stade. Les discussions se poursuivent et la décision définitive reste attendue.'
            self.assertTrue(sortie_coherente(resume, original))
            # Une négation ailleurs ne doit pas masquer une affirmation fausse.
            self.assertFalse(sortie_coherente(resume + ' Une autre société a reçu une aide.', original))

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

