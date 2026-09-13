"""Purple Book product universe and auditable CMS HCPCS identity matching."""
import re
from datetime import datetime

def norm(s):return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def token(text,word):return bool(word and re.search(r'(?<![a-z0-9])'+re.escape(norm(word))+r'(?![a-z0-9])',norm(text)))
def ndc(s,product=False):
 s=str(s).strip();parts=s.split('-')
 if len(parts)==3 and all(p.isdigit() for p in parts):
  a,b,c=parts
  if len(a)<=5 and len(b)<=4 and len(c)<=2:return a.zfill(5)+b.zfill(4)+c.zfill(2)
 if len(parts)==2 and product and all(p.isdigit() for p in parts) and len(parts[0])<=5 and len(parts[1])<=4:return parts[0].zfill(5)+parts[1].zfill(4)
 if re.fullmatch(r'\d{11}',s):return s
 return None

def build_catalog(products,portfolio=()):
 own={norm(p['name']) for p in portfolio};groups={}
 for p in products:
  key=(p['molecule'],norm(p['brand']),norm(p['reference']))
  if key not in groups:groups[key]={'id':p['id'],'molecule':p['molecule'],'brand':p['brand'],'proper':p['proper'],'reference':p['reference'],'kind':p['kind'],'company':p.get('applicant',''),'own':norm(p['brand']) in own,'blas':[],'ndcs':[],'productNdcs':[],'routes':[],'approvalDates':[]}
  row=groups[key];row['blas'].append(str(p['bla']))
  for presentation in p.get('presentations',[]):
   for fmt in ['%d-%b-%y','%d-%b-%Y','%Y-%m-%d']:
    try:row['approvalDates'].append(datetime.strptime(presentation.get('Approval Date',''),fmt).strftime('%Y-%m-%d'));break
    except ValueError:pass
  row['routes'].extend(v.get('Route of Administration','') for v in p.get('presentations',[]))
  for label in p.get('labels',[]):
   for drug in label.get('products',[]):
    n=ndc(drug.get('productNdc',''),product=True)
    if n:row['productNdcs'].append(n)
    for pack in drug.get('packages',[]):
     n=ndc(pack.get('ndc',''))
     if n:row['ndcs'].append(n)
  for field in ['blas','ndcs','productNdcs','routes','approvalDates']:row[field]=sorted(set(row[field]))
 return sorted(groups.values(),key=lambda r:(r['molecule'],r['kind']!='reference',r['brand'],r['reference']))

def suffix(p):
 m=re.search(r'-([a-z]{4})$',p['proper'].lower());return m[1] if m else None

def match_catalog(raw,catalog,crosswalk=None):
 crosswalk=crosswalk or {};matches={};by_mol={}
 for p in catalog:by_mol.setdefault(p['molecule'],[]).append(p)
 # Exact label NDC or product-NDC prefixes, distinct brand tokens and FDA suffixes.
 for p in catalog:
  out={};s=suffix(p)
  for code,v in raw.items():
   if s and token(v['description'],s):out[code]='FDA suffix'
   elif norm(p['brand'])!=norm(p['molecule']) and token(v['description'],p['brand']) and not re.search(r'hyaluron|hylecta|high.?dose|\bhd\b|implant',v['description'],re.I):out[code]='Brand name'
   if any(n in p['ndcs'] or n[:9] in p['productNdcs'] for n in crosswalk.get(code,[])):out[code]='DailyMed NDC → CMS crosswalk'
  matches[p['id']]=out
 # Unqualified reference molecule wording only; never assign a biosimilar from
 # molecule alone. Qualifiers/combination products require exact NDC or brand.
 for p in catalog:
  if p['kind']!='reference':continue
  peers=by_mol[p['molecule']];known=[w for x in peers if x['kind']=='biosimilar' for w in [x['brand'],suffix(x)] if w]
  refs=[x for x in peers if x['kind']=='reference']
  shared_ref=len(refs)==1 or p['molecule']=='denosumab'
  if matches[p['id']] or not shared_ref:continue
  for code,v in raw.items():
   text=v['description']
   if token(text,p['molecule']) and not any(token(text,w) for w in known) and not re.search(r'biosim|hyaluron|high dose|\bhd\b|implant|ophthalmic|non.?esrd',text,re.I):matches[p['id']][code]='Unqualified reference molecule'
 return matches
