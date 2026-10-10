"""Extraction stricte de tableaux publiés dans les notices officielles."""
import io
import re
import hashlib
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

def normaliser(texte):
    return ''.join(c for c in unicodedata.normalize('NFD', texte.lower()) if unicodedata.category(c) != 'Mn')

def tableau_resultats(table):
    if not table or any(len(row) != 2 for row in table):
        return None
    header = normaliser(' '.join(str(c or '') for row in table[:2] for c in row))
    if 'publie' not in header or 'brut' in header or 'redress' in header:
        return None
    results, total = [], None
    for row in table[2:]:
        nom, value = [re.sub(r'\s+', ' ', str(x or '')).strip() for x in row]
        if not re.fullmatch(r'\d{1,3}(?:[,.]\d+)?\s*%?', value):
            return None
        score = float(value.rstrip('% ').replace(',', '.'))
        if normaliser(nom) == 'total':
            total = score
            continue
        if len(nom.split()) < 2 or not 0 <= score <= 100 or any(x['nom']==nom for x in results):
            return None
        results.append({'nom': nom, 'pourcentage': score})
    if total != 100 or len(results) < 3 or abs(sum(x['pourcentage'] for x in results)-100) > 1:
        return None
    return results

def methodologie(texte):
    flat = re.sub(r'\s+', ' ', texte)
    date = re.search(r'(?:du|entre le)\s+(\d{1,2})\s*(?:au|et le)\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(20\d{2})', flat, re.I)
    sample = re.search(r'[ée]chantillon de\s+([\d ]+)\s+personnes\s+inscrites sur les listes [ée]lectorales', flat, re.I)
    org = re.search(r'[ée]tude r[ée]alis[ée]e par\s+([A-Za-zÀ-ÿ -]{3,45})\s+pour\s+(.{3,160}?)\s+[ée]chantillon', flat, re.I)
    if not date or not sample or not org:
        return None
    mois = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
    debut, fin, month, year = date.groups()
    try:
        date_fin = datetime(int(year),mois.index(month.lower())+1,int(fin),tzinfo=timezone.utc)
        date_debut = datetime(int(year),mois.index(month.lower())+1,int(debut),tzinfo=timezone.utc)
        n = int(sample.group(1).replace(' ',''))
    except ValueError:
        return None
    if not 100 <= n <= 100000 or date_debut > date_fin or date_fin > datetime.now(timezone.utc):
        return None
    return {'institut':org.group(1).strip(),'commanditaire':org.group(2).strip(),
            'terrain':f'{debut} au {fin} {month} {year}', 'date_fin':date_fin.date().isoformat(),
            'echantillon':f'{n:,}'.replace(',',' ')+' personnes inscrites sur les listes électorales',
            'methode':'Quotas' if 'quotas' in normaliser(flat) else 'Voir notice officielle'}

def extraire_notice(raw, notice):
    import pdfplumber
    if not raw.startswith(b'%PDF') or len(raw)>20_000_000:
        return []
    results = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages)>100:
            return []
        metadata = methodologie('\n'.join(page.extract_text() or '' for page in pdf.pages[:5]))
        if not metadata:
            return []
        for index,page in enumerate(pdf.pages):
            text = re.sub(r'\s+',' ',page.extract_text() or '')
            heading = re.search(r'(L.intention de vote au premier tour de l.[ée]lection pr[ée]sidentielle.{0,350}?)\s+Question\s*:',text,re.I)
            if not heading or 'suffrages exprim' not in normaliser(text):
                continue
            for table in page.extract_tables():
                rows = tableau_resultats(table)
                if not rows:
                    continue
                ident = hashlib.sha256((notice['url']+'#'+str(index)).encode()).hexdigest()[:16]
                premiers = sorted(rows, key=lambda x: x['pourcentage'], reverse=True)[:3]
                def pourcentage(value):
                    return str(value).replace('.', ',').removesuffix(',0') + ' %'
                synthese = 'Dans ce scénario de premier tour, ' + ', '.join(x['nom']+' obtient '+pourcentage(x['pourcentage']) for x in premiers) + '. '
                synthese += 'Enquête de '+metadata['institut']+', menée du '+metadata['terrain']+' auprès de '+metadata['echantillon']+'. '
                synthese += 'Ces résultats dépendent des candidatures testées et de la période du terrain. Les petits écarts ne permettent pas de conclure à une différence certaine ; ce sondage ne prédit pas le résultat de 2027.'
                results.append(dict(metadata, id=ident, titre=metadata['institut']+' — '+heading.group(1),
                    resume=synthese,
                    description='; '.join(x['nom']+' '+str(x['pourcentage']).replace('.',',').removesuffix(',0')+' %' for x in rows),
                    resultats=rows, url=notice['url']+'#page='+str(index+1), source='Commission des sondages — notice '+metadata['institut'],
                    controle='automatique', page=index+1, document_sha256=hashlib.sha256(raw).hexdigest()))
    return results

def actualiser_sondages(notices, existants, fetch_bytes):
    selection = [x for x in notices if re.search(r'\bIV\b|intentions? de vote|barom[eè]tre election|barom[eè]tre de l.[ée]lection',x.get('titre',''),re.I)]
    selection = sorted(selection,key=lambda x:int(x['url'].rstrip('/').split('/')[-1]) if x['url'].rstrip('/').split('/')[-1].isdigit() else 0,reverse=True)[:8]
    bilan = {'notices_examinees':len(selection),'scenarios_extraits':0,'non_exploitables':[]}
    def lire(item):
        try: return extraire_notice(fetch_bytes(item['url']),item)
        except Exception: return []
    scenarios = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for notice,items in zip(selection,pool.map(lire,selection)):
            scenarios.extend(items)
            if not items: bilan['non_exploitables'].append(notice['url'])
    nouveaux = {x['id']:x for x in existants if x.get('id') and x.get('controle')=='automatique'}
    nouveaux.update({x['id']:x for x in scenarios})
    bilan['scenarios_extraits']=len(scenarios)
    return sorted(nouveaux.values(),key=lambda x:x['date_fin'],reverse=True)[:36]+[x for x in existants if x.get('controle')!='automatique'], bilan


def enrichir_personnes(election, programmes):
    """Une personne testée dans une enquête n'est jamais déclarée candidate."""
    cle = lambda nom: re.sub(r'\W+', '', normaliser(nom))
    correspondances = {cle(x['nom']): x['nom'] for x in election['candidatures']}
    connus = set(correspondances.values())
    fiches = {x['nom'] for x in programmes['pretendants']}
    nouveaux = 0
    for sondage in election['sondages']:
        if sondage.get('controle') != 'automatique':
            continue
        for resultat in sondage.get('resultats', []):
            nom = correspondances.get(cle(resultat['nom']), resultat['nom'])
            if nom not in connus:
                election['candidatures'].append({'nom': nom,
                    'description': 'Personne testée dans un scénario de sondage. Cette présence n’établit pas une déclaration de candidature à la présidentielle de 2027.',
                    'source': sondage['source'], 'url': sondage['url'],
                    'nature': 'personne_testee', 'controle': 'automatique'})
                connus.add(nom)
                correspondances[cle(nom)] = nom
                nouveaux += 1
            if nom not in fiches:
                programmes['pretendants'].append({'nom': nom, 'themes': {
                    key: {'statut': 'Personne testée dans un sondage — programme non identifié par le dispositif',
                          'resume': 'Aucune proposition 2027 attribuable à cette personne n’a été extraite d’une source de campagne autorisée. Cela ne signifie pas qu’aucun programme n’existe.',
                          'solidite_documentaire': None, 'sources': []}
                    for key in ('ecole', 'sante', 'energie', 'fiscalite', 'ecologie')
                }})
                fiches.add(nom)
    return nouveaux
