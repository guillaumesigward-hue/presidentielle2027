import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
from pertinence import candidats_centraux, actualite_candidat
from automatisation import controler_article, conserver_article
from discours_auto import lire_support, actualiser_syntheses

class PerimetreCandidats(unittest.TestCase):
    def test_general_institutions_and_incidental_mentions_rejected(self):
        for titre,texte in [
            ('Le gouvernement finance une usine polluante','Le ministre annonce une aide publique pour le climat.'),
            ('La présidentielle approche','Les institutions de la République sont en débat.'),
            ('Une association sportive lance une collecte','Actualité sportive. '*100 + 'Gabriel Attal propose une mesure.'),
        ]:
            self.assertFalse(candidats_centraux(titre, texte))
        # Une liste de mentions périmée ne rend pas une actualité pertinente.
        self.assertFalse(actualite_candidat({'titre':'Un chantier industriel', 'candidats_mentions':['Gabriel Attal']}))

    def test_title_or_campaign_lead_and_accents(self):
        self.assertEqual(candidats_centraux('Melenchon présente ses propositions'), ['Jean-Luc Mélenchon'])
        self.assertEqual(candidats_centraux('Une réforme scolaire annoncée', 'Gabriel Attal propose de financer les écoles.'), ['Gabriel Attal'])
        self.assertFalse(candidats_centraux('Le président parle de son programme', 'Le ministre présente ses mesures.'))

    def test_old_snapshot_is_filtered_even_when_source_is_down(self):
        source={'url':'https://disclose.ngo/fr'}
        item={'url':'https://disclose.ngo/fr/article/usine','controle':'automatique','titre':'Le gouvernement finance une usine',
              'date_publication':'2026-11-15T12:00:00+00:00','derniere_verification_utc':'2026-11-15T12:00:00+00:00'}
        self.assertIsNone(conserver_article(item,source,datetime(2026,11,16,tzinfo=timezone.utc)))

    def test_stale_detection_cannot_contaminate_live_article(self):
        body='<meta property="og:title" content="Une usine reçoit une aide publique"><meta property="article:published_time" content="2026-11-15T12:00:00Z"><article>'+'Le ministère finance une usine. '*30+'</article>'
        self.assertIsNone(controler_article({'url':'https://disclose.ngo/fr/article/usine','resume':'Gabriel Attal propose une réforme'},
                         {'nom':'Disclose','url':'https://disclose.ngo/fr'},body,datetime(2026,11,16,tzinfo=timezone.utc)))

class SupportsPrimaires(unittest.TestCase):
    def test_party_site_does_not_assign_another_speakers_words(self):
        body='<meta property="og:title" content="Discours de Jordan Bardella"><article>' + 'Marine Le Pen soutient notre programme 2027. '*70 + '</article>'
        with self.assertRaises(ValueError):
            lire_support('Marine Le Pen','https://www.rassemblementnational.fr/discours',body)
        with self.assertRaises(ValueError):
            lire_support('Jean-Luc Mélenchon','https://exemple.fr/discours',body)
    def test_video_description_is_not_a_transcript(self):
        with self.assertRaises(ValueError):
            lire_support('Jean-Luc Mélenchon','https://melenchon.fr/2026/11/07/meeting/',
                         '<meta property="og:description" content="Jean-Luc Mélenchon au Bourget en 2027"><iframe src="https://youtube.com/embed/abc"></iframe>')

    def test_curated_sources_have_no_embedded_video_or_unsourced_status(self):
        p=Path(__file__).resolve().parents[1]/'data/syntheses_campagne.json'
        data=json.loads(p.read_text(encoding='utf-8'))
        # Ce fichier est actualisé par la veille : un report peut légitimement
        # réduire son contenu et ne doit pas bloquer les autres publications.
        self.assertIsInstance(data,list)
        for x in data:
            self.assertTrue(x['empreinte'])
            self.assertTrue(x['evolution'])
            self.assertTrue(x['dernier_controle_utc'])
            self.assertNotIn('<iframe',json.dumps(x))
            self.assertNotIn('youtube',x['url'])
            self.assertLess(sum(len(p['texte'].split()) for p in x['paragraphes']),200)

    def test_changed_document_does_not_reuse_old_summary(self):
        ancien={'url':'https://www.edouardphilippe.fr/programme/retraites','candidat':'Édouard Philippe',
                'empreinte':'ancienne','paragraphes':[{'titre':'Ancien','texte':'Une ancienne position.'}]}
        body='<article>Édouard Philippe présente son programme 2027. '+'Il propose des mesures pour les retraites. '*60+'</article>'
        with patch.dict('os.environ',{'RESUMES_LOCAUX':'0'}), patch('discours_auto.delai_reel', lambda _: nullcontext()):
            result,bilan=actualiser_syntheses([ancien],lambda _:body)
        self.assertFalse(any(x['url']==ancien['url'] for x in result))
        self.assertGreater(bilan['reportes'],0)

    def test_temporarily_unavailable_source_keeps_dated_summary(self):
        ancien={'url':'https://www.edouardphilippe.fr/programme/retraites','candidat':'Édouard Philippe',
                'empreinte':'ancienne','dernier_controle_utc':'2026-11-12', 'paragraphes':[{'titre':'Ancien','texte':'Position datée.'}]}
        def panne(_): raise OSError('panne')
        result,_=actualiser_syntheses([ancien],panne)
        self.assertEqual(result[0]['dernier_controle_utc'],'2026-11-12')
        self.assertTrue(result[0]['verification_differee'])

if __name__ == '__main__': unittest.main()
