  /* Persist user disclosure choices synchronously, before live HA renders. */
  const CARD66 = __CARD66__;
  const proto66 = AirQualityAdvisorCard.prototype;
  proto66._l66 = function(key) {return (CARD66[this._language()] || CARD66.en)[key] || CARD66.en[key] || '';};
  proto66._installInteractions66 = function() {
    if(this._interactions66) return;
    this._interactions66=true;
    this._detailsExpanded66=new Set();
    this._windowSwitchPending66=new Set();
    const identify=(node)=>{
      if(!node?.getAttribute) return null;
      const calibration=node.getAttribute('data-calibration-id');
      if(calibration) return [this._calibrationExpanded65,calibration];
      const id=node.getAttribute('data-detail-id');
      return id ? [this._detailsExpanded66,id] : null;
    };
    const setOpen=(node,open)=>{
      const item=identify(node);if(!item) return;
      const [set,key]=item;if(open)set.add(key);else set.delete(key);
    };
    this.shadowRoot.addEventListener('pointerdown',(e)=>{
      const summary=e.target.closest?.('summary');
      if(summary && identify(summary.parentElement)) {
        this._detailPointer66=true;clearTimeout(this._detailPointerTimer66);
        this._detailPointerTimer66=setTimeout(()=>release(),1000);
      }
    },true);
    const release=()=>{this._detailPointer66=false;clearTimeout(this._detailPointerTimer66);this._flushDeferredRenderSoon();};
    this.shadowRoot.addEventListener('pointerup',()=>setTimeout(release,0),true);
    this.shadowRoot.addEventListener('pointercancel',release,true);
    this.shadowRoot.addEventListener('click',(e)=>{
      const summary=e.target.closest?.('summary');
      const node=summary?.parentElement;
      if(summary && identify(node)) {
        e.preventDefault();e.stopPropagation();
        // Native toggle events are asynchronous. Store the intended choice
        // now so a concurrent state refresh cannot rebuild it as CLOSED.
        const open=!node.open;setOpen(node,open);node.open=open;
        release();return;
      }
      const button=e.target.closest?.('[data-window-policy-switch]');
      if(!button || !this._hass?.callService) return;
      e.preventDefault();e.stopPropagation();
      const area=button.dataset.controllerArea;
      const device=button.dataset.windowController;
      const id=button.dataset.windowPolicySwitch;
      const match=this._managedControllers(area).find(x=>x.entityId===device);
      const actual=match?.windowPolicyInfo;
      if(!actual || actual.id!==id || !['on','off'].includes(actual.state.state) ||
         this._windowSwitchPending66.has(id)) return;
      const action=actual.state.state==='on'?'turn_off':'turn_on';
      this._windowSwitchPending66.add(id);button.disabled=true;
      Promise.resolve().then(()=>this._hass.callService('switch',action,{entity_id:id}))
        .catch(()=>{this._climateEditError=this._climateLabels65().editFailed;})
        .finally(()=>{this._windowSwitchPending66.delete(id);this._render(true);});
    },true);
    this.shadowRoot.addEventListener('toggle',(e)=>{
      // Discard queued events belonging to a replaced DOM subtree.
      if(!e.target.isConnected || e.target.getRootNode()!==this.shadowRoot) return;
      setOpen(e.target,e.target.open);
    },true);
  };
  const originalDisconnect66=proto66.disconnectedCallback;
  proto66.disconnectedCallback=function(){this._detailPointer66=false;clearTimeout(this._detailPointerTimer66);return originalDisconnect66.call(this);};
  const originalRender66=proto66._render;
  proto66._render=function(force=false) {
    if(this._detailPointer66){this._pendingRender=true;this._pendingForceRender66 ||= force;return;}
    return originalRender66.call(this,force);
  };
  const originalStatus66=proto66._controllerStatusLabel;
  proto66._controllerStatusLabel=function(code) {
    const map={window_open_pause:'windowOpen',window_close_warmup:'windowWarmup',
      window_state_unknown:'windowUnknown',window_closed_ready:'windowReady',
      aqi_scale_unconfigured:'aqiSetup'};
    return map[code]?this._l66(map[code]):originalStatus66.call(this,code);
  };
  const originalManaged66=proto66._managedControllers;
  proto66._managedControllers=function(area) {
    const states=this._hass?.states || {};
    if(this._windowStates66!==states) {
      this._windowStates66=states;this._windowIndex66=new Map();
      for(const [id,state] of Object.entries(states)) {
        const a=state?.attributes;
        if(!id.startsWith('switch.') || a?.window_pause_role!=='policy' ||
           typeof a.area_id!=='string' || !Array.isArray(a.source_entity_ids) || !a.source_entity_ids.length) continue;
        const key=JSON.stringify([a.area_id,[...a.source_entity_ids].sort()]);
        this._windowIndex66.set(key,this._windowIndex66.has(key)?null:{id,state});
      }
    }
    return originalManaged66.call(this,area).map(entry=>({...entry,
      windowPolicyInfo:this._windowIndex66.get(JSON.stringify([area,
        [...entry.climate.attributes.source_entity_ids].sort()])) || null,
    }));
  };
  // Include configuration-switch-only changes and window timers in rendering.
  const originalSignature66=proto66._controllerSignature;
  proto66._controllerSignature=function() {
    return originalSignature66.call(this)+JSON.stringify(Object.entries(this._hass?.states || {})
      .filter(([id,s])=>s?.attributes?.window_pause_role==='policy' ||
        (id.startsWith('sensor.') && s?.attributes?.window_policy))
      .map(([id,s])=>[id,s.state,s.attributes.window_policy,s.attributes.source_entity_ids]));
  };
  proto66._detail66=function(key,title,content,cls='hem-diagnostics') {
    const opened=this._detailsExpanded66?.has(key)===true;
    return '<details class="'+escape(cls)+'" data-detail-id="'+escape(key)+'" '+(opened?'open':'')+
      '><summary>'+escape(title)+'</summary>'+content+'</details>';
  };
  const originalSummary66=proto66._deviceSummary65;
  proto66._deviceSummary65=function(entry) {
    this._installInteractions66();
    const previous=originalSummary66.call(this,entry);
    const marker=previous.indexOf('<details class="hem-diagnostics">');
    const base=marker<0?previous:previous.slice(0,marker);
    const a=entry.climate.attributes || {}, d=entry.statusInfo?.state?.attributes || {};
    const c=a.controller_status || {}, id=entry.entityId;
    const states=this._hass?.states || {};
    const friendly=entity=>states[entity]?.attributes?.friendly_name || entity;
    const row=(label,value)=>'<div><dt>'+escape(label)+'</dt><dd>'+escape(value)+'</dd></div>';
    const status=d.status_code || c.status || entry.climate.state;
    const reason=d.status_reason_code || c.reason;
    const sources=safeArray(a.source_entity_ids);
    const supply=d.upstream_power_switch || a.upstream_power_switch;
    let diagnostics=row(this._l66('controller'),a.friendly_name || friendly(id));
    diagnostics+=sources.map(entity=>row(this._l66('source'),friendly(entity))).join('');
    diagnostics+=row(this._l66('status'),this._controllerStatusLabel(status));
    if(reason && reason!==status)diagnostics+=row(this._l65('reason'),this._controllerStatusLabel(reason));
    if(supply)diagnostics+=row(this._l65('supply'),friendly(supply));
    const raw=[id,...sources,supply].filter(Boolean).map(escape).join('<br>');
    diagnostics='<dl class="hem-diagnostic-data66">'+diagnostics+'</dl>'+
      this._detail66('raw:'+id,this._l66('rawDetails'),'<code>'+raw+'</code>','hem-technical66');
    const info=entry.windowPolicyInfo, w=d.window_policy || {};
    let toggle='';
    if(info) {
      const on=info.state.state==='on';
      const disabled=!['on','off'].includes(info.state.state) || this._windowSwitchPending66.has(info.id);
      toggle='<div class="hem-window-policy66"><button type="button" role="switch" aria-checked="'+on+
        '" aria-label="'+escape(this._l66('windowSwitch'))+'" title="'+escape(this._l66('windowHelp'))+
        '" data-window-policy-switch="'+escape(info.id)+'" data-window-controller="'+escape(id)+
        '" data-controller-area="'+escape(a.area_id)+'" '+(disabled?'disabled':'')+'>'+
        this._icon('mdi:window-open-variant')+'<span>'+escape(this._l66('windowSwitch'))+'</span><b>'+
        escape(this._controllerStatusLabel(info.state.state))+'</b></button><small>'+escape(this._l66('windowHelp'))+'</small>';
      if(on && w.blocked) {
        const remain=typeof w.closed_since==='number' && typeof w.resume_delay_seconds==='number'
          ? Math.max(0,w.resume_delay_seconds-(Date.now()/1000-w.closed_since)):w.remaining_seconds;
        toggle+='<small class="hem-window-hold66">'+escape(this._controllerStatusLabel(w.status))+
          (typeof remain==='number' && remain>0?' · '+escape(this._format(remain,0))+' s':'')+'</small>';
      }
      toggle+='</div>';
    }
    return base+toggle+this._detail66('diagnostics:'+id,this._l65('details'),diagnostics);
  };
  proto66._roomHumidity66=function(room) {
    const p=room?.environment?.climate_plan || {};
    let rh=p.equipment_plan?.humidity?.measured_rh;
    if(typeof rh!=='number' || !Number.isFinite(rh) || rh<=0 || rh>100) {
      const readings=safeArray(room.readings).filter(r=>r.metric==='humidity' &&
        r.available!==false && typeof r.value==='number' && Number.isFinite(r.value) && r.value>0 && r.value<=100);
      rh=readings.length?readings.reduce((n,r)=>n+r.value,0)/readings.length:null;
    }
    return '<span class="hem-room-humidity66">'+escape(this._t('humidity'))+': <b>'+
      (typeof rh==='number' && Number.isFinite(rh)?escape(this._format(rh))+' %':escape(this._t('missing')))+'</b></span>';
  };
  const originalClimate66=proto66._climatePanel;
  proto66._climatePanel=function(room){this._installInteractions66();return originalClimate66.call(this,room);};
  const originalBlocker66=proto66._outsideBlocker;
  proto66._outsideBlocker=function(reason) {
    if(reason.code==='aqi_scale_unconfigured') {
      return '<span class="reason hem-aqi-setup66">'+this._icon('mdi:information-outline')+
        escape(this._l66('aqiSetup'))+(reason.label?' · '+escape(reason.label):'')+'</span>'+
        '<small class="hem-outside-help66">'+escape(this._l66('aqiHelp'))+'</small>';
    }
    return originalBlocker66.call(this,reason);
  };
  const originalOutside66=proto66._outside;
  proto66._outside=function(outdoor) {
    let html=originalOutside66.call(this,outdoor);
    if(outdoor.status!=='unknown') return html;
    const blockers=safeArray(outdoor.blockers);
    const weather=safeArray(outdoor.weather).some(w=>!!w.condition);
    const missingWeather=blockers.some(b=>['no_weather_data','unavailable_weather'].includes(b.code));
    const aqi=blockers.some(b=>b.code==='aqi_scale_unconfigured');
    const label=missingWeather?this._t('unavailableWeather'):aqi?this._l66('aqiSetup'):
      weather?this._l66('outsideIncomplete'):this._t('missingOutside');
    return html.replace('<div class="outside-title">'+escape(this._t('missingOutside'))+'</div>',
      '<div class="outside-title">'+escape(label)+'</div>');
  };
  const originalStyles66=proto66._styles;
  proto66._styles=function(){return originalStyles66.call(this)+`<style>
    .hem-room-readings66{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}
    .hem-room-readings66>span{display:flex;flex-direction:column;gap:5px;font-size:13px;padding:10px;border-radius:10px;background:var(--secondary-background-color,rgba(127,127,127,.08));overflow-wrap:anywhere}
    .hem-room-readings66 b{font-size:19px;color:var(--primary-text-color)}
    .hem-window-policy66{margin-top:12px}.hem-window-policy66>button{width:100%;display:flex;align-items:center;gap:9px;padding:10px;border:1px solid var(--divider-color);border-radius:10px;background:transparent;color:inherit;font:inherit;text-align:start;cursor:pointer}
    .hem-window-policy66>button[aria-checked=true]{border-color:var(--primary-color,#03a9f4)}
    .hem-window-policy66>button span{flex:1}.hem-window-policy66 small,.hem-outside-help66{display:block;margin-top:5px;color:var(--secondary-text-color);font-size:12px;overflow-wrap:anywhere}
    .hem-diagnostic-data66{margin:8px 0;font-size:12px}.hem-diagnostic-data66>div{margin:7px 0;overflow-wrap:anywhere}
    .hem-diagnostic-data66 dt{color:var(--secondary-text-color)}.hem-diagnostic-data66 dd{margin:3px 0;font-weight:500}
    .hem-technical66{margin-top:10px}.hem-technical66>summary{cursor:pointer;font-size:12px;padding:5px 0}.hem-technical66 code{font-size:11px}
    .hem-outside-help66{flex-basis:100%}.hem-aqi-setup66{white-space:normal}
    @media(max-width:340px){.hem-room-readings66{grid-template-columns:1fr}}
  </style>`;};
