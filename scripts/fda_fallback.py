import json,pathlib,urllib.request,urllib.parse,concurrent.futures,re,subprocess
from collect import ROOT,fetch
DIR=ROOT/'data/fda';DIR.mkdir(exist_ok=True)
def collect(p):
 bla=p['bla']
 if p['labels']:return p
 try:
  url='https://api.fda.gov/drug/drugsfda.json?'+urllib.parse.urlencode({'search':'application_number:"BLA'+bla+'"'})
  data=json.loads(fetch(url,DIR/(bla+'.json')))
  app=data['results'][0]
  docs=[d for s in app.get('submissions',[]) for d in s.get('application_docs',[]) if d.get('type')=='Label']
  docs.sort(key=lambda x:x.get('date',''),reverse=True)
  if not docs:raise ValueError('FDA API에 label 문서 링크 없음')
  doc=docs[0];url=doc['url'].replace('http:','https:');pdf=DIR/(bla+'.pdf');fetch(url,pdf)
  txt=DIR/(bla+'.txt');subprocess.run(['pdftotext','-layout',str(pdf),str(txt)],check=True,capture_output=True)
  raw=txt.read_text();body=raw
  starts=list(re.finditer(r'(?m)^[ \t\f]*1[ \t]+INDICATIONS[ \t]+AND[ \t]*USAGE[ \t]*$',raw))
  if not starts:raise ValueError('Full PI의 시작 경계를 확인하지 못함')
  index=0 if p['brand']=='Immgolis' else len(starts)-1
  body=raw[starts[index].start():starts[index+1].start() if index+1<len(starts) else len(raw)]
  names={'indications':(1,'INDICATIONS AND USAGE'),'dosage':(2,'DOSAGE AND ADMINISTRATION'),'strengths':(3,'DOSAGE FORMS AND STRENGTHS'),'description':(11,'DESCRIPTION'),'supplied':(16,'HOW SUPPLIED')}
  sections={}
  for key,(num,title) in names.items():
   pattern=r'[ \t]*'.join(title.split(' '))
   start=re.search(r'(?m)^[ \t\f]*'+str(num)+r'[ \t]+'+pattern+r'[^\n]*',body)
   if not start:sections[key]=[];continue
   rest=body[start.end():];end=re.search(r'(?m)^\s*'+str(num+1)+r'\s+[A-Z][A-Z /&-]+',rest)
   value=rest[:end.start()] if end else rest
   # Remove PDF pagination, keeping headings and source table lines together.
   value=re.sub(r'Reference ID:\s*\d+','',value).replace('\f','\n')
   value=re.sub(r'(?m)^\s*\d+\s*$','',value)
   paragraphs=[re.sub(r'\s+',' ',v).strip() for v in re.split(r'\n\s*\n',value)]
   sections[key]=[v for v in paragraphs if len(v)>3]
  sections['storage']=[v for v in sections['supplied'] if re.search(r'stor|refriger|temperatur|freez|expir|light',v,re.I)]
  latex=[v for k in ['supplied','description'] for v in sections[k] if re.search('latex|natural rubber',v,re.I)]
  if not sections['indications']:raise ValueError('FDA PDF의 PI section 경계를 확인하지 못함')
  p['labels']=[{'provider':'FDA','title':p['brand']+' FDA prescribing information','url':url,'published_date':doc.get('date',''),'labelEffective':doc.get('date',''),'sections':sections,'storage':sections['storage'],'latex':latex,'products':[],'labelOrganizations':[],'pdfTextExtracted':True}];p['issues']=[]
  print(p['brand'],'FDA OK',flush=True)
 except Exception as e:
  p['issues'].append('FDA 확인: '+str(e)[:120]);print(p['brand'],'FDA GAP',str(e)[:90],flush=True)
 (ROOT/'data'/('product-'+p['id']+'.json')).write_text(json.dumps(p,ensure_ascii=False))
 return p
if __name__=='__main__':
 path=ROOT/'dist/data.json';data=json.loads(path.read_text());products=data['products']
 # The same SPL can explicitly cover more than one presentation name in the same BLA.
 for p in products:
  if p['brand']=='Udenyca Onbody' and not p['labels']:
   base=next((x for x in products if x['brand']=='Udenyca' and x['bla']==p['bla'] and x['labels']),None)
   if base and 'onbody' in json.dumps(base['labels']).lower():p['labels']=base['labels'];p['issues']=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:data['products']=list(ex.map(collect,products))
 path.write_text(json.dumps(data,ensure_ascii=False));print('TOTAL PI',sum(bool(p['labels']) for p in data['products']),flush=True)
