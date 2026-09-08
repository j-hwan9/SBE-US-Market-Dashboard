import urllib.request, urllib.parse, json, pathlib, concurrent.futures, re, time, xml.etree.ElementTree as ET
from datetime import datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
NS={'s':'urn:hl7-org:v3'}
BASE='https://dailymed.nlm.nih.gov/dailymed/services/v2/'
rows=json.loads((ROOT/'data/purplebook.json').read_text())
groups={}
for r in rows: groups.setdefault((r['BLA Number'],r['Proprietary Name']),[]).append(r)
def fetch(url,path):
 if path.exists(): return path.read_bytes()
 for attempt in range(2):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'BiosimilarCompare/1.0 (public label research)'})
   data=urllib.request.urlopen(req,timeout=55).read();path.write_bytes(data);return data
  except Exception:
   if attempt: raise
def text(e): return re.sub(r'\s+',' ',' '.join(e.itertext())).strip() if e is not None else ''
def blocks(e):
 out=[]
 for child in e:
  tag=child.tag.split('}')[-1]
  if tag in ('paragraph','item','tr','caption'):out.append(text(child))
  elif tag in ('table','tbody','thead','list','content'):out+=blocks(child)
  else:
   t=text(child)
   if t:out.append(t)
 return out or [text(e)]
def section(r,codes):
 out=[]
 for s in r.findall('.//s:section',NS):
  c=s.find('s:code',NS)
  if c is not None and c.get('code') in codes:
   for q in [s]+s.findall('.//s:component/s:section',NS):
    title=text(q.find('s:title',NS))
    if title and title not in out:out.append(title)
    t=q.find('s:text',NS)
    if t is not None:
     for v in blocks(t):
      if v and v not in out:out.append(v)
 return out
def parse(xml,item,bla):
 r=ET.fromstring(xml)
 blas={e.get('extension','').replace('BLA','').lstrip('0') for e in r.findall('.//s:approval/s:id',NS)}
 if bla.lstrip('0') not in blas:return None
 sections={k:section(r,v) for k,v in {'indications':['34067-9'],'dosage':['34068-7'],'strengths':['43678-2'],'description':['34089-3'],'supplied':['34069-5'],'storage':['44425-7']}.items()}
 if not sections['indications']:return None
 products=[]
 parents={c:p for p in r.iter() for c in p}
 for mp in r.findall('.//s:manufacturedProduct/s:manufacturedProduct',NS):
  own={e.get('extension','').replace('BLA','').lstrip('0') for e in parents[mp].findall('.//s:approval/s:id',NS)}
  if bla.lstrip('0') not in own:continue
  c=mp.find('s:code',NS)
  if c is None or not c.get('code'):continue
  ing=[];active=[]
  for i in mp.findall('s:ingredient',NS):
   name=text(i.find('s:ingredientSubstance/s:name',NS));q=i.find('s:quantity',NS)
   n=q.find('s:numerator',NS) if q is not None else None;d=q.find('s:denominator',NS) if q is not None else None
   strength=(n.get('value','')+' '+n.get('unit','')+(' / '+d.get('value','')+' '+d.get('unit','') if d is not None else '')) if n is not None else ''
   obj={'name':name,'quantity':strength}
   (ing if i.get('classCode')=='IACT' else active).append(obj)
  packs=[]
  for pp in mp.findall('.//s:containerPackagedProduct',NS):
   pc=pp.find('s:code',NS);fc=pp.find('s:formCode',NS)
   if pc is not None and pc.get('code'):packs.append({'ndc':pc.get('code'),'container':fc.get('displayName','') if fc is not None else ''})
  forms=list(dict.fromkeys(e.get('displayName','') for e in mp.findall('.//s:containerPackagedProduct/s:formCode',NS)))
  products.append({'productNdc':c.get('code'),'name':text(mp.find('s:name',NS)),'generic':text(mp.find('s:asEntityWithGeneric/s:genericMedicine/s:name',NS)),'active':active,'inactive':ing,'forms':forms,'packages':packs})
 # Preserve full contextual paragraphs: do not collapse conditional storage rules into one number.
 storage=sections['storage'] or [x for x in sections['supplied'] if re.search(r'stor|refriger|temperatur|freez|expir|light',x,re.I)]
 latex=list(dict.fromkeys(x for k in ['supplied','description','storage'] for x in sections[k] if re.search('latex|natural rubber',x,re.I)))
 if not latex:
  latex=list(dict.fromkeys(text(x) for x in r.findall('.//s:paragraph',NS) if re.search('latex|natural rubber',text(x),re.I)))
 orgs=list(dict.fromkeys(text(x) for x in r.findall('s:author/s:assignedEntity/s:representedOrganization/s:name',NS)))
 manufacturer=list(dict.fromkeys(text(x) for x in r.findall('.//s:paragraph',NS) if re.match(r'(manufactured (by|for)|distributed by|marketed by)',text(x),re.I)))
 return {**item,'url':'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid='+item['setid'],'sections':sections,'storage':storage,'latex':latex,'products':products,'labelOrganizations':orgs,'manufacturerText':manufacturer,'labelEffective':r.find('s:effectiveTime',NS).get('value','')}
def collect(k,pr):
 bla,brand=k;first=pr[0];slug=re.sub('[^a-z0-9]+','-',brand.lower())+'-'+bla
 out={'id':slug,'brand':brand,'bla':bla,'molecule':first['Ref. Product Proper Name'] or first['Proper Name'],'proper':first['Proper Name'],'applicant':first['Applicant'],'reference':first['Ref. Product Proprietary Name'] or brand,'kind':'biosimilar' if '351(k)' in first['License Type'] else 'reference','presentations':pr,'labels':[],'issues':[]}
 try:
  query=brand
  listing=json.loads(fetch(BASE+'spls.json?'+urllib.parse.urlencode({'drug_name':query,'pagesize':100}),ROOT/'data/spls'/('list-'+slug+'.json')))
  candidates=listing.get('data',[])
  def rank(x):
   title=x['title'].upper();app=first['Applicant'].upper().split()[0].strip(',');return (app in title,not any(y in title for y in ['REPACK','A-S MEDICATION','CARDINAL HEALTH','MCKESSON','NUVAILA']),datetime.strptime(x['published_date'],'%b %d, %Y'))
  candidates.sort(key=rank,reverse=True)
  for item in candidates[:5]:
   xml=fetch(BASE+'spls/'+item['setid']+'.xml',ROOT/'data/spls'/(item['setid']+'.xml'))
   label=parse(xml,item,bla)
   if label:
    out['labels'].append(label)
    break
  if not out['labels']:out['issues'].append('DailyMed에서 BLA와 일치하는 PI 미확보 — FDA PI 확인 필요')
 except Exception as e:out['issues'].append('PI 수집 오류: '+str(e)[:120])
 (ROOT/'data'/('product-'+slug+'.json')).write_text(json.dumps(out,ensure_ascii=False))
 print(brand, 'OK' if out['labels'] else 'GAP',flush=True)
 return out
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  products=list(ex.map(lambda kv:collect(*kv),groups.items()))
 payload={'purpleBookDate':'2026-08','retrievedAt':'2026-09-08','purpleBookUrl':'https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-August-data-download.csv','products':products}
 (ROOT/'dist/data.json').write_text(json.dumps(payload,ensure_ascii=False))
 print('COMPLETE',len(products),sum(bool(x['labels']) for x in products),flush=True)
