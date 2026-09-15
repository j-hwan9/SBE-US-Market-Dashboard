"""Archive material data changes, excluding collection timestamps and ordering noise."""
import json,re
from datetime import datetime
from pathlib import Path
CHECK_FIELDS={'retrievedAt','piCheckedAt','checkedAt','sourceCheckedAt','cmsCheckedAt','builtAt','catalogUpdatedAt','lastCheckedAt','revision','lastChangedAt'}
def stable(value):
 if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in CHECK_FIELDS}
 if isinstance(value,list):return [stable(v) for v in value]
 return value
def encoded(value):return re.sub('[\ue000-\uf8ff]','•',json.dumps(stable(value),sort_keys=True,ensure_ascii=False,separators=(',',':')))
def sorted_records(rows):return sorted((stable(r) for r in rows),key=encoded)
def regulatory_content(data):
 products=[]
 for p in data.get('products',[]):
  p=stable(p);p['presentations']=sorted_records(p.get('presentations',[]));products.append(p)
 return {'schemaVersion':data.get('schemaVersion'),'products':sorted_records(products)}
def asp_content(data):
 return {'schemaVersion':data.get('schemaVersion'),'catalog':sorted_records(data.get('catalog',[])),'rows':sorted_records(data.get('rows',[]))}
def asp_changes(before,after):
 key=lambda r:json.dumps([r.get('productId') or r.get('brand'),r.get('quarter'),r.get('hcpcs')])
 a={key(r):r for r in before.get('rows',[])};b={key(r):r for r in after.get('rows',[])}
 brief=lambda r:{k:r.get(k) for k in ['productId','brand','quarter','hcpcs']}
 changed=[]
 for k in sorted(a.keys()&b.keys()):
  x,y=stable(a[k]),stable(b[k]);fields=[f for f in sorted(x.keys()|y.keys()) if x.get(f)!=y.get(f)]
  if fields:changed.append(dict(brief(b[k]),fields=fields,before={f:x.get(f) for f in fields},after={f:y.get(f) for f in fields}))
 return {'added':[brief(b[k]) for k in sorted(b.keys()-a.keys())],'removed':[brief(a[k]) for k in sorted(a.keys()-b.keys())],'changed':changed,'catalogChanged':sorted_records(before.get('catalog',[]))!=sorted_records(after.get('catalog',[]))}
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(re.sub('[\ue000-\uf8ff]','•',json.dumps(value,ensure_ascii=False,indent=2))+'\n');tmp.replace(path)
def archive(directory,previous,payload,stamp,content,delta,metadata=None):
 """Mutate revision metadata only; never append history for a check-only update."""
 if previous and encoded(content(previous))==encoded(content(payload)):
  for k in ['revision','lastChangedAt']:
   if k in previous:payload[k]=previous[k]
  return False
 directory=Path(directory);indexfile=directory/'index.json';index=json.loads(indexfile.read_text()) if indexfile.exists() else []
 if previous and not index:
  atomic_json(directory/'baseline.json',previous)
  index.append({'id':'baseline','path':directory.name+'/baseline.json','checkedAt':previous.get('retrievedAt') or previous.get('cmsCheckedAt') or previous.get('builtAt'),'changes':{'added':[],'removed':[],'changed':[]},'baseline':True})
 revision=datetime.fromisoformat(stamp.replace('Z','+00:00')).strftime('%Y%m%dT%H%M%S%fZ')
 payload['revision']=revision;payload['lastChangedAt']=stamp
 atomic_json(directory/(revision+'.json'),payload)
 index.insert(0,dict(metadata or {},id=revision,path=directory.name+'/'+revision+'.json',checkedAt=stamp,changes=delta))
 atomic_json(indexfile,index)
 return True
