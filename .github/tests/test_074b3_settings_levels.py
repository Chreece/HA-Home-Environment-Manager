"""Cumulative settings levels use the production policy, filters and menus.

Node exercises the real card's preference helpers in isolated browser-like
realms. Chromium covers native/form controls, view-only changes, persistence,
scope transitions and pending edits. All HA services and Options transports
are fixtures; no physical device or real configuration entry is contacted.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/home-environment-manager-card.js"
POLICY = CARD.with_name("settings-audit-policy.json")

NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(process.argv[1],'utf8');
// Isolated production sections use the same bundled locale helpers as the full card.
const localeStart=source.indexOf('  /* HEM_TRANSLATION_DATA_B8_START */');
const localeEnd=source.indexOf('  const BRAND_TITLE =',localeStart);
assert(localeStart>0&&localeEnd>localeStart);
const localeBootstrap=source.slice(localeStart,localeEnd);
const policy=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const start=source.indexOf('  const auditPolicyB8='),end=source.indexOf('  const auditProto=',start);
assert(start>0&&end>start);
const api=new Function(localeBootstrap+source.slice(start,end)+
 '\nreturn {auditPolicyB8,auditLevelB8,auditVisibleB8};')();
assert.deepEqual(api.auditPolicyB8,policy);
assert.deepEqual(policy.levels,['basic','advanced','expert']);
const plain=value=>JSON.parse(JSON.stringify(value));
const saved=level=>({settingsAudit:{level,query:''}});
const field=(key,domain='number',attrs={})=>({id:domain+'.renamed',domain,label:'A setting',
 reg:{translation_key:key},state:{state:'12',attributes:attrs}});
let cases=0;
for(const [key,minimum] of Object.entries(policy.native_levels)){
 const f=field(key),required=policy.levels.indexOf(minimum);
 assert.equal(api.auditLevelB8(f),minimum,key);
 for(const [rank,level] of policy.levels.entries()){
  assert.equal(Boolean(api.auditVisibleB8(saved(level),f)),rank>=required,key+' at '+level);
  cases++;
 }
}
for(const key of ['equipment_min_on_seconds','equipment_min_off_seconds','equipment_max_on_seconds',
 'equipment_control_mode','equipment_pid_calibration_method','equipment_off_state_watchdog_mode',
 'equipment_pid_review_approve','equipment_pid_review_discard','equipment_resume',
 'equipment_sensor_verified','equipment_pause_on_window_open','future_new_setting']){
 assert.equal(api.auditLevelB8(field(key)),'basic',key);
 assert(api.auditVisibleB8(saved('basic'),field(key)),key);
}
for(const key of ['kp','ki','kd']){
 const scoped=field('renamed_registry_translation','number',{
   settings_scope:'operating_mode',operating_mode:'cool',setting_key:key});
 assert.equal(api.auditLevelB8(scoped),'advanced');
 assert(!api.auditVisibleB8(saved('basic'),scoped));
 assert(api.auditVisibleB8(saved('advanced'),scoped));
}
assert.equal(api.auditLevelB8(field('unrelated','select',{door_setting_key:'energy_meter'})),'expert');
assert.equal(api.auditLevelB8(field('unrelated','select',{door_setting_key:'target_area'})),'basic');
const model=field('equipment_pid_process_gain');model.label='Process model gain';
const query={settingsAudit:{level:'basic',query:'process model'}};
const before=JSON.stringify({query,model});
assert(!api.auditVisibleB8(query,model),'Search must not reveal Expert controls in Basic');
query.settingsAudit.level='advanced';assert(!api.auditVisibleB8(query,model));
query.settingsAudit.level='expert';assert(api.auditVisibleB8(query,model));
query.settingsAudit.level='basic';assert.equal(JSON.stringify({query,model}),before);
for(const phase of ['dirty','saving','awaiting','failed']){
 const s={settingsAudit:{level:'basic',query:'does not match'},
   nativeEdits:new Map([[model.id,{phase,desired:14}]])};
 assert(api.auditVisibleB8(s,model),phase+' edit must remain discoverable');
 s.nativeEdits.get(model.id).phase='saved';assert(!api.auditVisibleB8(s,model));
}
assert(api.auditVisibleB8({settingsAudit:{advanced:true,query:''}},model),'Legacy show-all migrates to Expert');
assert(!api.auditVisibleB8({settingsAudit:{advanced:false,query:''}},model));
assert(!api.auditVisibleB8({settingsAudit:{level:'basic',advanced:true,query:''}},model),
 'A new explicit level outranks the old boolean');
assert(!api.auditVisibleB8({settingsAudit:{level:'__proto__',query:''}},model));

function storage(){const data=new Map();return {
 getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,String(value)),
 removeItem:key=>data.delete(key),data};}
function realm(store){
 const elements=new Map();
 const context={console,Promise,setTimeout,clearTimeout,localStorage:store,
  HTMLElement:class {},window:{customCards:[],localStorage:store},
  customElements:{get:name=>elements.get(name),define:(name,ctor)=>elements.set(name,ctor)}};
 vm.createContext(context);vm.runInContext(source,context);
 const Ctor=elements.get('home-environment-manager-card');assert(Ctor);
 return {card(user='alice',entry='entry0'){
  const c=Object.create(Ctor.prototype);
  c._hass={language:'en',user:{id:user,is_admin:true},states:{},entities:{},
   callService(){throw Error('A level preference must not call HA services');},
   callApi(){throw Error('A level preference must not save HA options');}};
  c._configEntryId114=entry;c._configEntryOwner114='sensor.hem';
  return c;
 }};
}
const persisted=storage(),first=realm(persisted),alice=first.card();
const room={entryId:'entry0',settingsAudit:{advanced:false,query:''}};
assert.equal(alice._settingsAuditSelectedLevelB8(room),'basic');
alice._settingsAuditSetLevelB8(room,'advanced');
assert.equal(alice._settingsAuditSelectedLevelB8({entryId:'entry0'}),'advanced');
assert.equal(first.card()._settingsAuditSelectedLevelB8({entryId:'entry0'}),'advanced');
const key=alice._settingsAuditPreferenceKeyB8(room);
assert.equal(key,'hem.settings-level.v1:alice:entry0');
assert.equal(realm(persisted).card()._settingsAuditSelectedLevelB8({entryId:'entry0'}),'advanced',
 'A fresh card script must restore the persisted preference');
assert.equal(first.card('bob')._settingsAuditSelectedLevelB8({entryId:'entry0'}),'basic');
assert.equal(first.card('alice','entry1')._settingsAuditSelectedLevelB8({entryId:'entry1'}),'basic');
alice._settingsAuditSetLevelB8(room,'basic');
assert.equal(alice._settingsAuditSelectedLevelB8({entryId:'entry0',settingsAudit:{advanced:true}}),'basic',
 'An old dialog must not overwrite a newer explicit preference');
const migrator=realm(storage()).card('legacy');
assert.equal(migrator._settingsAuditSelectedLevelB8({entryId:'entry0',settingsAudit:{advanced:true}}),'expert');
const invalid=storage();invalid.setItem('hem.settings-level.v1:alice:entry0','unlimited');
assert.equal(realm(invalid).card()._settingsAuditSelectedLevelB8({entryId:'entry0'}),'basic');
const denied={getItem(){throw Error('Storage denied');},setItem(){throw Error('Storage denied');}};
const blocked=realm(denied),privateCard=blocked.card();
privateCard._settingsAuditSetLevelB8({entryId:'entry0'},'expert');
assert.equal(privateCard._settingsAuditSelectedLevelB8({entryId:'entry0'}),'expert');
assert.equal(blocked.card()._settingsAuditSelectedLevelB8({entryId:'entry0'}),'expert');
const anonymousA=first.card(undefined),anonymousB=first.card(undefined);
delete anonymousA._hass.user.id;delete anonymousB._hass.user.id;
anonymousA._settingsAuditSetLevelB8({entryId:'entry0'},'expert');
assert.equal(anonymousA._settingsAuditSelectedLevelB8({entryId:'entry0'}),'expert');
assert.equal(anonymousB._settingsAuditSelectedLevelB8({entryId:'entry0'}),'basic',
 'An unidentified fixture/session must not inherit a different card preference');
for(const [key,level] of Object.entries(policy.home_option_levels))
 assert.equal(alice._settingsAuditOptionLevelB8(key,'home'),level,key);
for(const [key,level] of Object.entries(policy.room_option_levels))
 assert.equal(alice._settingsAuditOptionLevelB8(key,'room'),level,key);
assert.equal(alice._settingsAuditOptionLevelB8('future_option','home'),'basic');
// Native row markup describes the field; the audit pass owns visibility.
// Changing a view must not introduce a different source row on HA refresh.
const rowSaved={entryId:'entry0'};alice._roomSettingsDialog114=rowSaved;
const renderField=field('equipment_kp','number',{min:0,max:100,step:1});
let initialMarkup;
for(const level of policy.levels){
 alice._settingsAuditSetLevelB8(rowSaved,level);
 for(const query of ['', 'A setting', 'unmatched search']){
  rowSaved.settingsAudit.query=query;
  const markup=alice._hemFullRow127(renderField,'room');
  initialMarkup??=markup;
  assert.equal(markup,initialMarkup,'View filtering must leave native row rendering unchanged');
 }
}
console.log('PASS: '+cases+' native tier comparisons; exact scoped identities; source/safety/action essentials; level-aware search; stable native row rendering; pending edits; persisted per-user/entry preference; migration and denied-storage fallback');
"""


def node_checks():
    subprocess.run([shutil.which("node") or "node", "-e", NODE,
                    str(CARD), str(POLICY)], check=True)


DECORATE = r"""({language,user})=>{
  card._hass.language=language;card._hass.user={id:user,is_admin:true};
  const add=(id,key,value,device,extra={})=>{
    card._hass.states[id]={state:String(value),attributes:{min:0,max:100,step:1,
      friendly_name:key,configuration_help:'Settings-level fixture',...extra}};
    registry.push({entity_id:id,translation_key:key,device_id:device,
      unique_id:'entry0_area_room0_'+id.replace('.','_'),
      platform:'environment_manager',config_entry_id:'entry0'});
  };
  add('number.room_gain','equipment_kp',10,'living-device',{friendly_name:'Manual proportional gain'});
  add('number.room_model','area_area_environment_met',1,'living-device',{friendly_name:'Specialist comfort model'});
  add('number.room_safe','equipment_min_on_seconds',5,'living-device');
  const attrs=card._hass.states['climate.managed_0_0'].attributes;
  attrs.controller_id='level-controller';attrs.selected_operating_mode='dry';attrs.supported_operating_modes=['dry'];
  card._hass.entities['climate.managed_0_0']={device_id:'level-device',config_entry_id:'entry0'};
  const scoped={controller_id:'level-controller',area_id:'room0',
    source_entity_ids:['climate.physical_0_0'],settings_scope:'operating_mode',operating_mode:'dry'};
  add('number.device_gain','equipment_kp',12,'level-device',{...scoped,setting_key:'kp'});
  add('number.device_model','equipment_pid_process_gain',2,'level-device',{...scoped,setting_key:'pid_process_gain'});
  add('switch.device_pause','equipment_pause_on_window_open','on','level-device',{
    ...scoped,setting_key:'pause_on_window_open'});
  add('select.device_method','equipment_control_mode','pid','level-device',{
    ...scoped,setting_key:'control_mode',options:['existing','automatic','pid','manual','off']});
  for(const role of ['approve','discard'])add('button.device_'+role,'equipment_pid_review_'+role,
    'unknown','level-device',{...scoped,setting_key:'pid_review_'+role,pid_review_role:role});
  // Pollen thresholds form a validated pair; include both actual Options
  // fields so the rejected-save case reaches the transport boundary.
  for(const [name,value] of [['global_threshold_indoor_co2',1000],['pollen_high_from',3],['pollen_max_scale',5]]){
    homeData[name]=value;homeForm.data_schema.push({name,default:value,
      selector:{number:{min:0,max:2000,step:1}}});
  }
  card._hass={...card._hass,states:{...card._hass.states}};card._renderContent(true);
}"""


def browser_checks():
    from playwright.sync_api import sync_playwright, expect

    chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for cumulative setting-level menus"
    room = runpy.run_path(str(ROOT / ".github/tests/test_beta114_room_settings.py"))
    base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
    tree = ast.parse((ROOT / ".github/tests/test_062b7_autosave.py").read_text())
    autosave = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "SETUP" for t in n.targets))
    states = deepcopy(base["fixture_definitions"]()["states"])
    states["sensor.hem"]["attributes"]["dashboard"]["rooms"] = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][:2]
    body = ('<style>body{margin:0;background:#161616;color:#eee;font:14px Arial;'
            '--card-background-color:#222;--primary-text-color:#eee;'
            '--secondary-text-color:#aaa}</style>')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
        for language, width in (("en", 760), ("el", 320), ("de", 390)):
            context = browser.new_context(viewport={"width": width, "height": 950})
            context.route("https://hem-settings.test/**", lambda route: route.fulfill(
                status=200, content_type="text/html", body=body))
            errors = []

            def boot(user="alice"):
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("https://hem-settings.test/settings")
                page.evaluate(base["icon_fixture"]())
                page.add_script_tag(path=str(CARD))
                page.evaluate(room["SETUP"], {"states": states, "form": room["FORM"], "native": False})
                page.evaluate("form=>window.roomSchema=form", room["FORM"])
                page.evaluate(autosave)
                page.evaluate(DECORATE, {"language": language, "user": user})
                return page

            page = boot()

            def opened(scope):
                expressions = {"room": "card._openRoomSettings114('room0')",
                               "home": "card._openHomeSettings128()",
                               "device": "card._openHemControllerSettings126('room0','climate.managed_0_0')"}
                properties = {"room": "_roomSettingsDialog114", "home": "_homeSettingsDialog128",
                              "device": "_hemControllerDialog126"}
                dialogs = {"room": "dialog.hem-room-options114", "home": "dialog.hem-home-options128",
                           "device": "dialog.hem-controller-options126"}
                assert page.evaluate(expressions[scope]), scope
                page.wait_for_function(f"card.{properties[scope]}?.fullRegistry127?.length===registry.length")
                if scope == "home":
                    page.wait_for_function("card._homeSettingsDialog128?.fields?.length===7")
                page.evaluate(f"card.{properties[scope]}.node.querySelectorAll('details').forEach(node=>node.open=true)")
                return page.locator(dialogs[scope]), properties[scope]

            modal, prop = opened("room")
            level = modal.locator("[data-settings-level-b8]")
            expect(level).to_have_value("basic")
            assert modal.locator("[data-settings-advanced-b8]").count() == 0
            assert level.evaluate("node=>Boolean(node.labels?.length||node.getAttribute('aria-label'))")
            before = page.evaluate("JSON.stringify({writes,optionWrites,homeData,committed})")

            def check_levels(scope, modal, identities):
                selector = modal.locator("[data-settings-level-b8]")
                for rank, value in enumerate(("basic", "advanced", "expert")):
                    selector.select_option(value)
                    for required, identity in enumerate(identities):
                        row = modal.locator(identity)
                        assert row.count() == 1, (scope, identity)
                        assert (row.get_attribute("hidden") is None) == (rank >= required), (scope, value, identity)
                    assert modal.evaluate("node=>node.scrollWidth<=node.clientWidth+1"), (scope, value, width)
                    assert modal.locator("[data-settings-tools-b8]").evaluate("node=>node.scrollWidth<=node.clientWidth+1")
                    geometry = selector.evaluate("""node=>{
                      const style=getComputedStyle(node),canvas=document.createElement('canvas');
                      const painter=canvas.getContext('2d');painter.font=style.font;
                      const text=node.selectedOptions[0].textContent;
                      const needed=painter.measureText(text).width+parseFloat(style.paddingLeft)+
                        parseFloat(style.paddingRight)+18;
                      return {width:node.clientWidth,needed,text};
                    }""")
                    assert geometry["width"]+1 >= geometry["needed"], (scope, language, width, value, geometry)
                    for group in modal.locator("[data-hem-unified141]").all():
                        rows = group.locator("[data-hem-full-row127],[data-hem-home-field128],[data-room-options-group114]")
                        if rows.count():
                            hidden = rows.evaluate_all("nodes=>nodes.every(node=>node.hidden)")
                            assert (group.get_attribute("hidden") is not None) == hidden

            check_levels("room", modal, tuple(f'[data-hem-full-row127="number.room_{suffix}"]'
                                               for suffix in ("safe", "gain", "model")))
            for group in room["KEYS"]:
                assert modal.locator(f'[data-room-options-group114="{group}"]').get_attribute("hidden") is None
            # HA selector elements can keep their input inside a shadow root.
            # A level/filter refresh must preserve that focused source editor.
            shadow = page.evaluate(f"""()=>{{
              const saved=card.{prop},row=saved.node.querySelector('[data-room-options-group114="temperature"]');
              const host=document.createElement('div');row.append(host);
              const root=host.attachShadow({{mode:'open'}});root.innerHTML='<input aria-label="Fixture source editor">';
              const input=root.querySelector('input');input.focus();
              saved.settingsAudit.query='no matching setting';card._settingsAuditApplyB8(saved,'room');
              const result={{hidden:row.hidden,focused:root.activeElement===input}};
              input.blur();host.remove();saved.settingsAudit.query='';card._settingsAuditApplyB8(saved,'room');
              return result;
            }}""")
            assert shadow == {"hidden": False, "focused": True}
            page.evaluate(f"window.keptGain=card.{prop}.node.querySelector('[data-hem-full-value127=\"number.room_gain\"]');keptGain.focus()")
            page.evaluate(f"card._settingsAuditSetLevelB8(card.{prop},'basic')")
            expect(modal.locator('[data-hem-full-value127="number.room_gain"]')).to_be_focused()
            expect(modal.locator('[data-hem-full-row127="number.room_gain"]')).to_be_visible()
            page.evaluate(f"keptGain.blur();card._settingsAuditApplyB8(card.{prop},'room')")
            expect(modal.locator('[data-hem-full-row127="number.room_gain"]')).to_be_hidden()
            search = modal.locator("[data-settings-search-b8]")
            search.fill("Specialist comfort model")
            expect(modal.locator('[data-hem-full-row127="number.room_model"]')).to_be_hidden()
            expect(modal.locator("[data-settings-hidden-matches-b8]")).to_be_visible()
            level.select_option("expert")
            expect(modal.locator('[data-hem-full-row127="number.room_model"]')).to_be_visible()
            search.fill("")
            assert page.evaluate(f"keptGain===card.{prop}.node.querySelector('[data-hem-full-value127=\"number.room_gain\"]')")
            level.select_option("advanced")
            modal, prop = opened("home")
            expect(modal.locator("[data-settings-level-b8]")).to_have_value("advanced")
            check_levels("home", modal, tuple(f'[data-hem-home-field128="{key}"]' for key in (
                "weather_entities", "global_threshold_indoor_co2", "pollen_high_from")))
            modal, prop = opened("device")
            expect(modal.locator("[data-settings-level-b8]")).to_have_value("expert")
            check_levels("device", modal, ('[data-hem-full-row127="switch.device_pause"]',
                                           '[data-hem-full-row127="number.device_gain"]',
                                           '[data-hem-full-row127="number.device_model"]'))
            modal.locator("[data-settings-level-b8]").select_option("basic")
            for role in ("approve", "discard"):
                expect(modal.locator(f'[data-hem-full-row127="button.device_{role}"]')).to_be_visible()
            modal.locator("[data-settings-level-b8]").select_option("expert")
            assert page.evaluate("JSON.stringify({writes,optionWrites,homeData,committed})") == before
            key = page.evaluate(f"card._settingsAuditPreferenceKeyB8(card.{prop})")
            assert page.evaluate("key=>localStorage.getItem(key)", key) is not None
            page.close()
            # New page means a new script realm; this exercises persisted
            # storage, not just the current card's in-memory selection.
            page = boot()
            modal, prop = opened("room")
            expect(modal.locator("[data-settings-level-b8]")).to_have_value("expert")
            page.close()
            page = boot("bob")
            modal, prop = opened("home")
            expect(modal.locator("[data-settings-level-b8]")).to_have_value("basic")
            modal.locator("[data-settings-level-b8]").select_option("expert")
            page.evaluate("optionMode.fail=true")
            edited = modal.locator('[data-hem-home-input128="pollen_high_from"]')
            edited.fill("5");edited.dispatch_event("change")
            page.wait_for_function("card._homeSettingsDialog128.optionsAutosave.blocked===true")
            modal.locator("[data-settings-level-b8]").select_option("basic")
            expect(modal.locator('[data-hem-home-field128="pollen_high_from"]')).to_be_visible()
            expect(edited).to_have_value("5")
            writes = page.evaluate("optionWrites.length")
            modal.locator("[data-settings-level-b8]").select_option("expert")
            modal.locator("[data-settings-level-b8]").select_option("basic")
            assert page.evaluate("optionWrites.length") == writes, "Changing levels must not retry a failed save"
            assert page.evaluate("writes.length") == 0
            assert not errors, errors
            context.close()
        browser.close()
    print("PASS: all three levels across home/room/device; accessible EN/EL/DE menus at 320/390/760px; level-aware search; focus/stable controls; pending form errors; view-only behavior; per-user persisted preference")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-only", action="store_true")
    args = parser.parse_args()
    node_checks()
    if not args.node_only:
        browser_checks()
