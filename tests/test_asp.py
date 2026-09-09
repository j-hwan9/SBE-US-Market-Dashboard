import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('asp',Path(__file__).resolve().parents[1]/'scripts/asp.py');asp=importlib.util.module_from_spec(s);s.loader.exec_module(asp)
class ASPTests(unittest.TestCase):
 def pair(self,q='2023 Q1',notes=''):
  common=dict(quarter=q,molecule='Trastuzumab',billingUnit='10 MG',standardDose='420mg/vial',notes='')
  return [dict(common,brand='Herceptin',kind='reference',paymentLimit=106),dict(common,brand='Ontruzant',kind='biosimilar',paymentLimit=58,notes=notes)]
 def test_addon_requires_cms_evidence(self):
  self.assertEqual(asp.derive(self.pair())[1]['estimatedAsp'],52)
  self.assertEqual(asp.derive(self.pair(notes='8% of reference add-on applied'))[1]['estimatedAsp'],50)
  self.assertEqual(asp.derive(self.pair(q='2021 Q1',notes='8% of reference add-on applied'))[1]['addonPct'],6)
 def test_non_asp_and_missing_reference(self):
  for note in ['AMP-based payment limit','WAC-based payment limit','See COVID-19 vaccine pricing webpage','unrecognized note']:
   self.assertIsNone(asp.derive(self.pair(notes=note))[1]['estimatedAsp'])
  self.assertIsNone(asp.derive(self.pair()[1:])[0]['estimatedAsp'])
 def test_billing_alignment(self):
  rows=self.pair();rows[1]['billingUnit']='1 MG';rows[1]['paymentLimit']=5.8
  self.assertEqual(asp.derive(rows)[1]['estimatedAsp'],5.2)
  rows=self.pair();rows[1]['billingUnit']='100 units'
  self.assertIsNone(asp.derive(rows)[1]['estimatedAsp'])
 def test_standard_units(self):
  self.assertEqual(asp.dose_factor('420mg/vial','10 MG'),42)
  self.assertEqual(asp.dose_factor('300mcg/vial','1 MCG'),300)
  self.assertIsNone(asp.dose_factor('400mg','unknown'))
 def test_current_revision_links(self):
  html='<a href="/files/zip/july-2026-asp-pricing-file.zip">file</a><a href="/files/zip/july-2026-asp-pricing-file.zip">duplicate</a><a href="/files/zip/july-2026-noc-asp-pricing.zip">NOC</a>'
  self.assertEqual(len(asp.discover(html)['2026 Q3']),1)
 def test_ambiguous_reference(self):
  r=self.pair();r.append(dict(r[0],paymentLimit=200));self.assertIsNone(asp.derive(r)[1]['estimatedAsp'])
if __name__=='__main__':unittest.main()
