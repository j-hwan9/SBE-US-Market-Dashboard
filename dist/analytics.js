/* Public identifiers only. GA access tokens and reports are never persisted. */
(function(root){
 'use strict';
 const HOST='j-hwan9.github.io', BASE='/SBE-US-Market-Dashboard/';
 const TABS={home:'Home',regulatory:'Regulatory information',news:'Market news',prices:'Price tracker',competitive:'Competitive intelligence',performance:'Performance tracker'};
 function route(hash){const key=(hash||'').replace(/^#/,'')||'home';return key==='admin'?null:Object.hasOwn(TABS,key)?key:'home';}
 function reportBody(kind,range){
  const metrics={summary:['totalUsers','sessions','screenPageViews'],daily:['totalUsers','sessions','screenPageViews'],tabs:['screenPageViews','totalUsers'],devices:['sessions','totalUsers'],sources:['sessions','totalUsers']};
  const dimensions={daily:'date',tabs:'pagePath',devices:'deviceCategory',sources:'sessionSourceMedium'};
  if(!metrics[kind])throw Error('Unknown report');
  const days=['7','30','90'].includes(String(range))?String(range):'7';
  const body={dateRanges:[range==='today'?{startDate:'today',endDate:'today'}:{startDate:days+'daysAgo',endDate:'yesterday'}],metrics:metrics[kind].map(name=>({name})),dimensionFilter:{andGroup:{expressions:[{filter:{fieldName:'hostName',stringFilter:{matchType:'EXACT',value:HOST}}},{filter:{fieldName:'pagePath',stringFilter:{matchType:'BEGINS_WITH',value:BASE+'tab/'}}}]}},limit:'1000'};
  if(dimensions[kind])body.dimensions=[{name:dimensions[kind]}];
  if(kind==='daily')body.orderBys=[{dimension:{dimensionName:'date'}}];
  else if(kind!=='summary')body.orderBys=[{metric:{metricName:metrics[kind][0]},desc:true}];
  return body;
 }
 function unpack(report){return (report.rows||[]).map(row=>({label:(row.dimensionValues||[])[0]?.value||'',values:(row.metricValues||[]).map(x=>Number(x.value))}));}
 const api={HOST,BASE,TABS,route,reportBody,unpack};
 if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
 let configured=false,last=null,config={};
 function track(){
  const tab=route(location.hash);
  if(!/^G-[A-Z0-9]+$/.test(config.measurementId||'')||location.hostname!==HOST||!location.pathname.startsWith(BASE))return;
  root['ga-disable-'+config.measurementId]=tab===null;
  if(tab===null){last=null;return;}
  if(!configured){
   configured=true;root.dataLayer=root.dataLayer||[];root.gtag=function(){root.dataLayer.push(arguments);};
   root.gtag('js',new Date());root.gtag('config',config.measurementId,{send_page_view:false,allow_google_signals:false,allow_ad_personalization_signals:false});
   const script=document.createElement('script');script.async=true;script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(config.measurementId);document.head.append(script);
  }
  if(tab===last)return;
  last=tab;
  root.gtag('event','page_view',{page_title:TABS[tab],page_location:'https://'+HOST+BASE+'tab/'+tab});
 }
 api.ready=fetch('analytics-config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('통계 설정 파일을 불러오지 못했습니다.');return r.json();}).then(c=>{config=c;track();return c;}).catch(e=>({configError:e.message}));
 root.addEventListener('hashchange',track);root.DashboardAnalytics=api;
})(typeof window!=='undefined'?window:globalThis);
