'use strict';
(() => {
const data = window.MANTO_DATA;
if (!data) { document.querySelector('main').textContent = 'The snapshot did not load. Open this preview from its complete build directory.'; return; }
const $ = id => document.getElementById(id);
const places = new Map(data.places.map(p => [p.id,p]));
const number = x => Number(x).toLocaleString('en');
const pct = x => x === null || !Number.isFinite(x) ? 'Unobserved' : `${(x*100).toFixed(1)}%`;
const statuses = {
 inhabited_still_exists:'Inhabited / still exists',extant_uninhabited:'Extant, described as uninhabited',
 ruined_or_remains:'Ruins or remains',abandoned_or_deserted:'Abandoned / deserted',
 destroyed_no_trace:'Destroyed, no trace',renamed_refounded_or_transferred:'Renamed, refounded or transferred',unclear:'Unclear'
};
const scopes = {pausanias_present:"Pausanias's present",past_before_pausanias:'Earlier historical past',mythic_past:'Mythic past',later_commentary:'Later commentary',unclear:'Unclear time'};
const el = (tag, text, cls) => { const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n; };
const link = (text,href) => { const n=el('a',text);n.href=href;return n; };
const reset = n => n.replaceChildren();
const chip = (text,warning=false) => el('span',text,`status${warning?' warning':''}`);
const params = new URLSearchParams(location.search);
let claimPage=0;
function state(key,value){const u=new URL(location);u.searchParams.set(key,value);history.replaceState(null,'',u);}
function show(view){
 if(!['overview','explore','network','evidence','methods'].includes(view))view='overview';
 document.querySelectorAll('.view').forEach(n=>n.hidden=n.id!==view);
 document.querySelectorAll('nav button').forEach(n=>{n.classList.toggle('active',n.dataset.view===view);n.setAttribute('aria-current',n.dataset.view===view?'page':'false');});
 state('view',view);
}
document.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>show(n.dataset.view)));
document.querySelectorAll('[data-goto]').forEach(n=>n.addEventListener('click',()=>show(n.dataset.goto)));
function choosePlace(id){if(!places.has(id))return;$('place-select').value=id;state('place',id);renderPlace();show('explore');}
const mapped=data.places.filter(p=>p.lat!==null&&p.lon!==null);
for(const [value,label] of [[data.places.length,'geographic entities in the imported release'],[mapped.length,'with representative coordinates'],[data.claims.length,'automated passage-level evidence claims']]){
 const d=el('div',undefined,'metric');d.append(el('div',number(value),'metric-value'),el('div',label,'metric-label'));$('metrics').append(d);
}
const release=$('release-summary');release.append(el('p',`Displayed: ${data.release.file_key}`),link(`Imported MANTO release ${data.release.record_id}`,`https://zenodo.org/records/${data.release.record_id}`));
release.append(el('p',`Latest public release verified ${data.latest_public.verified_on}: ${data.latest_public.date}. It is not imported into this preview.`, 'notice'));
release.append(link('View the newer public release ↗',data.latest_public.url),el('p','Comparisons and evidence claims are derived from the existing project database. Scores describe this snapshot; they are not culture or survival verdicts.','muted'));
const ordered=[...data.places].sort((a,b)=>a.name.localeCompare(b.name));
for(const p of ordered){const o=el('option',`${p.name}${p.figures.length?'':' · no selected figure evidence'}`);o.value=p.id;$('place-select').append(o);}
const initial=places.has(params.get('place'))?params.get('place'):(ordered.find(p=>p.name.startsWith('Argos (Argolid)')&&p.figures.length)||ordered.find(p=>p.lat!==null&&p.figures.length)||ordered[0]).id;
$('place-select').value=initial;
if(['25','50','100'].includes(params.get('radius')))$('radius').value=params.get('radius');
$('place-select').addEventListener('change',()=>{state('place',$('place-select').value);renderPlace();});
$('radius').addEventListener('change',()=>{state('radius',$('radius').value);renderPlace();});
function neighbours(id,radius){return data.pairs.filter(e=>(e.a===id||e.b===id)&&e.km<=radius).map(e=>({...e,other:places.get(e.a===id?e.b:e.a),contain:e.a===id?e.a_in_b:e.b_in_a})).sort((a,b)=>a.km-b.km);}
function svgNode(tag,attrs={}){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;}
function interactiveSVGGroup(label,fn){const g=svgNode('g',{tabindex:'0',role:'button','aria-label':label});g.addEventListener('click',fn);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}});return g;}
function renderMap(p,ns,radius){
 const target=$('place-map');reset(target);
 if(p.lat===null||p.lon===null){target.append(el('p','No reliable representative coordinate is available. Geographic comparison is missing, not maximal difference.','empty'));return;}
 const svg=svgNode('svg',{viewBox:'0 0 500 365',role:'img','aria-label':`Schematic map of ${p.name} and neighbours within ${radius} kilometres`});
 const scale=145/radius;
 const title=svgNode('title');title.textContent='Geographic coordinates only; no terrain, travel times or political boundaries.';svg.append(title);
 for(const r of [0.5,1])svg.append(svgNode('circle',{cx:250,cy:175,r:145*r,fill:'none',stroke:'#d3ded4','stroke-dasharray':'3 6'}));
 const label=svgNode('text',{x:250,y:350,'text-anchor':'middle',class:'svg-guide'});label.textContent=`${radius} km radius · north is up`;svg.append(label);
 for(const n of [...ns].reverse().slice(0,150)){
  const x=250+(n.other.lon-p.lon)*111.2*Math.cos(p.lat*Math.PI/180)*scale,y=175-(n.other.lat-p.lat)*111.2*scale;
  const g=interactiveSVGGroup(n.other.name,()=>choosePlace(n.other.id));g.setAttribute('class','map-node');
  g.append(svgNode('circle',{cx:x,cy:y,r:4+Math.min(n.other.figures.length,20)/4,fill:n.similarity===null?'#9da9a0':'#328e83',opacity:'.8',stroke:'#fffef9'}));
  const t=svgNode('title');t.textContent=`${n.other.name}: ${n.km.toFixed(1)} km, similarity ${pct(n.similarity)}`;g.append(t);svg.append(g);
 }
 svg.append(svgNode('circle',{cx:250,cy:175,r:8,fill:'#cf9550',stroke:'#182f35','stroke-width':2}));
 const t=svgNode('text',{x:250,y:151,'text-anchor':'middle',class:'svg-label'});t.textContent=p.name.length>45?p.name.slice(0,43)+'…':p.name;svg.append(t);target.append(svg);
}
function renderPlace(){
 const p=places.get($('place-select').value),radius=Number($('radius').value),ns=neighbours(p.id,radius),observed=ns.filter(n=>n.similarity!==null);
 const weights=observed.map(n=>Math.exp(-n.km/25));
 const d=observed.length?1-observed.reduce((sum,n,i)=>sum+n.similarity*weights[i],0)/weights.reduce((a,b)=>a+b,0):null;
 reset($('place-summary'));const box=el('article',undefined,'panel');box.append(el('h2',p.name));
 box.append(el('p',`MANTO ${p.id}${p.parent?' · recorded locality: '+p.parent:''}. Settlement type and source-date provenance have not been adjudicated.`, 'muted'));
 if(p.pleiades_id&&/^\d+$/.test(p.pleiades_id))box.append(link('Pleiades location record ↗',`https://pleiades.stoa.org/places/${p.pleiades_id}`));
 const row=el('div',undefined,'score-row');for(const [val,label]of [[number(p.figures.length),'selected figures'],[number(ns.length),'mapped neighbours'],[pct(d),'local profile difference']]){const cell=el('div');cell.append(el('b',val),el('small',label));row.append(cell);}box.append(row);
 box.append(el('p',`Provisional descriptive score using ${observed.length} neighbours with nonempty profiles, with exp(−distance/25 km) weights. Low coverage can inflate difference; this is not a city-level cultural ranking.`, 'notice'));$('place-summary').append(box);
 reset($('figure-list'));const chips=el('div',undefined,'chips');for(const f of p.figures)chips.append(el('span',data.figures[f]||f,'chip'));$('figure-list').append(chips);if(!p.figures.length)$('figure-list').append(el('p','No figure association in the selected, filtered relation set. This is missing evidence, not proof of no mythology.','empty'));
 reset($('action-list'));for(const [action,ids]of Object.entries(p.actions).sort((a,b)=>b[1].length-a[1].length))$('action-list').append(el('p',`${action.replaceAll('_',' ')} · ${ids.length} figure${ids.length===1?'':'s'}`,'muted'));
 renderMap(p,ns,radius);$('neighbour-count').textContent=`${ns.length} neighbours · ${observed.length} comparable profiles`;
 const target=$('neighbours');reset(target);if(!ns.length){target.append(el('p','No mapped neighbour in this radius. Try a wider radius or another place.','empty'));return;}
 const table=el('table'),head=el('tr');for(const h of ['Neighbour','Distance','Similarity','Selected profile contained','Shared figures'])head.append(el('th',h));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');
 for(const n of ns){const r=el('tr'),name=el('td'),button=el('button',n.other.name,'link-button');button.addEventListener('click',()=>choosePlace(n.other.id));name.append(button);r.append(name,el('td',`${n.km.toFixed(1)} km`),el('td',pct(n.similarity)),el('td',pct(n.contain)));const fs=el('td');if(n.shared.length){const details=el('details'),summary=el('summary',`${n.shared.length} shared`);details.append(summary,el('p',n.shared.map(f=>data.figures[f]||f).join(', ')));fs.append(details);}else fs.textContent=n.similarity===null?'Unobserved':'None in this profile';r.append(fs);body.append(r);}table.append(body);const wrap=el('div',undefined,'table-wrap');wrap.append(table);target.append(wrap);
}
function renderGroupNetwork(){
 const groupOf=p=>{const match=p.name.match(/\(([^()]*)\)\s*$/);return match?match[1]:'No parenthetical label';};
 const groups=new Map();for(const p of data.places){const name=groupOf(p);if(!groups.has(name))groups.set(name,[]);groups.get(name).push(p);}
 const candidates=[...groups.entries()].filter(([n,ps])=>ps.length>=3&&!/unlocat|unknown|no parenthetical|city|island/i.test(n)).sort((a,b)=>b[1].length-a[1].length).slice(0,16);
 const index=new Map(candidates.map(([n],i)=>[n,i]));const agg=new Map();
 for(const pair of data.pairs){if(!(pair.similarity>0))continue;const a=groupOf(places.get(pair.a)),b=groupOf(places.get(pair.b));if(a===b||!index.has(a)||!index.has(b))continue;const key=[a,b].sort().join('|');if(!agg.has(key))agg.set(key,{a,b,total:0,count:0});const e=agg.get(key);e.total+=pair.similarity;e.count++;}
 const svg=svgNode('svg',{viewBox:'0 0 1080 560',role:'img','aria-label':'Exploratory network of geographic name-label groups sharing figures in nearby place pairs'});
 const coords=candidates.map((_,i)=>({x:540+390*Math.cos(i/candidates.length*Math.PI*2-Math.PI/2),y:270+200*Math.sin(i/candidates.length*Math.PI*2-Math.PI/2)}));
 for(const e of agg.values()){const a=coords[index.get(e.a)],b=coords[index.get(e.b)];const line=svgNode('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'#3e8c80','stroke-opacity':'.25','stroke-width':Math.min(10,1+Math.log1p(e.total))});const title=svgNode('title');title.textContent=`${e.a} ↔ ${e.b}: ${e.count} nearby pairs, summed similarity ${e.total.toFixed(2)}`;line.append(title);svg.append(line);}
 candidates.forEach(([name,ps],i)=>{const c=coords[i];const g=interactiveSVGGroup(`${name}: ${ps.length} geographic records. Show group.`,()=>{const panel=$('group-details');reset(panel);panel.append(el('h3',name),el('p',`${ps.length} geographic records. This is a label group, not a verified cultural community.`,'muted'));const chips=el('div',undefined,'chips');for(const p of ps.slice(0,40)){const b=el('button',p.name,'chip');b.addEventListener('click',()=>choosePlace(p.id));chips.append(b);}panel.append(chips);});g.setAttribute('class','group-node');g.append(svgNode('circle',{cx:c.x,cy:c.y,r:11+Math.sqrt(ps.length),fill:'#176f6d',stroke:'#f6f4ed','stroke-width':4}));const label=svgNode('text',{x:c.x,y:c.y+38,'text-anchor':'middle',class:'svg-label'});label.textContent=name;g.append(label);svg.append(g);});$('group-network').append(svg);
 $('network-caption').textContent=`Showing ${candidates.length} frequent name-label groups and ${agg.size} aggregate connections. Node area approximately reflects record count, not settlement size. Select a node to inspect contributing places.`;
}
for(const [value,label]of Object.entries(statuses)){const o=el('option',label);o.value=value;$('claim-status').append(o);}
if(params.has('q'))$('claim-query').value=params.get('q');
if([...$('claim-status').options].some(o=>o.value===params.get('status')))$('claim-status').value=params.get('status');
if([...$('claim-scope').options].some(o=>o.value===params.get('scope')))$('claim-scope').value=params.get('scope');
for(const id of ['claim-query','claim-scope','claim-status'])$(id).addEventListener(id==='claim-query'?'input':'change',()=>{claimPage=0;state('q',$('claim-query').value);state('scope',$('claim-scope').value);state('status',$('claim-status').value);renderClaims();});
$('claims-prev').addEventListener('click',()=>{claimPage=Math.max(0,claimPage-1);renderClaims();});$('claims-next').addEventListener('click',()=>{claimPage++;renderClaims();});
function renderClaims(){
 const q=$('claim-query').value.trim().toLocaleLowerCase(),scope=$('claim-scope').value,status=$('claim-status').value;
 const found=data.claims.filter(c=>(scope==='all'||c.temporal_scope===scope)&&(status==='all'||c.place_status===status)&&(!q||[c.canonical_place_name,c.exact_place_text,c.passage_id,c.evidence_quote].some(s=>(s||'').toLocaleLowerCase().includes(q))));
 const size=30;claimPage=Math.min(claimPage,Math.max(0,Math.ceil(found.length/size)-1));
 $('claim-count').textContent=`${number(found.length)} candidate claims · page ${claimPage+1} of ${Math.max(1,Math.ceil(found.length/size))}`;$('claims-prev').disabled=claimPage===0;$('claims-next').disabled=(claimPage+1)*size>=found.length;reset($('claims'));
 if(!found.length){$('claims').append(el('p','No claims match these filters. Try another name, status or temporal scope.','empty'));return;}
 for(const c of found.slice(claimPage*size,(claimPage+1)*size)){
  const card=el('article',undefined,'claim'),header=el('div',undefined,'claim-heading');header.append(el('h2',c.canonical_place_name));
  if(/^\d+\.\d+\.\d+$/.test(c.passage_id))header.append(link(`Pausanias ${c.passage_id} ↗`,`https://pausanias.symmachus.org/translation/${c.passage_id.replaceAll('.','/')}.html`));else header.append(el('span',c.passage_id));card.append(header);
  const meta=el('div',undefined,'claim-meta');meta.append(chip(statuses[c.place_status]||c.place_status),chip(scopes[c.temporal_scope]||c.temporal_scope),chip('Automated · not human-reviewed',true));card.append(meta);
  card.append(el('div',c.evidence_quote||'No quotation recorded.','quote'),el('p',`Model-assigned confidence: ${c.confidence}. This is not an independently calibrated confidence level.`,'muted'));
  const details=el('details'),summary=el('summary','Read the passage, rationale and possible place matches');details.append(summary);const context=el('div',undefined,'context');context.append(el('h3','Original Greek passage'),el('p',c.greek_text||'Not available','greek'),el('h3','Existing project translation'),el('p',c.english_translation||'Not available'),el('p','Translation is from the existing machine-assisted Pausanias project; verify difficult readings against the Greek.','muted'),el('h3','Automated extraction rationale'),el('p',c.rationale||'No rationale recorded'));
  context.append(el('h3','Name-based candidate matches'));
  if(c.candidate_manto_ids.length){context.append(el('p',`${c.candidate_manto_ids.length} possible MANTO match(es). None is adopted as this claim's verified settlement identity.`, 'notice'));const list=el('div',undefined,'chips');for(const id of c.candidate_manto_ids){if(!places.has(id))continue;const b=el('button',places.get(id).name,'chip');b.addEventListener('click',()=>choosePlace(id));list.append(b);}context.append(list);}else context.append(el('p','No candidate found by this preview’s exact name lookup. This is a linking gap, not an absence or abandonment finding.','muted'));
  context.append(el('p',`Source record: passage_place_state_mentions ${c.id}; review state: unreviewed.`, 'tiny muted'));details.append(context);card.append(details);$('claims').append(card);
 }
}
const models=$('historical-models');const table=el('table'),head=el('tr');for(const title of ['Feature family','Balanced accuracy','Evaluation'])head.append(el('th',title));const thead=el('thead');thead.append(head);table.append(thead);const tbody=el('tbody');
for(const m of data.historical_metrics){const name=(m.notes.match(/feature family=([^;]+)/)||[])[1]||m.feature_set_version;const r=el('tr');r.append(el('td',name),el('td',Number(m.balanced_accuracy).toFixed(3)),el('td','Historical stratified 5-fold; not spatial'));tbody.append(r);}table.append(tbody);const wrap=el('div',undefined,'table-wrap');wrap.append(table);models.append(wrap);
$('build-details').append(el('p',`Built ${data.generated_at}. Imported release checksum: ${data.release.file_checksum||'not recorded'}. All source database operations were read-only.`));
renderPlace();renderClaims();renderGroupNetwork();show(params.get('view')||'overview');
})();
