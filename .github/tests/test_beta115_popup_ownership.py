"""Run actual popup handlers against deterministic DOM boundary fixtures.

A details toggle is queued by the browser. Deliver the old disclosure's close
after the new popup has opened; it must not remove the new popup or misreport
a closed/hidden popup as an open room issue. No browser or appliance I/O.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"
SCRIPT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const registered=new Map(),toggleHandlers=[],folds=[],createdPopups=[];
const shadow={
  addEventListener(type,handler){if(type==='toggle')toggleHandlers.push(handler);},
  querySelectorAll(selector){return selector==='[data-room-fold87]'?folds:[];},
  appendChild(pop){pop.isConnected=true;},
};
function makePopup(){
  const listeners=new Map();
  const popup={isConnected:false,shown:false,removed:false,style:{},classList:{add(){}},
    setAttribute(){},
    addEventListener(type,handler){
      if(!listeners.has(type))listeners.set(type,[]);
      listeners.get(type).push(handler);
    },
    deliver(type,oldState,newState){
      for(const handler of listeners.get(type)||[])
        handler({target:this,type,oldState,newState});
    },
    matches(selector){return selector===':popover-open'&&this.shown;},
    // Native visibility and queued event delivery are controlled separately,
    // so tests can exercise the precise ordering that triggered the CI flake.
    showPopover(){this.shown=true;},hidePopover(){this.shown=false;},
    remove(){this.isConnected=false;this.removed=true;},focus(){},
  };
  createdPopups.push(popup);return popup;
}
// A real HTMLElement's ownerDocument is an EventTarget. Object.create below
// bypasses that native constructor, so provide the document explicitly.
const ownerDocument=Object.assign(new EventTarget(),{
  createElement:makePopup,documentElement:{clientWidth:500},
});
const context={HTMLElement:class{},window:{customCards:[],innerHeight:800},
  document:ownerDocument,
  customElements:{get:name=>registered.get(name),define:(name,ctor)=>registered.set(name,ctor)},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context,{filename:process.argv[1]});
const card=Object.create(registered.get('home-environment-manager-card').prototype);
Object.assign(card,{ownerDocument,shadowRoot:shadow,addEventListener(){}});
// Capture the production listeners, including the original information toggle
// handler through all later installation wrappers. Never reimplement it here.
card._installFolds87();
assert.ok(toggleHandlers.length>0);
function makeDetail(area,id){
  const fold={localName:'details',open:true,parentElement:null,
    getAttribute:name=>name==='data-room-fold87'?area:null,
    querySelector:()=>null,querySelectorAll:()=>[detail]};
  const detail={localName:'details',id,isConnected:true,open:true,parentElement:fold,
    getRootNode:()=>shadow,
    matches:selector=>selector==='details.hem-context76,details.metric-help',
    getAttribute:name=>name==='data-detail-id'?id:null,
    closest:()=>fold,
    querySelector:selector=>selector===':scope > summary'
      ?{getAttribute:()=>id,getBoundingClientRect:()=>({right:200,bottom:80,top:40})}
      :{innerHTML:'Content for '+id}};
  folds.push(fold);return detail;
}
const previous=makeDetail('room-a','device-info:A');
const current=makeDetail('room-b','device-info:B');
const view={kind:'controllers',infoKey:current.id};
const viewOpen=()=>card._roomIssueOpen115('room-b',view);
function deliverDetail(detail,oldState,newState){
  for(const handler of toggleHandlers)handler({target:detail,oldState,newState});
}
const deliverClose=detail=>deliverDetail(detail,'open','closed');
card._roomIssueInfo114=previous.id;
card._openInfo87(previous);
const oldPopup=card._floatingInfo87;
assert.equal(oldPopup._hemInfoSource87,previous);
// Closing A queues its toggle. Opening B is synchronous and may finish before
// A's notification runs (HTML details toggle tasks use the DOM task source).
previous.open=false;
card._roomIssueInfo114=current.id;
card._openInfo87(current);
const newPopup=card._floatingInfo87;
assert.notEqual(newPopup,oldPopup);
assert.equal(oldPopup.removed,true);
assert.equal(newPopup._hemInfoSource87,current);
assert.equal(viewOpen(),true);
deliverClose(previous);
oldPopup.deliver('beforetoggle','open','closed');
oldPopup.deliver('toggle','open','closed');
assert.equal(card._floatingInfo87,newPopup,'Old A close removed current B popup');
assert.equal(newPopup.removed,false);
assert.equal(newPopup.isConnected,true);
assert.equal(current.open,true);
assert.equal(card._roomIssueInfo114,current.id);
assert.equal(viewOpen(),true);

// Native light-dismiss/Escape hides the popup before its queued callback can
// update the details element. A hidden popup must immediately count as closed.
newPopup.hidePopover();
assert.equal(current.open,true);
assert.equal(viewOpen(),false,'Hidden popup was treated as visible controller information');
newPopup.showPopover();
assert.equal(viewOpen(),true);

// An unrelated popup must never make this room's controller view look open.
newPopup._hemInfoSource87=previous;
assert.equal(viewOpen(),false,'Wrong popup source satisfied this room controller view');
newPopup._hemInfoSource87=current;
newPopup.isConnected=false;
assert.equal(viewOpen(),false,'Detached popup was treated as open');
newPopup.isConnected=true;

// Opening settings removes the popup while leaving the disclosure's previous
// open property intact. The next warning press must be allowed to reopen it.
card._closeInfo87();
assert.equal(current.open,true);
assert.equal(card._floatingInfo87,null);
assert.equal(viewOpen(),false,'Removed popup left a stale open controller view');

card._openInfo87(current);
const reopened=card._floatingInfo87;
assert.equal(reopened._hemInfoSource87,current);
assert.equal(viewOpen(),true);
current.open=false;
deliverClose(current);
assert.equal(card._floatingInfo87,null,'B own close failed to remove B popup');
assert.equal(reopened.removed,true);
assert.equal(viewOpen(),false);
// Exact Escape race: the popup is open, but the disclosure's original
// OPEN notification has not yet run. Native beforetoggle(close) is synchronous;
// deliver that old disclosure notification before the popup's queued CLOSED
// notification. Neither notification may resurrect the dismissed popup.
current.open=true;
card._roomIssueInfo114=current.id;
card._detailsExpanded66=new Set([current.id]);
card._openInfo87(current);
const escaping=card._floatingInfo87;
const countBeforeEscape=createdPopups.length;
escaping.deliver('beforetoggle','open','closed');
const sourceClosedSynchronously=current.open===false;
escaping.hidePopover();
deliverDetail(current,'closed','open');
escaping.deliver('toggle','open','closed');
assert.equal(card._floatingInfo87,null,'Queued disclosure OPEN resurrected an escaped popup');
assert.equal(createdPopups.length,countBeforeEscape,'Escape created another popup');
assert.equal(sourceClosedSynchronously,true,'Source was not closed in native beforetoggle');
assert.equal(current.open,false);
assert.equal(card._detailsExpanded66.has(current.id),false);
assert.equal(viewOpen(),false);

// A genuine request can reopen after the dismissed view, with no stale popup
// left for the next warning activation to interpret as a request to close it.
current.open=true;
card._roomIssueInfo114=current.id;
card._openInfo87(current);
assert.equal(viewOpen(),true);
assert.equal(createdPopups.length,countBeforeEscape+1);
card._closeInfo87();

// A queued disclosure OPEN arriving while room settings is displayed must
// not create another top-layer popup or steal the dialog's focus.
card._roomSettingsDialog114={node:{isConnected:true},disposed:false};
const countBeforeSettings=createdPopups.length;
card._openInfo87(current);
deliverDetail(current,'closed','open');
assert.equal(card._floatingInfo87,null,'Information popup opened over room settings');
assert.equal(createdPopups.length,countBeforeSettings);
card._roomSettingsDialog114=null;

// Keep the asynchronous popup-close fallback for environments/events where
// beforetoggle was not observed. This still closes only the current source.
card._openInfo87(current);
const fallback=card._floatingInfo87;
fallback.hidePopover();
fallback.deliver('toggle','open','closed');
assert.equal(current.open,false);
assert.equal(card._floatingInfo87,null);
assert.equal(fallback.removed,true);
assert.equal(viewOpen(),false);
console.log('BETA115_POPUP_OWNERSHIP_QUEUED_CLOSE_AND_VISIBLE_CONTROLLER_STATE=PASS');
console.log('BETA115_POPUP_ESCAPE_OPEN_EVENT_RACE_AND_SETTINGS_GUARD=PASS');
"""


if __name__ == "__main__":
    subprocess.run(["node", "-e", SCRIPT, str(CARD)], check=True)
