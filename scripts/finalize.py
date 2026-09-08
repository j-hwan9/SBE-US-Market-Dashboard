"""Finalize the fixed August 2026 snapshot after collect.py and fda_fallback.py."""
import json,pathlib,re
from collect import ROOT,parse
p=ROOT/'dist/data.json';data=json.loads(p.read_text())
data['excludedHistorical']=[x for x in data['products'] if all(r['Licensure']!='Licensed' for r in x['presentations'])] or data.get('excludedHistorical',[])
data['products']=[x for x in data['products'] if any(r['Licensure']=='Licensed' for r in x['presentations'])]
for product in data['products']:
 if not product['labels']:continue
 label=product['labels'][0]
 if not label.get('provider'):
  raw=(ROOT/'data/spls'/(label['setid']+'.xml')).read_bytes()
  product['labels']=[parse(raw,{k:label[k] for k in ['setid','spl_version','published_date','title']},product['bla'])]
 else:
  raw=(ROOT/'data/fda'/(product['bla']+'.txt')).read_text()
  orgs=[]
  for m in re.finditer(r'(?im)^[ \t]*(Manufactured (?:by|for)|Distributed by)[^\n]*',raw):
   excerpt=raw[m.start():].split('\n\n')[0]
   v=re.sub(r'\s+',' ',excerpt).strip()
   if v not in orgs:orgs.append(v)
  label['manufacturerText']=orgs[:3]
raw=json.dumps(data,ensure_ascii=False)
raw=re.sub('[\ue000-\uf8ff]','•',raw)
p.write_text(raw)
summary={'snapshot':'2026-08','retrievedAt':data['retrievedAt'],'products':len(data['products']),'brands':len({x['brand'] for x in data['products']}),'molecules':len({x['molecule'] for x in data['products']}),'purpleBookRows':sum(len(x['presentations']) for x in data['products']),'piObtained':sum(bool(x['labels']) for x in data['products']),'notes':['Current Licensed records only; historical revoked BLA103737 excluded.','NDC mapped to own BLA within each SPL. Shared PI narrative preserves presentation-specific conditions.','Full PI sections preserved; wording differences are not clinical equivalence determinations.','NDC pending/XXXXX in FDA PI is not an assigned NDC.','Sorbitol absence from ingredient list is not an explicit free claim.','No automatic refresh or browser visual QA.']}
(ROOT/'data/verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False))
