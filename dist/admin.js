/* PIN is a convenience UI lock. GA4 authorization is enforced by Google. */
(function(){
 'use strict';
 const $=id=>document.getElementById(id), A=window.DashboardAnalytics;
 const scope='https://www.googleapis.com/auth/analytics.readonly';
 const slots={daily:'adminDaily',tabs:'adminTabs',devices:'adminDevices',sources:'adminSources'};
 let unlocked=false,config={},client=null,token='',expires=0,chart=null,epoch=0,controller=null,gisPromise;
 const num=n=>Number.isFinite(n)?new Intl.NumberFormat('en-US').format(n):'—';
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const status=s=>$('adminStatus').textContent=s;
 function clearReports(message='GA4 연결 후 표시됩니다.'){
  for(const id of ['adminUsers','adminSessions','adminViews','adminDepth'])$(id).textContent='—';
  for(const id of Object.values(slots))$(id).innerHTML='<p class="admin-empty">'+esc(message)+'</p>';
  if(chart){chart.destroy();chart=null;}$('adminChartWrap').hidden=true;
 }
 function cancel(){epoch++;if(controller)controller.abort();controller=null;}
 function connected(){return Boolean(token&&Date.now()<expires);}
 function controls(busy=false){$('adminRefresh').disabled=!connected()||busy;$('adminConnect').disabled=!client||busy;$('adminRange').disabled=busy;$('adminDisconnect').hidden=!token;}
 function dateLabel(s){return /^\d{8}$/.test(s)?new Date(s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8)+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'UTC'}):s;}
 function table(kind,report){
  const rows=A.unpack(report),heads={daily:['Date','Users','Sessions','Views'],tabs:['Tab','Views','Users'],devices:['Device','Sessions','Users'],sources:['Source / Medium','Sessions','Users']}[kind];
  if(!rows.length){$(slots[kind]).innerHTML='<p class="admin-empty">선택한 기간에 수집된 데이터가 없습니다.</p>';return;}
  const label=v=>kind==='daily'?dateLabel(v):kind==='tabs'?(A.TABS[v.split('/').pop()]||v):v;
  $(slots[kind]).innerHTML='<table class="data-table"><thead><tr>'+heads.map(h=>'<th scope="col">'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr><td>'+esc(label(r.label))+'</td>'+r.values.map(v=>'<td>'+num(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
  if(kind==='daily'&&window.Chart){
   $('adminChartWrap').hidden=false;
   chart=new window.Chart($('adminChart'),{type:'line',data:{labels:rows.map(r=>dateLabel(r.label)),datasets:[{label:'Users',data:rows.map(r=>r.values[0]),borderColor:'#345fa5',backgroundColor:'#345fa512',fill:true,tension:.2},{label:'Views',data:rows.map(r=>r.values[2]),borderColor:'#8a69b0',tension:.2}]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},scales:{y:{beginAtZero:true,ticks:{precision:0}}},plugins:{legend:{position:'bottom'}}}});
  }
 }
 async function refresh(){
  if(!unlocked)return;
  if(!connected()){token='';clearReports();status('Google 계정 연결이 필요하거나 만료되었습니다. 다시 연결하세요.');controls();return;}
  cancel();const ticket=epoch;controller=new AbortController();const signal=controller.signal;const accessToken=token;
  clearReports('통계를 불러오는 중입니다.');status('Google Analytics에서 실제 통계를 조회하고 있습니다…');controls(true);
  const kinds=['summary','daily','tabs','devices','sources'];
  const results=await Promise.allSettled(kinds.map(async kind=>{
   const response=await fetch('https://analyticsdata.googleapis.com/v1beta/properties/'+config.propertyId+':runReport',{method:'POST',headers:{Authorization:'Bearer '+accessToken,'Content-Type':'application/json'},body:JSON.stringify(A.reportBody(kind,$('adminRange').value)),signal});
   const data=await response.json();
   if(!response.ok){const err=new Error(response.status===401?'Google 연결이 만료되었습니다. 다시 연결하세요.':response.status===403?'GA4 속성 조회 권한, Data API 활성화 및 OAuth 동의 설정을 확인하세요.':response.status===429?'GA4 조회 한도에 도달했습니다. 잠시 후 다시 시도하세요.':'GA4 조회 실패: '+(data.error?.message||response.status));err.status=response.status;throw err;}
   return data;
  }));
  if(ticket!==epoch||!unlocked)return;
  const errors=[],metadata=[];
  results.forEach((result,i)=>{
   const kind=kinds[i];
   if(result.status==='rejected'){
    errors.push(result.reason.message);if(result.reason.status===401){token='';expires=0;}
    if(slots[kind])$(slots[kind]).innerHTML='<p class="admin-empty admin-error">'+esc(result.reason.message)+'</p>';return;
   }
   const report=result.value;metadata.push(report.metadata||{});
   if(kind==='summary'){
    const v=A.unpack(report)[0]?.values||[0,0,0];
    $('adminUsers').textContent=num(v[0]);$('adminSessions').textContent=num(v[1]);$('adminViews').textContent=num(v[2]);$('adminDepth').textContent=v[1]>0?(v[2]/v[1]).toFixed(2):'—';
   }else table(kind,report);
  });
  const timezone=metadata.find(m=>m.timeZone)?.timeZone||'GA4 속성 시간대';
  const caution=metadata.some(m=>m.subjectToThresholding)?' · 개인정보 보호 임계값으로 일부 데이터가 제한될 수 있습니다.':'';
  status(errors.length?'일부 또는 전체 지표를 불러오지 못했습니다. '+[...new Set(errors)].join(' '):'조회 완료 · '+timezone+' · '+new Date().toLocaleString('en-US',{month:'short',day:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Seoul'})+' KST'+caution);
  controls();
 }
 function loadIdentity(){
  if(window.google?.accounts?.oauth2)return Promise.resolve();
  if(gisPromise)return gisPromise;
  gisPromise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://accounts.google.com/gsi/client';s.async=true;const timer=setTimeout(()=>reject(Error('Google 로그인 로딩 지연. 네트워크 확인 후 페이지를 새로고침하세요.')),15000);s.onload=()=>{clearTimeout(timer);resolve();};s.onerror=()=>{clearTimeout(timer);reject(Error('Google 로그인 스크립트를 불러오지 못했습니다. 회사 네트워크 허용 여부를 확인하세요.'));};document.head.append(s);});return gisPromise;
 }
 async function setup(){
  config=await A.ready;if(!unlocked)return;
  const measurement=/^G-[A-Z0-9]+$/.test(config.measurementId||'');
  if(!/^\d+$/.test(config.propertyId||'')||!/^[-\w.]+\.apps\.googleusercontent\.com$/.test(config.oauthClientId||'')){
   status(config.configError|| (measurement?'방문 수집 설정 완료 · 관리자 조회를 위해 속성 ID와 OAuth 클라이언트 ID를 설정하세요.':'GA4 미연결 · 아래 안내에 따라 설정하면 방문 수집과 통계 조회를 시작할 수 있습니다.'));
   $('adminSetup').open=true;return;
  }
  if(connected()){controls();return;}
  status('Google 계정 연결을 준비하고 있습니다…');
  try{
   await loadIdentity();if(!unlocked)return;
   client=window.google.accounts.oauth2.initTokenClient({client_id:config.oauthClientId,scope,callback:response=>{
    if(!unlocked)return;
    if(response.error||!response.access_token){status('Google 연결을 완료하지 못했습니다. 다시 연결하세요.');controls();return;}
    if(!window.google.accounts.oauth2.hasGrantedAllScopes(response,scope)){status('Analytics 읽기 권한에 동의해야 통계를 조회할 수 있습니다.');controls();return;}
    token=response.access_token;expires=Date.now()+Number(response.expires_in||3600)*1000-30000;controls();refresh();
   },error_callback:()=>{if(unlocked){status('Google 로그인 창이 닫혔거나 열리지 않았습니다. 다시 연결하세요.');controls();}}});
   status('Google 계정을 연결하면 통계를 조회합니다.'+(measurement?'':' 측정 ID가 비어 있어 새 방문은 아직 수집하지 않습니다.'));controls();
  }catch(e){if(unlocked)status(e.message);}
 }
 function lock(){unlocked=false;cancel();token='';expires=0;client=null;clearReports();$('adminUnlocked').hidden=true;$('adminLocked').hidden=false;$('adminPin').value='';$('adminPinError').textContent='';controls();}
 $('adminPinForm').addEventListener('submit',e=>{e.preventDefault();if($('adminPin').value!=='970513'){$('adminPinError').textContent='PIN이 일치하지 않습니다.';$('adminPin').value='';$('adminPin').focus();return;}unlocked=true;$('adminPin').value='';$('adminPinError').textContent='';$('adminLocked').hidden=true;$('adminUnlocked').hidden=false;setup();});
 $('adminLock').addEventListener('click',lock);
 $('adminConnect').addEventListener('click',()=>{if(client){controls(true);status('Google 로그인 창에서 계정을 선택하세요.');client.requestAccessToken({prompt:'select_account'});}});
 $('adminDisconnect').addEventListener('click',()=>{const old=token;cancel();token='';expires=0;clearReports();controls();status('연결을 해제했습니다. 다시 연결하면 통계를 조회할 수 있습니다.');if(old)window.google?.accounts?.oauth2.revoke(old,()=>{});});
 $('adminRefresh').addEventListener('click',refresh);$('adminRange').addEventListener('change',()=>{if(connected())refresh();});
 window.addEventListener('hashchange',()=>{if(location.hash!=='#admin'&&unlocked)lock();});
 clearReports();window.AdminDashboard={open(){if(!unlocked)$('adminPin').focus();}};
})();
