'use strict';
// Conservative PI extraction: numbers remain tied to their sentence and presentation.
const PIFacts=(()=>{
 const uniq=a=>[...new Set(a.filter(Boolean))];
 const clean=s=>String(s||'').replace(/[\u00ad]/g,'').replace(/[º˚]/g,'°').replace(/[–−]/g,'-').replace(/\s+/g,' ').trim();
 const sentences=s=>clean(s).split(/(?<=[.!?])\s+(?=[A-Z])/).filter(Boolean);
 const types=raw=>{const s=raw.replace(/syringe-type pump/gi,'infusion pump');return uniq([/\bonpro\b|on-body|\bOBI\b/i.test(s)?'On-body injector':null,/autoinjector|auto-injector|\bpen\b/i.test(s)?'Autoinjector / Pen':null,/pre[ -]?filled.{0,15}syringe|\bsyringes?\b|\bPFS\b/i.test(s)?'PFS':null,/\bvials?\b/i.test(s)?'Vial':null,/\bcartridges?\b/i.test(s)?'Cartridge':null]);};
 const paragraphs=l=>['supplied','storage','description','dosage','strengths'].flatMap(k=>(l.sections?.[k]||[]).map(text=>({text:clean(text),section:k})));
 const gaugeRE=/\b(\d{2})(?:\s*[- ]\s*|\s*)gauge\b/gi;
 function needle(p){
 const l=p.labels?.[0];if(!l)return [];
 const found=[];let contextScope='',lastSection='';
 const nt=s=>types(s).filter(t=>t!=='PFS'||/pre[ -]?filled.{0,15}syringe|\bPFS\b/i.test(s));
 for(const {text,section} of paragraphs(l)){
  if(section!==lastSection){contextScope='';lastSection=section;}
  const localTypes=nt(text);if(localTypes.length===1)contextScope=localTypes[0];
  if(!/needle/i.test(text))continue;
  const gauges=[...text.matchAll(gaugeRE)];
  if(!gauges.length&&!/(?:fixed|staked).{0,35}needle|(?:needles?.{0,40}(?:not provided|not included))|(?:supplied|equipped).{0,40}needle/i.test(text))continue;
  const candidates=gauges.length?gauges:[{index:text.search(/needle/i),0:'',1:null}];
  for(const m of candidates){
   const at=m.index,start=Math.max(text.lastIndexOf('. ',at),text.lastIndexOf(';',at));
   const local=text.slice(start<0?0:start+1,Math.min(text.length,at+170));
   const before=local.slice(0,Math.max(0,at-(start<0?0:start+1)));
   const ts=nt(before);let device=ts.at(-1)||nt(local).at(0)||nt(text).at(0)||contextScope||'투여용 needle';
   if(/\bpen\b|autoinjector/i.test(text)&&/containing.{0,65}syringe/i.test(text))device='Autoinjector / Pen';
   if(/onpro|\bOBI\b|on-body/i.test(text))device='On-body injector';
   if(/vial kit|kit with injection components/i.test(text))device='Vial kit';
   const next=text.slice(at+(m[0]||'').length,at+100);
   const role=/filter/i.test(next.split(/\b(?:one|and|a)\b/)[0])?'Filter needle':/filter.{0,15}$/.test(before)?'Filter needle':'Injection needle';
   const excluded=/not (?:provided|included|supplied)/i.test(local);
   const included=/fixed|staked|attached|built.in|equipped with|supplied with/i.test(local)||section==='supplied'&&/with.{0,65}needle|kit with injection components/i.test(text);
   const state=excluded?'미포함':included?'포함':'포함 여부 미기재';
   const strengths=uniq([...before.matchAll(/\b\d+(?:\.\d+)?\s*mg\s*\/\s*\d+(?:\.\d+)?\s*mL/gi)].map(x=>x[0]));
   found.push({scope:device,detail:strengths.join(' / '),gauge:m[1]?m[1]+'G':'Gauge 미기재',included:state,role,evidence:text});
  }
 }
 // Instructions with no identified presentation do not override packaged-component facts.
 let rows=found.filter(r=>r.scope!=='투여용 needle'||!found.some(q=>q.scope!=='투여용 needle'&&q.gauge===r.gauge&&q.role===r.role));
 rows=rows.filter(r=>!(r.included==='포함 여부 미기재'&&rows.some(q=>q!==r&&q.included!=='포함 여부 미기재'&&q.gauge===r.gauge&&q.role===r.role&&(q.scope===r.scope||r.scope==='Vial'&&q.scope==='Vial kit'))));
 const out=[];
 for(const r of rows){const key=[r.scope,r.gauge,r.included,r.role].join('|');const old=out.find(q=>q.key===key);if(old){old.details=uniq([...old.details,r.detail]);}else out.push({...r,key,details:[r.detail]});}
 const declared=types(p.presentations.map(x=>x['Product Presentation']).join(' '));
 for(const t of declared)if(!out.some(r=>r.scope===t||t==='Vial'&&r.scope==='Vial kit'))out.push({scope:t,gauge:'Gauge 미기재',included:'포함 여부 미기재',role:'Needle',details:[]});
 return out.map(r=>({scope:r.scope==='투여용 needle'?'투여용 (제형 미기재)':r.scope,detail:r.details.filter(Boolean).join(' / '),value:r.gauge+' · '+r.included+(r.role==='Filter needle'?' · Filter needle':''),evidence:r.evidence||''}));
 }
 const temperatures=s=>[...s.matchAll(/(?:-?\d+(?:\.\d+)?\s*°?\s*[CF]?\s*(?:to|and|-)\s*)?-?\d+(?:\.\d+)?\s*°\s*[CF]\b/gi)].filter(m=>/C$/i.test(m[0])).map(m=>({index:m.index,text:m[0].replace(/\s+/g,'').replace(/to|and/g,'–').replace(/-/g,'–').replace(/°C–/g,'–')}));
 const durationRE=/\b(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four)(?:\s*(?:to|-)\s*(\d+))?\s*[- ]?\s*(hours?|days?|weeks?|months?|minutes?)\b/gi;
 const nums={one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,twelve:12,'twenty-four':24};

 function storage(p,kind){
 const l=p.labels?.[0];if(!l)return [];
 const out=[];let hasCold=false,expiry=false,heading='';
 const add=r=>{const same=out.find(q=>q.scope===r.scope&&q.value.replace('≤ ','')===r.value.replace('≤ ','')&&q.detail===r.detail);if(!same)out.push(r);};
 const blocks=paragraphs(l).filter(x=>['supplied','storage','dosage'].includes(x.section));
 for(let bi=0;bi<blocks.length;bi++){
  const {text,section}=blocks[bi];
  if(text.endsWith(':')&&types(text).length&&/mg|single-dose/i.test(text))heading=text;
  if(/^16\b|^Storage|^How supplied/i.test(text))heading='';
  const ss=sentences(text);let state='',lastTemp='';
  for(let si=0;si<ss.length;si++){
   const s=ss[si];const explicitPrep=/\b(?:admixture|admixed|diluted|reconstituted|reconstitution|dilution|infusion (?:bag|solution))\b/i.test(s)&&!/until.{0,15}reconstitution|prior to reconstitution|before reconstitution|refer to/i.test(s);
   if(explicitPrep)state='prep';
   if(/unopened|unused|prior to|until time of use/i.test(s)&&!explicitPrep)state='';
   const isPrepared=explicitPrep||state==='prep';
   const ts=temperatures(s);
   if(!isPrepared&&/refriger|store/i.test(s)&&ts.some(t=>/2.*8°C/.test(t.text)))hasCold=true;
   if(!isPrepared&&/expir/i.test(s))expiry=true;
   let ds=[...s.matchAll(durationRE)];
   const rt=[...s.matchAll(/room[ -]?temperature|ambient|out of (?:the )?refrigerator|outside (?:the )?refrigerator/gi)].map(m=>({index:m.index,text:'RT (온도 미기재)'}));
   // RT followed by a Celsius value is one condition, not two alternatives.
   const tokens=[...ts,...rt.filter(r=>!ts.some(t=>t.index>r.index&&t.index-r.index<90&&!ds.some(d=>d.index>r.index&&d.index<t.index)))].sort((a,b)=>a.index-b.index);
   const returned=/\b(?:may|can) be returned|return.{0,20}(?:one time|once)/i.test(s)&&!/do not return|not be returned/i.test(s);
   const returnAt=s.search(/return/i);
   for(let di=0;di<ds.length;di++){
    const d=ds[di];if(/minute/i.test(d[3])&&!isPrepared)continue;
    if(!/stor|kept|keep|stable|stability|held|hold|within|combined time|return/i.test(s))continue;
    if(/\bwithhold\b|dosing|dose modify/i.test(s))continue;
    if(!tokens.length&&!returned&&!isPrepared)continue;
    const previousD=di?ds[di-1].index:-1,nextD=ds[di+1]?.index||s.length;
    const before=tokens.filter(t=>t.index<d.index&&t.index>previousD),after=tokens.filter(t=>t.index>d.index&&t.index<nextD);
    let t=before.at(-1),temp=t?.text;
    // 'within 8 hours ... when stored at 2–8°C' has the temperature after the period.
    if(after.length&&(!t||/^\s*(?:at\b|(?:following|of) reconstitution when stored\b)/i.test(s.slice(d.index+d[0].length,after[0].index)))){t=after[0];temp=t.text;}
    if(before.length>1&&!after.length&&/\bor\b/i.test(s.slice(before.at(-2).index,before.at(-1).index))){temp=before.slice(-2).map(t=>t.text).join(' / ');}
    if(returned&&d.index>returnAt){
     if(/once within|one time within/i.test(s)){
      if(kind==='cold')add({scope:types(s).join(' + ')||'제품',value:'2–8°C · 유효기간까지',detail:d[0]+' 이내 재냉장 1회',evidence:s});continue;
     }
     temp='2–8°C';
    }
    if(returned&&d.index<returnAt)continue; // The preceding RT deadline is not a refrigerated shelf life.
    if(!temp&&isPrepared)temp=lastTemp||'온도 미기재';
    if(!temp)continue;
    if(temp.startsWith('RT')){
     const rtC=uniq(ss.flatMap(x=>temperatures(x)).filter(t=>!/2.*8°C/.test(t.text)).map(t=>t.text));
     if(rtC.length===1)temp=rtC[0];
    }
    const category=isPrepared?'prep':/2.*8°C/.test(temp)&&!temp.includes(' / ')?'cold':'room';
    if(category!==kind)continue;
    const n=nums[d[1].toLowerCase()]||d[1],period=String(n)+(d[2]?'–'+d[2]:'')+' '+d[3].toLowerCase().replace(/s$/,'')+(String(n)==='1'&&!d[2]?'':'s');
    const qualifiers=[];
    if(/additional/i.test(s))qualifiers.push('냉장 후 추가');
    if(/including (?:the )?infusion|including infusion|completely administered/i.test(s))qualifiers.push('투여시간 포함');
    if(/combined time|total time/i.test(s))qualifiers.push('누적 시간');
    if(returned)qualifiers.push(/one time|once/i.test(s)?'재냉장 1회':'재냉장');
    if(/do not return|not be placed back|must not.{0,20}refrigerat|should not.{0,20}refrigerat/i.test(text))qualifiers.push('재냉장 불가');
    if(/single period/i.test(s))qualifiers.push('단일 기간');
    const strength=uniq([...(heading||s).matchAll(/\d+(?:\.\d+)?\s*mg\s*\/\s*\d+(?:\.\d+)?\s*mL/gi)].map(m=>m[0])).join(' / ');
    const diluent=s.match(/(?:0\.9|0\.45)%\s*Sodium Chloride/i)?.[0];
    if(diluent)qualifiers.push(diluent.replace(/Sodium Chloride/i,'NaCl'));
    if(/without preservative|SWFI/i.test(s)||isPrepared&&/SWFI/i.test(text)&&!/BWFI/i.test(text))qualifiers.push('SWFI / 무보존제 조건');
    let scope=types(s).join(' + ')||types(heading).join(' + ')||types(text).join(' + ')||'제품';
    if(/multiple-dose vial and diluent/i.test(text))scope='Multi-dose vial + diluent';
    if(isPrepared)scope=(/dilut|infusion bag/i.test(s)?'희석 후':/reconstitut/i.test(s)?'재구성 후':'조제 후')+' · '+scope;
    const bounded=/up to|at or below|not.{0,25}above|not more than|maximum/i.test(s)||temp!=='2–8°C'&&ss.some(x=>/temperatures above|room temperature up to/i.test(x));
    const prefix=bounded&&/^\d+(?:\.\d+)?°C$/.test(temp)?'≤ ':'';
    add({scope:scope+(strength?' · '+strength:''),value:prefix+temp+' · '+period,detail:qualifiers.join(' · '),evidence:s});
   }
   if(tokens.length)lastTemp=tokens.at(-1).text;
  }
 }
 // PI storage tables: preserve unopened/opened columns rather than dropping numeric rows.
 const supplied=(l.sections?.supplied||[]).map(clean);
 const header=supplied.find(x=>/not in.use.*unopened/i.test(x)&&/in.use.*opened/i.test(x));
 if(header){
  const hi=supplied.indexOf(header),area=supplied.slice(Math.max(0,hi-2),hi+4).join(' '),temp=temperatures(area).find(t=>!/2.*8/.test(t.text)&&parseFloat(t.text)>8)?.text;
  for(const row of supplied.slice(hi+1)){
   const ds=[...row.matchAll(durationRE)];if(ds.length!==2||!types(row).length||!temp)continue;
   const scope=types(row).join(' + '),period=i=>ds[i][0].replace(/\s+/g,' ');
   if(kind==='room')add({scope:'미개봉 · '+scope,value:'≤ '+temp+' · '+period(0),detail:'',evidence:header+' | '+row});
   if(kind==='prep')add({scope:'개봉 후 · '+scope,value:(/refrigerated.or.room/i.test(row)?'2–8°C / ':'')+'≤ '+temp+' · '+period(1),detail:/do not refrigerate/i.test(row)?'재냉장 불가':'',evidence:header+' | '+row});
  }
 }
 if(kind==='cold'&&hasCold)out.unshift({scope:'미개봉',value:'2–8°C · '+(expiry?'유효기간까지':'기간 미기재'),detail:'PI에 명시된 개월 수 없음',evidence:''});
 const compact=[];
 for(const r of out){const old=compact.find(q=>q.scope===r.scope&&q.value===r.value&&!/NaCl|냉장 후 추가|SWFI/.test(q.detail+r.detail));if(old)old.detail=uniq([...old.detail.split(' · '),...r.detail.split(' · ')]).join(' · ');else compact.push({...r});}
 return compact.filter(r=>!compact.some(q=>q!==r&&q.value===r.value&&q.detail===r.detail&&r.scope.includes('제품')&&!q.scope.includes('제품')));
 }
 return {needle,storage};
})();
