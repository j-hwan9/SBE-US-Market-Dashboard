import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from asp import build_catalog,map_rows,derive

class GranixTests(unittest.TestCase):
 def test_granix_is_separate_from_neupogen_and_uses_300mcg(self):
  catalog=build_catalog([])
  catalog.append(dict(id='neupogen',molecule='filgrastim',brand='Neupogen',proper='filgrastim',reference='Neupogen',kind='reference',company='Amgen',own=False,blas=[],ndcs=[],productNdcs=[],approvalDates=[]))
  raw={'J1447':dict(hcpcs='J1447',description='Injection, tbo-filgrastim',billingUnit='1 MCG',paymentLimit=1.06,notes=''),'J1442':dict(hcpcs='J1442',description='Injection, filgrastim',billingUnit='1 MCG',paymentLimit=2.12,notes='')}
  rows=derive(map_rows(raw,'2026 Q3','https://www.cms.gov/test.zip','test.xlsx','2026-09-22',catalog))
  self.assertEqual({(r['brand'],r['hcpcs']) for r in rows},{('Granix','J1447'),('Neupogen','J1442')})
  granix=next(r for r in rows if r['brand']=='Granix')
  self.assertEqual(granix['kind'],'standalone')
  self.assertEqual(granix['standardFactor'],300)
  self.assertEqual(granix['estimatedAsp'],1)
if __name__=='__main__':unittest.main()
