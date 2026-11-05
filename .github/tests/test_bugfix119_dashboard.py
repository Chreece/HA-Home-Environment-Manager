"""Exercise actual settings navigation across card source/connection changes.

Only the DOM shell and Home Assistant transport are simulated. Deferred
registry replies exercise the production setters, loader and click listener;
ordinary state updates must keep the successful cache and request deduplication.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"

SCRIPT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const registered=new Map(),paths=[],warnings=[];
class Element {
  constructor(){this.isConnected=true;}
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
}
const context={HTMLElement:Element,window:{
  history:{pushState(_state,_unused,path){paths.push(path);}},dispatchEvent(){}},
  Event:class {constructor(type){this.type=type;}},
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
const state={state:'ready',attributes:{dashboard:{version:1,rooms:[{
  area_id:'shared_room',name:'Shared room'}]}}};
function registry(suffix=''){
  return ['a','b'].flatMap(name=>[
    {id:'home_'+name+suffix,identifiers:[['environment_manager','entry_'+name+suffix]]},
    {id:'room_'+name+suffix,identifiers:[['environment_manager','entry_'+name+suffix+'_area_shared_room']]},
  ]);
}
function transport(suffix=''){
  const requests=[];
  const hass={language:'en',connection:{},user:{is_admin:true},
    states:{'sensor.a':state,'sensor.b':state},
    entities:Object.fromEntries(['a','b'].map(name=>['sensor.'+name,{
      device_id:'home_'+name+suffix,config_entry_id:'entry_'+name+suffix}])),
    callWS(message){
      assert.equal(message.type,'config/device_registry/list');
      const request={...deferred(),message};requests.push(request);return request.promise;
    },
    callService(){throw Error('Settings navigation must not control a device');},
  };
  return {hass,requests};
}
function makeCard(hass,entity='sensor.a'){
  const card=new Card();
  // Painting is irrelevant to the production request/ownership behavior.
  card._render=()=>{};
  card.setConfig({entity});card.hass=hass;
  return card;
}
function clickHome(card){
  card.shadowRoot.deliver('click',{target:{closest(selector){
    return selector==='[data-edit-area],[data-edit-home]'?{getAttribute:()=>null}:null;
  }}});
}
function assertNoLinks(card){
  const before=paths.length;clickHome(card);
  assert.equal(paths.length,before,'Home settings navigated to an old source');
  assert.equal(card._homeDeviceId,null,'Old home device remained navigable');
  assert.equal(card._areaDeviceIds.size,0,'Old room devices remained available');
  assert.equal(card._configEntryId114,null,'Old options-flow entry remained available');
}
function assertLinks(card,name,suffix=''){
  assert.equal(card._homeDeviceId,'home_'+name+suffix);
  assert.equal(card._areaDeviceIds.get('shared_room'),'room_'+name+suffix);
  assert.equal(card._configEntryId114,'entry_'+name+suffix);
  assert.equal(card._configEntryOwner114,'sensor.'+name);
  clickHome(card);
  assert.equal(paths.at(-1),'/config/devices/device/home_'+name+suffix);
}
const cases=[];
const test=(name,run)=>cases.push({name,run});

test('setConfig retires old navigation immediately and loads selected source',async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();requests[0].resolve(registry());await drain();assertLinks(card,'a');
  card.setConfig({entity:'sensor.b'});
  assertNoLinks(card);
  await drain();assert.equal(requests.length,2,'Config change waited for another HA update');
  requests[1].resolve(registry());await drain();assertLinks(card,'b');
});

test('replacement connection cannot reuse loaded settings links',async()=>{
  const old=transport('_old'),next=transport('_new'),card=makeCard(old.hass);
  await drain();old.requests[0].resolve(registry('_old'));await drain();assertLinks(card,'a','_old');
  card.hass=next.hass;
  assertNoLinks(card);
  await drain();assert.equal(next.requests.length,1,'Reconnection retained the old registry cache');
  next.requests[0].resolve(registry('_new'));await drain();assertLinks(card,'a','_new');
});

for(const outcome of ['success','failure'])test('source change during pending '+outcome,async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();assert.equal(requests.length,1);
  card.setConfig({entity:'sensor.b'});await drain();
  assert.equal(requests.length,2,'New source was blocked by the old request');
  const current=card._deviceRegistryLoading;
  if(outcome==='success')requests[0].resolve(registry('_retired'));
  else requests[0].reject(Error('Retired source failed'));
  await drain();
  assert.equal(card._deviceRegistryLoading,current,'Retired completion released current request');
  assert.equal(card._deviceRegistryFailureCount,0,'Retired failure penalized current source');
  assert.equal(card._deviceRegistryNextAttemptAt,0);
  assertNoLinks(card);
  requests[1].resolve(registry());await drain();assertLinks(card,'b');
});

test('source retry delay does not block another source or connection',async()=>{
  const old=transport(),card=makeCard(old.hass);
  await drain();old.requests[0].reject(Error('Temporary registry failure'));await drain();
  assert.ok(card._deviceRegistryNextAttemptAt>Date.now());
  card._loadDeviceIds();await drain();assert.equal(old.requests.length,1,'Retry backoff was lost');
  card.setConfig({entity:'sensor.b'});await drain();
  assert.equal(old.requests.length,2,'Previous-source backoff blocked the new source');
  old.requests[1].reject(Error('Connection failed'));await drain();
  const next=transport('_new');card.hass=next.hass;await drain();
  assert.equal(next.requests.length,1,'Previous connection backoff blocked reconnection');
  next.requests[0].resolve(registry('_new'));await drain();assertLinks(card,'b','_new');
});

test('queued registry request uses its captured transport and cannot replace new links',async()=>{
  const old=transport('_old'),next=transport('_new'),card=makeCard(old.hass);
  card.hass=next.hass;await drain();
  assert.equal(old.requests.length,1,'Old queued work was sent through the replacement connection');
  assert.equal(next.requests.length,1,'Replacement connection was blocked by old queued work');
  next.requests[0].resolve(registry('_new'));await drain();assertLinks(card,'a','_new');
  old.requests[0].resolve(registry('_old'));await drain();assertLinks(card,'a','_new');
  assert.equal(card._deviceRegistryLoading,null);
});

test('ordinary hass updates keep request deduplication and loaded registry cache',async()=>{
  const {hass,requests}=transport(),card=makeCard(hass);
  await drain();
  for(let n=0;n<5;n++)card.hass={...hass,states:{...hass.states}};
  card.setConfig({entity:'sensor.a',title:'My home'});await drain();
  assert.equal(requests.length,1,'Ordinary update duplicated a pending registry request');
  requests[0].resolve(registry());await drain();assertLinks(card,'a');
  for(let n=0;n<5;n++)card.hass={...hass,states:{...hass.states}};
  card.setConfig({entity:'sensor.a',show_science:false});await drain();
  assert.equal(requests.length,1,'Ordinary update discarded a valid registry cache');
  assertLinks(card,'a');
});

(async()=>{
  let failed=0;
  for(const {name,run} of cases){
    try{await run();console.log('PASS: '+name);}
    catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}
  }
  if(failed)process.exitCode=1;
  else console.log('CARD_SETTINGS_REGISTRY_CONTEXT=PASS ('+cases.length+' cases)');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


if __name__ == "__main__":
    raise SystemExit(subprocess.call(["node", "-e", SCRIPT, str(CARD)]))
