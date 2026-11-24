// Render both documentation screenshots using the installed card and sample HA state.
// Dependencies and invocation are in .github/workflows/readme-images.yml.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');
const icons = require('@mdi/js');

const rooms = [
  ['bathroom', 'Bathroom', 19.2, 44.7, 58.9, 0],
  ['guest', 'Guest room', 17.6, 47.9, 58, 8],
  ['kitchen', 'Kitchen', 19.2, 48.5, 61, null],
  ['bedroom', 'Bedroom', 17, 50.2, 58, 0],
  ['living', 'Living room', 22.3, 34.4, null, null],
];

function sampleHome() {
  const states = {}, entities = {}, devices = [];
  function state(id, value, attributes) {
    states[id] = { state: String(value), attributes };
  }
  const roomData = rooms.map(([area, name, temperature, humidity, mold, lux]) => {
    const readings = [], evidence = {};
    function read(metric, label, value, unit, extra = {}) {
      const entity = 'sensor.' + area + '_' + metric;
      readings.push({metric, name: label, unit, value, entity_id: entity, available: value !== null, ...extra});
      state(entity, value ?? 'unavailable', {friendly_name: name + ' ' + label, unit_of_measurement: unit});
      if (['temperature', 'humidity'].includes(metric)) {
        const second = entity + '_2';
        state(second, value, {...states[entity].attributes, friendly_name: name + ' second ' + label});
        evidence[metric] = {value, source_count: 2, source_ids: [entity, second]};
      }
    }
    read('temperature', 'Temperature', temperature, '°C');
    read('humidity', 'Humidity', humidity, '%');
    if (area === 'bathroom') {
      readings.push({metric:'illuminance', name:'Illuminance', unit:'lx', available:false,
                     entity_id:'sensor.bathroom_light_secondary', value:null});
    }
    if (area !== 'living') {
      read('aqi', 'AQI', null, 'AQI');
      read('pm25', 'PM2.5', null, 'µg/m³', {threshold:25});
      read('mold', 'Mold indication', mold, '%', {threshold:70, details:{calibration_factor:1.310048}});
      if (lux !== null) read('illuminance', 'Illuminance', lux, 'lx');
    } else {
      read('pm25', 'PM2.5', 1, 'µg/m³', {threshold:25});
      read('aqi', 'AQI', 13, 'AQI');
    }
    const environment = {
      measurement_evidence:evidence,
      climate_plan:{status:'ready', controller:'environment', profile:'home', away:'home',
        occupancy:area === 'living' ? 'occupied' : 'unoccupied', temperature_c:temperature,
        equipment_plan:{humidity:{measured_rh:humidity, action:'idle'}}, actuation:{status:'advisory_only'}},
    };
    const windows = [];
    if (area === 'bathroom') {
      windows.push({entity_id:'binary_sensor.bathroom_window', name:'Bathroom window', opened:true});
      const door = 'binary_sensor.bathroom_door';
      state(door, 'on', {friendly_name:'Bathroom door', device_class:'door'});
      environment.door_context = {contacts:[{entity_id:door, state:'open', health:'ok', kind:'interior'}]};
      environment.condensation = {status:'ready', condensation_margin_c:8};
    }
    devices.push({id:'hem_'+area, identifiers:[['environment_manager','sample_area_'+area]]});
    return {area_id:area, name, status:area === 'living' ? 'safe' : 'attention',
      data_availability:{status:area === 'living' ? 'ready' : 'partial'},
      readings, environment, windows, high_count:0};
  });
  for (const [slug, name, mode, rh, area = 'bathroom', action = 'idle'] of [
    ['dehumidifier','Bathroom dehumidifier','dry',58.9], ['heater','Bathroom heater','heat',44.8],
    ['guest_heater','Guest room heater','heat',47.9,'guest','heating'],
  ]) {
    const physical='climate.'+slug, managed='climate.hem_'+slug;
    const running = action !== 'idle';
    const nativeMode = running ? mode : 'off';
    state(physical,nativeMode,{friendly_name:name, hvac_action:action});
    const temperature = rooms.find(row => row[0] === area)[2];
    const attrs={area_id:area, source_entity_ids:[physical], source_device_id:slug,
      friendly_name:name+' controller', physical_primary_entity_id:physical, physical_source_state:nativeMode,
      control_mode:'automatic', overview_targets:mode==='dry'?{mold:60}:{heat:21},
      humidity_demand:mode==='dry'?{target_basis:'mold_surface_rh',target_ready:true,control_measurement:rh,control_target:60}:{},
      hvac_modes:['off',mode], requested_hvac_mode:nativeMode,
      current_temperature:temperature, measurements:{temperature,humidity:rh},
      controller_status:{status:running ? 'controlling' : 'within_target_band'}};
    state(managed,nativeMode,attrs);
    entities[managed]={device_id:'hem_'+slug};
    entities[physical]={device_id:slug};
  }
  const frost='binary_sensor.frost_warning';
  state(frost,'on',{friendly_name:'Frost warning',headline:'FROST'});
  const dashboard = {version:1, rooms:roomData, summary:{safe:1,attention:4,unknown:0},
    arrival_preparation:{entry_id:'sample',active:false,home_status:'home',timeout_minutes:60},
    outdoor:{status:'unsafe', weather:[{condition:'partlycloudy',temperature_c:0.8,wind_kmh:11}],
      readings:[{metric:'aqi',name:'AQI',unit:'US AQI',value:16,available:true}],
      warnings:[{entity_id:frost,name:'Frost warning',active:true}],
      blockers:[{code:'temperature',label:'Low outdoor temperature',value:'0.9 °C'}]}};
  state('sensor.hem','ready',{dashboard,warning_sources:[frost]});
  entities['sensor.hem']={device_id:'hem_home', config_entry_id:'sample'};
  devices.push({id:'hem_home',identifiers:[['environment_manager','sample']]});
  return {states,entities,devices};
}

async function main() {
  const output=path.resolve(process.argv[2] || 'docs/images');
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({executablePath:process.env.CHROME_BIN || '/usr/bin/google-chrome'});
  try {
    const page=await browser.newPage({viewport:{width:650,height:1100},deviceScaleFactor:2,locale:'en-US',colorScheme:'dark'});
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.setContent(`<!doctype html><html lang="en"><style>
      :root{--primary-text-color:#e5e5e5;--secondary-text-color:#aaa;--card-background-color:#1d1d1d;
      --secondary-background-color:#202020;--divider-color:#383838;--primary-color:#03a9f4;
      --ha-card-box-shadow:none;color-scheme:dark}body{margin:0;padding:5px 8px;background:#101010}
      ha-card{display:block;border:1px solid var(--divider-color)}
      </style><main></main></html>`);
    await page.evaluate(paths=>{
      customElements.define('ha-icon',class extends HTMLElement {
        static get observedAttributes(){return ['icon'];}
        constructor(){super();this.attachShadow({mode:'open'});}
        connectedCallback(){this.draw();}
        attributeChangedCallback(){this.draw();}
        draw(){
          const key='mdi'+(this.getAttribute('icon')||'').replace(/^mdi:/,'')
            .split('-').map(x=>x.charAt(0).toUpperCase()+x.slice(1)).join('');
          const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
          svg.setAttribute('viewBox','0 0 24 24');
          svg.setAttribute('style','width:100%;height:100%;fill:currentColor');
          const p=document.createElementNS(svg.namespaceURI,'path');
          p.setAttribute('d',paths[key]||'');svg.append(p);
          const css=document.createElement('style');
          css.textContent=':host{display:inline-flex;vertical-align:middle;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)}';
          this.shadowRoot.replaceChildren(css,svg);
        }
      });
    },icons);
    await page.addScriptTag({path:path.resolve('custom_components/environment_manager/frontend/home-environment-manager-card.js')});
    await page.evaluate(({states,entities,devices})=>{
      const card=document.createElement('home-environment-manager-card');
      card.setConfig({type:'custom:home-environment-manager-card',entity:'sensor.hem'});
      document.querySelector('main').append(card);
      card.hass={language:'en',locale:{language:'en',number_format:'language'},states,entities,
        connection:{},user:{is_admin:true},config:{time_zone:'UTC'},localize:()=>undefined,
        callWS:async q=>q.type==='config/device_registry/list'?devices:[]};
    },sampleHome());
    const headers=page.locator('.hem-room-glance87');
    await headers.nth(4).waitFor();
    const frame=page.locator('main');
    assert.deepEqual(await headers.locator('.hem-room-name87').allTextContents(),rooms.map(r=>r[1]).sort());
    await page.locator('[data-room-fold87="guest"] .hem-room-tab080 > .hem-room-active87:last-child .hem-activity-heat').waitFor();
    const aqi = page.locator('[data-room-fold87="living"] summary [data-hem-source105="sensor.living_aqi"]');
    assert.equal((await aqi.innerText()).replace(/\s+/g, ' ').trim(), '13 AQI');
    await frame.screenshot({path:path.join(output,'hem-dashboard-overview.png')});
    const bathroom=page.locator('[data-room-fold87="bathroom"]');
    await bathroom.locator('summary .hem-room-name87').first().click();
    await bathroom.locator('.hem-room-condition-detail').first().waitFor();
    for(const [id,expected] of [['heater','19.2°C'],['dehumidifier','58.9%']]){
      const measures=bathroom.locator('[data-device-fold87="climate.hem_'+id+'"] > summary .hem-device-reading87');
      assert.deepEqual(await measures.allTextContents(),[expected]);
      const goal=bathroom.locator('[data-device-fold87="climate.hem_'+id+'"] > summary .hem-controller-target');
      assert.equal(await goal.textContent(),id==='heater'?'21°C':'60%');
    }
    assert.equal(await bathroom.getByRole('button',{name:/Bathroom door/}).count(),1);
    await bathroom.screenshot({path:path.join(output,'hem-room-expanded.png')});
    const detail=await bathroom.innerText();
    for(const label of ['Below the comfort band','Bathroom dehumidifier','Bathroom heater','Bathroom door']) assert.ok(detail.includes(label),label+' missing: '+detail);
    assert.deepEqual(errors,[]);
  } finally {await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
