"""Quiet settings use one editor per operating mode in the full device dialog.

Node executes the production registry/filter function against controlled HA
snapshots. Optional Chromium checks the complete card, rendered controls and
their service target. No Home Assistant installation or hardware is contacted.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"

NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const {test}=require('node:test');
const source=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  const pidActionsB18=');
const helpers=source.slice(start,source.indexOf('  const tr127=',start));
const body=source.match(/hemFull127\._hemFullFields127=function\(saved,scope\)\{[\s\S]*?\n  \};/);
assert.ok(start>=0&&body,'Production settings function must be present');
const prototype={};
new Function('hemFull127','DOMAINS127','HEM_PID_ACTIONS_B18','hemMetadataB8',helpers+'\n'+body[0])(
  prototype,new Set(['number','select','switch','button','time']),{en:{}},()=>null);

function fixture(modes=['dry'],fan='discrete'){
  const owner='entry0_area_living_controller_a',device='hem-controller-device';
  const states={},entities={},legacy=[],scoped=[];
  const quiet=fan===null?[]:[['quiet_sleep','switch'],['quiet_occupied','switch'],
    fan==='percentage'?['quiet_percentage','number']:['quiet_fan_mode','select']];
  function add(key,domain,mode=null,options={}){
    const id=options.id||domain+'.'+(mode||'legacy')+'_'+key;
    const identity=options.owner||owner;
    entities[id]={entity_id:id,unique_id:identity+(mode?'_mode_'+mode:'')+'_'+key,
      device_id:device,config_entry_id:'entry0',platform:'environment_manager',
      translation_key:'equipment_'+key,...options.registry};
    states[id]={state:options.state??(domain==='switch'?'off':domain==='select'?'low':'30'),
      attributes:{controller_id:identity,area_id:'living',source_entity_ids:['climate.native'],
        friendly_name:'User supplied name',
        ...(mode?{settings_scope:'operating_mode',operating_mode:mode,setting_key:key}:{}),
        ...options.attributes}};
    return id;
  }
  for(const [key,domain] of quiet){
    legacy.push(add(key,domain));
    for(const mode of modes)scoped.push(add(key,domain,mode));
  }
  const saved={entryId:'entry0',area:'living',device,
    controller:{climate:{attributes:{controller_id:owner}}}};
  const card={...prototype,_hass:{entities,states},_language:()=> 'en',
    _hemFullContext127:()=>true,_hemFullCategory127:()=> 'mode',
    _hemSettingLabel062:(_id,state,reg)=>reg.name_by_user||state?.attributes?.friendly_name||'Offline'};
  const ids=(scope='device')=>card._hemFullFields127(saved,scope).map(field=>field.id);
  return {owner,device,states,entities,saved,card,add,ids,legacy,scoped};
}

const devices=[
  ['dry-only climate',['dry'],'discrete'],
  ['heating climate with fan',['heat'],'discrete'],
  ['cooling climate with fan',['cool'],'discrete'],
  ['multimode climate',['heat','cool','dry','fan_only','auto','heat_cool'],'discrete'],
  ['native humidifier with accessory fan',['humidify'],'percentage'],
  ['native dehumidifier with accessory fan',['dry'],'percentage'],
  ['percentage fan, purifier or extractor',['fan_only'],'percentage'],
  ['preset fan, purifier or extractor',['fan_only'],'discrete'],
  ['fanless thermostat or heat actuator',['heat'],null],
];
for(const [name,modes,fan] of devices)test(name+': only named-mode quiet editors remain',()=>{
  const f=fixture(modes,fan),before=JSON.stringify([f.entities,f.states]);
  const ids=f.ids();
  for(const id of f.legacy)assert.ok(!ids.includes(id),'Duplicate legacy quiet editor: '+id);
  for(const id of f.scoped)assert.ok(ids.includes(id),'Lost independent mode editor: '+id);
  assert.equal(ids.length,f.scoped.length);
  assert.equal(JSON.stringify([f.entities,f.states]),before,'Presentation must preserve HA entities');
});

test('all unavailable, unknown, disabled or missing replacements keep a usable legacy editor',()=>{
  for(const mutate of [
    f=>{for(const id of f.scoped)f.states[id].state='unavailable';},
    f=>{for(const id of f.scoped)f.states[id].state='unknown';},
    f=>{for(const id of f.scoped)f.entities[id].disabled_by='user';},
    f=>{for(const id of f.scoped)delete f.states[id];},
  ])for(const fan of ['discrete','percentage']){
    const f=fixture(['heat','cool'],fan);mutate(f);
    for(const id of f.legacy)assert.ok(f.ids().includes(id),'Lost live fallback: '+id);
  }
  const f=fixture(['heat','cool']);
  for(const id of f.scoped)if(id.includes('.heat_'))f.states[id].state='unavailable';
  assert.deepEqual(new Set(f.ids()),new Set(f.scoped),'One usable named mode supersedes the legacy alias');
});

test('unsaved, pending and failed legacy edits remain visible until saved',()=>{
  for(const phase of ['dirty','pending','saving','failed'])for(const fan of ['discrete','percentage']){
    const f=fixture(['dry'],fan);
    f.saved.nativeEdits=new Map(f.legacy.map(id=>[id,{phase,valid:true}]));
    for(const id of f.legacy)assert.ok(f.ids().includes(id),phase+' draft lost: '+id);
    for(const edit of f.saved.nativeEdits.values())edit.phase='saved';
    assert.deepEqual(new Set(f.ids()),new Set(f.scoped));
  }
});

test('a replacement requires exact metadata, registry identity and HA domain',()=>{
  const mutations=[
    (f,id)=>{delete f.states[id].attributes.setting_key;},
    (f,id)=>{delete f.states[id].attributes.operating_mode;},
    (f,id)=>{delete f.states[id].attributes.controller_id;},
    (f,id)=>{f.states[id].attributes.settings_scope='device';},
    (f,id)=>{f.states[id].attributes.setting_key='quiet_other';},
    (f,id)=>{f.entities[id].unique_id+='wrong';},
    (f,id)=>{f.entities[id].config_entry_id='another-entry';},
    (f,id)=>{f.entities[id].device_id='another-device';},
    (f,id)=>{f.entities[id].platform='another-integration';},
  ];
  for(const mutate of mutations){
    const f=fixture();
    for(const id of f.scoped)mutate(f,id);
    for(const id of f.legacy)assert.ok(f.ids().includes(id),'Unverified peer hid: '+id);
  }
  const f=fixture([],null),old=f.add('quiet_sleep','switch');
  f.add('quiet_sleep','select','dry');
  assert.ok(f.ids().includes(old),'A select cannot replace a switch');
});

test('another controller or endpoint on the same physical device cannot hide this controller',()=>{
  const f=fixture([],null),old=f.add('quiet_sleep','switch');
  const other=f.add('quiet_sleep','switch','dry',{owner:f.owner+'_channel_b'});
  assert.deepEqual(f.ids(),[old],'Other endpoint must not enter this controller dialog');
  delete f.saved.controller;
  assert.deepEqual(new Set(f.ids()),new Set([old,other]),'Owner is part of the replacement identity');
});

test('custom entity IDs and names do not change identity; incomplete legacy metadata is retained',()=>{
  const f=fixture([],null);
  const old=f.add('quiet_sleep','switch',null,{id:'switch.my_custom_switch',registry:{name_by_user:'Night'}});
  const scoped=f.add('quiet_sleep','switch','dry',{id:'switch.another_custom_switch',registry:{name_by_user:'Different'}});
  assert.deepEqual(f.ids(),[scoped]);
  delete f.states[old].attributes.controller_id;
  assert.ok(f.ids().includes(old),'Cannot hide an unidentified legacy control');
});

test('shared settings and independent mode settings remain available',()=>{
  const f=fixture(['heat','cool']);
  const shared=[['min_on_seconds','number'],['min_off_seconds','number'],
    ['fan_min_percentage','number'],['fan_max_percentage','number'],
    ['presence_requirement','select'],['sleep_behavior','select'],['announce_device_errors','switch']];
  const keep=shared.map(([key,domain])=>f.add(key,domain));
  for(const mode of ['heat','cool'])for(const key of ['preset','fan_mode','swing_mode'])
    keep.push(f.add(key,'select',mode));
  keep.push(f.add('target_home_heat','number','heat'),f.add('target_home_cool','number','cool'));
  for(const id of keep)assert.ok(f.ids().includes(id),'Unrelated control removed: '+id);
});

test('existing PID suppression, unknown-state actions and non-device scopes are unchanged',()=>{
  const f=fixture(['heat','cool']);
  for(const [key,domain,state] of [['kp','number','10'],['sample_seconds','number','300'],
    ['pid_calibration_method','select','manual'],['pid_apply_calibration','button','unknown']]){
    const old=f.add(key,domain,null,{state});
    const modes=['heat','cool'].map(mode=>f.add(key,domain,mode,{state}));
    assert.ok(!f.ids().includes(old));
    for(const id of modes)assert.ok(f.ids().includes(id));
  }
  for(const scope of ['home','room'])for(const id of f.legacy)assert.ok(f.ids(scope).includes(id));
});
"""


BROWSER_SETUP = r"""data=>{
  const {modes,fan,language}=data,states=data.fixture.states,owner='ctrl_a';
  const controller=data.fixture.controller,physical=data.fixture.physical;
  const registry=[];
  window.calls=[];
  window.card=document.createElement('home-environment-manager-card');
  document.body.append(card);card._config={entity:'sensor.hem'};
  states[controller].attributes.controller_id=owner;
  states[controller].attributes.supported_operating_modes=modes;
  states[controller].attributes.selected_operating_mode=modes[0];
  states[controller].attributes.hvac_modes=['off',...modes];
  states[controller].state=modes[0];
  const keys=[['quiet_sleep','switch'],['quiet_occupied','switch'],
    fan==='percentage'?['quiet_percentage','number']:['quiet_fan_mode','select']];
  for(const [key,domain] of keys)for(const mode of [null,...modes]){
    const id=domain+'.'+(mode||'legacy')+'_'+key;
    const attrs={controller_id:owner,area_id:'living',source_device_id:'physical-heater-device',
      source_entity_ids:[physical],friendly_name:key,configuration_help:'Quiet fan configuration',
      ...(mode?{settings_scope:'operating_mode',operating_mode:mode,setting_key:key,
        operating_mode_label:mode}:{}),
      ...(domain==='select'?{options:['low','high']}:domain==='number'?{min:1,max:100,step:1}:{}),
    };
    states[id]={state:domain==='switch'?'off':domain==='select'?'low':'30',attributes:attrs};
    registry.push({entity_id:id,device_id:'hem-controller-device',config_entry_id:'entry0',
      platform:'environment_manager',unique_id:owner+(mode?'_mode_'+mode:'')+'_'+key,
      translation_key:'equipment_'+key});
  }
  card._hass={language,states,user:{is_admin:true},entities:{
    'sensor.hem':{config_entry_id:'entry0'},
    [controller]:{device_id:'hem-controller-device',config_entry_id:'entry0'}},
    connection:{},localize:()=>undefined,
    callService:(...args)=>{calls.push(args);return Promise.resolve();},
    callWS:async request=>request.type==='config/entity_registry/list'?registry:
      Promise.reject(Error('Unexpected WebSocket request'))};
  card._renderContent(true);card._configEntryId114='entry0';card._configEntryOwner114='sensor.hem';
  card._areaDeviceIds=new Map([['living','room-hub']]);
}"""


def browser_checks():
    from playwright.sync_api import expect, sync_playwright

    chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for --with-browser"
    fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))["fixture"]
    icons = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))["icon_fixture"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        for language, width, modes, fan in (
            ("el", 390, ["dry"], "discrete"),
            ("en", 760, ["heat", "cool"], "discrete"),
            ("de", 320, ["fan_only"], "percentage"),
        ):
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content('<style>body{margin:0;background:#161616;color:#eee;'
                '--card-background-color:#222;--primary-text-color:#eee;--secondary-text-color:#aaa}</style>')
            page.evaluate(icons())
            page.add_script_tag(path=str(CARD))
            page.evaluate(BROWSER_SETUP, {"fixture": fixture(), "modes": modes,
                "fan": fan, "language": language})
            room = page.locator('[data-room-fold87="living"]')
            room.locator(":scope > summary").evaluate("node=>node.click()")
            room.locator('[data-device-fold87="climate.hem_heater"] [data-open-controller-device122]').click()
            modal = page.locator(".hem-controller-options126")
            expect(modal).to_be_visible()
            page.wait_for_function("length=>card._hemControllerDialog126?.fullRegistry127?.length===length",
                arg=3 * (len(modes) + 1))
            modal.locator('[data-settings-level-b8]').select_option("expert")
            group = modal.locator('[data-hem-full-category127="mode"]')
            group.evaluate("node=>node.open=true")
            keys = [("quiet_sleep", "switch"), ("quiet_occupied", "switch"),
                ("quiet_percentage", "number") if fan == "percentage" else ("quiet_fan_mode", "select")]
            for key, domain in keys:
                assert modal.locator(f'[data-hem-full-row127="{domain}.legacy_{key}"]').count() == 0
                for mode in modes:
                    row = modal.locator(f'[data-hem-full-row127="{domain}.{mode}_{key}"]')
                    expect(row).to_be_visible()
                    assert row.count() == 1
            assert modal.evaluate("node=>node.scrollWidth<=node.clientWidth+1")
            assert page.evaluate("calls.length") == 0
            target = f"switch.{modes[0]}_quiet_sleep"
            modal.locator(f'[data-hem-full-row127="{target}"] button[data-hem-full-apply127]').click()
            page.wait_for_function("calls.length===1")
            assert page.evaluate("calls[0]") == ["switch", "turn_on", {"entity_id": target}]
            assert not errors, errors
            page.close()
        browser.close()
    print("PASS: rendered quiet editors and exact scoped service targets in EL/EN/DE at 320/390/760px")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-browser", action="store_true")
    args = parser.parse_args()
    node = shutil.which("node")
    assert node, "Node.js is required"
    subprocess.run([node, "-", str(CARD)], input=NODE, text=True, check=True)
    if args.with_browser:
        browser_checks()


if __name__ == "__main__":
    main()
