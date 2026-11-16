"""v0.7.1: room-data classification, read-only card disclosures and startup task."""
from __future__ import annotations

import ast
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"custom_components/environment_manager"
tree=ast.parse((SRC/"dashboard.py").read_text(encoding="utf-8"))
wanted={"_reading","_room"}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
assert {node.name for node in nodes}==wanted
scope={"math":math,"Any":Any,"UNIT_LABEL":{"humidity":"%","temperature":"°C","co2":"ppm"},
       "_reason":lambda x: {}, "_window":lambda x:{"entity_id":x.entity_id,"opened":x.opened}}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"dashboard.py","exec",
             flags=__import__("__future__").annotations.compiler_flag),scope)
snapshot_room=scope["_room"]

def reading(metric,value,entity=None):
    return NS(entity_id=entity or "sensor."+metric,name=metric.capitalize(),
              metric=metric,value=value,details={})

def check(readings,env=None,windows=(),limits=None,climate_only=False):
    area="room1"
    room=NS(area_id=area,name="Room",readings=tuple(readings),windows=tuple(windows))
    plan=NS(environment={area:env or {}},recommendations=(),
            climate_recommendations=(),outdoor_safe=True)
    return snapshot_room(room,plan,limits or {},climate_only=climate_only)

a=check([reading("temperature",22),reading("humidity",None),reading("co2",None)])
assert a["status"]=="safe",a
assert a["core_measurements"]=={"temperature":True,"humidity":False},a
assert {x["metric"] for x in a["missing_measurements"]}=={"humidity","co2"}
assert not a["window_data_incomplete"],"Unconfigured windows are optional"
assert a["status_detail"]=="partial_indoor_data"

b=check([reading("humidity",45),reading("mold",None)])
assert b["status"]=="safe" and b["core_measurements"]["humidity"]

c=check([reading("temperature",None),reading("humidity",None),reading("co2",500)])
assert c["status"]=="unknown",c
assert c["status_detail"]=="no_core_room_data"

d=check([reading("co2",1600)],limits={"indoor_co2":1000})
assert d["status"]=="attention","A verified pollutant hazard must override missing core data"

e=check([],env={"climate_plan":{"temperature_c":21.5}})
assert e["status"]=="safe" and e["core_measurements"]["temperature"]

f=check([reading("humidity",44)],windows=[
    NS(entity_id="binary_sensor.window",name="Window",opened=None)])
assert f["status"]=="safe" and f["window_data_incomplete"]

fault=(SRC/"device_faults.py").read_text(encoding="utf-8")
assert "self.manager.entry.async_create_background_task(" in fault
assert "self._announce_offline_after_delay(key)," in fault
assert "OFFLINE_NOTICE_DELAY_SECONDS = 180" in fault

js_test=r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(process.argv[1],'utf8');
new Function(source);
const registered=new Map();
class Element {attachShadow(){this.shadowRoot={addEventListener(){}};return this.shadowRoot;}}
const context={
  HTMLElement:Element,
  customElements:{get:name=>registered.get(name),define:(name,type)=>registered.set(name,type)},
  window:{},console
};
vm.runInNewContext(source,context,{filename:'card.js'});
const Card=registered.get('home-environment-manager-card');
assert.ok(Card);
const card=Object.create(Card.prototype);
card._language=()=> 'en';
card._t=k=>k;
card._l65=k=>k;
card._icon=id=>'<i>'+id+'</i>';
card._format=v=>String(v);
card._nativeAllowed105=()=>true;
card._info76=()=>'<details class="hem-door-info"></details>';
card._foldSections105=new Set();
card._hass={states:{
  'binary_sensor.window':{state:'on',attributes:{friendly_name:'Balcony window'}},
  'binary_sensor.door':{state:'off',attributes:{friendly_name:'Kitchen door'}},
  'cover.test':{state:'open',attributes:{friendly_name:'Rollo'}}
}};
card._doorContext063=()=>'<details class="hem-door-info"></details>';
const room={area_id:'kitchen',windows:[{entity_id:'binary_sensor.window',name:'Balcony window',opened:true}],
  environment:{door_context:{contacts:[{entity_id:'binary_sensor.door',state:'closed',health:'ok'}]}}};
let markup=card._windowsDoors071(room);
assert.ok(markup.includes('Windows &amp; doors'));
assert.ok(markup.includes('Balcony window')&&markup.includes('Kitchen door'));
assert.ok(markup.includes('mdi:window-open-variant')&&markup.includes('mdi:door-closed'));
assert.ok(!markup.includes('<small>·'),'Contact states must be icons, not visible text');
assert.equal((markup.match(/hem-door-contact071/g)||[]).length,1);

markup=card._roomDataInfo071({missing_measurements:[
  {metric:'humidity',name:'Humidity'},{metric:'co2',name:'CO₂'}],
  window_data_incomplete:false},null);
assert.ok(markup.includes('hem-room-missing071')&&markup.includes('Humidity')&&markup.includes('CO₂'));
assert.ok(markup.includes('<details'));

const science={area_id:'kitchen',environment:{moisture:{
  status:'drying',drying_potential_g_kg:1.2}}};
markup=card._environmentReport(science);
assert.ok(markup.includes('hem-science-help071'),'Building physics help must expand inline');
assert.ok(!markup.includes('class="metric-help"'),'Floating popovers are not used in physics');
card._shadingEvidence=room=>room.environment.shade_cooling;
card._shadingSwitch=()=>null;
card._controllerStatusLabel=value=>value;
const shades={area_id:'kitchen',environment:{shade_cooling:{
  selected_covers:['cover.test'],close_reason:'closing_recommended',
  status:'closing_recommended',covers:{'cover.test':'closing_recommended'}}}};
markup=card._shadePanel(shades);
assert.ok(markup.includes('hem-cover-close071'),'Collapsed covers must show a close-needed icon');
assert.ok(markup.includes('hem-cover-source071')&&markup.includes('Rollo'));
assert.ok(markup.includes('hem-cover-help071'),'Instructions must start behind the info button');
assert.ok(!markup.includes('<small>Closes in sunny weather'),'Long help must not always display');
shades.environment.shade_cooling.close_reason='sun_below_threshold';
shades.environment.shade_cooling.status='idle';
markup=card._shadePanel(shades);
assert.ok(!markup.includes('hem-cover-close071'),'No false close-needed indication');

assert.ok(card._arrivalHelp125().purpose.includes('all devices will get into Home mode'));
assert.equal(card._arrivalWords124().duration,'Max time for the arrival preparation');
console.log('PASS 0.7.1 card: merged contacts, state icons, inline disclosures, cover urgency and arrival labels');
"""
subprocess.run(["node","-e",js_test,str(SRC/"frontend/air-quality-advisor-card.js")],
               check=True,timeout=45)
print("PASS 0.7.1 dashboard: temp OR RH drives No-data; optional gaps shown; verified hazards protected")
