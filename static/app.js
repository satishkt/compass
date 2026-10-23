const $ = id => document.getElementById(id);
const state = {session:null, sessionInfo:null, newPrivate:false, local:true, me:'', agent:localStorage.getItem('pc-agent')||'supervisor', agents:[], contexts:{}, baseline:{}, busy:new Set(), revision:0, scope:'all', knowledgeType:'', dialog:null, detail:null, importMode:null, importItems:[]};
const TYPES = {
 requirement:{label:'Requirement',plural:'Requirements',approval:true,fields:[['priority','Priority','select',['must','should','could']],['acceptance_criteria','Acceptance criteria','textarea']]},
 rule:{label:'Business rule',plural:'Rules',approval:true,fields:[['track','Applies to track','text','e.g. public markets, private markets, consolidation'],['applies_to','Applies to (source, table or column)','text']]},
 decision:{label:'Decision',plural:'Decisions',approval:true,fields:[['@decided_by','Decided by','text','Who made the call (default: you)'],['context','Context','textarea'],['alternatives','Alternatives considered (one per line)','lines'],['consequences','Consequences','textarea']]},
 question:{label:'Open question',plural:'Questions',approval:false,fields:[['@assigned_to','Assigned to','text','Who should answer (email)'],['due','Due','date']]},
 todo:{label:'TODO',plural:'TODOs',approval:false,fields:[['@assigned_to','Assigned to','text','Owner (email)'],['due','Due','date']]},
 change:{label:'Change',plural:'Changes',approval:false,fields:[['impact','Impact','select',['model','transform','source','pipeline code','other']],['why','Why','textarea']]},
 source:{label:'Source',plural:'Sources',approval:true,fields:[['platform','Platform','text'],['path','Path / dataset','text'],['refresh','Refresh cadence','text']]},
 model:{label:'Data model',plural:'Model',approval:true,fields:[['table','Table','text','catalog.schema.table'],['grain','Grain','text'],['primary_key','Primary key','text'],['columns','Columns (one per line: name | type | nullable | source | transform)','columns']]},
 glossary:{label:'Glossary term',plural:'Glossary',approval:true,fields:[['synonyms','Synonyms','text']]},
 note:{label:'Note',plural:'Notes',approval:false,fields:[]},
};
const STATUS = {draft:'Draft',proposed:'Awaiting review',accepted:'Accepted',rejected:'Rejected',superseded:'Superseded',dismissed:'Dismissed',open:'Open',answered:'Answered',closed:'Closed',done:'Done',cancelled:'Cancelled',logged:'Logged'};
const CHANNEL = {web:'Web',cursor:'Cursor',seed:'Starting knowledge',import:'Import',consolidation:'From conversations'};

// ---------- Helpers ----------
function esc(s){return String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function inlineMarkdown(text){return esc(text).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[((?:[a-z0-9-]+-)?[A-Z]{1,3}-?\d+)\]/g,'<span class="citation">[$1]</span>');}
function renderAnswer(text){
 const lines=String(text||'').split('\n');let out='';
 for(let i=0;i<lines.length;i++){
  const line=lines[i];
  if(/^\|/.test(line)&&i+1<lines.length&&/^\|[\s:|\-]+\|?\s*$/.test(lines[i+1])){
   const cells=l=>l.replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
   out+='<div class="answer-table"><table><thead><tr>'+cells(line).map(c=>'<th>'+inlineMarkdown(c)+'</th>').join('')+'</tr></thead><tbody>';i++;
   while(i+1<lines.length&&/^\|/.test(lines[i+1])){i++;out+='<tr>'+cells(lines[i]).map(c=>'<td>'+inlineMarkdown(c)+'</td>').join('')+'</tr>';}
   out+='</tbody></table></div>';continue;
  }
  const h=line.match(/^(#{1,4})\s+(.+)/);
  if(h){out+='<h4>'+inlineMarkdown(h[2])+'</h4>';continue;}
  if(/^---+$/.test(line.trim())){out+='<hr>';continue;}
  if(/^<!--.*-->$/.test(line.trim()))continue;
  if(!line.trim()){out+='<div class="answer-gap"></div>';continue;}
  out+='<div>'+inlineMarkdown(line)+'</div>';
 }
 return out;
}
async function api(path, options={}){
 const r=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json','X-Demo-User':localStorage.getItem('research-demo-user')||'local-researcher',...(options.headers||{})}});
 let data;try{data=await r.json();}catch{throw Error('The server returned an unexpected response.');}
 if(!r.ok) throw Error(typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map(d=>d.msg).join('; '):JSON.stringify(data.detail||data));
 return data;
}
function tell(s,error=false){$('notice').hidden=false;$('notice').textContent=s;$('notice').className=error?'error':'';clearTimeout(tell.timer);if(!error)tell.timer=setTimeout(()=>{$('notice').hidden=true;},6000);}
const person=p=>!p?'—':p===state.me?'you':String(p).split('@')[0];
const when=t=>t?new Date(t).toLocaleString([], {dateStyle:'medium',timeStyle:'short'}):'';
const day=t=>t?new Date(t).toLocaleDateString([], {dateStyle:'medium'}):'';
const statusChip=s=>`<span class="tag status-${esc(s)}">${esc(STATUS[s]||s)}</span>`;
const typeChip=t=>`<span class="tag type-chip">${esc(TYPES[t]?.label||t)}</span>`;
const agentName=id=>state.agents.find(a=>a.id===id)?.name||id;
const splitList=v=>v.split(',').map(x=>x.trim()).filter(Boolean);
function debounce(fn,ms=300){let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms);};}

// ---------- Top bar: status, identity, menus, navigation ----------
const ICON={
 check:'<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 lock:'<svg class="lock" viewBox="0 0 16 16" width="12" height="12" aria-label="Private"><rect x="3.5" y="7" width="9" height="6.5" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 7V5.2a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
 route:'<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="2.3" fill="currentColor"/><path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
};
function initialsOf(text){const parts=String(text||'').split('@')[0].split(/[._\-\s]+/).filter(Boolean);return ((parts[0]||'?')[0]+(parts[1]?parts[1][0]:'')).toUpperCase();}
async function refresh(){const s=await api('/status');state.local=s.mode==='Local prototype';state.me=s.user;$('mode').textContent=state.local?'Local prototype':'Databricks';$('identity').textContent=s.user;$('user-initials').textContent=initialsOf(s.user);$('demo-user-label').hidden=!state.local;$('pending-count').textContent=s.inbox||'';$('pending-dot').hidden=!s.inbox;$('catalog').textContent=s.catalog;}
const MENUS=[['agent-switch','agent-menu'],['apps-toggle','apps-menu'],['user-toggle','user-menu']];
function closeMenus(){for(const [b,m] of MENUS){$(m).hidden=true;$(b).setAttribute('aria-expanded','false');}$('backdrop').hidden=true;}
function toggleMenu(button,menu){const open=$(menu).hidden;closeMenus();if(!open)return;$(menu).hidden=false;$(button).setAttribute('aria-expanded','true');if(menu==='agent-menu'){$('backdrop').hidden=false;$('agent-find').value='';renderAgentMenu();$('agent-find').focus();}}
MENUS.forEach(([b,m])=>$(b).onclick=e=>{e.stopPropagation();toggleMenu(b,m);});
document.addEventListener('click',e=>{if(!e.target.closest('.popover'))closeMenus();});
document.addEventListener('keydown',e=>{if(e.key!=='Escape'||document.querySelector('dialog[open]'))return;if(MENUS.some(([,m])=>!$(m).hidden))closeMenus();else if(!$('drawer').hidden)closeDrawer();});
async function tab(name){
 closeMenus();
 document.querySelectorAll('.tab').forEach(x=>x.hidden=x.id!==name);
 document.body.classList.toggle('on-page',name!=='chat');$('record-bar').hidden=name!=='chat';
 if(name!=='chat')closeDrawer();
 document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));
 window.scrollTo(0,0);
 try{if(name==='chat'){renderAgentContext();loadRecordSummary();scrollToEnd();}if(name==='knowledge')await loadKnowledge();if(name==='review')await loadInbox();if(name==='manage-agents')await loadAgentCatalog();if(name==='daily-updates')await loadDailyUpdates();if(name==='sources')await loadSources();if(name==='audit')await loadAudit();}catch(e){tell(e.message,true);}
}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>{if(b.dataset.tab==='knowledge'){$('knowledge-agent').value=state.agent;state.knowledgeType='';$('knowledge-status').value='active';}tab(b.dataset.tab);});
document.querySelectorAll('[data-back]').forEach(b=>b.onclick=()=>tab('chat'));
$('home-link').onclick=e=>{e.preventDefault();tab('chat');};
window.addEventListener('focus',()=>refresh().catch(()=>{}));
setInterval(()=>refresh().catch(()=>{}),60000);
$('demo-user').value=localStorage.getItem('research-demo-user')||'local-researcher';
$('demo-user').onchange=async()=>{localStorage.setItem('research-demo-user',$('demo-user').value||'local-researcher');state.session=null;state.contexts={};state.baseline={};state.revision++;welcome();try{await refresh();loadRecordSummary();if(!$('drawer').hidden)await savedSessions();tell('Demo identity switched.');}catch(e){tell(e.message,true);}};

// ---------- Agent switcher ----------
function currentAgent(){return state.agents.find(a=>a.id===state.agent);}
function initials(a){return (a.name.match(/[A-Za-z0-9]+/g)||[a.id]).map(w=>w[0]).join('').slice(0,2).toUpperCase();}
function tone(id){let h=0;for(const c of id)h=(h*31+c.charCodeAt(0))>>>0;return String(h%6);}
function avatarHtml(a,size='sm'){return `<span class="agent-avatar ${size}" data-agent="${esc(a.id)}" data-tone="${tone(a.id)}" aria-hidden="true">${a.id==='supervisor'?ICON.route:esc(initials(a))}</span>`;}
function setAvatar(node,a){node.dataset.agent=a.id;node.dataset.tone=tone(a.id);node.innerHTML=a.id==='supervisor'?ICON.route:esc(initials(a));}
function recentAgents(){try{return JSON.parse(localStorage.getItem('pc-recent')||'[]');}catch{return [];}}
function remember(agent){localStorage.setItem('pc-agent',agent);if(agent!=='supervisor')localStorage.setItem('pc-recent',JSON.stringify([agent,...recentAgents().filter(a=>a!==agent)].slice(0,6)));}
function renderAgentMenu(){
 const q=$('agent-find').value.trim().toLowerCase();
 const match=a=>!q||a.name.toLowerCase().includes(q)||a.purpose.toLowerCase().includes(q)||a.id.includes(q);
 const option=a=>{const sup=a.id==='supervisor';return `<button type="button" class="agent-option${a.id===state.agent?' selected':''}" data-select-agent="${esc(a.id)}" aria-pressed="${a.id===state.agent}">${avatarHtml(a)}<span class="agent-option-copy"><strong>${esc(sup?'Supervisor · auto-route':a.name)}</strong><span>${esc(sup?'Not sure? It picks the right agent for each question':a.purpose)}</span></span>${a.id===state.agent?ICON.check:''}</button>`;};
 const specialists=state.agents.filter(a=>a.id!=='supervisor'&&match(a));
 const current=specialists.find(a=>a.id===state.agent);
 const recent=recentAgents().map(id=>specialists.find(a=>a.id===id)).filter(a=>a&&a!==current).slice(0,3);
 const rest=specialists.filter(a=>a!==current&&!recent.includes(a));
 const sup=state.agents.find(a=>a.id==='supervisor');
 let html=current?option(current):'';
 if(recent.length)html+='<p class="menu-label">RECENT</p>'+recent.map(option).join('');
 if(rest.length)html+=`<p class="menu-label">${current||recent.length?'ALL AGENTS':'AGENTS'}</p>`+rest.map(option).join('');
 if(sup&&match(sup))html+=(html?'<hr>':'')+option(sup);
 $('agent-options').innerHTML=html||'<p class="muted empty">No agents match.</p>';
 $('agent-options').querySelectorAll('[data-select-agent]').forEach(b=>b.onclick=()=>{closeMenus();selectAgent(b.dataset.selectAgent).catch(e=>tell(e.message,true));});
}
$('agent-find').oninput=renderAgentMenu;
$('agent-find').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();$('agent-options').querySelector('[data-select-agent]')?.click();}};
function agentPrompts(a){
 const record=['fill','We decided that ','Record a decision…'];
 if(a.id==='supervisor')return [['ask','Which decisions have we made across agents?'],['ask','Which open questions still need an owner?'],record];
 return [['ask','What open questions do we have?'],['ask','Summarise decisions and rules so far'],record];
}
function renderAgentContext(){const a=currentAgent();if(!a)return;setAvatar($('switch-avatar'),a);$('switch-name').textContent=a.name;document.title=a.name+' · Pipeline Compass';updatePlaceholder();updateComposer();}
function updatePlaceholder(){const a=currentAgent();if(!a)return;$('question').placeholder=state.session?'Reply, or share another decision…':a.id==='supervisor'?'Ask across all agents, or share a decision, rule or requirement…':'Ask '+a.name+', or share a decision, rule or requirement…';}
function updateComposer(){const busy=state.busy.has(state.agent);$('send').disabled=busy;$('send').textContent=busy?'Thinking…':'Ask ↗';$('messages').setAttribute('aria-busy',String(busy));$('new-session').disabled=busy;}
function welcome(){
 const a=currentAgent();if(!a)return;
 state.sessionInfo=null;syncPrivate();updatePlaceholder();
 const sup=a.id==='supervisor';
 $('messages').innerHTML=`<div class="welcome">${avatarHtml(a,'lg')}<h1>What are we working on?</h1><p>${esc(sup?'I consult the pipeline agents and bring their answers together.':a.purpose)} ${esc(sup?'Ask a question, or share a decision, rule or requirement.':'Ask a question, or share a decision, rule or requirement and I’ll offer to record it.')}</p><div class="suggestions">${agentPrompts(a).map(([k,q,label])=>`<button type="button" class="suggestion" data-${k}="${esc(q)}">${esc(label||q)}</button>`).join('')}</div></div>`;
 $('messages').querySelectorAll('[data-ask]').forEach(b=>b.onclick=()=>ask(b.dataset.ask));
 $('messages').querySelectorAll('[data-fill]').forEach(b=>b.onclick=()=>{$('question').value=b.dataset.fill;$('question').focus();grow();});
}
async function selectAgent(agent,session){
 if(!state.agents.some(a=>a.id===agent))return;
 state.contexts[state.agent]={...(state.contexts[state.agent]||{}),session:state.session,draft:$('question').value};
 state.agent=agent;remember(agent);state.revision++;
 const saved=state.contexts[agent]||{};
 state.session=session!==undefined?session:(saved.session||null);
 $('question').value=saved.draft||'';grow();$('notice').hidden=true;state.baseline[agent]=null;
 renderAgentContext();loadRecordSummary();
 const rev=state.revision;
 if(state.session)await showConversation(state.session);else welcome();
 if(rev===state.revision&&!$('drawer').hidden)await savedSessions();
}
async function initAgents(){
 const rows=await api('/agents');
 state.agents=[...rows].sort((a,b)=>Number(b.id==='supervisor')-Number(a.id==='supervisor'));
 if(!rows.some(a=>a.id===state.agent)){state.agent=(rows.find(a=>a.id==='supervisor')||rows[0])?.id||'supervisor';state.session=null;}
 for(const id of ['memory-agent','knowledge-agent','item-agent']){const previous=$(id).value;$(id).innerHTML=state.agents.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');$(id).value=state.agents.some(a=>a.id===previous)?previous:state.agent;}
 renderAgentContext();
 if(!$('messages').querySelector('.msg'))welcome();
 loadRecordSummary();
 if(!$('drawer').hidden)await savedSessions();
}

// ---------- Project record bar ----------
async function loadRecordSummary(){
 const agent=state.agent;
 try{
  const r=await api('/agents/'+encodeURIComponent(agent)+'/items?status=proposed');
  if(state.agent!==agent)return;
  const c=r.counts,t=c.by_type;
  const chips=[['question','open','Open question','Open questions',c.open_questions,true],['','proposed','Awaiting review','Awaiting review',c.awaiting_review,true],['todo','open','Open TODO','Open TODOs',c.open_todos,true],['decision','active','Decision','Decisions',t.decision||0],['requirement','active','Requirement','Requirements',t.requirement||0],['rule','active','Rule','Rules',t.rule||0]];
  // Counts present when the agent was opened are the baseline; anything recorded since is marked "new".
  const base=state.baseline[agent]||(state.baseline[agent]=Object.fromEntries(chips.map(x=>[x[3],x[4]])));
  $('record-chips').innerHTML=chips.map(([type,status,one,many,n,attention])=>{const fresh=!attention&&n>(base[many]??n);return `<button type="button" class="record-chip${fresh?' fresh':attention&&n?' attention':''}" data-type="${type}" data-status="${status}"><strong>${n}</strong> ${esc(n===1?one:many)}${fresh?' · new':''}</button>`;}).join('');
  $('record-chips').querySelectorAll('.record-chip').forEach(b=>b.onclick=()=>openKnowledge(agent,b.dataset.type,b.dataset.status));
 }catch{$('record-chips').innerHTML='<span class="muted">Unavailable</span>';}
}
$('open-knowledge').onclick=()=>openKnowledge(state.agent,'','active');

// ---------- Conversations drawer ----------
function openDrawer(){if($('chat').hidden)tab('chat');$('drawer').hidden=false;document.body.classList.add('drawer-open');$('history-toggle').setAttribute('aria-expanded','true');$('history-toggle').classList.add('active');savedSessions().catch(e=>tell(e.message,true));}
function closeDrawer(){$('drawer').hidden=true;document.body.classList.remove('drawer-open');$('history-toggle').setAttribute('aria-expanded','false');$('history-toggle').classList.remove('active');}
$('history-toggle').onclick=()=>$('drawer').hidden?openDrawer():closeDrawer();
$('close-drawer').onclick=closeDrawer;
const narrow=()=>window.matchMedia('(max-width: 900px)').matches;
function dayGroup(t){const d=new Date(t),now=new Date(),start=x=>new Date(x.getFullYear(),x.getMonth(),x.getDate()).getTime(),diff=Math.round((start(now)-start(d))/86400000);if(diff===0)return 'TODAY';if(diff===1)return 'YESTERDAY';return d.toLocaleDateString([],d.getFullYear()===now.getFullYear()?{month:'short',day:'numeric'}:{dateStyle:'medium'}).toUpperCase();}
async function savedSessions(){
 const agent=state.agent,revision=state.revision;
 const rows=await api('/sessions?agent='+encodeURIComponent(agent)+(state.scope==='mine'?'&mine=true':'')+($('session-search').value?'&q='+encodeURIComponent($('session-search').value):''));
 if(state.agent!==agent||state.revision!==revision)return;
 if(!rows.length){$('session-list').innerHTML=`<p class="muted empty">${$('session-search').value?'No conversations match.':state.scope==='mine'?'You haven’t started a conversation here yet.':'No conversations with '+esc(agentName(agent))+' yet.'}</p>`;return;}
 let html='',group='';
 for(const s of rows){
  const g=dayGroup(s.updated_at||s.created_at);if(g!==group){html+=`<p class="menu-label">${esc(g)}</p>`;group=g;}
  const extra=s.participants.filter(p=>p!==s.owner).length;
  const who=s.owner!==state.me?person(s.owner)+(extra?' +'+extra:''):'';
  html+=`<button type="button" class="session-row${s.id===state.session?' selected':''}" data-session="${esc(s.id)}" title="${esc(when(s.updated_at||s.created_at))}"><span class="session-title">${esc(s.title||'Untitled conversation')}</span>${who?`<span class="who">· ${esc(who)}</span>`:''}${s.visibility==='private'?ICON.lock:''}</button>`;
 }
 $('session-list').innerHTML=html;
 $('session-list').querySelectorAll('[data-session]').forEach(b=>b.onclick=async()=>{state.session=b.dataset.session;state.revision++;state.contexts[state.agent]={session:state.session,draft:$('question').value};$('session-list').querySelectorAll('.session-row').forEach(x=>x.classList.toggle('selected',x===b));if(narrow())closeDrawer();await showConversation(state.session);});
}
document.querySelectorAll('.seg').forEach(b=>b.onclick=()=>{state.scope=b.dataset.scope;document.querySelectorAll('.seg').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});savedSessions().catch(e=>tell(e.message,true));});
$('session-search').oninput=debounce(()=>savedSessions().catch(e=>tell(e.message,true)));
$('new-session').onclick=()=>{state.session=null;state.revision++;state.contexts[state.agent]={session:null,draft:''};state.newPrivate=false;state.baseline[state.agent]=null;welcome();loadRecordSummary();$('question').value='';grow();$('session-list').querySelectorAll('.session-row').forEach(x=>x.classList.remove('selected'));if(narrow())closeDrawer();$('question').focus();};

// ---------- Conversation thread ----------
function el(tag,cls){const n=document.createElement(tag);if(cls)n.className=cls;return n;}
function scrollToEnd(){requestAnimationFrame(()=>window.scrollTo({top:document.documentElement.scrollHeight}));}
function grow(){const q=$('question');q.style.height='auto';q.style.height=Math.min(q.scrollHeight,220)+'px';}
function syncPrivate(){
 const box=$('new-private'),info=state.sessionInfo;
 if(!state.session||!info){box.disabled=false;box.checked=!!state.newPrivate;$('private-hint').hidden=false;$('private-label').title='A private conversation is visible only to you';return;}
 const mine=info.owner===state.me;
 box.checked=info.visibility==='private';box.disabled=!mine;$('private-hint').hidden=true;
 $('private-label').title=mine?'Only you can see a private conversation':'Only '+person(info.owner)+' can change who sees this conversation';
}
$('new-private').onchange=async()=>{
 if(!state.session||!state.sessionInfo){state.newPrivate=$('new-private').checked;return;}
 const visibility=$('new-private').checked?'private':'shared';
 try{state.sessionInfo={...state.sessionInfo,...await api('/sessions/'+state.session,{method:'PATCH',body:JSON.stringify({visibility})})};tell(visibility==='private'?'This conversation is now private.':'This conversation is now visible to the team.');if(!$('drawer').hidden)savedSessions();}
 catch(e){tell(e.message,true);syncPrivate();}
};
function msgTools(row,key,sourceEvent){
 const t=el('div','msg-tools');
 if(row.created_at){const s=el('small');s.textContent=when(row.created_at);t.append(s);}
 if(key&&row.id){const rec=el('button','link-button record-from');rec.type='button';rec.textContent='+ Record';rec.title='Record something from this message';rec.onclick=()=>openItemDialog({mode:'create',agent:state.agent,data:{type:'decision',title:row.content.replace(/\s+/g,' ').slice(0,90),body:row.content},source_session:key,source_event:sourceEvent});t.append(rec);}
 return t;
}
function userMessage(row,key){
 const d=el('div','msg user');
 if(row.author&&row.author!==state.me){const a=el('div','msg-author');a.textContent=person(row.author);d.append(a);}
 const b=el('div','bubble');b.textContent=row.content;d.append(b,msgTools(row,key,row.id));
 return d;
}
function agentMessage(row){
 const a=state.agents.find(x=>x.id===row.author)||currentAgent()||{id:'agent',name:'Agent'};
 const d=el('div','msg assistant');d.innerHTML=avatarHtml(a);
 const body=el('div','msg-body'),answer=el('div','answer');answer.innerHTML=renderAnswer(row.content);body.append(answer);d.append(body);
 return {node:d,body};
}
function thinkingEl(agent){const a=state.agents.find(x=>x.id===agent)||{id:agent,name:agent};const d=el('div','msg assistant thinking');d.innerHTML=avatarHtml(a)+`<div class="msg-body"><span class="typing">${esc(a.name)} is working…</span></div>`;return d;}
function stepsEl(steps){
 const d=el('details','steps');
 const names=steps.filter(s=>s.kind==='tool_call').map(s=>{try{return JSON.parse(s.content).tool;}catch{return 'step';}});
 d.innerHTML=`<summary>Show steps (${names.length})${names.length?': '+esc([...new Set(names)].map(n=>n.replaceAll('_',' ')).join(', ')):''}</summary>`+steps.map(s=>`<pre>${esc(s.kind.replace('_',' '))}: ${esc(s.content.slice(0,3000))}</pre>`).join('');
 return d;
}
// Sources come from the turn's recorded tool results, so they survive reloads; the live response adds approved memory.
function turnSources(steps){
 const out=[];
 for(const s of steps){
  if(s.kind!=='tool_result')continue;
  let d;try{d=JSON.parse(s.content);}catch{continue;}
  if(Array.isArray(d)){for(const x of d){if(x&&x.ref)out.push({label:x.ref,title:x.ref+' · '+x.title,content:x.body,kind:'knowledge_item',agent:x.agent_id});else if(x&&x.label)out.push({label:x.label,title:x.title,content:x.content,kind:x.kind});}}
  else if(d&&d.agent&&d.session_id&&'answer' in d)out.push({label:'consulted-'+d.agent,title:'Consulted '+agentName(d.agent),content:d.answer,kind:'delegation'});
 }
 return out;
}
function liveSources(sources){return (sources||[]).map(s=>s.kind==='knowledge_item'?{...s,agent:String(s.id).split(':')[0]}:s);}
function sourceName(s){
 if(s.kind==='knowledge_item')return String(s.title).replace(/\s*\((accepted|proposed|open|answered|done|logged|superseded|closed|cancelled)\)$/,'').slice(0,48);
 if(s.kind==='approved_memory')return 'Memory · '+String(s.title).split('/').pop().replace(/\.md$/,'').replaceAll('-',' ');
 if(s.kind==='delegation')return s.title;
 if(s.kind==='historical_conversation')return 'Past conversation';
 const n=String(s.title||s.label).replace(/\.md$/,'').replace(/^project-/,'').replaceAll('-',' ');
 return n.charAt(0).toUpperCase()+n.slice(1);
}
function sourcesEl(answer,sources){
 const unique=[...new Map(sources.map(s=>[s.label,s])).values()];
 const cited=unique.filter(s=>answer.includes('['+s.label+']')||(s.kind==='knowledge_item'&&answer.includes(s.label)));
 const shown=[...unique.filter(s=>s.kind==='delegation'),...(cited.length?cited:unique.filter(s=>s.kind==='document').slice(0,4)).filter(s=>s.kind!=='delegation')];
 const groups=new Map();for(const s of shown){const n=sourceName(s);groups.set(n,[...(groups.get(n)||[]),s]);}
 if(!groups.size)return null;
 const d=el('div','sources');const label=el('span','muted');label.textContent='Sources';d.append(label);
 for(const [name,items] of groups){
  const b=el('button','source-chip');b.type='button';b.textContent=name;
  b.onclick=()=>{const first=items[0];if(first.kind==='knowledge_item'){openDetail(first.agent||state.agent,first.label);return;}$('source-title').textContent=name;$('source-content').textContent=items.map(x=>x.content).join('\n\n— — —\n\n');$('source-dialog').showModal();};
  d.append(b);
 }
 return d;
}
const CARD_STATE={proposed:'recorded · awaiting review',accepted:'accepted',open:'recorded',logged:'recorded',answered:'answered',done:'done',rejected:'rejected',superseded:'superseded',cancelled:'cancelled',closed:'closed'};
function cardEl(item,agent){
 const d=el('div','capture-card');d.dataset.ref=item.ref;
 const meta=TYPES[item.type]||{label:item.type};
 if(item.status==='draft'){
  d.classList.add('draft');
  d.innerHTML=`<div class="capture-label">Suggested ${esc(meta.label.toLowerCase())}</div><strong class="capture-title">${esc(item.title)}</strong>${item.body?`<p>${esc(item.body)}</p>`:''}${item.type==='decision'?`<p class="muted">Decided by ${esc(person(item.decided_by))}</p>`:''}<div class="capture-links"><button type="button" class="link-button" data-act="edit">Edit</button><button type="button" class="link-button" data-act="confirm">${meta.approval?'Send for review':'Record'}</button><button type="button" class="link-button" data-act="dismiss">Dismiss</button></div>`;
  d.querySelector('[data-act="confirm"]').onclick=async e=>{e.target.disabled=true;try{const r=await api(`/agents/${agent}/items/${item.ref}/confirm`,{method:'POST',body:'{}'});d.replaceWith(cardEl(r,agent));tell(r.status==='proposed'?`${r.ref} recorded and sent for review.`:`${r.ref} recorded.`);refresh();loadRecordSummary();}catch(err){tell(err.message,true);e.target.disabled=false;}};
  d.querySelector('[data-act="edit"]').onclick=()=>openItemDialog({mode:'confirm',agent,item,onDone:r=>{d.replaceWith(cardEl(r,agent));refresh();loadRecordSummary();}});
  d.querySelector('[data-act="dismiss"]').onclick=async()=>{try{await api(`/agents/${agent}/items/${item.ref}/dismiss`,{method:'POST'});d.remove();}catch(err){tell(err.message,true);}};
  return d;
 }
 const settled=['rejected','superseded','cancelled','closed'].includes(item.status);
 d.classList.add(settled?'settled':'recorded');
 d.innerHTML=`<div class="capture-label">${settled?'':ICON.check}${esc(meta.label)} ${esc(CARD_STATE[item.status]||item.status)} <span class="ref">${esc(item.ref)}</span></div><strong class="capture-title">${esc(item.title)}</strong><div class="capture-links"><button type="button" class="link-button" data-act="view">View</button>${item.status==='proposed'?'<button type="button" class="link-button" data-act="edit">Edit</button>':''}</div>`;
 d.querySelector('[data-act="view"]').onclick=()=>openDetail(agent,item.ref);
 d.querySelector('[data-act="edit"]')?.addEventListener('click',()=>openItemDialog({mode:'edit',agent,item,onDone:r=>d.replaceWith(cardEl(r,agent))}));
 return d;
}
async function showConversation(key){
 const revision=state.revision,agent=state.agent;
 if(!key){welcome();return;}
 $('messages').innerHTML='<p class="muted loading">Loading conversation…</p>';
 try{
  const [rows,items,meta]=await Promise.all([api('/sessions/'+key),api('/sessions/'+key+'/items'),api('/sessions?agent='+encodeURIComponent(agent)+'&include_children=true')]);
  if(state.agent!==agent||state.revision!==revision||state.session!==key)return;
  state.sessionInfo=meta.find(s=>s.id===key)||null;syncPrivate();updatePlaceholder();
  const box=$('messages');box.replaceChildren();
  const cached=state.contexts[agent]?.session===key?state.contexts[agent].result:null;
  const lastAnswer=[...rows].reverse().find(r=>r.kind==='message'&&r.role==='assistant');
  let steps=[],lastUser=null,lastUserAt='',answered=true;
  const unanswered=()=>{if(!answered&&steps.some(s=>s.kind==='error')){const n=el('p','muted turn-note');n.textContent='The agent couldn’t finish this answer. Ask again to retry.';box.append(n);}steps=[];};
  for(const r of rows){
   if(r.kind!=='message'){steps.push(r);continue;}
   if(r.role==='user'){unanswered();lastUser=r.id;lastUserAt=r.created_at;answered=false;box.append(userMessage(r,key));continue;}
   answered=true;
   const {node,body}=agentMessage(r);
   // Cards follow the answer to the message they came from; delegated specialists' suggestions are placed by time.
   items.filter(i=>i.status!=='dismissed'&&(i.source_session===key?i.source_event===lastUser:i.created_at>=lastUserAt&&i.created_at<=r.created_at)).forEach(i=>body.append(cardEl(i,i.agent_id)));
   const src=turnSources(steps).concat(cached&&r===lastAnswer?liveSources(cached.sources):[]);
   const chips=sourcesEl(r.content,src);if(chips)body.append(chips);
   if(steps.length)body.append(stepsEl(steps));
   body.append(msgTools(r,key,lastUser));
   box.append(node);steps=[];
  }
  unanswered();
  if(!rows.length)welcome();
  scrollToEnd();
 }catch(e){if(state.agent===agent&&state.revision===revision){welcome();tell(e.message,true);}}
}
async function createAgentSession(agent){const id=(await api('/sessions',{method:'POST',body:JSON.stringify({agent,visibility:state.newPrivate?'private':'shared'})})).id;state.newPrivate=false;return id;}
async function ask(q){
 if(state.busy.has(state.agent)||!q.trim())return;
 const agent=state.agent;let key=state.session;const revision=state.revision;
 state.busy.add(agent);updateComposer();$('question').value='';grow();
 if($('messages').querySelector('.welcome'))$('messages').replaceChildren();
 $('messages').append(userMessage({role:'user',content:q,author:state.me}));
 const thinking=thinkingEl(agent);$('messages').append(thinking);scrollToEnd();
 try{
  if(!key)key=await createAgentSession(agent);
  state.contexts[agent]={...(state.contexts[agent]||{}),session:key,draft:''};
  if(state.agent===agent&&state.revision===revision)state.session=key;
  const r=await api('/chat',{method:'POST',body:JSON.stringify({session_id:key,question:q})});
  if(state.contexts[agent]?.session===key)state.contexts[agent].result=r;
  if(state.agent===agent&&state.session===key){await showConversation(key);loadRecordSummary();if(!$('drawer').hidden)savedSessions();if(r.warning)tell(r.warning,true);}
 }catch(e){thinking.remove();if(state.agent===agent&&(!state.session||state.session===key)){const n=el('p','muted turn-note');n.textContent='Could not complete the request: '+e.message;$('messages').append(n);}}
 finally{state.busy.delete(agent);updateComposer();}
}
$('chat-form').onsubmit=e=>{e.preventDefault();ask($('question').value);};
$('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('chat-form').requestSubmit();}};
$('question').oninput=grow;
$('composer-record').onclick=()=>openItemDialog({mode:'create',agent:state.agent,data:{type:'decision',title:'',body:$('question').value},source_session:state.session});

// ---------- Item dialog (record / confirm / edit / supersede) ----------
function fieldInput(key,label,kind,extra,value){
 const id='f-'+key.replace('@','');const v=value??'';
 if(kind==='select')return `<label>${esc(label)}<select id="${id}" data-field="${key}"><option value="">—</option>${extra.map(o=>`<option ${o===v?'selected':''}>${esc(o)}</option>`).join('')}</select></label>`;
 if(kind==='textarea'||kind==='lines'||kind==='columns'){const text=kind==='lines'?(Array.isArray(v)?v.map(a=>typeof a==='string'?a:a.option+(a.reason_rejected?' — '+a.reason_rejected:'')).join('\n'):v):kind==='columns'?(Array.isArray(v)?v.map(c=>[c.name,c.type,c.nullable,c.source,c.transform].join(' | ')).join('\n'):v):v;return `<label>${esc(label)}<textarea id="${id}" data-field="${key}" data-kind="${kind}" rows="${kind==='columns'?5:2}">${esc(text)}</textarea></label>`;}
 return `<label>${esc(label)}<input id="${id}" data-field="${key}" type="${kind==='date'?'date':'text'}" value="${esc(v)}" placeholder="${esc(extra||'')}"></label>`;
}
function renderItemFields(type,data={}){const meta=TYPES[type];$('item-fields').innerHTML=meta.fields.map(([key,label,kind,extra])=>fieldInput(key,label,kind,extra,key.startsWith('@')?data[key.slice(1)]:(data.fields||{})[key])).join('');}
function readItemForm(){
 const data={type:$('item-type').value,title:$('item-title').value.trim(),body:$('item-body').value.trim(),fields:{}};
 $('item-fields').querySelectorAll('[data-field]').forEach(el=>{const key=el.dataset.field,kind=el.dataset.kind;let v=el.value.trim();
  if(kind==='lines')v=v.split('\n').map(x=>x.trim()).filter(Boolean);
  if(kind==='columns')v=v.split('\n').map(x=>x.split('|').map(c=>c.trim())).filter(c=>c[0]).map(([name,type,nullable,source,transform])=>({name,type:type||'',nullable:nullable||'',source:source||'',transform:transform||''}));
  if(key.startsWith('@'))data[key.slice(1)]=v;else if(v&&(!Array.isArray(v)||v.length))data.fields[key]=v;});
 return data;
}
function openItemDialog(opts){
 state.dialog=opts;const item=opts.item||opts.data||{};
 $('item-type').innerHTML=Object.entries(TYPES).map(([k,t])=>`<option value="${k}">${esc(t.label)}</option>`).join('');
 $('item-type').value=item.type||'decision';$('item-type').disabled=opts.mode!=='create';
 $('item-agent').value=opts.agent;$('item-agent-label').hidden=opts.mode!=='create';
 $('item-title').value=item.title||'';$('item-body').value=item.body||'';
 renderItemFields($('item-type').value,item);$('item-error').textContent='';
 $('item-dialog-title').textContent={create:'Record knowledge',confirm:'Edit and record',edit:'Edit '+(item.ref||''),supersede:'Replace '+(item.ref||'')}[opts.mode];
 $('item-submit').textContent={create:'Record',confirm:'Record',edit:'Save changes',supersede:'Propose replacement'}[opts.mode];
 $('item-dialog').showModal();$('item-title').focus();
}
$('item-type').onchange=()=>renderItemFields($('item-type').value,readItemForm());
$('close-item').onclick=$('item-cancel').onclick=()=>$('item-dialog').close();
$('item-form').onsubmit=async e=>{
 e.preventDefault();const o=state.dialog,data=readItemForm();$('item-submit').disabled=true;$('item-error').textContent='';
 try{let r;const agent=o.mode==='create'?$('item-agent').value:o.agent;
  if(o.mode==='create')r=await api(`/agents/${agent}/items`,{method:'POST',body:JSON.stringify({...data,source_session:o.source_session||null,source_event:o.source_event||null})});
  if(o.mode==='confirm')r=await api(`/agents/${agent}/items/${o.item.ref}/confirm`,{method:'POST',body:JSON.stringify(data)});
  if(o.mode==='edit')r=await api(`/agents/${agent}/items/${o.item.ref}`,{method:'PATCH',body:JSON.stringify({...data,expected_version:o.item.version})});
  if(o.mode==='supersede')r=await api(`/agents/${agent}/items/${o.item.ref}/supersede`,{method:'POST',body:JSON.stringify(data)});
  $('item-dialog').close();tell(`${r.ref} ${r.status==='proposed'?'recorded and sent for approval':'saved'}.`);
  refresh();loadRecordSummary();if(o.onDone)o.onDone(r);else if(!$('knowledge').hidden)loadKnowledge();else if(!$('review').hidden)loadInbox();else if(state.session&&o.source_session===state.session)showConversation(state.session);
 }catch(err){$('item-error').textContent=err.message;}finally{$('item-submit').disabled=false;}
};

// ---------- Item detail ----------
async function openDetail(agent,ref){
 try{const i=await api(`/agents/${agent}/items/${ref}`);state.detail={agent,item:i};renderDetail();if(!$('detail-dialog').open)$('detail-dialog').showModal();}catch(e){tell(e.message,true);}
}
function renderDetail(){
 const {agent,item:i}=state.detail;const f=i.fields||{};
 $('detail-title').innerHTML=`${esc(i.ref)} · ${esc(i.title)}`;
 const fieldRows=Object.entries(f).filter(([k,v])=>v&&!['answer','answered_by','answered_at','legacy_id'].includes(k)&&!(Array.isArray(v)&&!v.length)).map(([k,v])=>`<tr><th>${esc(k.replaceAll('_',' '))}</th><td>${Array.isArray(v)?v.map(x=>typeof x==='string'?esc(x):esc(Object.values(x).filter(Boolean).join(' · '))).join('<br>'):esc(v)}</td></tr>`).join('');
 const people=[['Recorded by',i.recorded_by],['Decided by',i.decided_by],['Approved by',i.approved_by],['Assigned to',i.assigned_to]].filter(p=>p[1]).map(([l,p])=>`<span><strong>${l}</strong> ${esc(person(p))}</span>`).join('');
 const can=i.can_approve;
 let actions='';
 if(i.status==='proposed')actions=`<label>Comment<textarea id="review-note" rows="2" placeholder="Required to reject or request changes"></textarea></label><div class="actions">${can?'<button data-review="approve">Approve</button>':''}<button class="secondary" data-review="request_changes">Request changes</button>${can?'<button class="secondary" data-review="reject">Reject</button>':''}<button class="secondary" data-edit>Edit</button></div>${can?'':`<p class="muted">${esc(i.approval_note||'You can’t approve this item.')}</p>`}`;
 if(i.status==='draft')actions=`<div class="actions"><button data-confirm>Record</button><button class="secondary" data-dismiss>Dismiss</button></div>`;
 if(i.status==='accepted')actions=`<div class="actions"><button class="secondary" data-supersede>Replace with a new version</button></div>`;
 if(i.type==='question'&&['open','answered'].includes(i.status))actions+=`<label>Answer<textarea id="answer-text" rows="3">${esc(f.answer||'')}</textarea></label><label class="check compact"><input type="checkbox" id="answer-promote"> This answer is a decision; send it for approval</label><div class="actions"><button data-answer>Save answer</button><button class="secondary" data-status="closed">Close question</button><button class="secondary" data-edit>Edit</button></div>`;
 if(i.type==='todo'&&i.status==='open')actions+=`<div class="actions"><button data-status="done">Mark done</button><button class="secondary" data-status="cancelled">Cancel</button><button class="secondary" data-edit>Edit</button></div>`;
 if(i.type==='todo'&&['done','cancelled'].includes(i.status))actions+=`<div class="actions"><button class="secondary" data-status="open">Reopen</button></div>`;
 $('detail-body').innerHTML=`<div class="capture-head">${typeChip(i.type)} ${statusChip(i.status)} <span class="muted">${esc(agentName(agent))} · ${esc(CHANNEL[i.channel]||i.channel)}</span></div>
 <div class="detail-text">${renderAnswer(i.body||'')}</div>
 ${f.answer?`<div class="callout"><strong>Answer</strong> (${esc(person(f.answered_by))}, ${esc(day(f.answered_at))})<br>${esc(f.answer)}</div>`:''}
 ${fieldRows?`<table class="detail-fields">${fieldRows}</table>`:''}
 <div class="people">${people}</div>
 <div class="links">${i.supersedes_ref?`<button class="link-button" data-open="${esc(i.supersedes_ref)}">Replaces ${esc(i.supersedes_ref)}</button>`:''}${i.superseded_by_ref?`<button class="link-button" data-open="${esc(i.superseded_by_ref)}">Replaced by ${esc(i.superseded_by_ref)}</button>`:''}${(i.links||[]).filter(l=>l.kind!=='supersedes').map(l=>{const other=l.from_ref===i.ref?l.to_ref:l.from_ref;return `<button class="link-button" data-open="${esc(other)}">${esc(l.kind.replace('_',' '))} ${esc(other)}</button>`;}).join('')}${i.source_session?'<button class="link-button" data-conversation>View source conversation ↗</button>':''}</div>
 ${actions}
 <details class="history"><summary>History (${(i.history||[]).length})</summary>${(i.history||[]).map(h=>`<div class="history-row"><span>${esc(h.action.replace('status:','marked ').replace('_',' '))} by ${esc(person(h.actor))}${h.note?' — '+esc(h.note):''}</span><small>${esc(when(h.created_at))} · v${h.version}</small></div>`).join('')}</details>`;
 const body=$('detail-body'),reload=async()=>{await openDetail(agent,i.ref);refresh();loadRecordSummary();if(!$('knowledge').hidden)loadKnowledge();if(!$('review').hidden)loadInbox();};
 const run=async(fn)=>{try{await fn();await reload();}catch(e){tell(e.message,true);}};
 body.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>run(()=>api(`/agents/${agent}/items/${i.ref}/review`,{method:'POST',body:JSON.stringify({action:b.dataset.review,expected_version:i.version,note:$('review-note').value})})));
 body.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>run(()=>api(`/agents/${agent}/items/${i.ref}/status`,{method:'POST',body:JSON.stringify({status:b.dataset.status})})));
 body.querySelector('[data-answer]')?.addEventListener('click',()=>run(async()=>{const r=await api(`/agents/${agent}/items/${i.ref}/answer`,{method:'POST',body:JSON.stringify({answer:$('answer-text').value,promote_to_decision:$('answer-promote').checked})});if(r.decision)tell(`Answer saved. ${r.decision.ref} sent for approval.`);}));
 body.querySelector('[data-confirm]')?.addEventListener('click',()=>run(()=>api(`/agents/${agent}/items/${i.ref}/confirm`,{method:'POST',body:'{}'})));
 body.querySelector('[data-dismiss]')?.addEventListener('click',()=>run(()=>api(`/agents/${agent}/items/${i.ref}/dismiss`,{method:'POST'})));
 body.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{$('detail-dialog').close();openItemDialog({mode:'edit',agent,item:i});});
 body.querySelector('[data-supersede]')?.addEventListener('click',()=>{$('detail-dialog').close();openItemDialog({mode:'supersede',agent,item:i});});
 body.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openDetail(agent,b.dataset.open));
 body.querySelector('[data-conversation]')?.addEventListener('click',async()=>{$('detail-dialog').close();await tab('chat');const parentAgent=agent;await selectAgent(parentAgent,i.source_session).catch(e=>tell(e.message,true));});
}
$('close-detail').onclick=()=>$('detail-dialog').close();

// ---------- Knowledge register ----------
function openKnowledge(agent,type,status){$('knowledge-agent').value=agent;state.knowledgeType=type||'';$('knowledge-status').value=status??'active';tab('knowledge');}
async function loadKnowledge(){
 const agent=$('knowledge-agent').value||state.agent;
 const q=new URLSearchParams({status:$('knowledge-status').value,q:$('knowledge-search').value,type:state.knowledgeType});
 const r=await api(`/agents/${encodeURIComponent(agent)}/items?`+q);
 const counts=r.counts.by_type;
 $('knowledge-chips').innerHTML=`<button class="chip ${state.knowledgeType?'':'active'}" data-type="">All</button>`+Object.entries(TYPES).map(([k,t])=>`<button class="chip ${state.knowledgeType===k?'active':''}" data-type="${k}">${esc(t.plural)} <span>${counts[k]||0}</span></button>`).join('');
 $('knowledge-chips').querySelectorAll('.chip').forEach(b=>b.onclick=()=>{state.knowledgeType=b.dataset.type;loadKnowledge().catch(e=>tell(e.message,true));});
 $('knowledge-export').href=`/api/agents/${encodeURIComponent(agent)}/export.zip`;
 const owners=r.members.filter(m=>m.role!=='contributor').map(m=>person(m.user_email)+' ('+m.role+')');
 $('knowledge-table').innerHTML=(owners.length?`<p class="muted">Approvers: ${esc(owners.join(', '))}</p>`:'<p class="muted">No owners set: any signed-in user other than the recorder can approve.</p>')+(r.items.length?`<table class="register"><thead><tr><th>Ref</th><th>Title</th><th>Type</th><th>Status</th><th>People</th><th>Updated</th><th>From</th></tr></thead><tbody>${r.items.map(i=>`<tr data-ref="${esc(i.ref)}" tabindex="0"><td><strong>${esc(i.ref)}</strong></td><td class="title-cell">${esc(i.title)}${i.type==='question'&&i.fields.answer?`<small>Answer: ${esc(i.fields.answer.slice(0,120))}</small>`:''}</td><td>${esc(TYPES[i.type]?.label||i.type)}</td><td>${statusChip(i.status)}</td><td>${esc(i.type==='decision'?'decided by '+person(i.decided_by):i.assigned_to?'→ '+person(i.assigned_to):'by '+person(i.recorded_by))}</td><td>${esc(day(i.updated_at))}</td><td>${esc(CHANNEL[i.channel]||i.channel)}</td></tr>`).join('')}</tbody></table>`:'<p class="muted">Nothing recorded here yet. Use ＋ Record, import a pipeline folder, or tell the agent in a conversation.</p>');
 $('knowledge-table').querySelectorAll('tr[data-ref]').forEach(tr=>{tr.onclick=()=>openDetail(agent,tr.dataset.ref);tr.onkeydown=e=>{if(e.key==='Enter')openDetail(agent,tr.dataset.ref);};});
}
$('knowledge-agent').onchange=$('knowledge-status').onchange=()=>loadKnowledge().catch(e=>tell(e.message,true));
$('knowledge-search').oninput=debounce(()=>loadKnowledge().catch(e=>tell(e.message,true)));
$('knowledge-record').onclick=()=>openItemDialog({mode:'create',agent:$('knowledge-agent').value,data:{type:state.knowledgeType||'decision'}});
$('knowledge-import').onclick=()=>openImport('agent');

// ---------- Import ----------
function openImport(mode){state.importMode=mode;state.importItems=[];state.importFiles=null;$('import-form').reset();$('import-classify').checked=true;$('import-preview').innerHTML='';$('import-error').textContent='';$('import-submit').disabled=true;$('import-accept-label').hidden=mode!=='agent';$('import-submit').textContent=mode==='agent'?'Import':'Add to starting knowledge';$('import-dialog').showModal();}
$('import-folder-mode').onchange=()=>{$('import-files').webkitdirectory=$('import-folder-mode').checked;};
async function readImportFiles(){const files={};for(const f of $('import-files').files){if(/\.(md|markdown|txt)$/i.test(f.name)&&!/(^|\/)\./.test(f.webkitRelativePath||f.name))files[f.webkitRelativePath||f.name]=await f.text();}if(!Object.keys(files).length)throw Error('Choose Markdown or text files.');return files;}
function renderImportPreview(r){
 const counts={};r.items.forEach(i=>counts[i.type]=(counts[i.type]||0)+1);
 const summary=Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([t,n])=>`${n} ${(n===1?TYPES[t]?.label:TYPES[t]?.plural)||t}`.toLowerCase()).join(', ');
 $('import-preview').innerHTML=`<p class="muted">${r.classified?'The agent classified':'Found'} ${r.items.length} items${summary?': '+esc(summary):''}. Change a type or untick anything you don’t want.</p><div class="import-list">${r.items.map((i,n)=>`<div class="import-row"><input type="checkbox" data-n="${n}" checked aria-label="Include ${esc(i.title)}"><select data-type-n="${n}" aria-label="Type">${Object.entries(TYPES).map(([k,t])=>`<option value="${k}" ${k===i.type?'selected':''}>${esc(t.label)}</option>`).join('')}</select><span class="import-title">${esc(i.title)}<small>${esc([i.decided_by&&'decided by '+i.decided_by,i.assigned_to&&'→ '+i.assigned_to,i.type==='decision'&&i.accepted===false&&'not yet agreed',i.source_file].filter(Boolean).join(' · '))}</small></span></div>`).join('')}</div>`;
 $('import-preview').querySelectorAll('[data-type-n]').forEach(s=>s.onchange=()=>{state.importItems[s.dataset.typeN].type=s.value;});
 $('import-submit').disabled=!r.items.length;
}
async function parseImport(){
 $('import-error').textContent='';$('import-submit').disabled=true;
 try{
  state.importFiles=state.importFiles||await readImportFiles();
  const classify=$('import-classify').checked;
  const body={files:state.importFiles,classify};
  if(state.importMode==='agent')body.agent=$('knowledge-agent').value;else{body.name=$('new-agent-name').value.trim();body.purpose=$('new-agent-purpose').value.trim();}
  const needsModel=classify&&Object.keys(state.importFiles).some(n=>!SCAFFOLD.has(n.split('/').pop().toLowerCase()));
  $('import-preview').innerHTML=`<p class="muted thinking">${needsModel?'The agent is reading and classifying the document… this can take up to a minute.':'Reading files…'}</p>`;
  const r=await api('/knowledge/parse',{method:'POST',body:JSON.stringify(body)});
  state.importItems=r.items;renderImportPreview(r);
 }catch(e){$('import-preview').innerHTML='';$('import-error').textContent=e.message;}
}
const SCAFFOLD=new Set(['spec.md','sources.md','model.md','rules.md','decisions.md','todos.md','glossary.md','changes.md']);
$('import-files').onchange=()=>{state.importFiles=null;parseImport();};
$('import-classify').onchange=()=>{if($('import-files').files.length)parseImport();};
$('close-import').onclick=()=>$('import-dialog').close();
$('import-form').onsubmit=async e=>{
 e.preventDefault();const chosen=[...$('import-preview').querySelectorAll('[data-n]')].filter(c=>c.checked).map(c=>state.importItems[c.dataset.n]);
 if(!chosen.length)return;
 const clean=chosen.map(({source_file,...i})=>i);
 if(state.importMode==='seed'){clean.forEach(i=>addSeedRow(i));$('import-dialog').close();return;}
 if(state.importing)return;
 state.importing=true;$('import-submit').disabled=true;$('import-submit').textContent='Importing…';$('import-error').textContent='';
 $('import-status').textContent=`Importing ${clean.length} item${clean.length===1?'':'s'}…`;
 try{
  const agent=$('knowledge-agent').value;
  const r=await api(`/agents/${agent}/items/import`,{method:'POST',body:JSON.stringify({items:clean,accept:$('import-accept').checked})});
  $('import-dialog').close();
  const skipped=r.skipped?` ${r.skipped} already recorded and skipped.`:'';
  tell(r.created?`Imported ${r.created} item${r.created===1?'':'s'}${r.accepted?' as accepted':'; decisions, requirements and rules wait for review'}.${skipped}`:`Nothing new to import.${skipped}`);
  await loadKnowledge();refresh();loadRecordSummary();
 }catch(err){$('import-error').textContent=err.message;}
 finally{state.importing=false;$('import-submit').disabled=false;$('import-submit').textContent='Import';$('import-status').textContent='';}
};

// ---------- Review inbox ----------
function inboxCard(i){return `<article class="memory-card inbox-card"><div class="capture-head">${typeChip(i.type)} ${statusChip(i.status)} <strong>${esc(i.ref)}</strong> <span class="muted">${esc(agentName(i.agent_id))}</span></div><h3>${esc(i.title)}</h3><p>${esc((i.body||'').slice(0,400))}${(i.body||'').length>400?'…':''}</p><p class="muted">Recorded by ${esc(person(i.recorded_by))}${i.decided_by?' · decided by '+esc(person(i.decided_by)):''} · ${esc(CHANNEL[i.channel]||i.channel)} · ${esc(when(i.updated_at))}${i.supersedes?' · replaces an accepted item':''}</p><div class="actions">${i.can_approve?`<button data-quick-approve="${esc(i.agent_id)}|${esc(i.ref)}|${i.version}">Approve</button>`:''}<button class="secondary" data-open-item="${esc(i.agent_id)}|${esc(i.ref)}">${i.can_approve?'Review details':'View'}</button></div></article>`;}
async function loadInbox(){
 const r=await api('/inbox');
 $('inbox-review').innerHTML=r.review.length?r.review.map(inboxCard).join(''):'<p class="muted">Nothing is waiting for review.</p>';
 $('inbox-assigned').innerHTML=r.assigned.length?r.assigned.map(inboxCard).join(''):'<p class="muted">No open questions or TODOs are assigned to you.</p>';
 document.querySelectorAll('[data-open-item]').forEach(b=>b.onclick=()=>{const [a,ref]=b.dataset.openItem.split('|');openDetail(a,ref);});
 document.querySelectorAll('[data-quick-approve]').forEach(b=>b.onclick=async()=>{const [a,ref,v]=b.dataset.quickApprove.split('|');b.disabled=true;try{await api(`/agents/${a}/items/${ref}/review`,{method:'POST',body:JSON.stringify({action:'approve',expected_version:Number(v)})});tell(ref+' approved.');await loadInbox();refresh();}catch(e){tell(e.message,true);b.disabled=false;}});
 $('pending-count').textContent=r.count||'';
}
$('memory-agent').onchange=$('refresh-agent-memory').onclick=()=>loadAgentMemory().catch(e=>tell(e.message,true));
document.querySelector('#review details.advanced').addEventListener('toggle',e=>{if(e.target.open)loadAgentMemory().catch(err=>tell(err.message,true));});
$('run-pipeline').onclick=async()=>{const b=$('run-pipeline');b.disabled=true;try{await api('/agents/'+$('memory-agent').value+'/consolidate',{method:'POST'});tell('Memory job started. Suggestions appear in Review when it finishes.');}catch(e){tell(e.message,true);}finally{b.disabled=false;}};
async function loadAgentMemory(){const agent=$('memory-agent').value||'supervisor';const [m,p]=await Promise.all([api('/agents/'+agent+'/memory'),api('/agents/'+agent+'/pipeline')]);$('pipeline-summary').textContent=p.dreamer_policy?'Runs about every 24 hours.':'The memory job is not configured for this agent.';$('agent-memories').innerHTML=(m.candidates.length?m.candidates.map(x=>`<article class="memory-card"><span class="tag pending">Suggestion</span><h3>${esc(x.path)}</h3><div>${renderAnswer(x.content)}</div><div class="actions"><button data-candidate="${x.review_id}" data-action="approve">Approve</button><button class="secondary" data-candidate="${x.review_id}" data-action="reject">Reject</button></div></article>`).join(''):'<p class="muted">No older-format suggestions.</p>')+`<details><summary>What this agent remembers (${m.approved.length})</summary>${m.approved.map(x=>`<article class="memory-card"><h3>${esc(x.path)}</h3><div>${renderAnswer(x.content)}</div></article>`).join('')}</details>`;$('agent-memories').querySelectorAll('[data-candidate]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/agents/'+agent+'/review',{method:'POST',body:JSON.stringify({review_id:b.dataset.candidate,action:b.dataset.action})});await loadAgentMemory();}catch(e){tell(e.message,true);b.disabled=false;}});}

// ---------- Agents: catalog, members, creation ----------
let agentPoll=null,manualAgentId=false;
async function loadAgentCatalog(){
 if(agentPoll){clearTimeout(agentPoll);agentPoll=null;}
 const [ready,definitions]=await Promise.all([api('/agents'),api('/agent-definitions')]);
 const custom=new Map(definitions.map(a=>[a.id,a]));
 const cards=[...ready.filter(a=>!custom.has(a.id)).map(a=>({...a,status:'ready',builtin:true})),...definitions];
 $('agent-catalog').innerHTML=cards.map(a=>`<article class="memory-card agent-card"><div><span class="tag ${a.status==='ready'?'approved':'pending'}">${esc(a.status==='ready'?'Ready':a.status==='creating'?'Setting up':'Setup needs attention')}${a.builtin?' · Built in':''}</span><h3>${esc(a.name)}</h3><p>${esc(a.purpose)}</p><small class="muted">Cursor: /mcp/${esc(a.id)}</small>${a.error?`<p class="error">${esc(a.error)}</p>`:''}</div><div class="actions">${a.status==='ready'?`<button data-chat-agent="${esc(a.id)}">Open conversations</button><button class="secondary" data-knowledge-agent="${esc(a.id)}">Knowledge</button><button class="secondary" data-members-agent="${esc(a.id)}">Owners &amp; approvers</button>`:a.status==='failed'?`<button data-retry-agent="${esc(a.id)}">Retry setup</button>`:'<p class="muted">Preparing memory and conversation storage…</p>'}</div></article>`).join('');
 $('agent-catalog').querySelectorAll('[data-chat-agent]').forEach(b=>b.onclick=async()=>{await initAgents();await tab('chat');await selectAgent(b.dataset.chatAgent);});
 $('agent-catalog').querySelectorAll('[data-knowledge-agent]').forEach(b=>b.onclick=async()=>{await initAgents();openKnowledge(b.dataset.knowledgeAgent,'','active');});
 $('agent-catalog').querySelectorAll('[data-members-agent]').forEach(b=>b.onclick=()=>openMembers(b.dataset.membersAgent));
 $('agent-catalog').querySelectorAll('[data-retry-agent]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/agent-definitions/'+b.dataset.retryAgent+'/retry',{method:'POST'});await loadAgentCatalog();}catch(e){tell(e.message,true);b.disabled=false;}});
 await initAgents();
 if(definitions.some(a=>a.status==='creating'))agentPoll=setTimeout(()=>loadAgentCatalog().catch(e=>tell(e.message,true)),3000);
}
async function openMembers(agent){try{const m=await api('/agents/'+agent+'/members');state.membersAgent=agent;$('members-title').textContent='Owners & approvers · '+agentName(agent);$('members-owners').value=m.filter(x=>x.role==='owner').map(x=>x.user_email).join(', ');$('members-approvers').value=m.filter(x=>x.role==='approver').map(x=>x.user_email).join(', ');$('members-error').textContent='';$('members-dialog').showModal();}catch(e){tell(e.message,true);}}
$('close-members').onclick=()=>$('members-dialog').close();
$('members-form').onsubmit=async e=>{e.preventDefault();try{await api('/agents/'+state.membersAgent+'/members',{method:'PUT',body:JSON.stringify({owners:splitList($('members-owners').value),approvers:splitList($('members-approvers').value)})});$('members-dialog').close();tell('Owners and approvers saved.');}catch(err){$('members-error').textContent=err.message;}};
function addSeedRow(data={}){
 if($('new-agent-seeds').children.length>=500)return;
 const row=document.createElement('div');row.className='seed-editor';row.dataset.extra=JSON.stringify({fields:data.fields||{},accepted:data.accepted,done:data.done||false,assigned_to:data.assigned_to||null});
 row.innerHTML=`<div class="form-row"><label>Type<select data-seed-type>${Object.entries(TYPES).map(([k,t])=>`<option value="${k}" ${k===(data.type||'decision')?'selected':''}>${esc(t.label)}</option>`).join('')}</select></label><label class="grow">Title<input data-seed-title required minlength="3" maxlength="200" value="${esc(data.title||'')}" placeholder="Canonical model unifies public and private positions"></label></div><label>Details<textarea data-seed-body rows="2" maxlength="8000" placeholder="The statement and the reason behind it">${esc(data.body||'')}</textarea></label><label data-decided>Decided by<input data-seed-decided value="${esc(data.decided_by||'')}" placeholder="Who made the call (default: you)"></label><button type="button" class="link-button remove-seed">Remove</button>`;
 const syncType=()=>{row.querySelector('[data-decided]').hidden=row.querySelector('[data-seed-type]').value!=='decision';};
 row.querySelector('[data-seed-type]').onchange=syncType;syncType();
 row.querySelector('.remove-seed').onclick=()=>{row.remove();updateSeedSummary();};
 $('new-agent-seeds').append(row);updateSeedSummary();
}
function updateSeedSummary(){const n=$('new-agent-seeds').children.length;$('seed-summary').textContent=n?`${n} item${n===1?'':'s'}`:'Add at least one item, or import the pipeline’s design folder.';}
function openCreateAgent(){$('create-agent-form').reset();$('approve-agent-baseline').checked=true;$('create-agent-error').textContent='';$('new-agent-seeds').replaceChildren();manualAgentId=false;addSeedRow();$('create-agent-dialog').showModal();}
$('open-create-agent').onclick=openCreateAgent;
$('close-create-agent').onclick=()=>$('create-agent-dialog').close();
$('add-agent-seed').onclick=()=>addSeedRow();
$('seed-import').onclick=()=>openImport('seed');
$('new-agent-id').oninput=()=>{manualAgentId=true;};
$('new-agent-name').oninput=()=>{if(!manualAgentId)$('new-agent-id').value=$('new-agent-name').value.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').replace(/^[^a-z]+/,'').slice(0,40);};
$('create-agent-form').onsubmit=async e=>{
 e.preventDefault();const b=$('submit-create-agent');b.disabled=true;$('create-agent-error').textContent='';
 try{
  const items=[...$('new-agent-seeds').children].map(row=>{const extra=JSON.parse(row.dataset.extra||'{}');const type=row.querySelector('[data-seed-type]').value;return {type,title:row.querySelector('[data-seed-title]').value.trim(),body:row.querySelector('[data-seed-body]').value.trim(),decided_by:type==='decision'?row.querySelector('[data-seed-decided]').value.trim()||null:null,assigned_to:extra.assigned_to||null,fields:extra.fields||{},accepted:extra.accepted,done:extra.done||false};}).filter(i=>i.title);
  if(!items.length)throw Error('Add at least one starting knowledge item.');
  const r=await api('/agents',{method:'POST',body:JSON.stringify({id:$('new-agent-id').value.trim(),name:$('new-agent-name').value.trim(),purpose:$('new-agent-purpose').value.trim(),keywords:splitList($('new-agent-keywords').value),owners:splitList($('new-agent-owners').value),approvers:splitList($('new-agent-approvers').value),items,approve_baseline:$('approve-agent-baseline').checked})});
  $('create-agent-dialog').close();tell(r.name+' is being set up. You can leave this page; setup continues in the background.');await loadAgentCatalog();
 }catch(error){$('create-agent-error').textContent=error.message;}finally{b.disabled=false;}
};

// ---------- Daily updates, documents, tables, activity ----------
let dailyPoll=null;
async function loadDailyUpdates(){
 const cfg=await api('/daily-updates');const previous=$('daily-agent').value;
 $('daily-agent').innerHTML=cfg.agents.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');
 $('daily-agent').value=previous||state.agent;
 if(!$('daily-date').value)$('daily-date').value=cfg.default_date;
 $('daily-schedule').textContent=cfg.configured?'Generated automatically every night for the previous day.':'Daily updates are not configured in this environment.';
 $('daily-job-link').hidden=!cfg.job_url;if(cfg.job_url)$('daily-job-link').href=cfg.job_url;
 $('run-daily-update').disabled=!cfg.configured;
}
$('view-daily-update').onclick=async()=>{try{const r=await api('/agents/'+encodeURIComponent($('daily-agent').value)+'/daily-update?day='+encodeURIComponent($('daily-date').value));$('daily-content').innerHTML=renderAnswer(r.content.replace(/^- (UTC window|Day timezone|Generated at):.*$/gm,''));}catch(e){$('daily-content').textContent=e.message;}};
$('run-daily-update').onclick=async()=>{const b=$('run-daily-update');b.disabled=true;try{const r=await api('/daily-updates/run',{method:'POST',body:JSON.stringify({day:$('daily-date').value,agent:$('daily-agent').value})});$('daily-run-state').textContent='Regenerating… you can leave this page.';if(dailyPoll)clearTimeout(dailyPoll);await watchDailyRun(r.run_id);}catch(e){tell(e.message,true);}finally{b.disabled=false;}};
async function watchDailyRun(id){try{const r=await api('/daily-updates/runs/'+id);const s=r.state||{};const done=['TERMINATED','SKIPPED','INTERNAL_ERROR'].includes(s.life_cycle_state);$('daily-run-state').textContent=done?(s.result_state==='SUCCESS'?'Updated.':'The update failed: '+(s.state_message||s.result_state)):'Regenerating…';if(done){if(s.result_state==='SUCCESS')await $('view-daily-update').onclick();return;}dailyPoll=setTimeout(()=>watchDailyRun(id),5000);}catch(e){$('daily-run-state').textContent=e.message;}}
async function loadSources(){const s=await api('/sources');$('source-list').innerHTML=s.files.map(f=>`<div class="source-row"><button data-source="${esc(f.name)}">${esc(f.name)}</button><small>${f.historical?'Past conversation excerpt':'Document'} · ${(f.bytes/1024).toFixed(1)} KB</small></div>`).join('');$('source-list').querySelectorAll('[data-source]').forEach(b=>b.onclick=async()=>{try{const s=await api('/sources/'+encodeURIComponent(b.dataset.source));$('source-title').textContent=s.name;$('source-content').textContent=s.content;$('source-dialog').showModal();}catch(e){tell(e.message,true);}});}
$('close-source').onclick=()=>$('source-dialog').close();
async function loadAudit(){const rows=await api('/audit');$('audit-list').innerHTML=rows.length?rows.map(r=>`<div class="audit-row"><div><strong>${esc(r.action.replaceAll('_',' '))}</strong><p>${esc(person(r.actor))} · ${esc(r.target)}</p></div><small>${esc(when(r.created_at))}</small></div>`).join(''):'<p class="muted">Activity appears here as people use the agents.</p>';}
$('table-form').onsubmit=async e=>{e.preventDefault();$('run-query').disabled=true;$('table-result').textContent='Running query under your Databricks identity…';try{const r=await api('/tables/query',{method:'POST',body:JSON.stringify({operation:$('operation').value,schema_name:$('schema-name').value,table:$('table-name').value,column:$('column-name').value,confirm_scan:$('confirm-scan').checked})});$('table-result').innerHTML=`<pre class="sql">${esc(r.sql)}</pre><p class="muted">${esc(r.executed_at)} · ${esc(r.identity)}${r.truncated?' · Results truncated':''}</p><div class="table-wrap"><table><thead><tr>${r.columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${r.rows.map(row=>`<tr>${row.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}catch(e){$('table-result').textContent=e.message;}finally{$('run-query').disabled=false;}};

refresh().then(initAgents).catch(e=>tell(e.message,true));
