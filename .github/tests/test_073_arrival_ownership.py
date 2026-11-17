"""Arrival controls work with authenticated dashboard ownership and no entity map.

Exercise the production WebSocket loading path in Chromium, including delayed
responses and two homes. Home Assistant service transport is simulated.
"""
from pathlib import Path
import shutil
import subprocess
import sys

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
CHROME = shutil.which("chromium") or shutil.which("google-chrome")

LOGIC = r"""
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const classes=new Map();
const context={HTMLElement:class {},window:{},console,
  customElements:{get:k=>classes.get(k),define:(k,v)=>classes.set(k,v)}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const card=Object.create(classes.get('home-environment-manager-card').prototype);
card._config={entity:'sensor.hem'};const connection={};
card._hass={connection,language:'en',states:{
  'sensor.hem':{state:'idle',attributes:{}},
  'button.prepare':{state:'unknown',attributes:{entry_id:'home_a',arrival_preparation_role:'prepare'}},
  'button.cancel':{state:'unknown',attributes:{entry_id:'home_a',arrival_preparation_role:'cancel'}}}};
card._dashboardEntity='sensor.hem';card._dashboardContext={entityId:'sensor.hem',connection};
const payload={entry_id:'home_a',home_status:'away',active:false,can_start:true,
  timeout_minutes:60,entity_ids:{prepare:'button.prepare',cancel:'button.cancel'}};
card._dashboardData={version:1,owner_entry_id:'home_a',arrival_preparation:payload};
assert.equal(card._arrivalSource124().canStart,true,
  'Confirmed-away dashboard with optional HA entity map absent must enable Prepare');
for(const status of ['home','unknown']){
  payload.home_status=status;
  assert.equal(card._arrivalSource124().canStart,false);
}
payload.home_status='away';
for(const entity of ['sensor.hem','button.prepare']){
  card._hass.entities={[entity]:{config_entry_id:'home_b'}};
  assert.equal(card._arrivalSource124().controls.prepare.valid,false);
}
card._hass.entities={};
card._hass.connection={};
assert.equal(card._arrivalSource124().canStart,false,'Old connection owner leaked');
card._hass.connection=connection;
card._dashboardData.owner_entry_id='home_b';
assert.equal(card._arrivalSource124().canStart,false,'Conflicting nested owner accepted');
card._dashboardData.owner_entry_id='home_a';
card._hass.states['button.prepare'].state='unavailable';
assert.equal(card._arrivalSource124().controls.prepare.valid,false);
card._hass.states['button.prepare'].state='unknown';
for(const lang of ['en','el','de']){
  card._hass.language=lang;
  for(const status of ['away','home','unknown']){
    payload.home_status=status;
    const html=card._arrivalHeader124();
    const title=html.match(/title="([^"]*)"/)[1];
    assert.ok(title.length<260,[lang,status,title].join(': '));
    assert.ok(!title.includes('..'),title);
    assert.equal(html.match(/<button[^>]*>/)[0].includes(' disabled'),status!=='away');
  }
  payload.home_status='away';payload.active=true;payload.expires_at=Date.now()/1000+600;
  const title=card._arrivalHeader124().match(/title="([^"]*)"/)[1];
  assert.equal(title,card._arrivalWords124().cancel,'Active tooltip repeats its action');
  payload.active=false;payload.expires_at=null;
}
console.log('PASS: production arrival ownership, presence gates and compact EN/EL/DE tooltips');
"""
subprocess.run(["node", "-e", LOGIC, str(CARD)], check=True)
if "--logic-only" in sys.argv:
    sys.exit(0)
assert CHROME, "Chromium is required"

SETUP = r"""language => {
  window.calls=[]; window.pending=[]; window.revision=1;
  window.snapshots={}; window.states={};
  for (const name of ['a','b']) {
    const entry='entry_'+name;
    const ids={prepare:'button.prepare_'+name,cancel:'button.cancel_'+name,
      timeout:'number.timeout_'+name};
    snapshots['sensor.'+name]={version:1,owner_entry_id:entry,rooms:[],summary:{},outdoor:{},
      arrival_preparation:{entry_id:entry,active:false,can_start:true,home_status:'away',
        timeout_minutes:60,expires_at:null,entity_ids:ids}};
    states['sensor.'+name]={state:'idle',attributes:{
      dashboard_api:'environment_manager/dashboard',dashboard_revision:revision}};
    for (const [role,id] of Object.entries(ids)) states[id]={
      state:role==='timeout'?'60':role==='cancel'?'unavailable':'unknown',
      attributes:{entry_id:entry,arrival_preparation_role:role}};
  }
  window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);card.setConfig({entity:'sensor.a'});
  window.makeHass=()=>({language,states,connection:{},localize:()=>undefined,
    config:{time_zone:'UTC'},callService:async(...args)=>calls.push(args),
    callWS:async request=>{
      if(request.type==='environment_manager/dashboard') {
        if(window.delayDashboard) return new Promise(resolve=>pending.push({request,resolve}));
        return structuredClone(snapshots[request.entity_id]);
      }
      if(request.type==='config/device_registry/list') return ['a','b'].map(name=>({
        id:'home_'+name,model:'Home Environment Hub',
        identifiers:[['environment_manager','entry_'+name]]}));
      throw Error('Unexpected request: '+request.type);
    }});
  window.refresh=patch=>{
    const id=card._state()[0];
    Object.assign(snapshots[id].arrival_preparation,patch);
    states={...states,[id]:{...states[id],attributes:{...states[id].attributes,
      dashboard_revision:++revision}}};
    card.hass={...card._hass,states};
  };
  card.hass=makeHass();
}"""


def loaded(page):
    page.wait_for_function("card._dashboardLoadedRevision === "
                           "card._state()[1].attributes.dashboard_revision && "
                           "card._dashboardEntity === card._state()[0]")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    for language in ("en", "el", "de"):
        page = browser.new_page(viewport={"width":375,"height":850})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("<html><body></body></html>")
        page.add_script_tag(path=str(CARD))
        page.evaluate(SETUP, language)
        loaded(page)
        action = page.locator(".hem-arrival-action124")
        # HA's optional hass.entities map is absent, but the backend already
        # verified this recommendation sensor's exact config-entry ownership.
        expect(action).to_be_enabled(timeout=2000)
        title = action.get_attribute("title")
        assert len(title) < 240, (language, title)
        assert ".." not in title, title
        action.click()
        page.wait_for_function("calls.length===1&&!card._arrivalRequest124")
        assert page.evaluate("calls") == [["button", "press", {"entity_id":"button.prepare_a"}]]

        for status in ("home", "unknown"):
            page.evaluate("status=>refresh({home_status:status,can_start:false})", status)
            loaded(page)
            expect(action).to_be_disabled()
            assert len(action.get_attribute("title")) < 240
            action.evaluate("node=>node.dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true}))")
            assert page.evaluate("calls.length") == 1
        page.evaluate("refresh({home_status:'away',can_start:true})")
        loaded(page)
        expect(action).to_be_enabled()

        # Present-but-incomplete metadata is optional; contradictory metadata
        # must never let this home's control operate a different home.
        page.evaluate("() => {card.hass={...card._hass,entities:{'sensor.a':{}}};}")
        expect(action).to_be_enabled()
        for entity in ("sensor.a", "button.prepare_a"):
            page.evaluate("entity=>{card.hass={...card._hass,entities:{[entity]:{config_entry_id:'entry_b'}}};}", entity)
            expect(action).to_be_disabled()
        page.evaluate("() => {card.hass={...card._hass,entities:{}};}")
        page.evaluate("refresh({entity_ids:{prepare:'button.prepare_b',cancel:'button.cancel_a',timeout:'number.timeout_a'}})")
        loaded(page)
        expect(action).to_be_disabled()
        page.evaluate("refresh({entity_ids:{prepare:'button.prepare_a',cancel:'button.cancel_a',timeout:'number.timeout_a'}})")
        loaded(page)
        expect(action).to_be_enabled()

        # The WebSocket owner and nested arrival owner must agree, even if
        # both sets of controls are readable on the same HA connection.
        page.evaluate("refresh({entry_id:'entry_b',entity_ids:{prepare:'button.prepare_b',cancel:'button.cancel_b',timeout:'number.timeout_b'}})")
        loaded(page)
        expect(action).to_be_disabled()

        # A late response for home A must not authorize home B while B loads.
        page.evaluate("""() => {
          delayDashboard=true;refresh({entry_id:'entry_a'});
        }""")
        page.wait_for_function("pending.length===1")
        page.evaluate("card.setConfig({entity:'sensor.b'})")
        page.wait_for_function("pending.length===2")
        page.evaluate("pending[0].resolve(structuredClone(snapshots['sensor.a']))")
        assert page.evaluate("card._arrivalSource124()?.canStart===true") is False
        page.evaluate("pending[1].resolve(structuredClone(snapshots['sensor.b']))")
        loaded(page)
        expect(action).to_be_enabled()
        action.click()
        page.wait_for_function("calls.length===2&&!card._arrivalRequest124")
        assert page.evaluate("calls.at(-1)") == ["button", "press", {"entity_id":"button.prepare_b"}]

        # Reconnecting invalidates the previous authenticated snapshot until
        # the current connection returns its own verified response.
        page.evaluate("() => {card.hass=makeHass();}")
        page.wait_for_function("pending.length===3")
        assert page.evaluate("card._arrivalSource124()?.canStart===true") is False
        page.evaluate("pending[2].resolve(structuredClone(snapshots['sensor.b']))")
        loaded(page)
        expect(action).to_be_enabled()
        assert not errors, errors
        page.close()
        print(f"PASS: {language} arrival without entity metadata; exact-home ownership; compact help")
    browser.close()
