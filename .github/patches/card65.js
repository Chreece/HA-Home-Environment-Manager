  // Single bundled locale catalog: no per-render network fetch or filesystem I/O.
  const CARD65 = __BUNDLE65__;
  const proto65 = AirQualityAdvisorCard.prototype;
  proto65._l65 = function(key) {
    return (CARD65[this._language()] || CARD65.en).text[key] || CARD65.en.text[key] || '';
  };
  for (const [lang, data] of Object.entries(CARD65)) {
    LANGUAGE[lang] = {...LANGUAGE[lang], metric_illuminance:data.text.lux};
  }
  proto65._controllerStatusLabel = function(code) {
    const key=String(code ?? '').trim();
    if (!key) return '';
    const lang=this._language(), data=CARD65[lang] || CARD65.en, t=data.text;
    const modes={...data.profiles,heat:t.heat,cool:t.cool,dry:t.dry,fan_only:t.fan,
      on:t.on,off:t.off,unknown:t.unknown,unavailable:this._t('missing'),
      idle:t.idle,selected_mean:t.mean,selected_sensor:t.mean,
      selected_partial_mean:t.partialMean,selected_partial_sensor:t.partialMean,
      room_selected_mean:t.mean,not_configured:t.unconfigured,
      complete_measured_stage_capacities_required:t.inputs,
      ready_to_apply_when_physical_off:t.ready,
      ready:t.ready,measured:t.ready,choose:t.choose,
      select_pid_and_nonmanual_method:t.unconfigured,
      select_pid_and_measured_capacity_strategy:t.unconfigured,
      highest_speed_is_reference_100:t.calHelp,
      environment_only_no_hvac:t.summaryHelp,environment_only_no_primary_hvac:t.summaryHelp};
    if (modes[key]) return modes[key];
    const native=this._hass?.localize?.(
      'component.environment_manager.entity.sensor.equipment_control_status.state.'+key);
    const value=data.states[key];
    const english=CARD65.en.states[key];
    // Exact machine codes remain available in the explicit diagnostics section.
    if (typeof native==='string' && native.trim() && !native.startsWith('component.') &&
        native!==key && (lang==='en' || native!==english)) return native;
    if (value && (lang==='en' || value!==english)) return value;
    if (key==='sleep_room_control_paused') return t.sleep;
    if (key==='waiting_for_physical_device') return t.waiting+': '+t.physical;
    if (key==='sleep_room_evidence_unknown') return t.sleep+': '+t.unknown;
    if (/calibration|capacity|stage/.test(key) && /required|invalid|incomplete|missing|unmeasured/.test(key)) return t.inputs;
    if (/waiting|hold|pending|warmup/.test(key)) return t.waiting;
    return t.unknown;
  };
  proto65._climateLabels65 = function() {
    const lang=this._language(), t=CARD65[lang]?.text || CARD65.en.text;
    const data=CARD65[lang] || CARD65.en;
    const base=CLIMATE_LABELS[lang];
    const l=base ? {...base} : Object.fromEntries(Object.keys(CLIMATE_LABELS.en).map(k=>[k,t.information]));
    const state=(key)=>this._controllerStatusLabel(key);
    return {...l,
      advisory:t.overview,environmentOnly:t.summaryHelp,devices:t.devices,
      method:data.methodLabel,manual:data.methods.manual,automatic:data.methods.automatic,
      existing:data.methods.existing,off:t.off,pid:'PID',
      title:base?.title || t.overview,device:t.physical,selectedDevice:t.physical,
      target:t.target,mode:t.choose,currentHumidity:this._t('humidity'),
      humidity:base?.humidity || this._t('humidity'),humidityPower:base?.humidityPower || t.supply,
      sourceStatus:t.information,moistureAction:base?.moistureAction || this._t('humidity'),
      roomTemperature:MOLD_DETAIL_LABELS[lang]?.[5] || t.physical,
      temperatureMissing:this._t('missing'),noPriority:t.idle,
      home:state('home'),away:state('away'),sleep:state('sleep'),eco:state('eco'),
      comfort:state('comfort'),holding:t.waiting,
      heat:t.heat,cool:t.cool,primary:t.physical,secondary:t.physical,
      fan:t.speed,fanPower:t.supply,dryFanAuto:t.choose,
      manualTemperature:base?.manualTemperature || t.target,
      manualHumidity:base?.manualHumidity || t.target,save:t.save,
      openEntity:base?.openEntity || t.details,editFailed:base?.editFailed || this._t('missing'),
      invalidTarget:base?.invalidTarget || t.inputs,
      pause:base?.pause || state('paused'),resume:base?.resume || t.ready,
    };
  };
  proto65._pidLabels65 = function() {
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    return ['PID · '+t.calibration,this._climateLabels65().manual,'IMC / λ','Cohen-Coon',
      t.gain,t.timeConstant+' (min)',t.deadTime+' (min)','λ (min)',t.save,t.apply,t.inputs];
  };
  proto65._fanLabels65 = function() {
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    return ['PID · '+t.capacity,t.legacyStrategy,t.measuredStrategy,t.choose,t.choose,
      t.heat,t.cool,t.dry,t.fan,t.stage,t.speed,t.capacity,t.save,t.apply,t.calHelp,
      t.demand,t.capacity,t.demand,t.physical+': '+t.off];
  };
  const originalManaged65=proto65._managedControllers;
  proto65._managedControllers = function(area) {
    const states=this._hass?.states || {};
    if (this._statusStates65!==states) {
      this._statusStates65=states;
      this._statusIndex65=new Map();
      for (const [id,s] of Object.entries(states)) {
        const a=s?.attributes;
        if (!id.startsWith('sensor.') || !a || !('status_code' in a) ||
            typeof a.area_id!=='string') continue;
        const sources=Array.isArray(a.source_entity_ids) ? a.source_entity_ids : Object.keys(a.physical_entity_states || {});
        if (!sources.length) continue;
        const key=JSON.stringify([a.area_id,[...sources].sort()]);
        // Duplicate matches are ambiguous, not permission to choose one.
        this._statusIndex65.set(key,this._statusIndex65.has(key)?null:{id,state:s});
      }
    }
    return originalManaged65.call(this,area).map(entry=>({...entry,
      statusInfo:this._statusIndex65.get(JSON.stringify([area,
        [...entry.climate.attributes.source_entity_ids].sort()])) || null,
    }));
  };
  proto65._deviceSummary65 = function(entry) {
    const a=entry.climate.attributes || {}, d=entry.statusInfo?.state?.attributes || {};
    const c=a.controller_status || {};
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    const numeric=(v)=>typeof v==='number' && Number.isFinite(v);
    const value=(v,unit='')=>numeric(v)?this._format(v)+unit:null;
    const rows=[];
    const add=(label,display)=>{if(display!==null && display!==undefined && display!=='')
      rows.push('<div><span>'+escape(label)+'</span><b>'+escape(display)+'</b></div>');};
    const physical=a.physical_source_state;
    add(t.physical,this._controllerStatusLabel(physical ?? 'unavailable'));
    add(t.choose,this._controllerStatusLabel(a.requested_hvac_mode || entry.climate.state));
    const observedRh=a.measurements?.humidity ?? a.current_humidity;
    if (numeric(observedRh)) add(this._t('humidity'),value(observedRh,'%'));
    if (numeric(a.humidity)) add(this._t('humidity')+' · '+t.target,value(a.humidity,'%'));
    const nativeUnit=a.temperature_unit || '°C';
    const hasMeasuredTemp=numeric(a.measurements?.temperature);
    const observedTemp=hasMeasuredTemp?a.measurements.temperature:a.current_temperature;
    if (numeric(observedTemp)) add(MOLD_DETAIL_LABELS[this._language()]?.[5] || t.physical,value(observedTemp,' '+(hasMeasuredTemp?'°C':nativeUnit)));
    if (numeric(a.temperature)) add(t.target,value(a.temperature,' '+nativeUnit));
    if (numeric(a.target_temp_low) && numeric(a.target_temp_high))
      add(t.target,this._format(a.target_temp_low)+' - '+this._format(a.target_temp_high)+' '+nativeUnit);
    add(t.demand,value(d.demand_percent ?? c.demand_percent,'%'));
    const supplyId=d.upstream_power_switch || a.upstream_power_switch;
    if (supplyId) {
      const supply=this._hass?.states?.[supplyId];
      add(t.supply,this._controllerStatusLabel(supply?.state ?? d.upstream_power_state ?? a.upstream_power_state ?? 'unavailable'));
    }
    if (numeric(d.upstream_idle_since) && numeric(d.upstream_idle_cooldown_seconds)) {
      const elapsed=Math.max(0,Date.now()/1000-d.upstream_idle_since);
      add(t.cooldown,this._format(Math.max(0,d.upstream_idle_cooldown_seconds-elapsed),0)+' s');
    }
    if (d.sleep_pause_requested===true) add(t.sleep,this._controllerStatusLabel('sleep_room_control_paused'));
    const status=d.status_code || c.status;
    const reason=d.status_reason_code || c.reason;
    const reasonLabel=reason?this._controllerStatusLabel(reason):'';
    const diagnostics=[entry.entityId,...safeArray(a.source_entity_ids),supplyId,status,reason].filter(Boolean);
    const friendlySupply=this._hass?.states?.[supplyId]?.attributes?.friendly_name;
    return '<div class="managed-status">'+escape(this._controllerStatusLabel(status || entry.climate.state))+'</div>'+
      '<div class="hem-device-data">'+rows.join('')+'</div>'+
      (friendlySupply?'<small>'+escape(t.supply)+': '+escape(friendlySupply)+'</small>':'')+
      (reasonLabel && reasonLabel!==t.unknown ? '<small>'+escape(t.reason)+': '+escape(reasonLabel)+'</small>':'')+
      '<details class="hem-diagnostics"><summary>'+escape(t.details)+'</summary><code>'+
      diagnostics.map(escape).join('<br>')+'</code></details>';
  };
  proto65._calibrationDetails65 = function(entry,content) {
    if (!content) return '';
    const opened=this._calibrationExpanded65?.has(entry.entityId)===true;
    return '<details class="hem-calibration" data-calibration-id="'+escape(entry.entityId)+'" '+
      (opened?'open':'')+'><summary>'+escape(this._l65('calibration'))+' · PID</summary>'+content+'</details>';
  };
  // Read-only informational inputs: no actuator, occupancy or air-quality claim.
  const originalMetricHelp65=proto65._metricHelp;
  proto65._metricHelp = function(item) {
    if (item.metric!=='illuminance' && ['en','el','de'].includes(this._language()))
      return originalMetricHelp65.call(this,item);
    const note=item.metric==='illuminance'?this._l65('luxHelp'):
      this._metricName(item.metric)+'. '+this._l65('dataHelp');
    const limit=typeof item.threshold==='number' && Number.isFinite(item.threshold)
      ? ' '+this._t('limits')+': '+this._format(item.threshold)+' '+String(item.unit || '')+'.' : '';
    return note+limit;
  };
  const originalScienceHelp65=proto65._scienceHelp;
  proto65._scienceHelp = function(topic) {
    return ['en','el'].includes(this._language()) ? originalScienceHelp65.call(this,topic) : this._l65('estimateHelp');
  };
  const originalMetric65=proto65._metric;
  proto65._metric = function(item,miniature=false) {
    const html=originalMetric65.call(this,item,miniature);
    if (item.metric!=='illuminance' || miniature) return html;
    const label=this._hass?.states?.[item.entity_id]?.attributes?.friendly_name || item.name;
    return label ? html.replace(/<\/div>\s*$/, '<small class="hem-source">'+escape(label)+'</small></div>') : html;
  };
  const originalStyles65=proto65._styles;
  proto65._styles = function() { return originalStyles65.call(this)+`<style>
    .hem-device-data{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}
    .hem-device-data>div{padding:8px;border-radius:9px;background:var(--secondary-background-color,rgba(127,127,127,.09));min-width:0}
    .hem-device-data span{display:block;font-size:11px;color:var(--secondary-text-color);overflow-wrap:anywhere}
    .hem-device-data b{display:block;margin-top:4px;font-size:14px;overflow-wrap:anywhere}
    .hem-calibration,.hem-diagnostics{margin-top:12px;border-top:1px solid var(--divider-color,rgba(127,127,127,.25));padding-top:8px}
    .hem-calibration>summary,.hem-diagnostics>summary{cursor:pointer;padding:8px 0;font-weight:600}
    .hem-calibration:not([open])>*:not(summary),.hem-diagnostics:not([open])>*:not(summary){display:none}
    .hem-calibration[open]>summary{margin-bottom:10px}
    .hem-diagnostics code{display:block;overflow-wrap:anywhere;white-space:normal;font-size:11px;margin:8px 0;user-select:text}
    .hem-source{display:block;font-size:10px;opacity:.8;overflow-wrap:anywhere;margin-top:6px}
    .managed-controller{min-width:0}.managed-controller .climate-entity-link strong{overflow-wrap:anywhere}
    @media(max-width:340px){.hem-device-data{grid-template-columns:1fr}}
  </style>`; };
