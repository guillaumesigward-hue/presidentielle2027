from pathlib import Path
from datetime import datetime, timezone
import json, re, urllib.request

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
  "commission_sondages":"https://www.commission-des-sondages.fr/notices/medias/fichiers/bytag/14/2027-Presidentielle",
  "verian":"https://www.veriangroup.com/fr/news-and-insights",
  "verian_sofres":"https://www.veriangroup.com/fr/a-propos-de-nous",
}

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Presidentielle2027SourceMonitor/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode('utf-8','replace')

now=datetime.now(timezone.utc)
months=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
status={'last_checked_utc':now.isoformat(),'last_checked_fr':f"{now.day} {months[now.month-1]} {now.year}",'sources':{}}
for key,url in SOURCES.items():
    try:
        body=fetch(url)
        status['sources'][key]={'ok':True,'url':url,'bytes':len(body)}
        if key=='commission_sondages':
            ids=re.findall(r'102\d{2}',body)
            status['sources'][key]['latest_notice_id']=max(ids) if ids else None
    except Exception as e:
        status['sources'][key]={'ok':False,'url':url,'error':str(e)[:180]}
(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data/status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(status,ensure_ascii=False))
