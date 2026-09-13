import asyncio,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from competitive_capture import prepare_page,OVERLAYS,full_screenshot
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True)
  page=await browser.new_page(viewport={'width':1280,'height':900})
  await page.goto('https://www.simlandihcp.com/',wait_until='domcontentloaded')
  await page.wait_for_timeout(3500)
  await page.evaluate(OVERLAYS)
  print('TEVA_CONTROLS',await page.evaluate('''()=>[...document.querySelectorAll('[data-ci-overlay]')].map(e=>({tag:e.tagName,id:e.id,cls:e.className,controls:[...e.querySelectorAll('button,a,[role="button"],svg,[class*="close" i],[class*="dismiss" i]')].map(x=>x.outerHTML.slice(0,1500))}))'''),flush=True)
  popups,warnings=await prepare_page(page)
  print('TEVA_RESULT',json.dumps({'warnings':warnings,'popups':[{k:v for k,v in x.items() if k!='image'} for x in popups]}),flush=True)
  print('TEVA_SCROLL',await page.evaluate('''()=>[...document.querySelectorAll('body *')].filter(e=>e.scrollHeight>e.clientHeight+200&&e.clientHeight>80).map(e=>({tag:e.tagName,id:e.id,cls:e.className,scroll:e.scrollHeight,client:e.clientHeight,overflow:getComputedStyle(e).overflowY,position:getComputedStyle(e).position})).slice(0,20)'''),flush=True)
  from PIL import Image
  import io
  height=Image.open(io.BytesIO(await full_screenshot(page))).height
  print('TEVA_FULL_HEIGHT',height,flush=True)
  assert height>2400,'Nested safety panel was not captured in full'
  assert any('coverage is expanding' in x['text'] for x in popups),'Promotional text evidence missing'
  await browser.close()
  assert not warnings,'Teva overlay still blocks capture'
asyncio.run(main())
