"""Exercise production dashboard requests and cover links across source changes.

Deferred WebSocket replies reproduce out-of-order success/failure without a
browser or network. The small DOM fixture records the card's real click
listener; it does not reimplement its source checks or request lifecycle.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"

SCRIPT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const registered=new Map(),warnings=[];
class Element {
  constructor(){this.isConnected=true;this.events=[];}
  attachShadow(){
    const listeners=new Map();
    this.shadowRoot={
      addEventListener(type,handler){
        if(!listeners.has(type))listeners.set(type,[]);
        listeners.get(type).push(handler);
      },
      deliver(type,event){for(const handler of listeners.get(type)||[])handler(event);},
    };
    return this.shadowRoot;
  }
  dispatchEvent(event){this.events.push(event);return true;}
}
const context={HTMLElement:Element,window:{},
  CustomEvent:class {constructor(type,options){this.type=type;Object.assign(this,options);}},
  customElements:{get:name=>registered.get(name),define:(name,ctor)=>registered.set(name,ctor)},
  console:{...console,warn:(...args)=>warnings.push(args)},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context,{filename:process.argv[1]});
const Card=registered.get('home-environment-manager-card');
const drain=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
  return {promise,resolve,reject};
}
const apiState=revision=>({state:'ready',attributes:{
  dashboard_api:'environment_manager/dashboard',dashboard_revision:revision}});
const snapshot=(name,cover='cover.'+name)=>({version:1,rooms:[{
  area_id:'shared_room',name,environment:{shade_cooling:{selected_covers:[cover]}}}]});
function transport(){
  const requests=[];
  const hass={language:'en',connection:{},states:{
    'sensor.a':apiState(1),'sensor.b':apiState(2)},
    callWS(message){
      assert.equal(message.type,'environment_manager/dashboard');
      const request={...deferred(),message};requests.push(request);return request.promise;
    },
    callService(){throw Error('Read-only loading/link tests must not control a device');},
  };
  return {hass,requests};
}
function makeCard(hass,entity='sensor.a'){
  const card=new Card();
  // These tests exercise the actual setters/loader and click listener. DOM
  // painting and the independent device registry request are outside scope.
  card._render=()=>{};
  card._loadDeviceIds=()=>{};
  card.setConfig({entity});card.hass=hass;
  return card;
}

const cases=[];
const test=(name,run)=>cases.push({name,run});
for(const outcome of ['success','failure'])test('source change during pending '+outcome,async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();assert.equal(requests.length,1);
  card.setConfig({entity:'sensor.b'});
  await drain();
  assert.equal(requests.length,2,'Selected source B waited for unfinished source A');
  assert.equal(requests[1].message.entity_id,'sensor.b');
  const current=card._dashboardFetching;
  if(outcome==='success')requests[0].resolve(snapshot('old'));
  else requests[0].reject(Error('Old source is offline'));
  await drain();
  assert.equal(card._dashboardFetching,current,'Old completion cleared the new request');
  assert.equal(card._dashboardEntity,null,'Old source was painted into the selected card');
  assert.equal(card._dashboardFailureCount,0,'Old failure penalized the new source');
  assert.equal(card._dashboardNextAttemptAt,0);
  requests[1].resolve(snapshot('current'));
  await drain();
  assert.equal(card._dashboard105().rooms[0].name,'current');
  assert.equal(card._dashboardEntity,'sensor.b');
  assert.equal(card._dashboardLoadedRevision,2);
  assert.equal(card._dashboardFetching,null);
});

test('failure backoff belongs to its selected source',async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();requests[0].reject(Error('Source A is unavailable'));await drain();
  assert.equal(card._dashboardFailureCount,1);
  assert.ok(card._dashboardNextAttemptAt>Date.now());
  card._loadDashboard();await drain();
  assert.equal(requests.length,1,'Current-source failures must retain retry backoff');
  card.setConfig({entity:'sensor.b'});await drain();
  assert.equal(requests.length,2,'Source A retry delay blocked healthy source B');
  requests[1].resolve(snapshot('healthy'));await drain();
  assert.equal(card._dashboard105().rooms[0].name,'healthy');
  assert.equal(card._dashboardFailureCount,0);
});

test('same-source requests stay deduplicated and catch up to revision changes',async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();
  card.hass={...hass,states:{...hass.states,'sensor.a':apiState(3)}};
  card._loadDashboard();await drain();
  assert.equal(requests.length,1,'Ordinary HA updates duplicated an in-flight request');
  requests[0].resolve(snapshot('revision_one'));await drain();
  assert.equal(requests.length,2,'New revision was lost while the previous request ran');
  requests[1].resolve(snapshot('revision_three'));await drain();
  assert.equal(card._dashboardLoadedRevision,3);
  assert.equal(card._dashboard105().rooms[0].name,'revision_three');
  card._loadDashboard();await drain();
  assert.equal(requests.length,2,'Already loaded revision was fetched again');
});

test('replacement connection uses its own transport and rejects late old data',async()=>{
  const old=transport(),next=transport(),card=makeCard(old.hass);
  await drain();
  card.hass=next.hass;await drain();
  assert.equal(next.requests.length,1,'A replaced connection remained blocked by the old one');
  next.requests[0].resolve(snapshot('new_connection'));await drain();
  old.requests[0].resolve(snapshot('old_connection'));await drain();
  assert.equal(card._dashboard105().rooms[0].name,'new_connection');
  assert.equal(card._dashboardFetching,null);
  // A connection can also change before the deferred call is dispatched.
  // Source A's queued request must never be sent through source B's transport.
  const queued=transport(),replacement=transport(),other=makeCard(queued.hass);
  other._config={entity:'sensor.b'};other.hass=replacement.hass;await drain();
  assert.deepEqual(replacement.requests.map(r=>r.message.entity_id),['sensor.b']);
  replacement.requests[0].resolve(snapshot('replacement'));await drain();
  for(const request of queued.requests)request.resolve(snapshot('ignored'));
  await drain();
  assert.equal(other._dashboard105().rooms[0].name,'replacement');
});

test('new connection cannot reuse the previous connection cache',async()=>{
  const old=transport(),next=transport(),card=makeCard(old.hass);
  await drain();old.requests[0].resolve(snapshot('old_cached'));await drain();
  card.hass=next.hass;await drain();
  assert.equal(next.requests.length,1,'Same entity/revision reused another connection cache');
  assert.equal(card._dashboard105(),null,'Old connection readings remained current');
  next.requests[0].resolve(snapshot('new_cached'));await drain();
  assert.equal(card._dashboard105().rooms[0].name,'new_cached');
});

test('cover links use only the currently displayed source',async()=>{
  const card=new Card(),old=snapshot('old'),current=snapshot('current');
  card._config={entity:'sensor.b'};
  card._hass={language:'en',states:{
    'sensor.b':{state:'ready',attributes:{dashboard:current}}},
    callService(){throw Error('Cover detail navigation must not issue device commands');}};
  card._dashboardEntity='sensor.a';card._dashboardData=old;
  const click=id=>card.shadowRoot.deliver('click',{target:{
    closest(selector){return selector==='[data-open-shade]'?{
      getAttribute:name=>name==='data-open-shade'?id:'shared_room'}:null;}}});
  assert.equal(card._shadingEvidence('shared_room').selected_covers[0],'cover.current',
    'Cover source validation preferred cached A over displayed B');
  click('cover.current');
  assert.equal(card.events.length,1,'Current inline cover link became inert');
  assert.equal(card.events[0].type,'hass-more-info');
  assert.equal(card.events[0].detail.entityId,'cover.current');
  click('cover.old');assert.equal(card.events.length,1,'Old source cover was accepted');
  // While current B has no snapshot, stale A must not authorize a link.
  card._hass.states['sensor.b']=apiState(2);
  assert.equal(card._shadingEvidence('shared_room'),null);
  click('cover.old');assert.equal(card.events.length,1);
  // The current WS-backed dashboard remains a supported source too.
  card._dashboardEntity='sensor.b';card._dashboardData=current;
  click('cover.current');assert.equal(card.events.length,2);
  // A newer inline dashboard for the same entity also takes precedence.
  card._hass.states['sensor.b']={state:'ready',attributes:{dashboard:snapshot('inline')}};
  click('cover.inline');assert.equal(card.events.at(-1).detail.entityId,'cover.inline');
  click('cover.current');assert.equal(card.events.length,3);
});

(async()=>{
  let failed=0;
  for(const {name,run} of cases){
    try{await run();console.log('PASS: '+name);}
    catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}
  }
  if(failed)process.exitCode=1;
  else console.log('CARD_ASYNC_SOURCE_CONTEXT_AND_COVER_NAVIGATION=PASS ('+cases.length+' cases)');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


if __name__ == "__main__":
    raise SystemExit(subprocess.call(["node", "-e", SCRIPT, str(CARD)]))
