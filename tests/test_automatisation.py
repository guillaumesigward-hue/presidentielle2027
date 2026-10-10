from datetime import datetime, timezone
import unittest
from automatisation import controler_article, selectionner_articles

class AutomatisationTests(unittest.TestCase):
    def setUp(self):
        self.source = {'nom':'Mediapart','url':'https://www.mediapart.fr/journal/politique'}
        self.item = {'source':'Mediapart','url':'https://www.mediapart.fr/journal/politique/101026/article','candidats_mentions':[]}
        self.now = datetime(2026,10,10,18,tzinfo=timezone.utc)
        self.body = '<meta property="og:title" content="La présidentielle et les propositions pour 2027"><meta property="article:published_time" content="2026-10-10T10:00:00Z">'
    def test_source_date_pertinence_and_no_invented_summary(self):
        article = controler_article(self.item,self.source,self.body,self.now)
        self.assertEqual(article['controle'],'automatique')
        self.assertEqual(article['source'],'Mediapart')
        self.assertNotIn('resume',article)
        self.assertIsNotNone(controler_article(self.item,self.source,self.body.replace('article:published_time','og:article:published_time'),self.now))
        for body in [self.body.replace('2026-10-10','2025-10-10'),self.body.replace('2026-10-10','2026-11-10'),self.body.replace('article:published_time','missing'),self.body.replace('La présidentielle et les propositions pour 2027','Le jardinage pour tout le monde')]:
            self.assertIsNone(controler_article(self.item,self.source,body,self.now))
        self.assertIsNone(controler_article(dict(self.item,url='https://evil.test/article'),self.source,self.body,self.now))
    def test_duplicates_rejections_and_source_outage(self):
        result = selectionner_articles([self.item,self.item],[self.source],lambda url:self.body,self.now)
        self.assertEqual(len(result),1)
        self.assertEqual(selectionner_articles([self.item],[self.source],lambda url:self.body,self.now,[self.item['url']]),[])
        def fail(url): raise OSError('source inaccessible')
        self.assertEqual(selectionner_articles([self.item],[self.source],fail,self.now),[])
