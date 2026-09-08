import unittest,sys,pathlib,json,copy,tempfile,argparse
from unittest.mock import patch
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from refresh import discover_latest,read_purple,changes,validate,refresh,CollectionError
class RefreshTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((ROOT/'dist/data.json').read_text())
 def test_latest_official_month_not_future(self):
  html=''.join(f'<a href="https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-{m}-data-download.csv">CSV</a>' for m in ['July','August','December'])
  month,url=discover_latest(html,datetime(2026,9,8,tzinfo=timezone.utc));self.assertEqual(month,'2026-08');self.assertIn('August',url)
 def test_full_section_not_changes_section(self):
  ps,rows=read_purple((ROOT/'data/purplebook.csv').read_bytes());self.assertEqual(len(ps),130);self.assertEqual(len(rows),315);self.assertNotIn('103737',{p['bla'] for p in ps})
 def test_material_change_not_check_timestamp(self):
  new=copy.deepcopy(self.data);new['retrievedAt']='2030-01-01';self.assertFalse(changes(self.data,new)['changed'])
  new['products'][0]['presentations'][0]['Inter. Approval Date']='01-Jan-30'
  self.assertIn('Interchangeability',changes(self.data,new)['changed'][0]['fields'])
 def test_large_loss_rejected(self):
  bad=copy.deepcopy(self.data);bad['products']=bad['products'][:3]
  with self.assertRaises(CollectionError):validate(bad,self.data)
 def test_missing_reference_rejected(self):
  bad=copy.deepcopy(self.data);bad['products']=[p for p in bad['products'] if p['brand']!='Humira']
  with self.assertRaises(CollectionError):validate(bad,{})
 def test_snapshot_has_complete_pi(self):self.assertTrue(validate(self.data,{}))
 def test_source_failure_preserves_published_bytes(self):
  with tempfile.TemporaryDirectory() as td:
   path=pathlib.Path(td)/'data.json';raw=json.dumps(self.data).encode();path.write_bytes(raw)
   args=argparse.Namespace(output=td,force=False,check_only=False,catalog_only=False,workers=1)
   with patch('refresh.Sources.get',side_effect=CollectionError('source unavailable')):
    with self.assertRaises(CollectionError):refresh(args)
   self.assertEqual(path.read_bytes(),raw)
if __name__=='__main__':unittest.main()
