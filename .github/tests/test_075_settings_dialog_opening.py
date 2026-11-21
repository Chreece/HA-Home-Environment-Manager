"""Opening settings must never paint a provisional, resizing menu.

Use the complete production card and existing Options/autosave fixtures. Only
the HA transports are delayed; screenshots/geometry and visible controls are
observed at browser paint boundaries. Node also exercises the production
registry loader and reveal helper without requiring a browser or HA install.
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
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"


NODE = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map(),timers=new Map();let timerId=0;
class Element {
 constructor(){this.attrs=new Map();this.children=[];this.isConnected=true;
  this.classList={values:new Set(),add:(...names)=>names.forEach(n=>this.classList.values.add(n))};}
 setAttribute(k,v){this.attrs.set(k,String(v));}
 removeAttribute(k){this.attrs.delete(k);}
 hasAttribute(k){return this.attrs.has(k);}
 prepend(child){child.parent=this;this.children.unshift(child);}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
 querySelector(selector){
  if(selector==='.hem-room-options-body114')return this.body;
  if(selector==='[data-settings-loading075]')return this.body?.children.find(c=>c.hasAttribute('data-settings-loading075'));
  return null;
 }
}
const context={console,Promise,HTMLElement:class {},window:{customCards:[]},
 document:{createElement:()=>new Element()},
 setTimeout:(fn,ms)=>{const id=++timerId;timers.set(id,{fn,ms});return id;},
 clearTimeout:id=>timers.delete(id),customElements:{
  get:name=>elements.get(name),define:(name,ctor)=>elements.set(name,ctor)}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const Ctor=elements.get('home-environment-manager-card');assert(Ctor);
const flush=async()=>{for(let n=0;n<8;n++)await Promise.resolve();};
function fixture(scope='room'){
 const card=Object.create(Ctor.prototype),node=new Element();node.body=new Element();
 const saved={node,owner:'sensor.hem',connection:{},busy:true},requests=[],renders=[];
 let current=saved;
 card._language=()=> 'en';card._hass={connection:saved.connection,
  callWS(request){assert.equal(this,card._hass);return new Promise((resolve,reject)=>requests.push({request,resolve,reject}));}};
 card._settingsOpenActive075=s=>s===current&&s.connection===card._hass.connection&&!s.disposed;
 card._hemFullContext127=card._settingsOpenActive075;
 card._hemFullRender127=s=>renders.push({saved:s,opening:s.initialOpening075,
  masked:s.node.hasAttribute('data-settings-opening075')});
 card._settingsAttachSourcesB10=()=>{};
 card._settingsBeginOpen075(saved,scope);
 assert(node.classList.values.has('hem-settings-stable075'));
 assert(node.hasAttribute('data-settings-opening075'));
 assert.equal(node.body.children.length,1);
 assert(node.body.children[0].textContent.trim());
 return {card,saved,requests,renders,replace:()=>{current={node:new Element()};return current;}};
}
(async()=>{
 for(const scope of ['room','home']){
  // Re-entrant initial refreshes share one request, with no provisional render.
  let f=fixture(scope),p=f.card._hemFullLoad127(f.saved,scope);
  assert(p&&typeof p.then==='function','Opening must be able to await the registry');
  const same=f.card._hemFullLoad127(f.saved,scope);await flush();
  assert.equal(f.requests.length,1);assert.equal(f.renders.length,0);
  assert.equal(f.requests[0].request.type,'config/entity_registry/list');
  f.requests[0].resolve([{entity_id:'number.actual'}]);await Promise.all([p,same]);
  assert.equal(f.saved.fullRegistry127[0].entity_id,'number.actual');
  assert.equal(f.saved.fullLoading127,false);assert.equal(f.saved.fullError127,false);
  assert.equal(f.renders.length,0,'Registry alone cannot reveal the form');
  f.saved.busy=false;f.card._settingsFinishOpen075(f.saved,scope);
  assert.equal(f.renders.length,1);
  assert.equal(f.renders[0].opening,false);
  assert.equal(f.renders[0].masked,true,'Final grouping/filtering must precede reveal');
  assert(!f.saved.node.hasAttribute('data-settings-opening075'));
  assert.equal(f.saved.node.body.children.length,0);
  f.card._settingsFinishOpen075(f.saved,scope);assert.equal(f.renders.length,1);
  assert.equal(timers.size,0,'A completed request must release its deadline');

  // Rejection and malformed responses terminate loading without showing partial UI.
  for(const malformed of [false,true]){
   f=fixture(scope);p=f.card._hemFullLoad127(f.saved,scope);await flush();
   if(malformed)f.requests[0].resolve({unexpected:true});else f.requests[0].reject(Error('offline'));
   await p;assert.equal(f.saved.fullLoading127,false);assert.equal(f.saved.fullError127,true);
   assert.equal(f.renders.length,0);assert.equal(timers.size,0);
  }
  f=fixture(scope);p=f.card._hemFullLoad127(f.saved,scope);await flush();
  const deadline=[...timers.values()].find(t=>t.ms>0&&t.ms<=10000);
  assert(deadline,'A stalled registry must have a bounded deadline');deadline.fn();await p;
  assert.equal(f.saved.fullLoading127,false);assert.equal(f.saved.fullError127,true);
  f.requests[0].resolve([{entity_id:'number.too_late'}]);await flush();
  assert.equal(f.saved.fullRegistry127,undefined,'A late response cannot overwrite timeout fallback');
  assert.equal(f.saved.fullError127,true);assert.equal(f.renders.length,0);assert.equal(timers.size,0);

  // A response from a closed/replaced dialog must not populate the replacement.
  f=fixture(scope);p=f.card._hemFullLoad127(f.saved,scope);await flush();
  const replacement=f.replace();f.requests[0].resolve([{entity_id:'number.stale'}]);await p;
  assert.equal(replacement.fullRegistry127,undefined);assert.equal(f.saved.fullRegistry127,undefined);
  assert.equal(f.renders.length,0);f.card._settingsFinishOpen075(f.saved,scope);
  assert.equal(f.renders.length,0);assert.equal(timers.size,0);

  // A genuine Options error reveals its existing retry UI without rendering settings.
  f=fixture(scope);f.saved.failed=true;f.saved.busy=false;
  f.card._settingsFinishOpen075(f.saved,scope);
  assert.equal(f.renders.length,0);assert(!f.saved.node.hasAttribute('data-settings-opening075'));
 }
 console.log('SETTINGS_OPENING_REQUEST_ORDER_REVEAL_FAILURE_TIMEOUT_AND_STALE_OWNERSHIP=PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


DELAYED_TRANSPORT = r"""language=>{
  card._hass.language=language;card._hass.user={id:'opening-test',is_admin:true};
  const add=(id,key,device)=>{
    card._hass.states[id]={state:'12',attributes:{min:0,max:100,step:1,
      friendly_name:key,configuration_help:'Detailed setting explanation.'}};
    registry.push({entity_id:id,translation_key:key,device_id:device,
      unique_id:'entry0_'+(device==='homehub'?'home_':'area_room0_')+key,
      platform:'environment_manager',config_entry_id:'entry0'});
  };
  add('number.opening_home_alias','global_occupancy_away_cooldown_minutes','homehub');
  add('number.opening_home_gain','equipment_kp','homehub');
  add('number.opening_room_gain','equipment_kp','living-device');
  window.delayed075={registry:[],options:[],create:[],holdCreate:false};
  const hold=(kind,result)=>{
    const settled=Promise.resolve(result).then(value=>({value}),error=>({error}));
    return new Promise((resolve,reject)=>{
      const item={done:false,release:async(fail=false)=>{
        if(item.done)return;item.done=true;
        const response=await settled;
        if(fail||response.error)reject(response.error||Error('Fixture request failed'));
        else resolve(response.value);
      }};
      delayed075[kind].push(item);
    });
  };
  const api=card._hass.callApi,ws=card._hass.callWS;
  card._hass.callApi=(method,path,data)=>{
    const result=api(method,path,data);
    if(method==='POST'&&path==='config/config_entries/options/flow'&&delayed075.holdCreate)
      return hold('create',result);
    return method==='POST'&&data?.next_step_id?hold('options',result):result;
  };
  card._hass.callWS=request=>request.type==='config/entity_registry/list'
    ?hold('registry',ws(request)):ws(request);
  card._renderContent(true);
  window.visible075=node=>{
    if(!node||!node.getClientRects().length)return false;
    for(let parent=node;parent;parent=parent.parentElement){
      const style=getComputedStyle(parent);
      if(style.display==='none'||style.visibility==='hidden')return false;
    }
    const rect=node.getBoundingClientRect();return rect.width>0&&rect.height>0;
  };
  window.frames075=[];window.shown075=[];window.capture075=true;
  window.sample075=node=>{
    const rect=node.getBoundingClientRect(),body=node.querySelector('.hem-room-options-body114');
    const children=[...body.children].filter(n=>!n.hasAttribute('data-settings-loading075'));
    return {opening:node.hasAttribute('data-settings-opening075'),
      rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},
      loading:[...node.querySelectorAll('[data-settings-loading075]')].filter(visible075).length,
      categories:[...node.querySelectorAll('[data-hem-unified141]>summary')].filter(visible075).length,
      counters:[...node.querySelectorAll('[data-settings-count-b8]')].filter(visible075).length,
      provisional:children.filter(visible075).length,
      header:visible075(node.querySelector('header')),
      close:visible075(node.querySelector('header button'))};
  };
  const original=HTMLDialogElement.prototype.showModal;
  HTMLDialogElement.prototype.showModal=function(){
    if(this.matches('.hem-room-options114'))shown075.push({
      masked:this.hasAttribute('data-settings-opening075'),
      loaders:this.querySelectorAll('[data-settings-loading075]').length});
    return original.call(this);
  };
  const capture=()=>{
    if(!capture075)return;
    const node=card._homeSettingsDialog128?.node||card._roomSettingsDialog114?.node;
    if(node?.isConnected&&node.open)frames075.push(sample075(node));
    requestAnimationFrame(capture);
  };
  requestAnimationFrame(capture);
}"""


def literal_setup(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "SETUP"
                        for target in node.targets))


def paint(page, count=3):
    page.evaluate("""count=>new Promise(resolve=>{
      const frame=()=>--count<=0?resolve():requestAnimationFrame(frame);
      requestAnimationFrame(frame);
    })""", count)


def browser_checks():
    from playwright.sync_api import expect, sync_playwright

    chrome = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
    assert chrome, "Chromium is required for visible settings opening checks"
    room = runpy.run_path(str(ROOT / ".github/tests/test_beta114_room_settings.py"))
    base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_setpoint_feedback_browser.py"))
    autosave = literal_setup(ROOT / ".github/tests/test_062b7_autosave.py")
    states = deepcopy(base["fixture_definitions"]()["states"])
    states["sensor.hem"]["attributes"]["dashboard"]["rooms"] = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][:2]
    properties = {"room": "_roomSettingsDialog114", "home": "_homeSettingsDialog128"}
    expressions = {"room": "card._openRoomSettings114('room0')", "home": "card._openHomeSettings128()"}
    body = ('<style>body{margin:0;background:#161616;color:#eee;font:14px Arial;'
            '--card-background-color:#222;--secondary-background-color:#292929;'
            '--primary-text-color:#eee;--secondary-text-color:#aaa;--divider-color:#555}</style>')

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True,
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])

        def boot(language="en", width=390, height=844):
            context = browser.new_context(viewport={"width": width, "height": height})
            context.route("https://hem-dialog-opening.test/**", lambda route: route.fulfill(
                status=200, content_type="text/html", body=body))
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("https://hem-dialog-opening.test/settings")
            page.evaluate(base["icon_fixture"]())
            page.add_script_tag(path=str(CARD))
            page.evaluate(room["SETUP"], {"states": states, "form": room["FORM"], "native": False})
            page.evaluate("form=>window.roomSchema=form", room["FORM"])
            page.evaluate(autosave)
            page.evaluate(DELAYED_TRANSPORT, language)
            return context, page, errors

        def modal(page, scope):
            selector = "dialog.hem-home-options128" if scope == "home" else "dialog.hem-room-options114:not(.hem-home-options128)"
            return page.locator(selector)

        def start(page, scope, index=0):
            page.evaluate("()=>{window.openingPromise075=" + expressions[scope] + ";}")
            page.wait_for_function("index=>delayed075.registry.length>index&&delayed075.options.length>index", arg=index)
            paint(page)
            return modal(page, scope)

        def release(page, kind, index=0, fail=False):
            page.evaluate("([kind,index,fail])=>delayed075[kind][index].release(fail)", [kind, index, fail])
            paint(page)

        def no_writes(page):
            assert page.evaluate("writes.length+optionWrites.length") == 0
            assert page.evaluate("calls.filter(c=>c.method==='POST'&&!c.data?.handler&&!c.data?.next_step_id).length") == 0

        def loading(page, dialog):
            expect(dialog).to_have_attribute("data-settings-opening075", "")
            sample = dialog.evaluate("sample075")
            assert sample["loading"] == 1, sample
            assert sample["categories"] == sample["counters"] == sample["provisional"] == 0, sample
            assert sample["header"] and sample["close"], sample
            no_writes(page)

        def ready(page, dialog):
            expect(dialog).not_to_have_attribute("data-settings-opening075", "")
            expect(dialog.locator("[data-settings-loading075]")).to_have_count(0)
            paint(page)
            assert page.evaluate("shown075.every(s=>s.masked&&s.loaders===1)")
            no_writes(page)

        def geometry(page, height):
            frames = page.evaluate("frames075")
            assert any(frame["opening"] for frame in frames), frames
            assert any(not frame["opening"] for frame in frames), frames
            initial = frames[0]["rect"]
            assert abs(initial["height"] - min(700, height - 24)) <= 2, initial
            for frame in frames:
                assert frame["header"] and frame["close"], frame
                assert all(abs(frame["rect"][key] - initial[key]) <= 1 for key in initial), (initial, frame)
                if frame["opening"]:
                    assert frame["loading"] == 1 and frame["provisional"] == frame["categories"] == frame["counters"] == 0, frame

        # All languages, desktop/mobile and response orderings reach one final menu.
        for language in ("en", "el", "de"):
            for width, height in ((1264, 800), (320, 700)):
                for scope in ("room", "home"):
                    for first in ("registry", "options"):
                        context, page, errors = boot(language, width, height)
                        dialog = start(page, scope)
                        loading(page, dialog)
                        release(page, first)
                        page.evaluate("card._renderContent(true)")
                        paint(page)
                        loading(page, dialog)
                        release(page, "options" if first == "registry" else "registry")
                        ready(page, dialog)
                        expect(dialog.locator("[data-settings-level-b8]")).to_have_value("basic")
                        expect(dialog.locator("[data-settings-tools-b8] .hem-settings-source-actions-b15")).to_have_count(1)
                        expect(dialog.locator(":scope > .hem-settings-source-actions-b15")).to_have_count(0)
                        expect(dialog.locator('[data-hem-full-row127="number.opening_' + scope + '_gain"]')).to_be_hidden()
                        if scope == "home":
                            expect(dialog.locator("[data-hem-home-field128]")).to_have_count(4)
                            expect(dialog.locator('[data-hem-full-row127="number.opening_home_alias"]')).to_have_count(0)
                        else:
                            expect(dialog.locator("[data-room-options-group114]")).to_have_count(7)
                        geometry(page, height)
                        # Live HA updates retain the completed search and disclosure DOM.
                        identity = "number.home_maximum" if scope == "home" else "number.maximum"
                        search = dialog.locator("[data-settings-search-b8]")
                        search.fill(identity)
                        row = dialog.locator(f'[data-hem-full-row127="{identity}"]')
                        expect(row).to_be_visible()
                        help_node = row.locator("details.hem-full-help127")
                        expect(help_node).to_have_count(1)
                        help_node.locator("summary").click()
                        assert help_node.evaluate("node=>node.open")
                        page.evaluate(f"window.savedRow075=card.{properties[scope]}.node.querySelector('[data-hem-full-row127=\"{identity}\"]');card._renderContent(true)")
                        expect(search).to_have_value(identity)
                        assert help_node.evaluate("node=>node.open")
                        assert row.evaluate("node=>node===savedRow075")
                        no_writes(page)
                        assert not errors, errors
                        context.close()

        for scope in ("room", "home"):
            # Registry failure leaves the valid source/options form usable.
            context, page, errors = boot()
            dialog = start(page, scope)
            release(page, "options")
            release(page, "registry", fail=True)
            ready(page, dialog)
            selector = "[data-hem-home-field128]" if scope == "home" else "[data-room-options-group114]"
            assert dialog.locator(selector).count() > 0
            expect(dialog.locator("[data-hem-unified-notice141][role=status]")).to_be_visible()
            geometry(page, 844)
            assert not errors, errors
            context.close()

            # A stalled registry settles at its deadline and cannot repaint later.
            context, page, errors = boot()
            page.clock.install()
            page.evaluate("()=>{window.openingPromise075=" + expressions[scope] + ";}")
            page.wait_for_function("delayed075.registry.length===1&&delayed075.options.length===1")
            page.evaluate("delayed075.options[0].release()")
            page.clock.run_for(10050)
            dialog = modal(page, scope)
            expect(dialog).not_to_have_attribute("data-settings-opening075", "")
            expect(dialog.locator("[data-hem-unified-notice141][role=status]")).to_be_visible()
            before = dialog.inner_html()
            page.evaluate("delayed075.registry[0].release()")
            page.clock.run_for(100)
            assert dialog.inner_html() == before, "A late response replaced timeout fallback"
            no_writes(page)
            assert not errors, errors
            context.close()

            # Error and Retry use fresh requests, and closing while busy stays possible.
            context, page, errors = boot()
            dialog = start(page, scope)
            release(page, "options", fail=True)
            ready(page, dialog)
            retry_selector = "[data-hem-home-retry128]" if scope == "home" else "[data-room-options-retry114]"
            expect(dialog.locator(retry_selector)).to_be_visible()
            dialog.locator(retry_selector).click()
            page.wait_for_function("delayed075.registry.length===2&&delayed075.options.length===2")
            paint(page)
            loading(page, dialog)
            release(page, "registry", index=0)
            loading(page, dialog)
            release(page, "registry", index=1)
            release(page, "options", index=1)
            ready(page, dialog)
            assert not errors, errors
            context.close()

            context, page, errors = boot()
            dialog = start(page, scope)
            page.evaluate(f"window.previousDialog075=card.{properties[scope]}.node")
            dialog.locator("header button").click()
            expect(dialog).to_have_count(0)
            dialog = start(page, scope, index=1)
            release(page, "registry", index=0)
            release(page, "options", index=0)
            loading(page, dialog)
            assert dialog.evaluate("node=>node!==previousDialog075")
            release(page, "options", index=1)
            release(page, "registry", index=1)
            ready(page, dialog)
            no_writes(page)
            assert not errors, errors
            context.close()

            # The initial menu can arrive after close, before the old dialog
            # knew its flow ID. Delete that old flow without touching the new one.
            context, page, errors = boot()
            page.evaluate("()=>{delayed075.holdCreate=true;window.openingPromise075=" + expressions[scope] + ";}")
            page.wait_for_function("delayed075.registry.length===1&&delayed075.create.length===1")
            paint(page)
            dialog = modal(page, scope)
            loading(page, dialog)
            dialog.locator("header button").click()
            expect(dialog).to_have_count(0)
            page.evaluate("()=>{delayed075.holdCreate=false;window.openingPromise075=" + expressions[scope] + ";}")
            page.wait_for_function("delayed075.registry.length===2&&delayed075.options.length===1")
            page.evaluate(f"window.replacementDialog075=card.{properties[scope]}.node")
            release(page, "create")
            page.wait_for_function("calls.some(c=>c.method==='DELETE'&&c.path==='config/config_entries/options/flow/fresh1')")
            release(page, "registry", index=0)
            loading(page, dialog)
            assert dialog.evaluate("node=>node===replacementDialog075")
            assert page.evaluate("optionFlows.has('fresh2')")
            release(page, "registry", index=1)
            release(page, "options")
            ready(page, dialog)
            no_writes(page)
            assert not errors, errors
            context.close()
        browser.close()
    print("SETTINGS_OPENING_PAINTS_GEOMETRY_EN_EL_DE_FAILURE_RETRY_TIMEOUT_AND_REOPEN=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-only", action="store_true")
    arguments = parser.parse_args()
    subprocess.run([shutil.which("node") or "node", "-e", NODE, str(CARD)], check=True)
    if not arguments.node_only:
        browser_checks()
