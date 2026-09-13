"""Real browser fixture: long lazy-loaded document, removable promotion, protected gate."""
import asyncio,sys,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from competitive_capture import prepare_page,full_screenshot
from playwright.async_api import async_playwright
from PIL import Image
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  page=await browser.new_page(viewport={'width':1280,'height':900})
  await page.set_content('''<main style="height:6500px">Top of page<div id="bottom" style="position:absolute;top:6100px">Bottom evidence</div></main><div role="dialog" style="position:fixed;inset:100px;background:white;z-index:100"><p>Coverage expansion effective September 1</p><a href="https://example.com/coverage.pdf">Coverage guide</a><button aria-label="Close" onclick="this.parentNode.remove()">×</button></div><script>addEventListener('scroll',()=>{if(scrollY>3000)document.getElementById('bottom').textContent='Lazy loaded bottom evidence'})</script>''')
  popups,warnings=await prepare_page(page)
  assert len(popups)==1 and popups[0]['closed'] and popups[0]['image']
  assert 'Coverage expansion' in popups[0]['text'] and len(popups[0]['links'])==1
  assert not warnings and await page.locator('[role=dialog]').count()==0
  assert 'Lazy loaded' in await page.locator('#bottom').inner_text()
  img=Image.open(io.BytesIO(await full_screenshot(page)))
  assert img.height>=6500 and img.width==1280
  await page.set_content('<div role="dialog" style="position:fixed;inset:50px">Are you a healthcare professional?<button>Yes</button></div>')
  try:await prepare_page(page)
  except ValueError:pass
  else:raise AssertionError('Professional gate was not detected')
  await browser.close()
 print('Full-page, lazy loading, popup evidence/text/links, dismissal and protected-gate checks passed.')
asyncio.run(main())
