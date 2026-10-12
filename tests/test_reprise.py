"""Reprises après panne : ne pas effacer, périmer ou ressusciter un article rejeté."""
import io
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from urllib.error import HTTPError

from automatisation import controler_article, selectionner_articles
from resumes_auto import VERSION, resumer_publications
from update import lire_url


class Reprise(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 12, tzinfo=timezone.utc)
        self.source = {'nom': 'Blast', 'url': 'https://www.blast-info.fr/'}
        self.item = {'source': 'Blast', 'url': 'https://www.blast-info.fr/articles/2026/presidentielle'}
        self.body = '<meta property="og:title" content="Les propositions pour la présidentielle 2027"><meta property="article:published_time" content="2026-10-10T10:00:00Z">'
        self.old = controler_article(self.item, self.source, self.body, self.now - timedelta(days=1))
        self.old.update(resume='Une synthèse déjà publiée.', resume_statut='disponible',
                        resume_version=VERSION, resume_empreinte='empreinte', resume_limite='Résumé automatique.')

    def panne(self, _):
        raise TimeoutError('panne simulée')

    def selection(self, fetch=None, **kwargs):
        return selectionner_articles([], [self.source], fetch or self.panne, self.now,
                                     precedentes=[self.old], **kwargs)

    def test_panne_conserve_article_resume_et_date_sans_recalcul(self):
        articles = self.selection()
        self.assertEqual(len(articles), 1)
        self.assertIn('11/10/2026', articles[0]['description'])
        bilan = resumer_publications(articles, lambda _: self.fail('Pas de nouvel accès'), [self.old],
                                    generate=lambda _: self.fail('Pas de génération'))
        self.assertEqual(bilan['reutilises'], 1)
        self.assertEqual(articles[0]['resume'], self.old['resume'])
        self.assertEqual(articles[0]['derniere_verification_utc'], self.old['derniere_verification_utc'])

    def test_rejet_humain_prime_sur_cache(self):
        self.assertEqual(self.selection(exclusions=[self.old['url']]), [])

    def test_repli_expire_apres_sept_jours(self):
        self.old['derniere_verification_utc'] = (self.now - timedelta(days=8)).isoformat()
        self.assertEqual(self.selection(), [])

    def test_page_supprimee_et_metadonnees_invalides_ne_sont_pas_conservees(self):
        def supprimee(url):
            raise HTTPError(url, 410, 'Gone', {}, None)
        self.assertEqual(self.selection(supprimee), [])
        self.assertEqual(self.selection(lambda _: '<html>Page absente</html>'), [])

    def test_reprise_revalide_et_retire_avertissement(self):
        self.old['verification_differee'] = True
        articles = self.selection(lambda _: self.body)
        self.assertNotIn('verification_differee', articles[0])
        self.assertEqual(articles[0]['derniere_verification_utc'], self.now.isoformat())

    def test_ancien_article_ou_source_inconnue_non_repris(self):
        self.old['date_publication'] = '2025-01-01T00:00:00+00:00'
        self.assertEqual(self.selection(), [])
        self.old['source'] = 'Source inconnue'
        self.assertEqual(self.selection(), [])


class Telechargement(unittest.TestCase):
    def test_taille_bornee(self):
        with patch('update.urllib.request.urlopen', return_value=io.BytesIO(b'abcdef')):
            with self.assertRaisesRegex(ValueError, 'volumineux'):
                lire_url('https://exemple.fr', 5)

    def test_flux_lent_interrompu(self):
        with patch('update.urllib.request.urlopen', return_value=io.BytesIO(b'abc')), patch('update.time.monotonic', side_effect=[0, 46]):
            with self.assertRaises(TimeoutError):
                lire_url('https://exemple.fr', 5)

    def test_reponse_complete(self):
        with patch('update.urllib.request.urlopen', return_value=io.BytesIO(b'abc')):
            self.assertEqual(lire_url('https://exemple.fr', 5), b'abc')
