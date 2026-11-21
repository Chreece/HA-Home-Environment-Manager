"""B6: every relevant measurement owns its native activity icon and bubble.

The full production card runs against local, immutable HA fixtures. Node checks
evidence precedence and all measurement mappings; Chromium additionally checks
actual icon colours, mobile visibility, read-only bubbles and native-only updates.
No Home Assistant service or physical device is contacted.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
BASELINE = ROOT / ".github/tests/test_beta112_room_activity.py"
spec = importlib.util.spec_from_file_location("beta112_activity_fixture", BASELINE)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def fixture():
    states = baseline.fixture()
    # Automatic purpose is resolved by the backend; native fan metadata or a
    # suggestive name cannot identify a purifier/extractor by themselves.
    states["select.purpose_purifier"]["state"] = "auto"
    states["climate.managed_purifier"]["attributes"]["resolved_fan_purpose"] = "filtration"
    rooms = states["sensor.hem"]["attributes"]["dashboard"]["rooms"]
    air = next(room for room in rooms if room["area_id"] == "air")
    for metric, value, unit in (
        ("pm1", 2.5, "µg/m³"), ("pm4", 8.5, "µg/m³"),
        ("pm10", 12., "µg/m³"), ("pollen", 3., ""), ("aqi", 21., ""),
        ("voc", 80., "µg/m³"), ("tvoc", 70., "µg/m³"), ("voc_parts", 25., "ppb"),
        ("voc_index", 65., ""), ("hcho", 5., "µg/m³"), ("formaldehyde", 6., "µg/m³"),
        ("radon", 30., "Bq/m³"), ("no2", 9., "ppb"), ("o3", 14., "ppb"),
        ("so2", 4., "ppb"), ("co", 2., "ppm"), ("mold", 55., "%"),
        ("pressure", 1012., "hPa"), ("illuminance", 120., "lx"), ("noise", 35., "dB"),
    ):
        entity = "sensor.air_" + metric
        states[entity] = {"state": str(value), "attributes": {
            "friendly_name": metric.upper(), "unit_of_measurement": unit}}
        air["readings"].append({"metric": metric, "value": value, "unit": unit,
            "available": True, "name": metric.upper(), "entity_id": entity})
    return states


NODE_CHECKS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
global.HTMLElement=class {};
global.customElements={classes:new Map(),get(name){return this.classes.get(name)},
  define(name,Class){this.classes.set(name,Class)}};
global.window={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const Card=customElements.get('home-environment-manager-card');
const make=()=>{
  const card=Object.create(Card.prototype);
  card._hass={language:'en',states:structuredClone(input.states),localize:()=>undefined,
    callService:()=>{throw Error('Read-only activity sent a service call')}};
  card._interactions66=true;card._detailsExpanded66=new Set();
  card._windowSwitchPending66=new Set();card._calibrationExpanded65=new Set();
  card._expanded=new Set(['air']);card._areaDeviceIds=new Map();card._config={entity:'sensor.hem'};
  return card;
};
const room=(c,area)=>c._hass.states['sensor.hem'].attributes.dashboard.rooms.find(r=>r.area_id===area);
const glance=(c,area)=>c._room(room(c,area)).split('</summary>')[0];
const tones=html=>[...html.matchAll(/class="[^"]*hem-room-metric107[^\"]*hem-activity-([a-z]+)[^\"]*"/g)].map(m=>m[1]);
const reading=(c,area,metric)=>room(c,area).readings.find(r=>r.metric===metric);
const tile=(c,area,metric)=>c._metric(reading(c,area,metric),false,area);
const tone=(html,wanted)=>assert.ok(new RegExp('\\bhem-activity-'+wanted+'\\b').test(html),
  'Expected '+wanted+' activity on '+html.slice(0,230));
const change=(c,id,patch)=>{
  const old=c._hass.states[id];
  c._hass={...c._hass,states:{...c._hass.states,[id]:{...old,...patch,
    attributes:patch.attributes?{...old.attributes,...patch.attributes}:old.attributes}}};
};
const title=html=>[...html.matchAll(/\btitle="([^"]*)"/g)].map(m=>m[1]).join(' ');
const withoutHelp=html=>html.replace(/<details class="metric-help">[\s\S]*?<\/details>/g,'');
const visibleText=html=>withoutHelp(html).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const cases=[];function test(name,run){cases.push({name,run});}

test('thermal actions colour only their relevant measurement with distinct evidence text',()=>{
  for(const [action,wanted,label] of [
    ['heating','heat','Heating'],['cooling','cool','Cooling'],
    ['preheating','preheat','Preheating'],['defrosting','defrost','Defrosting']]){
    const c=make();change(c,'climate.heater',{attributes:{hvac_action:action}});
    assert.deepEqual(tones(glance(c,'heat')),[wanted,'neutral','neutral','neutral']);
    for(const html of [glance(c,'heat'),tile(c,'heat','temperature')]){
      tone(html,wanted);assert.ok(title(html).includes(label),label);
      assert.ok(!visibleText(html).includes(label),'Activity became a visible row/label');
    }
    assert.ok(tile(c,'heat','temperature').includes('metric-help-content'));
    assert.ok(tile(c,'heat','temperature').includes(label));
  }
});
test('humidity actions include native humidifiers and drying climate endpoints',()=>{
  for(const [area,wanted,label] of [['humidify','humidify','Humidifying'],['dry','dry','Dehumidifying']]){
    const c=make();
    assert.deepEqual(tones(glance(c,area)),['neutral',wanted,'neutral','neutral']);
    tone(tile(c,area,'humidity'),wanted);assert.ok(title(tile(c,area,'humidity')).includes(label));
  }
  const c=make(),s=c._hass.states;
  s['climate.dryer']={state:'dry',attributes:{hvac_action:'drying'}};
  for(const id of ['climate.managed_dryer','select.method_dryer'])
    s[id].attributes.source_entity_ids=['climate.dryer'];
  s['climate.managed_dryer'].attributes.physical_primary_entity_id='climate.dryer';
  delete s['humidifier.dryer'];
  assert.deepEqual(tones(glance(c,'dry')),['neutral','dry','neutral','neutral']);
});
test('simultaneous opposing actions retain every reported direction in the bubble',()=>{
  const c=make();assert.deepEqual(tones(glance(c,'mixed')),['mixed','mixed','neutral','neutral']);
  const thermal=tile(c,'mixed','temperature'),moisture=tile(c,'mixed','humidity');
  tone(thermal,'mixed');tone(moisture,'mixed');
  for(const word of ['Heating','Cooling'])assert.ok(title(thermal).includes(word));
  for(const word of ['Humidifying','Dehumidifying'])assert.ok(title(moisture).includes(word));
});
test('resolved automatic purification covers every particle reading without implying gas removal',()=>{
  const c=make();assert.deepEqual(tones(glance(c,'air')),['neutral','neutral','neutral','filtration']);
  for(const metric of ['pm1','pm25','pm4','pm10','pollen','aqi']){
    const html=tile(c,'air',metric);tone(html,'filtration');
    assert.ok(title(html).includes('Filtering air'),metric);
    assert.ok(!visibleText(html).includes('Filtering air'),metric);
  }
  for(const metric of ['co2','voc','tvoc','voc_parts','voc_index','hcho','formaldehyde',
      'radon','no2','o3','so2','co','mold','pressure','illuminance','noise'])
    tone(tile(c,'air',metric),'neutral');
  const info=c._metricInfo122({...reading(c,'air','pm10'),exceeded:true,threshold:10},'air');
  tone(info,'filtration');assert.ok(title(info).includes('Filtering air'));
});
test('resolved extraction reaches particle and gas readings but not unrelated measurements',()=>{
  const c=make();change(c,'climate.managed_purifier',{attributes:{resolved_fan_purpose:'extraction'}});
  assert.deepEqual(tones(glance(c,'air')),['neutral','neutral','ventilation','ventilation']);
  for(const metric of ['pm1','pm25','pm4','pm10','pollen','aqi','co2','voc','tvoc','voc_parts',
      'voc_index','hcho','formaldehyde','radon','no2','o3','so2','co']){
    const html=tile(c,'air',metric);tone(html,'ventilation');
    assert.ok(title(html).includes('Ventilating'),metric);
  }
  for(const metric of ['temperature','humidity','pressure','illuminance','noise'])
    tone(tile(c,'air',metric),'neutral');
});
test('mold shows related moisture, thermal and ventilation activity without removal claims',()=>{
  for(const [area,wanted,label] of [['heat','heat','Heating'],['dry','dry','Dehumidifying'],
      ['humidify','humidify','Humidifying'],['air','ventilation','Ventilating']]){
    const c=make(),mold={...reading(c,'air','mold'),entity_id:'sensor.'+area+'_mold'};
    if(area==='air')change(c,'climate.managed_purifier',{attributes:{resolved_fan_purpose:'extraction'}});
    else room(c,area).readings.push(mold);
    const html=c._metric(mold,false,area);
    tone(html,wanted);assert.match(title(html),/Related device activity/);
    assert.ok(title(html).includes(label));
    assert.ok(!/mold remov|risk reduc|mold clear/i.test(html));
    assert.ok(!visibleText(html).includes('Related device activity'));
  }
});
test('unresolved purpose and companion fan metadata cannot invent filtration',()=>{
  for(const resolved of [null,undefined]){
    const c=make(),a=c._hass.states['climate.managed_purifier'].attributes;
    if(resolved===undefined)delete a.resolved_fan_purpose;else a.resolved_fan_purpose=resolved;
    change(c,'fan.purifier',{attributes:{device_class:'air_purifier',pm2_5:7.2}});
    assert.deepEqual(tones(glance(c,'air')),['neutral','neutral','neutral','neutral']);
  }
  const c=make();change(c,'climate.managed_heater',{attributes:{resolved_fan_purpose:'filtration'}});
  assert.deepEqual(tones(glance(c,'heat')),['heat','neutral','neutral','neutral']);
  const old=make();delete old._hass.states['climate.managed_purifier'].attributes.resolved_fan_purpose;
  change(old,'select.purpose_purifier',{state:'filtration'});
  assert.equal(tones(glance(old,'air'))[3],'filtration','Older explicit-role metadata remains usable');
  const signature=old._controllerSignature();
  change(old,'climate.managed_purifier',{attributes:{resolved_fan_purpose:null}});
  assert.notEqual(old._controllerSignature(),signature,'Absent role and authoritative null have different rendering');
  assert.equal(tones(glance(old,'air'))[3],'neutral','Authoritative unresolved role overrides stale selector');
});
test('monitoring without applicable equipment omits device state from every measurement bubble',()=>{
  for(const language of ['en','el','de']){
    const c=make();c._hass.language=language;
    for(const [id,state] of Object.entries(c._hass.states))
      if(state.attributes?.area_id==='air')delete c._hass.states[id];
    assert.equal(c._managedControllers('air').length,0);
    for(const item of room(c,'air').readings){
      const activity=c._metricActivityHelpB6(item,'air');
      assert.equal(activity.text,'',language+' '+item.metric);
      assert.equal(activity.help,c._metricHelp(item),language+' '+item.metric);
      assert.equal(activity.tone,'neutral');
      const html=tile(c,'air',item.metric);
      assert.ok(html.includes(c._metricHelp(item)),'Measurement help disappeared');
    }
    const outside=c._hass.states['sensor.hem'].attributes.dashboard.outdoor.readings[0];
    assert.equal(c._metricActivityHelpB6(outside,null).text,'');
  }
});
test('inactive thermal and humidity devices cannot inherit air-treatment activity from room sensors',()=>{
  for(const language of ['en','el','de'])for(const purpose of ['filtration','extraction']){
    for(const [area,native,facade,ownMetric] of [
      ['heat','climate.heater','climate.managed_heater','temperature'],
      ['humidify','humidifier.moisture','climate.managed_moisture','humidity'],
      ['dry','humidifier.dryer','climate.managed_dryer','humidity']]){
      const c=make();c._hass.language=language;
      change(c,facade,{attributes:{resolved_fan_purpose:purpose}});
      const own=c._hass.states[native].attributes;
      // Monitoring humidity or air pollutants on a thermal controller is
      // not evidence that it can control those measurements.
      own.current_humidity=54.2;own.pm2_5=7.2;
      if(area==='heat')own.hvac_modes=['off','heat'];
      for(const status of ['off','idle','unavailable']){
        const action=status==='idle'?'idle':'off';
        change(c,native,{state:status==='unavailable'?'unavailable':status==='off'?'off':'on',
          attributes:{hvac_action:action,action}});
        for(const metric of ['pm1','pm25','pm4','pm10','pollen','aqi','co2','voc','tvoc',
          'voc_parts','voc_index','hcho','formaldehyde','radon','no2','o3','so2','co']){
          const item=reading(c,'air',metric),activity=c._metricActivityHelpB6(item,area);
          assert.equal(activity.text,'',language+' '+area+' '+purpose+' '+status+' '+metric);
          assert.equal(activity.help,c._metricHelp(item));
          assert.equal(activity.tone,'neutral');
          for(const html of [c._metric(item,false,area),c._metricInfo122(item,area)]){
            assert.ok(!html.includes('Ανενεργό'),'Unrelated Greek Off leaked into data help');
            assert.ok(html.includes(c._metricHelp(item)),'Monitoring explanation disappeared');
          }
        }
        // The actual equipment channel retains its real state and neutral icon.
        const relevant=c._metricActivityHelpB6(reading(c,area,ownMetric),area);
        assert.notEqual(relevant.text,'',language+' '+area+' '+status);
        assert.equal(relevant.tone,'neutral');
        if(area==='heat')assert.equal(c._metricActivityHelpB6(reading(c,area,'humidity'),area).text,'');
        else assert.equal(c._metricActivityHelpB6(reading(c,area,'temperature'),area).text,'');
      }
    }
  }
});
test('real fan-only and drying capabilities keep applicable inactive and unavailable explanations',()=>{
  const c=make();
  change(c,'climate.heater',{state:'off',attributes:{hvac_action:'off',hvac_modes:['off','heat','dry','fan_only']}});
  change(c,'climate.managed_heater',{attributes:{resolved_fan_purpose:'extraction',
    supported_operating_modes:['heat','dry','fan_only']}});
  for(const metric of ['temperature','humidity','co2','aqi']){
    const item=reading(c,metric==='aqi'?'air':'heat',metric);
    assert.equal(c._metricActivityHelpB6(item,'heat').text,'Off',metric);
  }
  for(const [state,expected] of [['off','Off'],['unavailable','Device unavailable']]){
    const fan=make();change(fan,'fan.purifier',{state});
    assert.equal(fan._metricActivityHelpB6(reading(fan,'air','aqi'),'air').text,expected);
    assert.equal(fan._metricActivityHelpB6(reading(fan,'air','co2'),'air').text,'');
    assert.equal(fan._metricActivityHelpB6(reading(fan,'air','humidity'),'air').text,'');
  }
});
test('missing action, idle and unavailable are distinct explanations with neutral icons',()=>{
  for(const [action,label] of [['idle','Idle'],[null,'Current activity is not reported']]){
    const c=make();
    if(action===null)delete c._hass.states['climate.heater'].attributes.hvac_action;
    else change(c,'climate.heater',{attributes:{hvac_action:action}});
    assert.equal(tones(glance(c,'heat'))[0],'neutral');
    assert.ok(title(glance(c,'heat')).includes(label));
    tone(tile(c,'heat','temperature'),'neutral');
  }
  for(const state of ['unknown','unavailable']){
    const c=make();change(c,'climate.heater',{state});
    assert.equal(tones(glance(c,'heat'))[0],'neutral');
    tone(tile(c,'heat','temperature'),'neutral');
    assert.ok(!title(glance(c,'heat')).includes('Heating reported'));
  }
  for(const action of ['idle','off','unknown','',null]){
    const c=make();
    if(action===null)delete c._hass.states['humidifier.moisture'].attributes.action;
    else change(c,'humidifier.moisture',{attributes:{action}});
    assert.equal(tones(glance(c,'humidify'))[1],'neutral');
  }
  for(const action of ['constructor','__proto__','toString','unrecognized-action']){
    const c=make();change(c,'climate.cooler',{attributes:{hvac_action:action}});
    const html=glance(c,'cool');
    assert.deepEqual(tones(html),['neutral','neutral','neutral','neutral']);
    assert.match(html,/class="hem-room-active87" aria-label="0 Active"/,
      'Unrecognized native action became an active device: '+action);
    assert.ok(!title(html).includes('Output on'));
  }
});
test('confirmed supply Off blocks stale activity while preserving the conflict in the bubble',()=>{
  const c=make();change(c,'climate.managed_heater',{attributes:{upstream_power_switch:'switch.supply'}});
  c._hass.states['switch.supply']={state:'off',attributes:{}};
  assert.equal(tones(glance(c,'heat'))[0],'neutral');
  const html=tile(c,'heat','temperature');tone(html,'neutral');
  assert.match(title(html),/Power supply off/);assert.match(title(html),/Heating reported/);
  const signature=c._controllerSignature();change(c,'switch.supply',{state:'on'});
  assert.notEqual(c._controllerSignature(),signature,'Supply-only update did not invalidate');
  assert.equal(tones(glance(c,'heat'))[0],'heat');
  delete c._hass.states['climate.heater'].attributes.hvac_action;
  assert.equal(tones(glance(c,'heat'))[0],'neutral','Supply ON was treated as heating evidence');
});
test('native Off with reported activity is an explicit conflict, not silent idle',()=>{
  const c=make();change(c,'climate.heater',{state:'off'});
  assert.equal(tones(glance(c,'heat'))[0],'conflict');
  const html=tile(c,'heat','temperature');tone(html,'conflict');
  assert.match(title(html),/Heating reported while set to Off/);
  assert.ok(!visibleText(html).includes('Heating reported'));
});
test('manual, existing and paused control methods still show real native activity',()=>{
  for(const mode of ['manual','existing','off']){
    const c=make();change(c,'climate.managed_heater',{attributes:{control_mode:mode,
      controller_status:{status:'paused'}}});change(c,'select.method_heater',{state:mode});
    assert.equal(tones(glance(c,'heat'))[0],'heat',mode);
  }
  const c=make();delete c._hass.states['climate.managed_heater'];delete c._hass.states['select.method_heater'];
  assert.equal(tones(glance(c,'heat'))[0],'neutral','Unselected room entity was enrolled by display logic');
});
test('zero fan output and unavailable native fans cannot display active measurement icons',()=>{
  for(const percentage of [0,null]){
    const c=make();change(c,'fan.purifier',{state:percentage===null?'off':'on',attributes:{percentage}});
    assert.equal(tones(glance(c,'air'))[3],'neutral');
  }
  const c=make();change(c,'fan.purifier',{state:'unavailable'});
  assert.equal(tones(glance(c,'air'))[3],'neutral');tone(tile(c,'air','pm10'),'neutral');
});
test('inventory-only native action, purpose and supply changes invalidate and refresh',()=>{
  const c=make(),s=c._hass.states;
  delete s['select.method_purifier'];delete s['select.purpose_purifier'];
  s['climate.managed_purifier']={state:'unavailable',attributes:{}};
  s['sensor.hem'].attributes.dashboard.controllers=[{
    area_id:'air',controller_id:'entry_controller_purifier',climate_entity_id:'climate.managed_purifier',
    source_entity_ids:['fan.purifier'],source_device_id:'device_purifier',name:'Purifier',
    control_mode:'existing',supported_operating_modes:['fan_only'],native_primary_entity_id:'fan.purifier',
    resolved_fan_purpose:'filtration',status_code:'waiting_for_physical_device',
    unavailable_source_entity_ids:[],upstream_power_switch:'switch.purifier_supply'}];
  s['switch.purifier_supply']={state:'on',attributes:{}};
  assert.equal(tones(glance(c,'air'))[3],'filtration');
  let sig=c._controllerSignature();change(c,'fan.purifier',{attributes:{percentage:0}});
  assert.notEqual(c._controllerSignature(),sig);assert.equal(tones(glance(c,'air'))[3],'neutral');
  change(c,'fan.purifier',{attributes:{percentage:50}});
  sig=c._controllerSignature();change(c,'switch.purifier_supply',{state:'off'});
  assert.notEqual(c._controllerSignature(),sig);assert.equal(tones(glance(c,'air'))[3],'neutral');
  change(c,'switch.purifier_supply',{state:'on'});sig=c._controllerSignature();
  const data=structuredClone(c._hass.states['sensor.hem']);
  data.attributes.dashboard.controllers[0].resolved_fan_purpose='extraction';
  change(c,'sensor.hem',data);
  assert.notEqual(c._controllerSignature(),sig);assert.equal(tones(glance(c,'air'))[2],'ventilation');

  const heat=make(),hs=heat._hass.states;delete hs['select.method_heater'];
  hs['climate.managed_heater']={state:'unavailable',attributes:{}};
  hs['sensor.hem'].attributes.dashboard.controllers=[{
    area_id:'heat',controller_id:'entry_controller_heater',climate_entity_id:'climate.managed_heater',
    source_entity_ids:['climate.heater'],source_device_id:'device_heater',control_mode:'existing',
    supported_operating_modes:['heat'],native_primary_entity_id:'climate.heater',
    unavailable_source_entity_ids:[],status_code:'waiting_for_physical_device'}];
  sig=heat._controllerSignature();change(heat,'climate.heater',{attributes:{hvac_action:'idle'}});
  assert.notEqual(heat._controllerSignature(),sig,'Inventory-only action attribute was omitted');
  assert.equal(tones(glance(heat,'heat'))[0],'neutral');
});
test('registry recovery uses inventory purpose only for the same exact controller identity',()=>{
  const recover=()=>{
    const c=make(),s=c._hass.states,controller='entry_controller_purifier';
    const sources=['fan.purifier','humidifier.purifier_companion'];
    s['humidifier.purifier_companion']={state:'unavailable',attributes:{}};
    s['climate.managed_purifier']={state:'unavailable',attributes:{}};
    delete s['select.method_purifier'];delete s['select.purpose_purifier'];
    s['sensor.purifier_status']={state:'waiting_for_physical_device',attributes:{
      controller_id:controller,area_id:'air',source_device_id:'device_purifier',
      source_entity_ids:sources,native_primary_entity_id:'fan.purifier',
      control_method:'existing',status_code:'waiting_for_physical_device'}};
    const common={platform:'environment_manager',config_entry_id:'entry',device_id:'hem_purifier'};
    c._hass.entities={
      'climate.managed_purifier':{...common,unique_id:controller+'_climate'},
      'sensor.purifier_status':{...common,unique_id:controller+'_control_status'}};
    s['sensor.hem'].attributes.dashboard.controllers=[{
      controller_id:controller,area_id:'air',climate_entity_id:'climate.managed_purifier',
      source_device_id:'device_purifier',source_entity_ids:sources,
      native_primary_entity_id:'fan.purifier',control_mode:'existing',
      unavailable_source_entity_ids:['humidifier.purifier_companion'],
      supported_operating_modes:['fan_only'],resolved_fan_purpose:'filtration'}];
    return c;
  };
  const c=recover(),before=JSON.stringify(c._hass.states);
  assert.equal(tones(glance(c,'air'))[3],'filtration');
  assert.equal(JSON.stringify(c._hass.states),before,'Inventory enrichment mutated native evidence');
  const unrelated=recover();
  unrelated._hass.states['sensor.hem'].attributes.dashboard.controllers[0].source_entity_ids=['fan.purifier'];
  assert.equal(tones(glance(unrelated,'air'))[3],'neutral','A different source identity supplied fan purpose');
  const replaced=recover();
  replaced._hass.states['sensor.hem'].attributes.dashboard.controllers[0].source_device_id='replacement_device';
  assert.equal(tones(glance(replaced,'air'))[3],'neutral','A replacement physical device supplied fan purpose');
  const unresolved=recover();
  unresolved._hass.states['sensor.purifier_status'].attributes.resolved_fan_purpose=null;
  assert.equal(tones(glance(unresolved,'air'))[3],'neutral','Recovered authoritative null was overwritten');
});
test('climate-only rooms and second-reading warnings retain narrow reading activity',()=>{
  const c=make(),r=room(c,'air');r.climate_only=true;r.readings=[];
  c._hass.states['climate.managed_purifier'].attributes.measurements={
    temperature:21.3,humidity:54.2,co2:718,pm25:7.2};
  const html=c._room(r),body=html.slice(html.indexOf('</summary>')+10);
  assert.match(body,/class="metric-grid hem-metric-narrow-b6"/);
  tone(body,'filtration');assert.match(title(body),/Filtering air/);
  c._config.show_metrics=false;
  assert.ok(!c._room(r).slice(c._room(r).indexOf('</summary>')+10).includes('hem-metric-narrow-b6'),
    'Hidden metrics configuration was ignored in climate-only room');
  const warning=make(),item=reading(warning,'air','pm25');item.exceeded=true;item.threshold=5;
  const details=warning._roomDetailReadings122(room(warning,'air'));
  const retained=details.filter(value=>value.metric==='pm25');
  assert.equal(retained.length,1);assert.ok(retained[0].overview_detail122);
  const info=warning._metricInfo122(retained[0],'air');
  assert.match(info,/hem-metric-narrow-value-b6/);tone(info,'filtration');

  const duplicates=make(),dr=room(duplicates,'air'),first=reading(duplicates,'air','pm25');
  first.name='Z source';delete dr.environment.measurement_evidence.pm25;
  const selected={...first,name:'A source',value:3,entity_id:'sensor.air_pm25_alternative'};
  dr.readings.push(selected);
  duplicates._hass.states[selected.entity_id]={state:'3',attributes:{}};
  const overview=duplicates._roomGlance122(dr);
  assert.equal(overview.extras[1].entity_id,selected.entity_id);
  const fallback=duplicates._roomDetailReadings122(dr,overview).filter(value=>value.overview_narrow_b6);
  assert.equal(fallback.length,1);assert.equal(fallback[0].entity_id,selected.entity_id);
  assert.equal(fallback[0].value,3,'Narrow fallback uses the actual selected reading');
});
test('rendering preserves source evidence and introduces no standalone activity text',()=>{
  const c=make(),before=JSON.stringify(c._hass.states);
  for(const area of ['heat','cool','humidify','dry','air','mixed']){
    const html=c._room(room(c,area));
    assert.ok(!visibleText(html).match(/Heating reported|Preheating|Defrosting|Filtering air|Ventilating/));
  }
  assert.equal(JSON.stringify(c._hass.states),before);
});
let failed=0;for(const {name,run} of cases){try{run();console.log('PASS: '+name);}
 catch(error){failed++;console.error('FAIL: '+name+'\n'+error.stack);}}
if(failed)process.exitCode=1;else console.log('B6_METRIC_ACTIVITY_EVIDENCE_AND_MARKUP=PASS ('+cases.length+' cases)');
"""


VISIBLE_REPORT = r"""area=>{
 const root=card.shadowRoot.querySelector('[data-room-fold87="'+area+'"]');
 const visible=el=>!!el&&el.getClientRects().length>0&&getComputedStyle(el).visibility!=='hidden';
 const colour=el=>el?getComputedStyle(el).color:null;
 const tiles=[...root.querySelectorAll('.metric[data-room-metric114]')].filter(visible).map(el=>({
   metric:el.dataset.roomMetric114,classes:el.className,
   icon:colour(el.querySelector('.metric-name > ha-icon')),
   value:colour(el.querySelector('.metric-number')),text:el.innerText,
   help:el.querySelector('.metric-help-content')?.textContent||'',
   valueVisible:visible(el.querySelector('.metric-number'))}));
 const badges=[...root.querySelectorAll('summary .hem-room-metric107')].filter(visible).map(el=>({
   classes:el.className,title:el.title,
   metric:el.dataset.hemAverage105||el.dataset.hemSource105?.replace('sensor.'+area+'_',''),
   icon:colour(el.querySelector(':scope > ha-icon')),
   value:colour(el.querySelector('.hem-room-metric-value107')),
   average:colour(el.querySelector('.hem-avg-marker105 ha-icon')),text:el.innerText}));
 return {tiles,badges,text:root.innerText,width:root.getBoundingClientRect().width,
   overflow:document.documentElement.scrollWidth>innerWidth+1};
}"""


def browser_checks(states):
    from playwright.sync_api import sync_playwright

    chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
        shutil.which("chromium") or shutil.which("google-chrome"))
    assert chrome, "Chromium required"
    helpers = baseline.layout_helpers()
    output = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
    if output:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 760, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
          *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial,sans-serif}
          :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
          --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
          #card-frame{width:100%;max-width:100%}
        </style></head><body><main id="card-frame"></main></body></html>""")
        page.evaluate(helpers["ICON_FIXTURE"])
        page.add_script_tag(path=str(CARD))
        page.evaluate("""states=>{
          window.calls=[];window.info=[];
          window.card=document.createElement('home-environment-manager-card');
          document.getElementById('card-frame').append(card);
          card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
          card._hass={language:'en',states,localize:()=>undefined,callWS:async()=>({}),
            callService:(...args)=>{calls.push(args);return Promise.resolve()}};
          card._config={entity:'sensor.hem'};card._expanded.add('air');card._renderContent(true);
          card.shadowRoot.querySelector('[data-room-fold87="air"]').open=true;
        }""", states)
        filtration = baseline.COLOURS["filtration"]
        for width in (760, 390, 320, 760):
            page.set_viewport_size({"width": width, "height": 1000})
            report = page.evaluate(VISIBLE_REPORT, "air")
            assert not report["overflow"], (width, report)
            for metric in ("co2", "pm25"):
                number_count = sum(b["metric"] == metric for b in report["badges"]) + sum(
                    t["metric"] == metric and t["valueVisible"] for t in report["tiles"])
                assert number_count == 1, (width, metric, report)
            for metric in ("pm1", "pm4", "pm10"):
                metric_tiles = [t for t in report["tiles"] if t["metric"] == metric]
                assert len(metric_tiles) == 1, (width, metric, report)
                tile = metric_tiles[0]
                assert tile["icon"] == filtration and tile["value"] != filtration, (width, tile)
                assert "Filtering air" in tile["help"] and "Filtering air" not in tile["text"], tile
            for tile in report["tiles"]:
                if tile["metric"] in ("voc", "pressure", "illuminance", "noise"):
                    assert tile["icon"] != filtration, (width, tile)
            pm25 = [b for b in report["badges"] if b["metric"] == "pm25"] + [
                t for t in report["tiles"] if t["metric"] == "pm25" and t["valueVisible"]]
            assert pm25[0]["icon"] == filtration and pm25[0]["value"] != filtration, (width, pm25)
            assert "Filtering air" not in report["text"], (width, report["text"])
            if output:
                page.locator('#card-frame').screenshot(path=str(output / f"b6-metric-activity-{width}.png"))
        heat = page.evaluate(VISIBLE_REPORT, "heat")
        temperature = next(b for b in heat["badges"] if b["metric"] == "temperature")
        assert temperature["icon"] == baseline.COLOURS["heat"]
        assert temperature["value"] != baseline.COLOURS["heat"]
        assert temperature["average"] not in baseline.COLOURS.values()

        # A warning already owns an explanatory tile. Its hidden-header value
        # belongs inside that tile on narrow cards, without a duplicate tile.
        page.evaluate("""()=>{
          const state=structuredClone(card._hass.states['sensor.hem']);
          const room=state.attributes.dashboard.rooms.find(r=>r.area_id==='air');
          const reading=room.readings.find(r=>r.metric==='pm25');
          reading.exceeded=true;reading.threshold=5;
          card._hass={...card._hass,states:{...card._hass.states,'sensor.hem':state}};
          card._roomsExpanded87.add('air');card._renderContent(true);
        }""")
        for width in (760, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            report = page.evaluate(VISIBLE_REPORT, "air")
            particles = [tile for tile in report["tiles"] if tile["metric"] == "pm25"]
            assert len(particles) == 1 and particles[0]["icon"] == filtration, (width, report)
            number_count = sum(b["metric"] == "pm25" for b in report["badges"]) + sum(
                tile["valueVisible"] for tile in particles)
            assert number_count == 1, (width, report)
        page.set_viewport_size({"width": 760, "height": 1000})

        # The pre-existing info control carries activity, and opening it cannot
        # invoke a service or fold its room. No extra visible activity row exists.
        help_control = page.locator('[data-room-fold87="air"] [data-room-metric114="pm10"] .metric-help > summary')
        help_control.click()
        page.wait_for_function("!!card._floatingInfo87")
        bubble = page.locator('.hem-floating-info87')
        assert bubble.is_visible() and "Filtering air" in bubble.inner_text()
        assert page.locator('[data-room-fold87="air"]').get_attribute("open") is not None
        page.keyboard.press("Escape")
        assert page.evaluate("calls") == []

        # Facade and recommendation objects remain unchanged. A fan-only update
        # must update both header and body colours through the real HA setter.
        page.evaluate("""()=>{
          window.beforeSensor=card._hass.states['sensor.hem'];
          window.beforeFacade=card._hass.states['climate.managed_purifier'];
          const old=card._hass.states['fan.purifier'];
          card.hass={...card._hass,states:{...card._hass.states,
            'fan.purifier':{...old,attributes:{...old.attributes,percentage:0}}}};
        }""")
        page.wait_for_function("""()=>card.shadowRoot.querySelector(
          '[data-room-fold87="air"] [data-room-metric114="pm10"]').classList.contains('hem-activity-neutral')""")
        assert page.evaluate("card._hass.states['sensor.hem']===beforeSensor && card._hass.states['climate.managed_purifier']===beforeFacade")
        idle = page.evaluate(VISIBLE_REPORT, "air")
        assert any(t["metric"] == "pm10" for t in idle["tiles"]), idle
        assert all(t["icon"] != filtration for t in idle["tiles"])
        assert all(b["icon"] != filtration for b in idle["badges"])

        # An inactive heater may carry a room-inferred fan purpose, but the
        # actual Greek humidity/AQI information bubbles remain monitoring-only.
        page.evaluate("""states=>{
          const native=states['climate.heater'];
          native.state='off';native.attributes.hvac_action='off';
          native.attributes.hvac_modes=['off','heat'];native.attributes.current_humidity=54.2;
          states['climate.managed_heater'].attributes.resolved_fan_purpose='filtration';
          const rooms=states['sensor.hem'].attributes.dashboard.rooms;
          const heat=rooms.find(room=>room.area_id==='heat');
          const humidity=heat.readings.find(item=>item.metric==='humidity');
          humidity.exceeded=true;humidity.threshold=50;
          const aqi=structuredClone(rooms.find(room=>room.area_id==='air').readings.find(item=>item.metric==='aqi'));
          aqi.entity_id='sensor.heat_aqi';states[aqi.entity_id]={state:String(aqi.value),attributes:{}};
          heat.readings.push(aqi);
          card._hass={...card._hass,language:'el',states};
          card._expanded.add('heat');card._roomsExpanded87.add('heat');card._renderContent(true);
        }""", states)
        for metric, explanation in (("humidity", "Η σχετική υγρασία"), ("aqi", "Ο δείκτης AQI")):
            help_control = page.locator(
                f'[data-room-fold87="heat"] [data-room-metric114="{metric}"] .metric-help > summary')
            help_control.click()
            page.wait_for_function("!!card._floatingInfo87")
            bubble_text = page.locator('.hem-floating-info87').inner_text()
            assert explanation in bubble_text, (metric, bubble_text)
            assert "Ανενεργό" not in bubble_text, (metric, bubble_text)
            assert "Τρέχουσα δραστηριότητα συσκευών" not in bubble_text, (metric, bubble_text)
            assert page.locator('[data-room-fold87="heat"]').get_attribute("open") is not None
            page.keyboard.press("Escape")
        assert page.evaluate("card._measurementActivityB6('temperature','heat').text") == "Ανενεργό"
        assert page.evaluate("calls") == []
        assert not errors, errors
        browser.close()
    print("B6_METRIC_ACTIVITY_COLOURS_BUBBLES_NATIVE_UPDATES_MOBILE=PASS")


if __name__ == "__main__":
    states = fixture()
    result = subprocess.run(["node", "-e", NODE_CHECKS, str(CARD)],
        input=json.dumps({"states": states}), text=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if "--logic-only" not in sys.argv:
        browser_checks(states)
