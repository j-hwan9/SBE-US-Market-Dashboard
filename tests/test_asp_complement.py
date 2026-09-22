import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from asp import build_catalog,map_rows,derive,refresh_catalog

class ComplementTests(unittest.TestCase):
 def test_ravulizumab_cms_mapping_and_300mg(self):
  catalog=build_catalog([])
  raw={'J1303':dict(hcpcs='J1303',description='Injection, ravulizumab-cwvz',billingUnit='10 mg',paymentLimit=106,notes='')}
  rows=derive(map_rows(raw,'2026 Q3','https://www.cms.gov/test.zip','test.xlsx','2026-09-22',catalog))
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['brand'],'Ultomiris')
  self.assertEqual(rows[0]['standardDose'],'300 mg')
  self.assertEqual(rows[0]['standardFactor'],30)
  self.assertEqual(rows[0]['estimatedAsp']*rows[0]['standardFactor'],3000)
 def test_existing_eculizumab_rows_recalculated_without_changing_billing_unit(self):
  rows=[dict(quarter='2026 Q3',molecule='Eculizumab',brand='Soliris',kind='reference',standardDose='2 mg',billingUnit='2 mg',paymentLimit=106,notes='')]
  derive(rows)
  self.assertEqual(rows[0]['billingUnit'],'2 mg')
  self.assertEqual(rows[0]['standardDose'],'300 mg')
  self.assertEqual(rows[0]['standardFactor'],150)
  self.assertEqual(rows[0]['estimatedAsp'],100)
if __name__=='__main__':unittest.main()
