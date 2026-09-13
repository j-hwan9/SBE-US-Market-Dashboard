import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from asp_catalog import build_catalog,match_catalog,ndc
import asp
class CatalogTests(unittest.TestCase):
 def products(self):
  return [dict(id=n.lower(),brand=n,bla='1',molecule='denosumab',proper=proper,reference=ref,kind=kind) for n,proper,ref,kind in [('Prolia','denosumab','Prolia','reference'),('Xgeva','denosumab','Xgeva','reference'),('Ospomyv','denosumab-dssb','Prolia','biosimilar'),('Xbryk','denosumab-dssb','Xgeva','biosimilar'),('Conexxence','denosumab-bnht','Prolia','biosimilar')]]
 def test_complete_catalog_and_bla_dedup(self):
  p=self.products();r=build_catalog(p+[dict(p[2],bla='2')]);self.assertEqual(len(r),5);self.assertEqual(next(x for x in r if x['brand']=='Ospomyv')['blas'],['1','2'])
 def test_new_suffix_shared_names(self):
  c=build_catalog(self.products());raw={'Q9991':{'description':'Inj denosumab-dssb, 1 mg'},'Q9992':{'description':'Inj denosumab-bnht, 1 mg'},'J0897':{'description':'Denosumab injection'}}
  m=match_catalog(raw,c);self.assertIn('Q9991',m['ospomyv']);self.assertIn('Q9991',m['xbryk']);self.assertIn('Q9992',m['conexxence']);self.assertNotIn('Q9992',m['prolia']);self.assertIn('J0897',m['prolia'])
 def test_ndc_fallback(self):
  c=build_catalog(self.products());p=next(x for x in c if x['brand']=='Ospomyv');p['ndcs']=['83457001210'];m=match_catalog({'Q9999':{'description':'Abbreviated drug description'}},c,{'Q9999':{'83457001210'}});self.assertIn('Q9999',m['ospomyv'])
 def test_ndc_normalization(self):
  self.assertEqual(ndc('83457-012-10'),'83457001210');self.assertEqual(ndc('1234-5678-90'),'01234567890');self.assertIsNone(ndc('1234567890'))
 def test_no_generic_biosimilar_match(self):
  m=match_catalog({'J0897':{'description':'Denosumab injection'}},build_catalog(self.products()));self.assertEqual(m['ospomyv'],{})
 def test_same_class_reference_and_price(self):
  c=build_catalog(self.products());v=lambda description,pl:dict(description=description,paymentLimit=pl,billingUnit='1 mg',notes='',hcpcs='')
  raw={'J0897':v('Denosumab injection',106),'Q9991':v('Denosumab-dssb',58)}
  for k,r in raw.items():r['hcpcs']=k
  rows=asp.derive(asp.map_rows(raw,'2026 Q3','https://www.cms.gov/files/zip/test.zip','test.xls','2026-09-13',c))
  for brand in ['Ospomyv','Xbryk']:self.assertEqual(next(r for r in rows if r['brand']==brand)['estimatedAsp'],52)
 def test_pooled_identity_withheld(self):
  rows=[dict(quarter='2026 Q3',molecule='Insulin glargine',brand='Lantus',kind='reference',billingUnit='1 unit',standardDose='1 unit',notes='',paymentLimit=106,pooledIdentities=True)]
  self.assertIsNone(asp.derive(rows)[0]['estimatedAsp'])
 def test_all_purple_book_products(self):
  p=json.loads((asp.ROOT/'dist/data.json').read_text())['products'];c=build_catalog(p);self.assertEqual({(x['molecule'],x['brand'],x['reference']) for x in c},{(x['molecule'],x['brand'],x['reference']) for x in p})
if __name__=='__main__':unittest.main()
