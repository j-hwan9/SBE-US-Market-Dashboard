const {chromium}=require('/tmp/dashboard-browser-check/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/analytics-config.json',r=>r.fulfill({json:{measurementId:'',propertyId:'',oauthClientId:''}}));
  await page.goto('http://127.0.0.1:8765/#admin');
  await page.locator('#adminPin').fill('000000');await page.locator('#adminPinForm button').click();
  assert.match(await page.locator('#adminPinError').innerText(),/일치하지/);assert.equal(await page.locator('#adminUnlocked').isVisible(),false);
  await page.locator('#adminPin').fill('970513');await page.locator('#adminPinForm button').click();
  await page.waitForFunction(()=>document.querySelector('#adminStatus').textContent.includes('GA4 미연결'));
  assert.equal(await page.locator('#adminUsers').innerText(),'—');assert.equal(await page.locator('#adminConnect').isDisabled(),true);
  await page.screenshot({path:'/tmp/admin-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
  await page.screenshot({path:'/tmp/admin-mobile.png',fullPage:true});
  await page.locator('#adminLock').click();assert.equal(await page.locator('#adminLocked').isVisible(),true);
  await page.locator('.section-tabs a[href="#home"]').click();await page.locator('#landingPage').waitFor({state:'visible'});assert.equal(await page.locator('#adminPage').isVisible(),false);
  for(const [route,id] of [['regulatory','regulatoryPage'],['news','newsPage'],['prices','pricePage']]){await page.locator('.section-tabs a[href="#'+route+'"]').click();await page.locator('#'+id).waitFor({state:'visible'});}
  // Auth/API fixtures are only used here, never in production data or configuration.
  await page.route('**/analytics-config.json',r=>r.fulfill({json:{measurementId:'G-TEST123',propertyId:'12345',oauthClientId:'test.apps.googleusercontent.com'}}));
  await page.route('https://accounts.google.com/gsi/client',r=>r.fulfill({contentType:'text/javascript',body:`window.google={accounts:{oauth2:{initTokenClient(c){return {requestAccessToken(){c.callback({access_token:'test-only-token',expires_in:3600})}}},hasGrantedAllScopes(){return true},revoke(t,cb){cb()}}}};`}));
  let denied=false;const requests=[];
  await page.route('https://analyticsdata.googleapis.com/**',r=>{
   if(denied)return r.fulfill({status:403,json:{error:{message:'denied'}}});
   const body=r.request().postDataJSON();requests.push(body);
   assert.equal(r.request().headers().authorization,'Bearer test-only-token');
   const dim=body.dimensions?.[0]?.name;
   const row=(label,values)=>({dimensionValues:label?[{value:label}]:[],metricValues:values.map(value=>({value:String(value)}))});
   const rows=dim==='date'?[row('20260914',[2,3,4]),row('20260915',[2,3,6])]:dim==='pagePath'?[row('/SBE-US-Market-Dashboard/tab/news',[10,3])]:dim==='deviceCategory'?[row('desktop',[6,3])]:dim==='sessionSourceMedium'?[row('<unsafe> / referral',[6,3])]:[row('',[3,6,10])];
   return r.fulfill({json:{rows,metadata:{timeZone:'Asia/Seoul'}}});
  });
  await page.goto('http://127.0.0.1:8765/#admin');
  await page.reload(); // Hash-only navigation keeps the previous config promise; reload to apply test config.
  await page.locator('#adminPin').fill('970513');await page.locator('#adminPinForm button').click();
  await page.waitForFunction(()=>!document.querySelector('#adminConnect').disabled);await page.locator('#adminConnect').click();
  await page.waitForFunction(()=>document.querySelector('#adminStatus').textContent.includes('조회 완료'));
  assert.equal(await page.locator('#adminUsers').innerText(),'3'); // daily sum=4, whole period=3.
  assert.equal(await page.locator('#adminDepth').innerText(),'1.67');
  assert.match(await page.locator('#adminTabs').innerText(),/Market news/);assert.equal(await page.locator('#adminSources unsafe').count(),0);
  assert.equal(await page.locator('#adminChartWrap').isVisible(),true);assert.equal(requests.length,5);
  await page.locator('#adminRange').selectOption('30');await page.waitForFunction(()=>!document.querySelector('#adminRefresh').disabled);
  assert.equal(requests.at(-1).dateRanges[0].startDate,'30daysAgo');
  denied=true;await page.locator('#adminRefresh').click();await page.waitForFunction(()=>document.querySelector('#adminStatus').textContent.includes('권한'));
  assert.equal(await page.locator('#adminUsers').innerText(),'—');
  await page.locator('.section-tabs a[href="#home"]').click();
  await page.locator('.section-tabs a[href="#admin"]').click();await page.locator('#adminPage').waitFor({state:'visible'});assert.equal(await page.locator('#adminLocked').isVisible(),true);
  assert.equal(await page.evaluate(()=>JSON.stringify(localStorage).includes('test-only-token')),false);
  assert.deepEqual(errors,[]);console.log('Admin browser verified: PIN, mobile, existing routes, no fake data, OAuth reports, period totals, escaped content, failure clears stale stats, lock clears access.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
