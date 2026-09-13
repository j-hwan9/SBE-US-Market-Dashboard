"""Capture public pages with inspectable popup evidence and full-page screenshots."""
import re

OVERLAYS = r'''() => {
 document.querySelectorAll('[data-ci-overlay]').forEach(e=>e.removeAttribute('data-ci-overlay'));
 const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>180&&r.height>80&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)!==0};
 const nodes=[...document.querySelectorAll('[role="dialog"],dialog,[aria-modal="true"],[class*="modal" i],[id*="modal" i],[class*="popup" i],[id*="popup" i],[class*="pop-up" i],[id*="onetrust-banner"],[class*="cookie-banner" i]')].filter(visible);
 const candidates=nodes.filter(e=>{if(e.closest('header,nav')||e.matches('aside')||e.querySelector('main'))return false;const s=getComputedStyle(e);return e.matches('[role="dialog"],dialog,[aria-modal="true"]')||s.position==='fixed'||Number(s.zIndex)>=20||!!e.querySelector('[aria-label*="close" i],.close,[class*="close" i],[data-dismiss="modal"]')});
 return candidates.filter(e=>!candidates.some(p=>p!==e&&p.contains(e))).map((e,i)=>{e.setAttribute('data-ci-overlay',String(i));return {id:String(i),text:(e.innerText||'').trim(),links:[...e.querySelectorAll('a[href]')].map(a=>({url:a.href,label:(a.innerText||a.title||'').trim(),context:(a.innerText||'').trim()})),cookie:/cookie|onetrust|consent/i.test(e.id+' '+e.className)||/cookies.*personaliz|non-essential cookies/i.test(e.innerText)}});
}'''
GATE=re.compile(r'verify.{0,30}(human|identity)|captcha|are you.{0,50}(healthcare|health care|medical professional)|confirm.{0,50}(healthcare|health care|professional)|sign in to access|log in to access',re.I)

async def prepare_page(page, evidence=True):
 """Dismiss only ordinary close/reject controls; never satisfy access attestations."""
 popups=[];warnings=[]
 for _ in range(3):
  overlays=sorted(await page.evaluate(OVERLAYS),key=lambda x:not x['cookie'])
  if not overlays:break
  progressed=False
  for item in overlays:
   box=page.locator('[data-ci-overlay="'+item['id']+'"]')
   if not await box.is_visible():continue
   if GATE.search(item['text']):raise ValueError('Professional/identity verification gate: manual review required')
   popup={'text':item['text'],'links':item['links'],'cookie':item['cookie'],'closed':False}
   if evidence and not item['cookie']:
    popup['image']=await page.screenshot(type='jpeg',quality=65,animations='disabled',timeout=20000)
   buttons=box.get_by_role('button',name=re.compile(r'^(reject( all)?( non-essential cookies)?|reject non-essential|only necessary|necessary only|decline( all)?|close|dismiss|×|✕|x)$',re.I))
   if not await buttons.count():buttons=box.locator('[aria-label*="close" i],[title*="close" i],.close,[class*="close" i],[data-dismiss="modal"],[data-bs-dismiss="modal"]')
   for button in await buttons.all():
    if not await button.is_visible():continue
    try:
     await button.click(timeout=2000)
     try:await box.wait_for(state='hidden',timeout=2500)
     except Exception:pass
     popup['closed']=not await box.is_visible()
     if popup['closed']:progressed=True;break
    except Exception:continue
   if not item['cookie'] and not any(p['text']==popup['text'] for p in popups):popups.append(popup)
   if not popup['closed']:warnings.append('Visible overlay could not be dismissed: '+item['text'][:100])
  if not progressed:break
 remaining=await page.evaluate(OVERLAYS)
 warnings=['Visible overlay could not be dismissed: '+x['text'][:100] for x in remaining]
 if not remaining:
  # Expand nested scroll panels, including fixed Important Safety Information drawers.
  await page.evaluate('''()=>{
   for(const root of [document.documentElement,document.body]){root.style.setProperty('overflow','visible','important');root.style.setProperty('height','auto','important');root.style.setProperty('max-height','none','important')}
   for(let pass=0;pass<3;pass++)for(const e of [...document.querySelectorAll('body *')].reverse()){
    const r=e.getBoundingClientRect(),s=getComputedStyle(e);
    if(r.width<200||e.clientHeight<80||e.scrollHeight<e.clientHeight+100||e.closest('[role="dialog"],dialog,[aria-modal="true"],nav'))continue;
    if(!/auto|scroll|hidden/.test(s.overflowY)&&!['fixed','sticky'].includes(s.position))continue;
    const height=e.scrollHeight;e.style.setProperty('height',height+'px','important');e.style.setProperty('max-height','none','important');e.style.setProperty('overflow','visible','important');
    if(['fixed','sticky'].includes(s.position)){e.style.setProperty('position','relative','important');e.style.setProperty('top','auto','important');e.style.setProperty('bottom','auto','important')}
   }
  }''')
 # Trigger images/sections that load only while scrolling. Never remove overlays by CSS.
 complete=False
 for _ in range(90):
  at_bottom=await page.evaluate('''()=>{window.scrollBy(0,Math.max(600,innerHeight-150));return scrollY+innerHeight>=document.documentElement.scrollHeight-2}''')
  await page.wait_for_timeout(120)
  if at_bottom:
   await page.wait_for_timeout(300)
   if await page.evaluate('scrollY+innerHeight>=document.documentElement.scrollHeight-2'):
    complete=True;break
 if not complete:warnings.append('Lazy-load scroll limit reached; full document captured but some lazy content may be incomplete')
 await page.evaluate('window.scrollTo(0,0)')
 await page.wait_for_timeout(250)
 await page.evaluate("()=>document.querySelectorAll('video,audio').forEach(v=>{v.pause();try{v.currentTime=0}catch(e){}})")
 await page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}')
 return popups,list(dict.fromkeys(warnings))

async def full_screenshot(page):
 return await page.screenshot(type='jpeg',quality=65,full_page=True,animations='disabled',timeout=45000)
