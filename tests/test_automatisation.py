from datetime import datetime, timezone
import unittest
import json
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

    def test_blast_date_matches_article_not_recommendation(self):
        source = {'nom':'Blast','url':'https://www.blast-info.fr/'}
        url = 'https://www.blast-info.fr/articles/2026/test-bardella'
        data = [{'canonical_url':1,'published_at':2,'title':3},url,'2026-10-06T10:00:00Z','Jordan Bardella présente ses propositions']
        body = '<script id="__NUXT_DATA__" type="application/json">'+json.dumps(data)+'</script>'
        self.assertIsNotNone(controler_article({'url':url},source,body,self.now))
        self.assertIsNone(controler_article({'url':url+'/autre'},source,body,self.now))

    def test_disclose_investigation_is_dated_and_theme_classified(self):
        source = {'nom':'Disclose','url':'https://disclose.ngo/fr'}
        url = 'https://disclose.ngo/fr/article/financement-pollution'
        data = {'@type':'NewsArticle','mainEntityOfPage':{'@id':url},'headline':'Le gouvernement finance la pollution et le climat', 'datePublished':'2026-06-18T10:00:00Z'}
        body = '<script type="application/ld+json">'+json.dumps(data)+'</script>'
        result = controler_article({'url':url},source,body,self.now)
        self.assertTrue(result['enquete_anterieure'])
        self.assertIn('Écologie',result['themes'])
        self.assertIsNone(controler_article({'url':url},source,body.replace('2026-06-18','2025-06-18'),self.now))

    def test_one_source_cannot_exclude_other_sources(self):
        blast = {'nom':'Blast','url':'https://www.blast-info.fr/'}
        items = [dict(self.item,url=self.item['url']+str(i)) for i in range(30)]
        items.append({'source':'Blast','url':'https://www.blast-info.fr/articles/2026/test'})
        results = selectionner_articles(items,[self.source,blast],lambda url:self.body,self.now)
        self.assertEqual(sum(x['source']=='Mediapart' for x in results),7)
        self.assertEqual(sum(x['source']=='Blast' for x in results),1)
