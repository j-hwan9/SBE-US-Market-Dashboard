import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from competitive import canonical,text_state,difference,brand_match,category
class CompetitiveTests(unittest.TestCase):
 def state(self,text,links=[]):return dict(text=text_state(text),links=links,images=[])
 def test_normalization(self):
  self.assertEqual(canonical('https://site.com/hcp?utm_source=x&a=1#top'),'https://site.com/hcp?a=1')
  self.assertIsNone(canonical('javascript:alert(1)'));self.assertIsNone(canonical('http://127.0.0.1/a'))
 def test_diff(self):
  d=difference(self.state('Old eligibility'),self.state('New eligibility'))
  self.assertEqual(d['added'],['New eligibility']);self.assertEqual(d['removed'],['Old eligibility']);self.assertIn('Text',d['types'])
 def test_noise(self):self.assertEqual(difference(self.state('Main content\nCopyright 2025'),self.state('Main content\nCopyright 2026'))['types'],[])
 def test_pdf_same_url_changed(self):
  d=difference(self.state('Main', [dict(url='https://site.com/a.pdf',label='Guide',fileHash='a')]),self.state('Main',[dict(url='https://site.com/a.pdf',label='Guide',fileHash='b')]))
  self.assertIn('PDF updated',d['types'])
 def test_product_boundary(self):
  self.assertTrue(brand_match('Kanjinti','https://www.kanjinti.com/hcp'));self.assertFalse(brand_match('Avsola','NotAvsola'))
 def test_long_text_excerpt_is_inspectable(self):
  chunks=text_state('word '*200);self.assertGreater(len(chunks),1);self.assertTrue(all(len(x['excerpt'])<=220 for x in chunks))
 def test_category(self):self.assertEqual(category('https://site.com/reimbursement'),'Access / support')
if __name__=='__main__':unittest.main()
