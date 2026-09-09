"""BLA-matched FDA approval-letter dating periods, as dated historical evidence.

Never turn a drug-substance period, redaction, protocol, or in-use stability
into an unopened finished-product shelf life. PI remains the primary source.
"""
import argparse, concurrent.futures, hashlib, json, pathlib, re, subprocess, tempfile
import urllib.parse, urllib.error
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION=1

def clean(s):return re.sub(r'\s+',' ',s.replace('−','-').replace('–','-').replace('º','°')).strip()

def pdf_text(raw):
 if not raw.startswith(b'%PDF'):raise ValueError('FDA response is not PDF')
 with tempfile.TemporaryDirectory() as td:
  pdf=pathlib.Path(td)/'letter.pdf';txt=pathlib.Path(td)/'letter.txt';pdf.write_bytes(raw)
  subprocess.run(['pdftotext','-layout',str(pdf),str(txt)],check=True,capture_output=True,timeout=60)
  return txt.read_text()

def pi_has_unopened_period(product):
 for label in product.get('labels',[]):
  for key in ('storage','supplied'):
   for paragraph in label.get('sections',{}).get(key,[]):
    s=clean(paragraph)
    if re.search(r'\b(unopened|shelf.life|dating period)\b',s,re.I) and re.search(r'\b\d+\s*months?\b',s,re.I) and cold(s) and not re.search(r'dilut|reconstitut|after opening',s,re.I):return True
 return False

def cold(s):return bool(re.search(r'\b2\s*°?\s*C?\s*(?:-|to|and)\s*8\s*°?\s*C\b',s,re.I))

def extract_periods(text,product,doc,sibling_brands=None):
 bla=product['bla'];brand=product['brand']
 if not re.search(r'\bBLA\s*(?:No\.?\s*)?'+re.escape(bla)+r'\b',text,re.I):return []
 if not re.search(r'\b'+re.escape(brand)+r'\b',text,re.I):return []
 sections=list(re.finditer(r'(?im)^\s*(?:EXPIRATION\s+)?DATING\s+PERIOD\s*$',text))
 records=[]
 # Approval context is retained as strength scope, never extrapolated to later presentations.
 intro=clean(text[:5000])
 strengths=sorted(set(clean(m.group()) for m in re.finditer(r'\b\d+(?:\.\d+)?\s*mg\s*/\s*\d+(?:\.\d+)?\s*mL\b',intro,re.I)))
 for heading in sections:
  tail=text[heading.end():];end=re.search(r'(?m)^\s*[A-Z][A-Z /&-]{5,}\s*$',tail)
  body=tail[:end.start()] if end else tail[:2500]
  for sentence in re.split(r'(?<=[.;])\s+(?=[A-Z])',clean(body)):
   if not re.search(r'(?:dating period|shelf.life)',sentence,re.I):continue
   if re.search(r'drug substance|bulk substance|protocol|proposed|request|\(b\)\s*\(4\)|redacted',sentence,re.I):continue
   named=bool(re.search(r'\b'+re.escape(brand)+r'\b',sentence,re.I))
   other_named=any(b.casefold()!=brand.casefold() and re.search(r'\b'+re.escape(b)+r'\b',sentence,re.I) for b in sibling_brands or [])
   if other_named:continue
   if not named:
    # Generic 'drug product' cannot resolve multiple brands within a single BLA letter.
    if not re.search(r'drug product|finished product',sentence,re.I):continue
    if any(b.casefold()!=brand.casefold() and re.search(r'\b'+re.escape(b)+r'\b',intro,re.I) for b in sibling_brands or []):continue
   ds=list(re.finditer(r'\b(\d{1,3})\s*months?\b',sentence,re.I))
   if len(ds)!=1 or not cold(sentence):continue
   months=int(ds[0][1])
   if not 1<=months<=120:continue
   if not re.search(r'shall be|is\s|of\s|established|approved',sentence,re.I):continue
   devices=sorted(set(m.group().lower() for m in re.finditer(r'\b(?:prefilled syringes?|auto-?injectors?|vials?|cartridges?|pens?)\b',sentence,re.I)))
   local_strengths=sorted(set(clean(m.group()) for m in re.finditer(r'\b\d+(?:\.\d+)?\s*mg\s*/\s*\d+(?:\.\d+)?\s*mL\b',sentence,re.I))) or strengths
   records.append({'presentation':', '.join(devices),'months':months,'temperature':'2–8°C','basis':'from manufacture' if re.search(r'from (?:the )?date of manufacture',sentence,re.I) else 'as stated in letter','brand':brand,'bla':bla,'strengths':local_strengths,'documentDate':doc['date'],'documentUrl':doc['url'],'submission':doc.get('submission',''),'page':text[:heading.start()].count('\f')+1,'evidence':sentence,'historical':True,'scope':(' / '.join(local_strengths) if local_strengths else '문서 대상 완제품 · 함량 범위 미확인')+(' · '+', '.join(devices) if devices else '')})
 return records

def letter_documents(app,bla):
 if app.get('application_number')!='BLA'+bla:raise ValueError('FDA application number mismatch')
 docs={}
 for s in app.get('submissions',[]):
  if s.get('submission_status')!='AP':continue
  for d in s.get('application_docs',[]):
   url=d.get('url','').replace('http:','https:');url=urllib.parse.quote(url,safe=":/%?=&;,+");p=urllib.parse.urlsplit(url)
   if p.hostname!='www.accessdata.fda.gov' or '/appletter/' not in p.path.lower() or not p.path.lower().endswith('.pdf'):continue
   date=s.get('submission_status_date','') or d.get('date','')[:10].replace('-','')
   if not re.fullmatch(r'\d{8}',date):continue
   date=date[:4]+'-'+date[4:6]+'-'+date[6:]
   docs[url]={'url':url,'date':date,'submission':s.get('submission_type','')+' '+s.get('submission_number',''),'indexDate':d.get('date','')}
 return sorted(docs.values(),key=lambda d:(d['date'],d['url']),reverse=True)

def enrich_products(products,sources,cache=None,force=False):
 cache=cache if cache is not None else {};now=datetime.now(timezone.utc).isoformat(timespec='seconds')
 groups={}
 for p in products:groups.setdefault(p['bla'],[]).append(p)
 def one(item):
  bla,ps=item;status={'bla':bla,'checkedAt':now,'documents':0,'errors':[]}
  needs=[p for p in ps if not pi_has_unopened_period(p)]
  for p in ps:
   if p not in needs:p['approvalLetter']={'status':'pi_period_available','checkedAt':now,'facts':[]}
  if not needs:return status
  try:
   url='https://api.fda.gov/drug/drugsfda.json?'+urllib.parse.urlencode({'search':'application_number:"BLA'+bla+'"'})
   data=json.loads(sources.get(url));docs=letter_documents(data['results'][0],bla);status['documents']=len(docs)
   found={p['id']:[] for p in needs};reviewed=[]
   for doc in docs:
    try:
     entry=cache.get(doc['url'])
     identity=hashlib.sha256(json.dumps([VERSION,doc,[(p['id'],p['brand']) for p in ps]],sort_keys=True).encode()).hexdigest()
     if not entry or entry.get('identity')!=identity or force:
      raw=sources.get(doc['url']);text=pdf_text(raw)
      entry={'identity':identity,'hash':hashlib.sha256(raw).hexdigest(),'products':{p['id']:extract_periods(text,p,doc,[q['brand'] for q in ps]) for p in needs}}
      cache[doc['url']]=entry
     for p in needs:
      for original in entry.get('products',{}).get(p['id'],[]):
       fact=dict(original);sentence=fact['evidence']
       devices=sorted(set(m.group().lower() for m in re.finditer(r'\b(?:prefilled syringes?|auto-?injectors?|vials?|cartridges?|pens?)\b',sentence,re.I)))
       strengths=sorted(set(clean(m.group()) for m in re.finditer(r'\b\d+(?:\.\d+)?\s*mg\s*/\s*\d+(?:\.\d+)?\s*mL\b',sentence,re.I))) or fact['strengths']
       fact.update(presentation=', '.join(devices),strengths=strengths,scope=(' / '.join(strengths) if strengths else '문서 대상 완제품 · 함량 범위 미확인')+(' · '+', '.join(devices) if devices else ''))
       found[p['id']].append(fact)
     reviewed.append(doc['url'])
    except Exception as e:status['errors'].append({'url':doc['url'],'error':str(e)[:200]})
   for p in needs:
    # Keep each documented scope; newest record for the same explicit scope takes precedence.
    unique={}
    for fact in sorted(found[p['id']],key=lambda f:f['documentDate'],reverse=True):
     key=(tuple(fact['strengths']),fact.get('presentation',''),fact['basis'])
     if key not in unique:unique[key]=fact
     elif unique[key] and unique[key]['documentDate']==fact['documentDate'] and unique[key]['months']!=fact['months']:
      unique[key]=None # Conflicting periods for an unresolved same scope remain unfilled.
    facts=[f for f in unique.values() if f]
    p['approvalLetter']={'status':'partial' if status['errors'] else 'documented' if facts else 'not_found','checkedAt':now,'documentsDiscovered':len(docs),'documentsChecked':len(reviewed),'facts':facts,'note':'FDA letter 작성 당시 완제품 dating period. 현재 모든 제형의 유효기간을 의미하지 않으며 실제 포장 유효기간을 확인하세요.'}
  except urllib.error.HTTPError as e:
   state='not_found' if e.code==404 else 'unavailable';status['errors'].append({'error':str(e)})
   for p in needs:p['approvalLetter']={'status':state,'checkedAt':now,'facts':p.get('approvalLetter',{}).get('facts',[])}
  except Exception as e:
   status['errors'].append({'error':str(e)[:240]})
   for p in needs:p['approvalLetter']={'status':'unavailable','checkedAt':now,'facts':p.get('approvalLetter',{}).get('facts',[])}
  print('Approval letters '+bla+': '+str(status['documents'])+' documents, '+str(len(status['errors']))+' errors',flush=True)
  return status
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:statuses=list(pool.map(one,groups.items()))
 return {'checkedAt':now,'blas':statuses,'productsWithEvidence':sum(bool(p.get('approvalLetter',{}).get('facts')) for p in products)}

def run(output=None,force=False):
 from refresh import Sources,atomic_json
 out=pathlib.Path(output or ROOT/'dist');payload=json.loads((out/'data.json').read_text());path=ROOT/'data/approval-letter-cache.json'
 cache=json.loads(path.read_text()) if path.exists() else {}
 report=enrich_products(payload['products'],Sources(),cache,force)
 atomic_json(path,cache);atomic_json(ROOT/'reports/approval-letters.json',report)
 payload['approvalLettersCheckedAt']=report['checkedAt'];atomic_json(out/'data.json',payload)
 print(json.dumps({'productsWithEvidence':report['productsWithEvidence']}))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output');ap.add_argument('--force',action='store_true');args=ap.parse_args();run(args.output,args.force)
