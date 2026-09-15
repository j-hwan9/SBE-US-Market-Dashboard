import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from snapshot_history import archive,regulatory_content,asp_content,asp_changes,encoded
class SnapshotHistoryTests(unittest.TestCase):
 def reg(self):return {'schemaVersion':2,'retrievedAt':'2026-09-01T00:00:00Z','products':[{'id':'p1','brand':'A','piCheckedAt':'old','presentations':[{'Strength':'10mg'},{'Strength':'20mg'}],'labels':[{'sourceHash':'a','spl_version':1}],'approvalLetter':{'checkedAt':'old','facts':[]}}]}
 def asp(self):return {'schemaVersion':1,'cmsCheckedAt':'old','catalog':[{'id':'a'}],'rows':[{'productId':'a','brand':'A','quarter':'2026 Q3','hcpcs':'Q1','paymentLimit':10,'sourceCheckedAt':'old'}]}
 def test_unchanged_regulatory_check_does_not_create_archive(self):
  old=self.reg();new=copy.deepcopy(old);new['retrievedAt']='new';new['products'][0]['piCheckedAt']='new';new['products'][0]['approvalLetter']['checkedAt']='new';new['products'][0]['presentations'].reverse();new['purpleBookDate']='2026-10'
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'history';self.assertFalse(archive(p,old,new,'2026-09-02T00:00:00Z',regulatory_content,{}));self.assertFalse(p.exists())
 def test_changed_source_hash_and_version_are_material(self):
  old=self.reg();new=copy.deepcopy(old);new['products'][0]['labels'][0]['sourceHash']='b'
  self.assertNotEqual(encoded(regulatory_content(old)),encoded(regulatory_content(new)))
 def test_archive_baseline_changed_and_repeated_checks(self):
  old=self.reg();new=copy.deepcopy(old);new['products'][0]['presentations'][0]['Strength']='15mg'
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'history';self.assertTrue(archive(p,old,new,'2026-09-02T00:00:00Z',regulatory_content,{'changed':['Strength']}))
   self.assertEqual(json.loads((p/'baseline.json').read_text()),old)
   index=json.loads((p/'index.json').read_text());self.assertEqual(len(index),2);self.assertEqual(json.loads((p/(new['revision']+'.json')).read_text())['products'],new['products'])
   raw=(p/'index.json').read_bytes();same=copy.deepcopy(new);same['retrievedAt']='newer'
   self.assertFalse(archive(p,new,same,'2026-09-03T00:00:00Z',regulatory_content,{}));self.assertEqual((p/'index.json').read_bytes(),raw);self.assertEqual(same['revision'],new['revision'])
   later=copy.deepcopy(new);later['products'][0]['labels'][0]['spl_version']=2
   self.assertTrue(archive(p,new,later,'2026-09-04T00:00:00Z',regulatory_content,{'changed':['PI']}));self.assertEqual(len(json.loads((p/'index.json').read_text())),3)
 def test_asp_metadata_only_check_does_not_archive(self):
  old=self.asp();new=copy.deepcopy(old);new['cmsCheckedAt']='new';new['builtAt']='new';new['rows'][0]['sourceCheckedAt']='new';new['files']=[{'checkedAt':'new','sha256':'changed ZIP metadata'}]
  with tempfile.TemporaryDirectory() as td:self.assertFalse(archive(Path(td)/'asp-history',old,new,'2026-09-02T00:00:00Z',asp_content,asp_changes(old,new)))
 def test_asp_price_change_has_before_after_and_full_snapshot(self):
  old=self.asp();new=copy.deepcopy(old);new['rows'][0]['paymentLimit']=9
  delta=asp_changes(old,new);self.assertEqual(delta['changed'][0]['before']['paymentLimit'],10);self.assertEqual(delta['changed'][0]['after']['paymentLimit'],9)
  with tempfile.TemporaryDirectory() as td:self.assertTrue(archive(Path(td)/'asp-history',old,new,'2026-09-02T00:00:00Z',asp_content,delta))
 def test_asp_catalog_and_removed_rows_are_material(self):
  old=self.asp();new=copy.deepcopy(old);new['rows']=[];new['catalog'].append({'id':'b'})
  d=asp_changes(old,new);self.assertTrue(d['catalogChanged']);self.assertEqual(len(d['removed']),1);self.assertNotEqual(encoded(asp_content(old)),encoded(asp_content(new)))
if __name__=='__main__':unittest.main()
