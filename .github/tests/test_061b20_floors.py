"""HEM beta20: native HA floors, zero-floor parity, folding and safe settings.

All assertions operate against the actual packaged frontend. Chromium uses a
mocked Home Assistant connection; real devices and registries are untouched.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"

NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
global.HTMLElement=class {};
global.window={};
global.customElements={classes:new Map(),get(n){return this.classes.get(n)},
 define(n,C){this.classes.set(n,C)}};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Klass=customElements.get('home-environment-manager-card');
const card=Object.create(Klass.prototype);
card._hass={language:'en',user:{is_admin:true}};
card._language=()=>card._hass.language;
card._room=r=>'<article data-test-area="'+r.area_id+'">'+r.name+'</article>';
card._icon=i=>'<ha-icon icon="'+i+'"></ha-icon>';
const rooms=[
 {area_id:'living',name:'Living room',status:'safe'},
 {area_id:'kitchen',name:'Kitchen',status:'attention'},
 {area_id:'loft',name:'Loft',status:'unknown'}
];
const flat=rooms.map(r=>card._room(r)).join('');
assert.equal(card._floorRooms140(rooms),flat,'missing HA metadata must not add floor UI');
card._floorRegistry140={floors:[],membership:new Map(),areas:[]};
assert.equal(card._floorRooms140(rooms),flat,'zero HA floors must keep the EXACT flat UI');
assert.ok(!flat.includes('floor-fold140'));
card._floorRegistry140={
 floors:[{floor_id:'ground',name:'Ground & <unsafe>',icon:'mdi:home-floor-0',level:0},
         {floor_id:'top',name:'Upstairs',icon:null,level:1},
         {floor_id:'empty',name:'Empty floor',icon:null,level:null}],
 membership:new Map([['living','ground'],['kitchen','ground'],['loft',null]]),
 areas:[]
};
let html=card._floorRooms140(rooms);
assert.ok(html.includes('Ground &amp; &lt;unsafe&gt;'),html.slice(0,600));
assert.ok(!html.includes('<unsafe>'),'floor names must be HTML escaped');
assert.equal((html.match(/data-floor-fold140=/g)||[]).length,4,
  '3 native floors and an unassigned group');
for(const id of ['ground','top','empty','__hem_unassigned140__'])
 assert.ok(html.includes('data-floor-fold140="'+id+'"'));
for(const room of rooms)
 assert.equal((html.match(new RegExp('data-test-area="'+room.area_id+'"','g'))||[]).length,1,
  'one room must not appear on multiple floors');
assert.ok(html.includes('data-floor-settings140="ground"'));
assert.ok(html.includes('1 need attention'));
assert.ok(html.includes('No HEM rooms assigned'));
card._floorCollapsed140=new Set(['ground']);
html=card._floorRooms140(rooms);
assert.ok(html.includes('data-floor-fold140="ground" ><summary') ||
  html.includes('data-floor-fold140="ground"><summary'));
card._hass.user={is_admin:false};
assert.ok(!card._floorRooms140(rooms).includes('data-floor-settings140='),
  'non-admin can read floors but not edit them');
card._hass.user={is_admin:true};

(async()=>{
 const conn={};
 const handlers={};let subscriptions=0,unsubs=0,renders=0,requests=0;
 conn.subscribeEvents=async(callback,type)=>{handlers[type]=callback;subscriptions++;
   return ()=>{unsubs++;delete handlers[type];};};
 let floors=[{floor_id:'ground',name:'Ground',level:0,icon:'mdi:home-floor-0'}];
 let areas=[{area_id:'living',floor_id:'ground',name:'Living room'},
            {area_id:'kitchen',floor_id:null,name:'Kitchen'}];
 card._hass={language:'en',user:{is_admin:true},connection:conn,
   callWS:async req=>{requests++;if(req.type==='config/floor_registry/list')return floors;
     if(req.type==='config/area_registry/list')return areas;throw Error('Foreign WS call');}};
 card._floorConnection140=conn;card._floorRegistry140=null;
 card._renderContent=()=>{renders++;};card.isConnected=true;
 card._floorFetch140();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(card._floorRegistry140.floors.length,1);
 assert.equal(card._floorRegistry140.membership.get('kitchen'),null);
 assert.equal(renders,1);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(subscriptions,2);
 areas=areas.map(a=>a.area_id==='kitchen'?{...a,floor_id:'ground'}:a);
 handlers.area_registry_updated({data:{action:'update',area_id:'kitchen'}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(card._floorRegistry140.membership.get('kitchen'),'ground');
 assert.equal(renders,2);
 assert.equal(requests,4);
 card._floorCleanupSubscriptions140();
 assert.equal(unsubs,2,'native registry subscriptions must unsubscribe');
 console.log('HEM_B20_FLOOR_ZERO_GROUPING_ESCAPING_LIVE_REGISTRY=PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
"""

source = runpy.run_path(str(ROOT / ".github/tests/test_beta122_card_details.py"))
base = source["fixture"]()
room = base["room"]
kitchen = deepcopy(room)
kitchen.update(area_id="kitchen", name="Kitchen", status="safe", high_count=0)
loft = deepcopy(room)
loft.update(area_id="loft", name="Loft", status="unknown", high_count=0)
base["states"]["sensor.hem"]["attributes"]["dashboard"]["rooms"] = [
    room, kitchen, loft
]
base["states"]["sensor.hem"]["attributes"]["dashboard"]["summary"] = {
    "total": 3, "safe": 1, "attention": 1, "unknown": 1
}

check = subprocess.run(["node", "-e", NODE, str(CARD)], text=True,
                       capture_output=True)
assert check.returncode == 0, check.stderr + check.stdout
print(check.stdout.strip(), flush=True)
if "--logic-only" in sys.argv:
    raise SystemExit(0)

from playwright.sync_api import expect, sync_playwright

chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or \
    shutil.which("chromium") or shutil.which("google-chrome")
assert chrome, "Chromium required for floor UI regressions"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 390, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content("""<style>
    *{box-sizing:border-box} body{background:#181818;color:#eee;font:14px Arial;margin:0}
    :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
    --card-background-color:#222;--secondary-background-color:#303030;--divider-color:#444}
    </style>""")
    page.add_script_tag(path=str(CARD))
    page.evaluate("""states=>{
      window.calls=[];window.writes=[];window.floors140=[
        {floor_id:'ground',name:'Ground floor',icon:'mdi:home-floor-0',level:0},
        {floor_id:'upper',name:'Upper floor',icon:'mdi:home-floor-1',level:1}
      ];window.areas140=[
        {area_id:'living',name:'Living room',floor_id:'ground'},
        {area_id:'kitchen',name:'Kitchen',floor_id:'ground'},
        {area_id:'loft',name:'Loft',floor_id:null}
      ];window.events140={};
      const conn={subscribeEvents:async(callback,type)=>{
        events140[type]=callback;return ()=>{delete events140[type];};
      }};
      window.card=document.createElement('home-environment-manager-card');
      document.body.appendChild(card);
      card._config={entity:'sensor.hem'};
      card._hass={language:'en',states,user:{is_admin:true},connection:conn,
        entities:{'sensor.hem':{config_entry_id:'entry0'}},
        localize:()=>undefined,
        callWS:async req=>{
          if(req.type==='config/floor_registry/list')
            return structuredClone(floors140);
          if(req.type==='config/area_registry/list')
            return structuredClone(areas140);
          writes.push(req);
          if(req.type==='config/floor_registry/update'){
            const floor=floors140.find(f=>f.floor_id===req.floor_id);
            if(!floor)throw Error('Unknown floor');
            Object.assign(floor,Object.fromEntries(Object.entries(req)
              .filter(([k])=>!['type','floor_id'].includes(k))));
            return floor;
          }
          if(req.type==='config/area_registry/update'){
            const area=areas140.find(a=>a.area_id===req.area_id);
            if(!area)throw Error('Unknown room');
            area.floor_id=req.floor_id;
            return area;
          }
          throw Error('Unexpected '+req.type);
        },
        callService:(...args)=>{calls.push(args);throw Error('Physical service in floor UI');}};
      window.roomOpened140=[];
      card._openRoomSettings114=async id=>{roomOpened140.push(id);return true;};
      card._renderContent(true);
    }""", base["states"])
    page.wait_for_function("card._floorRegistry140?.floors.length===2")
    floor = page.locator('[data-floor-fold140="ground"]')
    upper = page.locator('[data-floor-fold140="upper"]')
    unassigned = page.locator('[data-floor-fold140="__hem_unassigned140__"]')
    expect(floor).to_have_count(1)
    expect(upper).to_have_count(1)
    expect(unassigned).to_have_count(1)
    assert floor.locator('[data-room-fold87]').count() == 2
    assert upper.locator('[data-room-fold87]').count() == 0
    assert unassigned.locator('[data-room-fold87="loft"]').count() == 1
    assert floor.locator('.hem-floor-main140 strong').inner_text() == "Ground floor"
    assert page.evaluate('calls') == []

    floor.locator(':scope > summary').click(position={"x": 30, "y": 12})
    expect(floor).not_to_have_attribute("open", "")
    page.evaluate("card._renderContent(true)")
    expect(floor).not_to_have_attribute("open", "")
    floor.locator(':scope > summary').click(position={"x": 30, "y": 12})
    expect(floor).to_have_attribute("open", "")
    floor.locator('[data-floor-settings140="ground"]').click()
    dialog = page.locator('dialog.hem-floor-dialog140')
    expect(dialog).to_be_visible()
    assert dialog.locator('[data-floor-name140]').input_value() == "Ground floor"
    dialog.locator('[data-floor-name140]').fill("Living level")
    dialog.locator('[data-floor-level140]').fill("-1")
    dialog.locator('[data-floor-icon140]').fill("mdi:home-floor-b")
    dialog.locator('[data-floor-area140="kitchen"]').uncheck()
    dialog.locator('[data-floor-area140="loft"]').check()
    dialog.locator('[data-floor-save140]').click()
    expect(dialog).to_have_count(0)
    page.wait_for_function("""()=>card._floorRegistry140?.floors[0]?.name==='Living level'&&
      card._floorRegistry140.membership.get('loft')==='ground'&&
      card._floorRegistry140.membership.get('kitchen')===null""")
    expect(page.locator('[data-floor-fold140="ground"] [data-room-fold87="loft"]')).to_have_count(1)
    expect(page.locator('[data-floor-fold140="__hem_unassigned140__"] [data-room-fold87="kitchen"]')).to_have_count(1)
    assert page.evaluate("writes.map(w=>w.type)") == [
        "config/floor_registry/update",
        "config/area_registry/update",
        "config/area_registry/update",
    ]
    assert page.evaluate("calls") == []

    page.locator('[data-floor-settings140="ground"]').click()
    dialog = page.locator('dialog.hem-floor-dialog140')
    dialog.locator('[data-floor-room-settings140="loft"]').click()
    expect(dialog).to_have_count(0)
    assert page.evaluate("roomOpened140") == ["loft"]

    # Live HA registry move re-groups without HEM room settings/actuator writes.
    page.evaluate("""()=>{
      areas140.find(a=>a.area_id==='kitchen').floor_id='upper';
      events140.area_registry_updated({data:{action:'update',area_id:'kitchen'}});
    }""")
    expect(page.locator('[data-floor-fold140="upper"] [data-room-fold87="kitchen"]')).to_have_count(1)
    # Home Assistant now has NO floors: not even an empty floor heading/gear.
    page.evaluate("""()=>{
      floors140=[];for(const area of areas140)area.floor_id=null;
      events140.floor_registry_updated({data:{action:'remove',floor_id:'ground'}});
    }""")
    page.wait_for_function("card._floorRegistry140?.floors.length===0")
    expect(page.locator('[data-floor-fold140]')).to_have_count(0)
    expect(page.locator('.rooms-list > [data-room-fold87]')).to_have_count(3)
    assert page.locator('.rooms-list').locator('[data-floor-settings140]').count() == 0
    # No fake commands were issued to devices during any floor transition.
    assert page.evaluate("calls") == []
    assert not errors, errors
    browser.close()
print("HEM_B20_CHROMIUM_FLOORS_FOLD_SETTINGS_ASSIGNMENTS_AND_ZERO_PARITY=PASS")
