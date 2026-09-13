"""CMS pricing adapter, based on j-hwan9/biosimilar-monitor (mapping/discovery).
No email functionality or credentials. Each published row retains its source.
Estimated ASP is withheld for non-ASP bases and ambiguous references/units.
"""
import argparse,csv,hashlib,io,json,math,re,sys,zipfile
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from asp_catalog import build_catalog,match_catalog,norm
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
 m=re.search(r'([\d,.]+)\s*(mcg|mg|units?|iu|u)\b',s,re.I)
 if not m:return None
 return (float(m[1].replace(',','')),'units' if m[2].lower() in ('u','unit','units','iu') else m[2].lower())
def dose_factor(dose,unit):
 a,b=quantity(dose),quantity(unit)
 if not a or not b or b[0]<=0:return None
 scale={'mg':1000,'mcg':1,'units':1}
 if ('units' in (a[1],b[1])) and a[1]!=b[1]:return None
 return a[0]*scale[a[1]]/(b[0]*scale[b[1]])
def basis(notes):
 text=' '.join(notes.lower().split())
 if re.search(r'\b(amp|wamp|wac|awp|mfp|nadac|fss)\b',text):return 'Non-ASP basis'
 if any(x in text for x in ['vaccine','covid','contractor','not otherwise','invoice']):return 'Basis requires review'
 if not text or re.fullmatch(r'(updated|added)\s+\w+\s+20\d\d',text) or '8% of reference' in text or text=='inflation-adjusted coinsurance':return 'ASP methodology estimate'
 return 'Basis requires review'
def derive(rows):
 lookup={}
 for r in rows:lookup.setdefault((r['quarter'],r['molecule'],r['brand']),[]).append(r)
 for r in rows:
  r['estimatedAsp']=None;r['addonPct']=None;r['method']=basis(r['notes']);r['standardFactor']=dose_factor(r['standardDose'],r['billingUnit'])
  if r.get('pooledIdentities'):r['method']='HCPCS pools different drug identities; brand ASP unavailable'
  if r['method']!='ASP methodology estimate':continue
  if r['brand']=='Zymfentra':r['method']='SC product: reference basis requires review';continue
  if r['kind']=='reference':r['estimatedAsp']=round(r['paymentLimit']/1.06,6);r['addonPct']=6;continue
  reference=r.get('reference') or CONFIG[r['molecule']]['originator']['brand'];refs=lookup.get((r['quarter'],r['molecule'],reference),[])
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
 def __init__(self):super().__init__();self.links=[];self.labels={};self.active=None
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   url=urljoin(CMS,dict(attrs).get('href',''))
   self.active=url if urlparse(url).hostname=='www.cms.gov' and '/files/zip/' in url else None
   if self.active:self.labels.setdefault(url,'')
 def handle_data(self,text):
  if self.active:self.labels[self.active]+=text
 def handle_endtag(self,tag):
  if tag=='a' and self.active:self.links.append(self.active);self.active=None
def discover(html,crosswalk=False):
 p=Links();p.feed(html);out={}
 for url in p.links:
  name=url.rsplit('/',1)[-1].lower();label=p.labels.get(url,'').lower()
  if crosswalk:
   if not re.search('crosswalk',name+' '+label) or re.search('noc|vaccine',name+' '+label):continue
  else:
   if re.search('crosswalk|noc|payable',name+' '+label):continue
   if not re.search(r'asp[- ]pric|payment[- ]limit',name+' '+label):continue
  # Link text identifies the payment quarter even when a filename contains a
  # different revision year or uses an abbreviated / opaque filename.
  text=label if re.search(r'20\d{2}',label) and any(x in label for x in MONTHS) else name
  y=re.search(r'20\d{2}',text);m=next((x for x in MONTHS if x in text),None)
  if y and m and int(y[0])>=2021:
   key=f'{y[0]} Q{MONTHS[m]}'
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
    if not re.fullmatch('[JQC][0-9]{4}',c) or pl is None:continue
    n=str(row.iloc[note]).strip() if note is not None else ''
    out[c]={'hcpcs':c,'paymentLimit':pl,'description':str(row.iloc[desc]).strip(),'billingUnit':str(row.iloc[dose]).strip(),'notes':'' if n.lower()=='nan' else n}
   break
 if len(out)<100:raise ValueError('Payment-limit workbook schema or coverage invalid')
 return out
def parse_crosswalk(content):
 import pandas as pd
 archive=zipfile.ZipFile(io.BytesIO(content));out={};headers=[]
 for name in archive.namelist():
  if not name.lower().endswith(('.xls','.xlsx','.csv')):continue
  if name.lower().endswith('.csv'):
   frames=[pd.read_csv(io.BytesIO(archive.read(name)),header=None,dtype=str,encoding='latin1')]
  else:frames=list(pd.read_excel(io.BytesIO(archive.read(name)),sheet_name=None,header=None,dtype=str,engine='xlrd' if name.lower().endswith('.xls') else 'openpyxl').values())
  for frame in frames:
   for i in range(min(100,len(frame))):
    h=[str(v).lower() for v in frame.iloc[i]]
    if any('hcpcs' in v or 'ndc' in v for v in h):headers.append(h)
    hc=next((j for j,v in enumerate(h) if ('hcpcs' in v or re.fullmatch(r'_?20\d{2}_code',v.strip())) and 'dosage' not in v and 'unit' not in v),None)
    nc=next((j for j,v in enumerate(h) if ('ndc' in v or 'national drug code' in v) and not any(w in v for w in ['unit','quantity','package','name'])),None)
    if hc is None or nc is None or hc==nc:continue
    for _,r in frame.iloc[i+1:].iterrows():
     code=str(r.iloc[hc]).strip().upper();n=re.sub(r'\.0$','',str(r.iloc[nc]).strip());n=re.sub(r'[^0-9]','',n)
     if re.fullmatch('[JQC][0-9]{4}',code) and 9<=len(n)<=11:out.setdefault(code,set()).add(n.zfill(11))
    break
 if not out:raise ValueError('CMS crosswalk schema not recognized: '+str(headers[-2:]))
 return out

def display_molecule(s):return next((k for k in CONFIG if k.lower()==s.lower()),s[:1].upper()+s[1:])

def map_rows(raw,q,url,filename,stamp,catalog=None,crosswalk=None):
 if catalog is None:catalog=build_catalog(json.loads((ROOT/'dist/data.json').read_text())['products'],json.loads((ROOT/'dist/portfolio.json').read_text())['products'])
 matched=match_catalog(raw,catalog,crosswalk);rows=[]
 for p in catalog:
  if p.get('approvalDates'):
   approved=min(p['approvalDates']);approved_q=approved[:4]+' Q'+str((int(approved[5:7])-1)//3+1)
   if q<approved_q:continue
  cfg=next((v for k,v in CONFIG.items() if k.lower()==p['molecule'].lower()),{})
  for code,method in matched[p['id']].items():
   v=raw[code]
   rows.append(dict(v,quarter=q,molecule=display_molecule(p['molecule']),brand=p['brand'],proper=p['proper'],reference=p['reference'],productId=p['id'],blas=p['blas'],company=p['company'],kind=p['kind'],own=p['own'],standardDose=cfg.get('display_dose',v['billingUnit']),unitSource='CMS HCPCS dosage',matchBasis=method,sourceUrl=url,sourceFile=filename,sourceCheckedAt=stamp,publicationStatus='Preliminary' if 'preliminary' in url.lower() else 'CMS published'))
 identities={};brands={}
 for r in rows:
  identities.setdefault(r['hcpcs'],set()).add(norm(r['proper']));brands.setdefault(r['hcpcs'],set()).add(r['brand'])
 for r in rows:r['sharedBrands']=sorted(brands[r['hcpcs']]);r['pooledIdentities']=len(identities[r['hcpcs']])>1
 return rows
def validate(rows):
 keys=[(r['quarter'],r['molecule'],r['brand'],r['hcpcs']) for r in rows]
 if not rows or len(keys)!=len(set(keys)):raise ValueError('Empty or duplicate ASP records')
 for r in rows:
  if not quarter(r['quarter']) or not number(r['paymentLimit']):raise ValueError('Invalid payment record')
def publish(rows,checked=None,files=None,errors=None,catalog=None,purple=None):
 validate(rows)
 obj={'schemaVersion':1,'sourceRepository':SOURCE_REPO,'sourceCommit':SOURCE_COMMIT,'sourceRepositoryUpdatedAt':'2026-06-08T03:35:15Z','cmsCheckedAt':checked,'builtAt':datetime.now(timezone.utc).isoformat(),'catalog':[dict(p,molecule=display_molecule(p['molecule'])) for p in (catalog or [])],'purpleBookAsOf':(purple or {}).get('purpleBookAsOf',(purple or {}).get('purpleBookDate')),'coverage':'All approved brands in the Regulatory Purple Book snapshot. CMS-matched HCPCS prices only; brands without matched ASP remain N/A. Shared-HCPCS prices are not independently reported brand prices.','files':files or [],'collectionErrors':errors or [],'rows':derive(rows)}
 target=ROOT/'dist/asp.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(target)
 print(f'ASP snapshot: {len(rows)} rows / {len(set(r["molecule"] for r in rows))} molecules / {len(set(r["quarter"] for r in rows))} quarters')
def refresh():
 import requests
 stamp=datetime.now(timezone.utc).isoformat();session=requests.Session();session.headers['User-Agent']='SBE-US-Market-Dashboard/1.0 (public CMS pricing monitor)'
 page=session.get(CMS,timeout=60);page.raise_for_status();quarters=discover(page.text)
 previous=json.loads((ROOT/'dist/asp.json').read_text()) if (ROOT/'dist/asp.json').exists() else {'rows':[]}
 purple=json.loads((ROOT/'dist/data.json').read_text());catalog=build_catalog(purple['products'],json.loads((ROOT/'dist/portfolio.json').read_text())['products'])
 crosswalks=discover(page.text,crosswalk=True);diagnostics=[]
 rows=[r for r in previous['rows'] if r.get('productId') in {p['id'] for p in catalog}];files=[];errors=[];success=0
 for q,urls in sorted(quarters.items()):
  try:
   if len(urls)!=1:raise ValueError('Multiple CMS revision URLs: manual review required')
   url=urls[0];r=session.get(url,timeout=90);r.raise_for_status();archive=zipfile.ZipFile(io.BytesIO(r.content))
   candidates=[n for n in archive.namelist() if n.lower().endswith(('.xls','.xlsx')) and not re.search('crosswalk|noc|payable|508',n,re.I)]
   if len(candidates)!=1:raise ValueError('Ambiguous payment workbook selection')
   name=candidates[0];raw=parse_workbook(archive.read(name),name);crosswalk={};cw_url=None
   try:
    cw_urls=crosswalks.get(q,[])
    if len(cw_urls)!=1:raise ValueError('No unique current CMS crosswalk link')
    cw_url=cw_urls[0];cw=session.get(cw_url,timeout=90);cw.raise_for_status();crosswalk=parse_crosswalk(cw.content)
   except Exception as e:errors.append({'quarter':q,'error':'Crosswalk: '+str(e)+'; exact brand/suffix matching remains active'})
   mapped=map_rows(raw,q,url,name,stamp,catalog,crosswalk)
   diagnostics.append({'quarter':q,'crosswalkUrl':cw_url,'crosswalkCodes':len(crosswalk),'denosumabCms':[v for v in raw.values() if 'denosumab' in v['description'].lower()],'matchedBrands':sorted(set(r['brand'] for r in mapped))})
   if len({r['molecule'] for r in mapped})<5:raise ValueError('Unexpectedly low mapped molecule coverage')
   rows=[r for r in rows if r['quarter']!=q]+mapped;files.append({'quarter':q,'url':url,'file':name,'sha256':hashlib.sha256(r.content).hexdigest(),'checkedAt':stamp});success+=1;print(q,len(mapped),'mapped rows',flush=True)
  except Exception as e:errors.append({'quarter':q,'error':str(e)});print(q,'retained previous data:',e,flush=True)
 for q in sorted({r['quarter'] for r in rows}-set(quarters)):errors.append({'quarter':q,'error':'Current CMS link not discovered; prior snapshot retained'})
 if not success:raise RuntimeError('All CMS downloads failed; existing snapshot preserved')
 publish(rows,stamp,files,errors,catalog,purple)
 (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/asp-matching.json').write_text(json.dumps({'checkedAt':stamp,'catalogCount':len(catalog),'quarters':diagnostics},indent=2)+'\n')
def refresh_catalog():
 target=ROOT/'dist/asp.json'
 if not target.exists():return
 previous=json.loads(target.read_text());purple=json.loads((ROOT/'dist/data.json').read_text())
 catalog=build_catalog(purple['products'],json.loads((ROOT/'dist/portfolio.json').read_text())['products'])
 previous['catalog']=[dict(p,molecule=display_molecule(p['molecule'])) for p in catalog]
 previous['purpleBookAsOf']=purple.get('purpleBookAsOf',purple.get('purpleBookDate'))
 previous['catalogUpdatedAt']=datetime.now(timezone.utc).isoformat()
 tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(previous,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(target)
 print('Purple Book ASP catalog:',len(catalog),'approved brands; existing CMS price observations retained')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seed-csv');p.add_argument('--catalog-only',action='store_true');args=p.parse_args()
 if args.catalog_only:refresh_catalog()
 elif args.seed_csv:publish(seed(args.seed_csv))
 else:refresh()
