"""CMS pricing adapter, based on j-hwan9/biosimilar-monitor (mapping/discovery).
No email functionality or credentials. Each published row retains its source.
Estimated ASP is withheld for non-ASP bases and ambiguous references/units.
"""
import argparse,csv,hashlib,io,json,math,re,sys,zipfile
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
ROOT=Path(__file__).resolve().parents[1]
CMS='https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files'
CONFIG=json.loads((ROOT/'data/asp-molecules.json').read_text())
SOURCE_COMMIT='39ac46d96502ce2e05a291b1d6915205efbb8c8f'
SOURCE_REPO='https://github.com/j-hwan9/biosimilar-monitor'
MONTHS={'january':1,'april':2,'july':3,'october':4}
def quarter(s):
 m=re.search(r'(20\d{2}).*?Q([1-4])',s);return f'{m[1]} Q{m[2]}' if m else None
def quantity(s):
 m=re.search(r'([\d,.]+)\s*(mcg|mg|units?|u)\b',s,re.I)
 if not m:return None
 return (float(m[1].replace(',','')),'units' if m[2].lower() in ('u','unit','units') else m[2].lower())
def dose_factor(dose,unit):
 a,b=quantity(dose),quantity(unit)
 if not a or not b or b[0]<=0:return None
 scale={'mg':1000,'mcg':1,'units':1}
 if ('units' in (a[1],b[1])) and a[1]!=b[1]:return None
 return a[0]*scale[a[1]]/(b[0]*scale[b[1]])
def basis(notes):
 text=notes.lower()
 if re.search(r'\b(amp|wamp|wac|awp|mfp|nadac|fss)\b',text):return 'Non-ASP basis'
 if any(x in text for x in ['vaccine','covid','contractor','not otherwise','invoice']):return 'Basis requires review'
 if not text or re.fullmatch(r'(updated|added)\s+\w+\s+20\d\d',text) or '8% of reference' in text or text=='inflation-adjusted coinsurance':return 'ASP methodology estimate'
 return 'Basis requires review'
def derive(rows):
 lookup={}
 for r in rows:lookup.setdefault((r['quarter'],r['molecule'],r['brand']),[]).append(r)
 for r in rows:
  r['estimatedAsp']=None;r['addonPct']=None;r['method']=basis(r['notes']);r['standardFactor']=dose_factor(r['standardDose'],r['billingUnit'])
  if r['method']!='ASP methodology estimate':continue
  if r['brand']=='Zymfentra':r['method']='SC product: reference basis requires review';continue
  if r['kind']=='reference':r['estimatedAsp']=round(r['paymentLimit']/1.06,6);r['addonPct']=6;continue
  cfg=CONFIG[r['molecule']];refs=lookup.get((r['quarter'],r['molecule'],cfg['originator']['brand']),[])
  ref=refs[0] if len(refs)==1 else None
  if not ref or basis(ref['notes'])!='ASP methodology estimate':r['method']='Reference ASP unavailable';continue
  ratio=dose_factor(r['billingUnit'],ref['billingUnit'])
  if ratio is None:r['method']='Billing-unit alignment unavailable';continue
  rate=8 if '8%' in r['notes'] and r['quarter']>='2022 Q4' else 6
  value=r['paymentLimit']-ref['paymentLimit']/1.06*ratio*rate/100
  if value<=0:r['method']='Non-positive estimate: review required';continue
  r['estimatedAsp']=round(value,6);r['addonPct']=rate
 return rows
def seed(path):
 rows=[]
 for d in csv.DictReader(open(path,encoding='utf-8-sig')):
  cfg=CONFIG[d['molecule']];dose=quantity(cfg['display_dose']);unit=f'{dose[0]/cfg["display_mult"]:g} {dose[1]}'
  rows.append(dict(quarter=quarter(d['quarter']),molecule=d['molecule'],brand=d['brand'],proper=d['suffix'],company=d['company'],kind='reference' if d['is_orig']=='True' else 'biosimilar',own=d['is_sb']=='True',hcpcs=d['hcpcs_code'],description=d['desc'],billingUnit=unit,unitSource='Inherited mapping; verify CMS dosage',standardDose=cfg['display_dose'],paymentLimit=float(d['payment_limit']),notes=d['notes'],sourceUrl=f'{SOURCE_REPO}/blob/{SOURCE_COMMIT}/data/asp_data.csv',sourceFile='Existing ASP dashboard CSV',sourceCheckedAt=None))
 return derive(rows)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   href=dict(attrs).get('href','');url=urljoin(CMS,href)
   if urlparse(url).hostname=='www.cms.gov' and '/files/zip/' in url and re.search(r'(asp-pricing|payment-limit)',url,re.I) and not re.search('crosswalk|noc|payable',url,re.I):self.links.append(url)
def discover(html):
 p=Links();p.feed(html);out={}
 for url in p.links:
  name=url.rsplit('/',1)[-1].lower();y=re.search(r'20\d{2}',name);m=next((x for x in MONTHS if x in name),None)
  if y and m and int(y[0])>=2021:
   key=f'{y[0]} Q{MONTHS[m]}'
   # CMS landing page lists the current revision. Duplicate quarter links are
   # retained as candidates rather than silently selecting an arbitrary archive.
   out.setdefault(key,[])
   if url not in out[key]:out[key].append(url)
 if not out:raise ValueError('No CMS quarterly files discovered')
 return out
def number(v):
 try:
  n=float(str(v).replace(',','').replace('$',''));return n if math.isfinite(n) and n>0 else None
 except ValueError:return None
def parse_workbook(data,filename):
 import pandas as pd
 sheets=pd.read_excel(io.BytesIO(data),sheet_name=None,header=None,dtype=str,engine='xlrd' if filename.lower().endswith('.xls') else 'openpyxl')
 out={}
 for frame in sheets.values():
  for i in range(min(35,len(frame))):
   hdr=[str(x).lower().replace('\n',' ').strip() for x in frame.iloc[i]]
   code=next((j for j,x in enumerate(hdr) if 'hcpcs' in x and 'code' in x and 'dosage' not in x),None)
   pay=next((j for j,x in enumerate(hdr) if 'payment' in x and 'limit' in x),None)
   desc=next((j for j,x in enumerate(hdr) if 'description' in x),None)
   dose=next((j for j,x in enumerate(hdr) if 'dosage' in x),None)
   note=next((j for j,x in enumerate(hdr) if 'note' in x),None)
   if None in (code,pay,desc,dose):continue
   for _,row in frame.iloc[i+1:].iterrows():
    c=str(row.iloc[code]).strip().upper();pl=number(row.iloc[pay])
    if not re.fullmatch('[JQ][0-9]{4}',c) or pl is None:continue
    n=str(row.iloc[note]).strip() if note is not None else ''
    out[c]={'hcpcs':c,'paymentLimit':pl,'description':str(row.iloc[desc]).strip(),'billingUnit':str(row.iloc[dose]).strip(),'notes':'' if n.lower()=='nan' else n}
   break
 if len(out)<100:raise ValueError('Payment-limit workbook schema or coverage invalid')
 return out
def map_rows(raw,q,url,filename,stamp):
 rows=[]
 for molecule,cfg in CONFIG.items():
  for spec in [cfg['originator'],*cfg['biosimilars']]:
   fixed=spec.get('hcpcs_fixed');matches=[v for code,v in raw.items() if (code==fixed if fixed else any(k in v['description'].lower() for k in spec['desc_keywords']) and not any(k in v['description'].lower() for k in spec['desc_exclude']))]
   # Historical originator code changes (e.g. Neulasta) use reviewed keywords.
   if fixed and not matches:matches=[v for v in raw.values() if any(k in v['description'].lower() for k in spec['desc_keywords']) and not any(k in v['description'].lower() for k in spec['desc_exclude'])]
   for v in matches:
    rows.append(dict(v,quarter=q,molecule=molecule,brand=spec['brand'],proper=spec.get('suffix',molecule.lower()),company=spec['company'],kind='reference' if fixed else 'biosimilar',own=spec.get('is_sb',False),standardDose=cfg['display_dose'],unitSource='CMS HCPCS dosage',sourceUrl=url,sourceFile=filename,sourceCheckedAt=stamp))
 return rows
def validate(rows):
 keys=[(r['quarter'],r['molecule'],r['brand'],r['hcpcs']) for r in rows]
 if not rows or len(keys)!=len(set(keys)):raise ValueError('Empty or duplicate ASP records')
 for r in rows:
  if not quarter(r['quarter']) or not number(r['paymentLimit']):raise ValueError('Invalid payment record')
def publish(rows,checked=None,files=None,errors=None):
 validate(rows)
 obj={'schemaVersion':1,'sourceRepository':SOURCE_REPO,'sourceCommit':SOURCE_COMMIT,'sourceRepositoryUpdatedAt':'2026-06-08T03:35:15Z','cmsCheckedAt':checked,'builtAt':datetime.now(timezone.utc).isoformat(),'coverage':'Existing ASP dashboard scope: 10 molecules. HCPCS-level data, not NDC-level or all approved biosimilars.','files':files or [],'collectionErrors':errors or [],'rows':derive(rows)}
 target=ROOT/'dist/asp.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(target)
 print(f'ASP snapshot: {len(rows)} rows / {len(set(r["molecule"] for r in rows))} molecules / {len(set(r["quarter"] for r in rows))} quarters')
def refresh():
 import requests
 stamp=datetime.now(timezone.utc).isoformat();session=requests.Session();session.headers['User-Agent']='SBE-US-Market-Dashboard/1.0 (public CMS pricing monitor)'
 page=session.get(CMS,timeout=60);page.raise_for_status();quarters=discover(page.text)
 previous=json.loads((ROOT/'dist/asp.json').read_text()) if (ROOT/'dist/asp.json').exists() else {'rows':[]}
 rows=previous['rows'];files=[];errors=[];success=0
 for q,urls in sorted(quarters.items()):
  try:
   if len(urls)!=1:raise ValueError('Multiple CMS revision URLs: manual review required')
   url=urls[0];r=session.get(url,timeout=90);r.raise_for_status();archive=zipfile.ZipFile(io.BytesIO(r.content))
   candidates=[n for n in archive.namelist() if n.lower().endswith(('.xls','.xlsx')) and not re.search('crosswalk|noc|payable|508',n,re.I)]
   if len(candidates)!=1:raise ValueError('Ambiguous payment workbook selection')
   name=candidates[0];raw=parse_workbook(archive.read(name),name);mapped=map_rows(raw,q,url,name,stamp)
   if len({r['molecule'] for r in mapped})<5:raise ValueError('Unexpectedly low mapped molecule coverage')
   rows=[r for r in rows if r['quarter']!=q]+mapped;files.append({'quarter':q,'url':url,'file':name,'sha256':hashlib.sha256(r.content).hexdigest(),'checkedAt':stamp});success+=1;print(q,len(mapped),'mapped rows',flush=True)
  except Exception as e:errors.append({'quarter':q,'error':str(e)});print(q,'retained previous data:',e,flush=True)
 if not success:raise RuntimeError('All CMS downloads failed; existing snapshot preserved')
 publish(rows,stamp,files,errors)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seed-csv');args=p.parse_args()
 if args.seed_csv:publish(seed(args.seed_csv))
 else:refresh()
