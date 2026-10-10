"""Actualisation descriptive à partir de publications primaires de campagne."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlsplit
import hashlib
import re
from automatisation import Metadonnees, donnees_article
from veille import PageArticle, contient_expression, THEMES

CAMPAGNES = {
 'Gabriel Attal':'https://attalpresident.fr/',
 'Bruno Retailleau':'https://www.avecretailleau.fr/',
 'Fabien Roussel':'https://www.pcf.fr/',
 'Jean-Luc Mélenchon':'https://melenchon2027.fr/',
 'Édouard Philippe':'https://www.edouardphilippe.fr/',
 'Nicolas Dupont-Aignan':'https://www.dupontaignan.fr/',
 'Marine Le Pen':'https://www.rassemblementnational.fr/',
 'Éric Zemmour':'https://programme.ericzemmour.fr/',
}
THEME_KEYS = {'École':'ecole','Santé':'sante','Énergie':'energie','Fiscalité':'fiscalite','Écologie':'ecologie'}

class TextePrincipal(PageArticle):
    def __init__(self):
        super().__init__()
        self.main = []
    def handle_data(self,data):
        super().handle_data(data)
        if 'main' in self.stack and not any(tag in self.IGNORES for tag in self.stack):
            self.main.append(data)
    def texte(self):
        if not self.a_article and len(' '.join(self.main))>=200:
            return re.sub(r'\s+',' ',' '.join(self.main)).strip()
        return super().texte()

def lien_officiel(url, root):
    url = urljoin(root,url)
    parsed = urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password:
        return None
    if (parsed.hostname or '').removeprefix('www.') != urlsplit(root).hostname.removeprefix('www.'):
        return None
    if any(x in parsed.path for x in ('connexion','adhesion','don/','boutique','confidential','contact')) or parsed.path.endswith('.pdf'):
        return None
    return parsed._replace(fragment='',query='').geturl()

def analyser_publication(nom,url,body):
    root = CAMPAGNES[nom]
    if not lien_officiel(url,root): return None
    parser=TextePrincipal(); parser.feed(body); texte=parser.texte()
    metadata=Metadonnees(); metadata.feed(body)
    article=donnees_article(metadata,url)
    date=metadata.meta.get('article:published_time') or metadata.meta.get('og:article:published_time') or article.get('datePublished')
    if date:
        try:
            parsed=datetime.fromisoformat(date.replace('Z','+00:00'))
            if parsed.year<2026 or parsed.date()>datetime.now(timezone.utc).date(): return None
        except ValueError: return None
    if not re.search(r'\b2027\b',texte) and '2027' not in urlsplit(url).hostname:
        return None
    if re.search(r'(?:programme|présidentielle).{0,35}\b2022\b',texte[:1000],re.I):
        return None
    sentences = re.split(r'(?<=[.!?])\s+',texte)
    claims=[]
    for sentence in sentences:
        if not 5<=len(sentence.split())<=25 or not 35<=len(sentence)<=230: continue
        if not re.search(r'\b(propose|proposons|proposer|proposera|proposent|souhaite|souhaitons|voulons|veut|cr[ée]er|garantir|r[ée]duire|augmenter|r[ée]tablir|supprimer|financer|renforcer|instaurer)\b',sentence,re.I): continue
        themes=[key for theme,key in THEME_KEYS.items() if any(contient_expression(sentence,mot) for mot in THEMES[theme])]
        if themes:
            claims=[{'texte':sentence,'themes':themes}]
            break
    statut=None
    titre=metadata.meta.get('og:title') or article.get('headline') or ''
    author=article.get('author',{})
    author=author.get('name','') if isinstance(author,dict) else ''
    personnel = nom.casefold() in (titre+' '+author).casefold()
    # Seules les déclarations personnelles explicites sont interprétées.
    for sentence in sentences:
        if not personnel or '2027' not in sentence or not 5<=len(sentence.split())<=25: continue
        if re.search(r'\bje retire ma candidature\b',sentence,re.I): statut={'description':'Retrait de candidature annoncé sur la source de campagne.','preuve':sentence}
        elif re.search(r'\bje (suis|serai) candidat(?:e)?\b',sentence,re.I): statut={'description':'Candidature annoncée pour 2027 sur la source de campagne.','preuve':sentence}
    return {'nom':nom,'url':url,'titre':metadata.meta.get('og:title') or article.get('headline') or 'Publication de campagne',
            'date_publication':date,'empreinte':hashlib.sha256(texte.encode()).hexdigest(),'propositions':claims,'statut':statut}

def actualiser_officiel(election,programmes,fetch,date_fr):
    urls={nom:{root} for nom,root in CAMPAGNES.items()}
    for personne in programmes['pretendants']:
        nom=personne['nom']
        if nom not in urls: continue
        for theme in personne.get('themes',{}).values():
            for source in theme.get('sources',[]):
                url=lien_officiel(source.get('url',''),CAMPAGNES[nom])
                if url: urls[nom].add(url)
    bilan={'pages_examinees':0,'pages_accessibles':0,'propositions_extraites':0,'statuts_actualises':0,'sources':{}}
    # La découverte commence sur les racines officielles, pas sur des sites tiers.
    def decouvrir(item):
        nom,root = item
        decouvertes = set(urls[nom])
        try:
            body=fetch(root)
            links=re.findall(r'href=["\']([^"\']+)["\']',body,re.I)
            for href in links:
                url=lien_officiel(href,root)
                if url and re.search(r'projet|priorit|proposition|programme|actualit|2027|mesure',url,re.I):
                    decouvertes.add(url)
                    if len(decouvertes)>=10: break
        except Exception: pass
        return nom,decouvertes
    with ThreadPoolExecutor(max_workers=6) as pool:
        for nom,decouvertes in pool.map(decouvrir,CAMPAGNES.items()):
            urls[nom] = decouvertes
    jobs=[(nom,url) for nom,links in urls.items() for url in sorted(links)[:10]]
    def lire(job):
        nom,url=job
        try: return nom,analyser_publication(nom,url,fetch(url)),True
        except Exception: return nom,None,False
    records=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for nom,record,ok in pool.map(lire,jobs):
            bilan['pages_examinees']+=1
            bilan['pages_accessibles']+=int(ok)
            source=bilan['sources'].setdefault(nom,{'examinees':0,'accessibles':0})
            source['examinees']+=1; source['accessibles']+=int(ok)
            if record: records.append(record)
    records.sort(key=lambda x:x.get('date_publication') or '',reverse=True)
    for candidat in election['candidatures']:
        preuve=next((x for x in records if x['nom']==candidat['nom'] and x['statut']),None)
        if preuve:
            candidat.update(description=preuve['statut']['description'],preuve_automatique=preuve['statut']['preuve'],
                url=preuve['url'],source='Source de campagne — contrôle automatique',verification_automatique=date_fr)
            bilan['statuts_actualises']+=1
        if candidat['nom'] in CAMPAGNES:
            candidat['dernier_controle_sources']=date_fr
    for personne in programmes['pretendants']:
        for key,theme in personne.get('themes',{}).items():
            if personne['nom'] not in CAMPAGNES:
                continue
            claims=[dict(claim,url=record['url'],date_publication=record['date_publication']) for record in records
                    if record['nom']==personne['nom'] for claim in record['propositions'] if key in claim['themes']][:3]
            if claims:
                # Un extrait bref ne remplace pas une fiche détaillée déjà sourcée.
                # La section automatique enrichit la fiche, sans masquer ses détails.
                theme['propositions_automatiques']=claims
                bilan['propositions_extraites']+=len(claims)
            theme['dernier_controle_sources']=date_fr
    programmes['dernier_controle_automatique']=date_fr
    return bilan
