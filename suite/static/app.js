'use strict';
let token = '';
const $ = id => document.getElementById(id);
function status(message, error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
async function api(path, options={}){
 const headers={...(options.body?{'Content-Type':'application/json'}:{}),...(token?{'Authorization':'Bearer '+token}:{}),...(options.headers||{})};
 const res=await fetch(path,{...options,headers});
 const data=await res.json();
 if(!res.ok) throw new Error(data.error||'Request failed.');
 return data;
}
function clearPrivateView(){for(const id of ['record-list','vault-list','audit-list','pass-list'])$(id).replaceChildren();$('verify-form').reset();}
function formData(form){return Object.fromEntries(new FormData(form));}
function safeHandler(fn){return async event=>{if(event)event.preventDefault();try{await fn(event);}catch(e){status(e.message,true);}};}
function tile(title, lines){const div=document.createElement('div');div.className='tile';const h=document.createElement('strong');h.textContent=title;div.append(h);for(const line of lines){const p=document.createElement('p');p.textContent=line;div.append(p);}return div;}
function action(label,fn){const b=document.createElement('button');b.textContent=label;b.className='secondary';b.addEventListener('click',safeHandler(async()=>{b.disabled=true;try{await fn();}finally{b.disabled=false;}}));return b;}
for(const b of document.querySelectorAll('.tab')) b.addEventListener('click',()=>{document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==b.dataset.panel);document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===b));});
$('auth-form').addEventListener('submit',safeHandler(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify(formData($('auth-form')))});token=d.token;clearPrivateView();$('account-state').textContent='Signed in as '+d.email+' · Session expires in one hour.';$('auth-form').elements.password.value='';status('Signed in. Your access token is held only in this tab’s memory.');}));
$('register').addEventListener('click',safeHandler(async()=>{const d=await api('/api/register',{method:'POST',body:JSON.stringify(formData($('auth-form')))});status(d.message);}));
$('logout').addEventListener('click',safeHandler(async()=>{try{if(token)await api('/api/logout',{method:'POST'});status('Signed out. Token revoked.');}finally{token='';$('account-state').textContent='Signed out.';clearPrivateView();}}));
async function loadRecords(){const d=await api('/api/records');$('record-list').replaceChildren(...d.records.map(r=>tile(r.name,[r.external_id,r.email])));if(!d.records.length)$('record-list').textContent='No records yet.';}
$('record-form').addEventListener('submit',safeHandler(async()=>{const data=formData($('record-form'));data.confirm_distinct=$('record-form').elements.confirm_distinct.checked;const d=await api('/api/records',{method:'POST',body:JSON.stringify(data)});status(d.classification+': '+d.message);await loadRecords();}));
$('load-records').addEventListener('click',safeHandler(loadRecords));
$('vault-form').addEventListener('submit',safeHandler(async()=>{const d=await api('/api/vault',{method:'POST',body:JSON.stringify(formData($('vault-form')))});status(d.message);}));
$('vault-search').addEventListener('submit',safeHandler(async()=>{const q=$('vault-search').elements.q.value;const d=await api('/api/vault?q='+encodeURIComponent(q));$('vault-list').replaceChildren(...d.entries.map(r=>tile(r.label,[r.secret])));if(!d.entries.length)$('vault-list').textContent='No matching entries.';status('Returned '+d.entries.length+' entries from your account.');}));
$('load-audit').addEventListener('click',safeHandler(async()=>{$('audit-list').textContent=JSON.stringify(await api('/api/audit'),null,2);status('Loaded recent audit events.');}));
async function loadRoutes(){const d=await api('/api/routes');$('route-list').replaceChildren(...d.routes.map(r=>{const div=tile(r.name,['$'+(r.fare_cents/100).toFixed(2)+' · '+r.remaining+' seats',new Date(r.departure).toLocaleString()]);let pendingKey=null;div.append(action('Book pass',async()=>{pendingKey=pendingKey||crypto.randomUUID();const result=await api('/api/passes',{method:'POST',headers:{'Idempotency-Key':pendingKey},body:JSON.stringify({route_id:r.id})});pendingKey=null;status('Pass issued: '+result.booking.id);await loadRoutes();await loadPasses();}));return div;}));}
async function loadPasses(){const d=await api('/api/passes');$('pass-list').replaceChildren(...d.bookings.map(b=>{const div=tile('Pass '+b.id.slice(0,8),['Route '+b.route_id+' · $'+(b.fare_cents/100).toFixed(2),b.status]);if(b.verification_code){const pre=document.createElement('pre');pre.textContent=b.verification_code;div.append(pre);div.append(action('Cancel pass',async()=>{const result=await api('/api/passes/'+encodeURIComponent(b.id)+'/cancel',{method:'POST'});status(result.message);await loadPasses();await loadRoutes();}));}return div;}));if(!d.bookings.length)$('pass-list').textContent='No bookings yet.';}
$('load-routes').addEventListener('click',safeHandler(loadRoutes));$('load-passes').addEventListener('click',safeHandler(loadPasses));
$('verify-form').addEventListener('submit',safeHandler(async()=>{await api('/api/passes/verify',{method:'POST',body:JSON.stringify(formData($('verify-form')))});status('Valid active pass owned by your account.');}));
$('chat-form').addEventListener('submit',safeHandler(async()=>{const question=$('chat-form').elements.question.value;const q=document.createElement('p');q.className='bubble user';q.textContent=question;$('chat-log').append(q);const d=await api('/api/chat',{method:'POST',body:JSON.stringify({question})});const a=document.createElement('p');a.className='bubble';a.textContent=d.answer;const s=document.createElement('small');s.textContent=d.source?'Source: '+d.source+' · Similarity: '+d.similarity:'No reliable source match';a.append(s);$('chat-log').append(a);$('chat-form').reset();a.scrollIntoView({block:'nearest'});}));
loadRoutes().catch(e=>status(e.message,true));
