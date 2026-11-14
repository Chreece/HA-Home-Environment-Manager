"""B14: a quiet Home Assistant frontend recovers failed dashboard WebSockets.

A temporary dashboard or device registry rejection must no longer require a
new physical sensor state, manual reload, or a duplicate card. Retries are
bounded, tied to the original authenticated owner/connection, and cleared
on disconnect. No Home Assistant service or hardware command is issued.
"""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"frontend/air-quality-advisor-card.js"
browser_path=shutil.which("chromium") or shutil.which("google-chrome")
assert browser_path, "Chromium is required for actual Lovelace regression"

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=browser_path,headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":425,"height":850})
    errors=[]
    page.on("pageerror",lambda exc: errors.append(str(exc)))
    page.set_content("<html><body></body></html>")
    page.add_script_tag(path=str(SCRIPT))
    page.evaluate("""() => {
      window.calls=[];
      window.attempts={dashboard:0,registry:0};
      window.entry={
        state:'idle',attributes:{dashboard_api:'environment_manager/dashboard',
                                 dashboard_revision:1}
      };
      const states={'sensor.hem_recommendation':entry};
      window.card=document.createElement('home-environment-manager-card');
      document.body.append(card);
      card.setConfig({entity:'sensor.hem_recommendation'});
      const devices=[
        {id:'other_home',model:'Home Environment Hub',
          identifiers:[['environment_manager','other_entry']]},
        {id:'hem_home',model:'Home Environment Hub',
          identifiers:[['environment_manager','hem_entry']]},
        {id:'hem_controller',model:'Managed Environment Controller',
          identifiers:[['environment_manager','hem_entry_controller_child']]},
        {id:'hem_room',model:'Area Environment Hub',
          identifiers:[['environment_manager','hem_entry_area_wohnzimmer']]}
      ];
      window.hass={
        language:'en',states,connection:{},
        localize:()=>undefined,
        callService:(...args)=>{calls.push(args);return Promise.resolve();},
        callWS:({type})=>{
          if(type==='environment_manager/dashboard'){
            attempts.dashboard+=1;
            if(attempts.dashboard===1)
              return Promise.reject(Error('temporary dashboard transport error'));
            return Promise.resolve({version:1,owner_entry_id:'hem_entry',
              summary:{safe:0,attention:0,unknown:0},
              rooms:[],outdoor:{status:'unknown',readings:[],warnings:[],weather:[]},
              controllers:[]});
          }
          if(type==='config/device_registry/list'){
            attempts.registry+=1;
            if(attempts.registry===1)
              return Promise.reject(Error('temporary device registry error'));
            return Promise.resolve(devices);
          }
          return Promise.reject(Error('unexpected request: '+type));
        },
      };
      card.hass=hass;
    }""")
    page.wait_for_function(
        "() => attempts.dashboard===1 && attempts.registry===1 && "
        "card._dashboardRetryHandle!==null && "
        "card._deviceRegistryRetryHandle!==null", timeout=6000)
    page.wait_for_function(
        "() => attempts.dashboard>=2 && attempts.registry>=2 && "
        "card._dashboardData?.version===1 && card._deviceRegistryLoaded",
        timeout=13000)
    status=page.evaluate("""() => ({
        attempts:{...attempts},
        loaded:card._dashboardData?.version,
        home:card._homeDeviceId,
        room:card._areaDeviceIds.get('wohnzimmer'),
        dashboardRetry:card._dashboardRetryHandle,
        deviceRetry:card._deviceRegistryRetryHandle,
        calls:calls.length,
    })""")
    assert status["loaded"]==1,status
    assert status["attempts"]["dashboard"]==2,status
    assert 2<=status["attempts"]["registry"]<=3,status
    assert status["home"]=="hem_home" and status["room"]=="hem_room",status
    assert status["dashboardRetry"] is None and status["deviceRetry"] is None
    assert status["calls"]==0
    assert page.locator("ha-card").count()==1

    # A new owner/connection invalidates a delayed retry from an old source.
    page.evaluate("""() => {
      const state={state:'idle',attributes:{
        dashboard_api:'environment_manager/dashboard',dashboard_revision:2}};
      const nextStates={...hass.states,'sensor.new_owner':state};
      const nextConnection={};
      window.oldDashboardCalls=0;
      window.newDashboardCalls=0;
      window.newHass={...hass,states:nextStates,connection:nextConnection,
        callWS:({type,entity_id})=>{
          if(type==='environment_manager/dashboard') {
            if(entity_id==='sensor.hem_recommendation'){
              oldDashboardCalls++;
              return Promise.reject(Error('old snapshot disconnected'));
            }
            if(entity_id==='sensor.new_owner'){
              newDashboardCalls++;
              return Promise.resolve({version:1,owner_entry_id:'new_entry',
                rooms:[],summary:{},outdoor:{}});
            }
          }
          if(type==='config/device_registry/list')
            return Promise.resolve([
              {id:'home2',identifiers:[['environment_manager','new_entry']]}
            ]);
          return Promise.reject(Error('unexpected request'));
        }
      };
      card.setConfig({entity:'sensor.new_owner'});
      card.hass=newHass;
    }""")
    page.wait_for_function("()=>newDashboardCalls===1 && card._dashboardEntity==='sensor.new_owner'",
                           timeout=6000)
    page.wait_for_timeout(2100)
    assert page.evaluate("oldDashboardCalls")==0, "Retired owner retried"
    assert page.evaluate("newDashboardCalls")==1, "New owner retried needlessly"

    page.evaluate("()=>card.remove()")
    assert page.evaluate("""()=>card._dashboardRetryHandle===null &&
                             card._deviceRegistryRetryHandle===null""")
    assert page.evaluate("calls.length")==0
    assert not errors,errors
    browser.close()
print("HEM_B14_WEBSOCKET_RETRY_OWNER_AND_DISCONNECT=PASS")
