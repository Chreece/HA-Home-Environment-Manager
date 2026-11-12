  /* HEM_SETTINGS_AUTOSAVE_B7_START
   * Edits are drafts until HA confirms them. Never write into hass.states.
   * One entry-scoped queue orders native writes and fresh Options transactions.
   * Requests retain exact owner/device/connection identity across every await.
   */
  const settingsCopy={
    en:{saving:"Saving…",confirming:"Waiting for confirmation…",saved:"Saved",invalid:"Check the value and its allowed range.",failed:"Not saved. Your edited value is retained.",unconfirmed:"Not confirmed. Reported value:",retry:"Retry",changed:"The settings owner or connection changed. Reopen this menu."},
    el:{saving:"Αποθήκευση…",confirming:"Αναμονή επιβεβαίωσης…",saved:"Αποθηκεύτηκε",invalid:"Έλεγξε την τιμή και τα επιτρεπόμενα όριά της.",failed:"Δεν αποθηκεύτηκε. Η τιμή που έγραψες διατηρήθηκε.",unconfirmed:"Δεν επιβεβαιώθηκε. Αναφερόμενη τιμή:",retry:"Επανάληψη",changed:"Άλλαξε η σύνδεση ή ο κάτοχος των ρυθμίσεων. Άνοιξε ξανά το μενού."},
    de:{saving:"Wird gespeichert…",confirming:"Bestätigung wird erwartet…",saved:"Gespeichert",invalid:"Wert und zulässigen Bereich prüfen.",failed:"Nicht gespeichert. Der bearbeitete Wert bleibt erhalten.",unconfirmed:"Nicht bestätigt. Gemeldeter Wert:",retry:"Erneut versuchen",changed:"Verbindung oder Einstellungszuordnung geändert. Menü erneut öffnen."}
  };
  const settingsDescriptions={
    en:{weather:"Outdoor sensors, weather and warning sources.",targets:"Sensor readings, comfort targets and air-quality limits.",mode:"Equipment, operating modes, targets and fan settings.",pid:"Controller gains, learning and calibration.",presence:"Presence sources, sleep schedules and arrival policies.",ventilation:"Window and door contacts, ventilation and shading.",power:"Power supply, minimum and maximum run times, and protection.",alerts:"Notification choices, delivery and device-error reporting.",fan:"Fan speed, airflow and quiet operation.",other:"Additional controls for this device."},
    el:{weather:"Εξωτερικοί αισθητήρες, καιρός και πηγές προειδοποιήσεων.",targets:"Μετρήσεις αισθητήρων, στόχοι άνεσης και όρια ποιότητας αέρα.",mode:"Συσκευές, τρόποι λειτουργίας, στόχοι και ρυθμίσεις ανεμιστήρων.",pid:"Συντελεστές ελεγκτή, εκμάθηση και βαθμονόμηση.",presence:"Πηγές παρουσίας, πρόγραμμα ύπνου και πολιτικές άφιξης.",ventilation:"Επαφές παραθύρων και θυρών, αερισμός και σκίαση.",power:"Τροφοδοσία, ελάχιστοι και μέγιστοι χρόνοι λειτουργίας και προστασία.",alerts:"Επιλογές ειδοποιήσεων, παράδοση και αναφορά σφαλμάτων συσκευών.",fan:"Ταχύτητα ανεμιστήρων, ροή αέρα και αθόρυβη λειτουργία.",other:"Πρόσθετοι έλεγχοι αυτής της συσκευής."},
    de:{weather:"Außensensoren, Wetter und Warnungsquellen.",targets:"Sensormessungen, Komfortziele und Luftqualitätsgrenzen.",mode:"Geräte, Betriebsarten, Sollwerte und Lüftereinstellungen.",pid:"Reglerparameter, Lernen und Kalibrierung.",presence:"Anwesenheitsquellen, Schlafzeiten und Ankunftsregeln.",ventilation:"Fenster- und Türkontakte, Lüftung und Beschattung.",power:"Stromversorgung, minimale und maximale Laufzeiten und Schutz.",alerts:"Benachrichtigungen, Zustellung und Gerätestörungen.",fan:"Lüftergeschwindigkeit, Luftstrom und leiser Betrieb.",other:"Weitere Bedienelemente dieses Geräts."}
  };
  function settingsDescription(card,scope,key){
    const words=settingsDescriptions[card._language()]||settingsDescriptions.en;
    return words[key]||words.other;
  }
  const settingsText=(card,key)=>(settingsCopy[card._language()]||settingsCopy.en)[key];
  const settingsClone=value=>JSON.parse(JSON.stringify(value));
  const settingsEqual=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const settingsFlow=id=>'config/config_entries/options/flow/'+encodeURIComponent(id);
  const settingsDialog=(card,scope)=>scope==="home"?card._homeSettingsDialog128:
    scope==="room"?card._roomSettingsDialog114:card._hemControllerDialog126;
  const settingsProto=AirQualityAdvisorCard.prototype;

  settingsProto._settingsQueue=function(key,work){
    this._settingsQueues ||= new Map();
    const previous=this._settingsQueues.get(key)||Promise.resolve();
    const task=previous.catch(()=>{}).then(work);
    const tail=task.catch(()=>{});
    this._settingsQueues.set(key,tail);
    tail.finally(()=>{if(this._settingsQueues.get(key)===tail)this._settingsQueues.delete(key);});
    return task;
  };
  settingsProto._settingsActive=function(saved,scope){
    return saved&&!saved.settingsClosed&&saved.connection===this._hass?.connection&&
      this._hemFullContext127(saved,scope);
  };
  const settingsValue=(field,value)=>field.domain==="number"?Number(value):
    field.domain==="time"?String(value).slice(0,5):String(value);
  settingsProto._settingsNativeValue=function(saved,scope,id){
    const field=this._hemFullFields127(saved,scope).find(item=>item.id===id);
    return field?.state?settingsValue(field,field.state.state):undefined;
  };
  settingsProto._settingsNativeFeedback=function(saved,scope){
    if(!saved?.nativeEdits)return;
    for(const row of saved.node.querySelectorAll('[data-hem-full-row127]')){
      const id=row.getAttribute('data-hem-full-row127'),edit=saved.nativeEdits.get(id);
      if(!edit)continue;
      if(edit.phase==="confirming"&&this._settingsNativeValue(saved,scope,id)===edit.value){
        edit.phase="saved";clearTimeout(edit.confirmTimer);
      }
      const status=row.querySelector('[data-hem-full-status127]');
      if(!status)continue;
      const bad=["failed","unconfirmed","invalid"].includes(edit.phase);
      const text=edit.phase==="unconfirmed"?settingsText(this,"unconfirmed")+" "+
        String(this._settingsNativeValue(saved,scope,id)??"—"):
        settingsText(this,edit.phase==="queued"?"saving":edit.phase);
      status.textContent=text||"";status.setAttribute('role',bad?'alert':'status');
      status.classList.toggle('hem-room-options-error114',bad);
      row.setAttribute('aria-busy',String(edit.running||edit.phase==="confirming"));
      const toggle=row.querySelector('[data-hem-full-apply127]');
      if(toggle&&edit.domain==="switch"&&edit.valid&&edit.phase!=="saved"){
        toggle.textContent=this._quickState8?.(edit.value)||edit.value;
        toggle.setAttribute('aria-pressed',String(edit.value==="on"));
      }
      const input=row.querySelector('[data-hem-full-value127]');
      if(input){
        input.setAttribute('aria-invalid',String(edit.phase==="invalid"));
        if(edit.phase!=="saved"&&input!==_roomOptionsDeepFocus114()&&edit.raw!==undefined)
          input.value=edit.raw;
      }
      row.querySelector('[data-settings-retry]')?.remove();
      if(edit.phase==="failed"||edit.phase==="unconfirmed"){
        const retry=document.createElement('button');retry.type='button';
        retry.setAttribute('data-settings-retry',id);retry.textContent=settingsText(this,"retry");
        retry.addEventListener('click',()=>{
          edit.dirty=true;edit.revision++;edit.phase="queued";
          this._settingsNativeSend(saved,scope,id);
        });
        status.append(' ',retry);
      }
    }
  };
  const settingsRowBefore=settingsProto._hemFullRow127;
  settingsProto._hemFullRow127=function(field,scope){
    const saved=settingsDialog(this,scope),edit=saved?.nativeEdits?.get(field.id);
    if(edit&&edit.phase!=="saved"&&edit.valid&&field.state&&
       !["unknown","unavailable"].includes(field.state.state)){
      field={...field,state:{...field.state,state:String(edit.value)}};
    }
    return settingsRowBefore.call(this,field,scope);
  };
  settingsProto._settingsNativeEdit=function(saved,scope,element,immediate=false){
    if(!this._settingsActive(saved,scope)||element.disabled)return;
    const row=element.closest('[data-hem-full-row127]');
    const id=row?.getAttribute('data-hem-full-row127');
    if(row?.getAttribute('data-hem-full-scope127')!==scope)return;
    const field=this._hemFullFields127(saved,scope).find(item=>item.id===id);
    if(!field||field.disabled||!field.state||["unknown","unavailable"].includes(field.state.state))return;
    saved.nativeEdits ||= new Map();
    const previous=saved.nativeEdits.get(id),attr=field.state.attributes||{};
    const input=row.querySelector('[data-hem-full-value127]');
    let value,raw,valid=false;
    if(field.domain==="switch"){
      const shown=previous&&previous.phase!=="saved"?previous.value:field.state.state;
      if(!["on","off"].includes(shown))return;
      value=shown==="on"?"off":"on";raw=value;valid=true;
    }else if(field.domain==="number"){
      raw=input?.value;value=Number(raw);
      valid=Boolean(raw?.trim()&&input.checkValidity()&&Number.isFinite(value)&&
        Number.isFinite(Number(attr.min))&&Number.isFinite(Number(attr.max))&&
        value>=Number(attr.min)&&value<=Number(attr.max));
    }else if(field.domain==="select"){
      raw=value=input?.value;valid=Array.isArray(attr.options)&&attr.options.includes(value);
    }else if(field.domain==="time"){
      raw=value=input?.value;valid=Boolean(input?.checkValidity()&&/^\d{2}:\d{2}$/.test(value)&&
        Number(value.slice(0,2))<24&&Number(value.slice(3))<60);
    }else return;
    if(previous&&previous.raw===raw&&previous.valid===valid&&
       !["failed","unconfirmed","invalid"].includes(previous.phase)){
      if(immediate&&previous.dirty){clearTimeout(previous.timer);this._settingsNativeSend(saved,scope,id);}
      return;
    }
    if(!previous&&valid&&settingsValue(field,field.state.state)===value)return;
    const edit=previous||{revision:0,running:false};
    clearTimeout(edit.timer);clearTimeout(edit.confirmTimer);
    Object.assign(edit,{value,raw,valid,dirty:valid,revision:edit.revision+1,
      phase:valid?"queued":"invalid",domain:field.domain,
      identity:[field.reg?.device_id,field.reg?.config_entry_id,field.reg?.unique_id||null]});
    saved.nativeEdits.set(id,edit);
    this._settingsNativeFeedback(saved,scope);
    if(!valid)return;
    if(immediate||field.domain==="switch"||field.domain==="select")this._settingsNativeSend(saved,scope,id);
    else edit.timer=setTimeout(()=>this._settingsNativeSend(saved,scope,id),450);
  };
  settingsProto._settingsNativeSend=function(saved,scope,id){
    const edit=saved.nativeEdits?.get(id);
    if(!edit||edit.running||!edit.dirty||!edit.valid)return;
    clearTimeout(edit.timer);edit.running=true;
    this._settingsQueue(saved.entryId,async()=>{
      if(!this._settingsActive(saved,scope)){edit.dirty=false;return;}
      // Read the newest draft only when this entry's earlier write has finished.
      const field=this._hemFullFields127(saved,scope).find(item=>item.id===id);
      if(!field||field.disabled||!field.state||["unknown","unavailable"].includes(field.state.state))
        throw Error("Setting unavailable");
      if(!settingsEqual(edit.identity,[field.reg?.device_id,field.reg?.config_entry_id,field.reg?.unique_id||null]))
        throw Error("Setting identity changed");
      const value=edit.value,revision=edit.revision;
      if(!edit.valid){edit.dirty=false;return;}
      const a=field.state.attributes||{},data={entity_id:id};let action;
      if(field.domain==="number"){
        const step=Number(a.step??1),offset=(value-Number(a.min))/step;
        if(!Number.isFinite(value)||!Number.isFinite(offset)||step<=0||
           value<Number(a.min)||value>Number(a.max)||Math.abs(offset-Math.round(offset))>1e-7)
          throw Error("Invalid numeric setting");
        action="set_value";data.value=value;
      }else if(field.domain==="select"){
        if(!Array.isArray(a.options)||!a.options.includes(value))throw Error("Option removed");
        action="select_option";data.option=value;
      }else if(field.domain==="time"){
        if(!/^\d{2}:\d{2}$/.test(value))throw Error("Invalid time");
        action="set_value";data.time=value+":00";
      }else if(field.domain==="switch"){
        if(!["on","off"].includes(value))throw Error("Invalid switch setting");
        action=value==="on"?"turn_on":"turn_off";
      }else throw Error("Unsupported setting");
      edit.dirty=false;edit.phase="saving";this._settingsNativeFeedback(saved,scope);
      try{
        await this._hass.callService(field.domain,action,data);
        if(edit.revision!==revision)return;
        edit.phase="confirming";
        if(this._settingsActive(saved,scope)){
          this._settingsNativeFeedback(saved,scope);
          edit.confirmTimer=setTimeout(()=>{
            if(this._settingsActive(saved,scope)&&edit.revision===revision&&edit.phase==="confirming"){
              edit.phase="unconfirmed";this._settingsNativeFeedback(saved,scope);
            }
          },15000);
        }
      }catch(error){
        if(edit.revision===revision)edit.phase="failed";
      }
    }).catch(()=>{edit.phase="failed";edit.dirty=false;}).finally(()=>{
      edit.running=false;
      if(this._settingsActive(saved,scope)){
        this._settingsNativeFeedback(saved,scope);
        if(edit.dirty&&edit.valid)this._settingsNativeSend(saved,scope,id);
      }
    });
  };
  const settingsApplyBefore=settingsProto._hemFullApply127;
  settingsProto._hemFullApply127=function(saved,scope,button){
    const id=button.getAttribute('data-hem-full-apply127');
    if(id?.startsWith('button.'))return settingsApplyBefore.call(this,saved,scope,button);
    this._settingsNativeEdit(saved,scope,button,true);
  };
  settingsProto._settingsBind=function(saved,scope){
    if(!saved||saved.settingsBound)return;
    saved.settingsBound=true;
    saved.node.querySelector('[data-room-options-save114],[data-hem-home-save128]')?.remove();
    saved.node.addEventListener('input',event=>{
      const input=event.target?.closest?.('[data-hem-full-value127]');
      if(input)this._settingsNativeEdit(saved,scope,input,false);
    });
    saved.node.addEventListener('change',event=>{
      const input=event.target?.closest?.('[data-hem-full-value127]');
      if(input)this._settingsNativeEdit(saved,scope,input,true);
      if(scope==="home"&&event.target?.closest?.('[data-hem-home-input128]')){
        clearTimeout(saved.optionsAutosave?.timer);this._settingsSaveOptions(saved,scope);
      }
    });
    saved.node.addEventListener('keydown',event=>{
      if(event.key!=="Enter")return;
      const input=event.target?.closest?.('[data-hem-full-value127]');
      if(input){event.preventDefault();this._settingsNativeEdit(saved,scope,input,true);}
    });
  };
  const settingsRenderBefore=settingsProto._hemFullRender127;
  settingsProto._hemFullRender127=function(saved,scope){
    this._settingsBind(saved,scope);
    // Confirm before rendering so a matching state removes only its own draft.
    this._settingsNativeFeedback(saved,scope);
    const result=settingsRenderBefore.call(this,saved,scope);
    this._settingsNativeFeedback(saved,scope);
    return result;
  };

  const settingsRoomRefreshBefore=settingsProto._refreshRoomSettings114;
  settingsProto._refreshRoomSettings114=function(){
    const result=settingsRoomRefreshBefore.call(this);
    const saved=this._roomSettingsDialog114;
    if(saved)this._hemFullRender127(saved,"room");
    return result;
  };

  // Options forms save changed fields over a fresh server form, not an old
  // whole-dialog snapshot. The dialog and its focus stay in place after saving.
  settingsProto._settingsOptionsStatus=function(saved,scope,message,error=false){
    if(!this._settingsActive(saved,scope))return;
    if(scope==="home")this._homeStatus128(saved,message,error);
    else this._roomSettingsStatus114(saved,message,error);
  };
  settingsProto._settingsOptionsEdit=function(saved,scope,name,value,delay=0){
    if(!this._settingsActive(saved,scope))return;
    saved.optionsAutosave ||= {dirty:new Map(),revision:0,running:false};
    const state=saved.optionsAutosave;
    const previous=state.dirty.get(name);
    if(previous&&settingsEqual(previous.value,value))return;
    state.dirty.set(name,{value:settingsClone(value),revision:++state.revision});
    state.blocked=false;clearTimeout(state.timer);
    this._settingsOptionsStatus(saved,scope,settingsText(this,"saving"));
    if(delay)state.timer=setTimeout(()=>this._settingsSaveOptions(saved,scope),delay);
    else this._settingsSaveOptions(saved,scope);
  };
  settingsProto._settingsSaveOptions=function(saved,scope){
    const state=saved.optionsAutosave;
    if(!state||state.running||state.blocked||!state.dirty.size||!this._settingsActive(saved,scope))return;
    clearTimeout(state.timer);state.running=true;
    this._settingsQueue(saved.entryId,async()=>{
      if(!this._settingsActive(saved,scope))return;
      const patch=new Map(state.dirty);let flow=null,posted=false;
      const active=()=>{if(!this._settingsActive(saved,scope))throw Error("Context changed");};
      try{
        // Dispose the read-only initial form before creating a short transaction.
        if(saved.flowId&&!saved.cleanupStarted){await _roomOptionsCleanup114(saved);active();}
        const menu=await saved.api('POST','config/config_entries/options/flow',{handler:saved.entryId});
        flow=menu?.flow_id;active();
        const step=scope==="home"?'general_settings':'edit_room_'+saved.area;
        const options=Array.isArray(menu?.menu_options)?menu.menu_options:Object.keys(menu?.menu_options||{});
        if(menu?.type!=="menu"||typeof flow!=="string"||!/^[A-Za-z0-9_-]{1,128}$/.test(flow)||
           !options.includes(step)||(menu.handler!==undefined&&menu.handler!==saved.entryId))throw Error("Invalid menu");
        const form=await saved.api('POST',settingsFlow(flow),{next_step_id:step});active();
        if(form?.type!=="form"||form.flow_id!==flow||
           form.step_id!==(scope==="home"?'setup_general':'edit_room')||
           (form.handler!==undefined&&form.handler!==saved.entryId)||!Array.isArray(form.data_schema))throw Error("Invalid form");
        const fields=scope==="room"?_roomOptionsFields114(form):form.data_schema;
        const names=new Set(),values={};
        for(const record of fields){
          const schema=scope==="room"?record.schema:record,name=schema.name;
          if(typeof name!=="string"||names.has(name))throw Error("Invalid field");names.add(name);
          const kind=scope==="room"?'select':homeType128(schema);
          if(!kind)throw Error("Unsupported field");
          const prior=schema.default??schema.description?.suggested_value??
            (schema.selector?.select?.multiple?[]:kind==="boolean"?false:null);
          const value=patch.has(name)?patch.get(name).value:prior;
          if(kind==="select"){
            const allowed=homeOptions128(schema).map(item=>item.value);
            const multiple=schema.selector.select.multiple===true;
            const list=multiple?value:[value],old=multiple?prior:[prior];
            if(!Array.isArray(list)||list.some(item=>typeof item!=="string"||
               (!allowed.includes(item)&&!(Array.isArray(old)&&old.includes(item)))))throw Error("Invalid selection");
          }else if(kind==="number"){
            const bounds=schema.selector.number||{};
            if(typeof value!=="number"||!Number.isFinite(value)||
               (bounds.min!==undefined&&value<bounds.min)||(bounds.max!==undefined&&value>bounds.max))throw Error("Invalid value");
          }else if(kind==="boolean"&&typeof value!=="boolean")throw Error("Invalid boolean");
          else if(kind==="text"&&value!==null&&typeof value!=="string")throw Error("Invalid text");
          values[name]=settingsClone(value);
        }
        if([...patch.keys()].some(name=>!names.has(name)))throw Error("Setting removed");
        active();posted=true;
        const result=await saved.api('POST',settingsFlow(flow),values);
        if(result?.flow_id!==flow)throw Error("Wrong save response");
        if(result.type!=="create_entry"){
          if(this._settingsActive(saved,scope)&&result.type==="form"){
            for(const [name,error] of Object.entries(result.errors||{})){
              if(scope==="room")this._roomSettingsFieldError114(saved,name,_roomOptionsError114(this,error,result));
            }
          }
          throw Error("Settings rejected");
        }
        flow=null;
        for(const [name,sent] of patch){
          if(state.dirty.get(name)?.revision===sent.revision)state.dirty.delete(name);
        }
        if(this._settingsActive(saved,scope)){
          this._settingsOptionsStatus(saved,scope,settingsText(this,state.dirty.size?"saving":"saved"));
          this._hemFullLoad127(saved,scope);
        }
      }catch(error){
        state.blocked=true;
        this._settingsOptionsStatus(saved,scope,settingsText(this,"failed"),true);
        if(this._settingsActive(saved,scope)){
          const target=saved.node.querySelector(scope==="home"?'[data-hem-home-status128]':'[data-room-options-status114]');
          const retry=document.createElement('button');retry.type='button';retry.textContent=settingsText(this,"retry");
          retry.addEventListener('click',()=>{state.blocked=false;this._settingsSaveOptions(saved,scope);});
          target?.append(' ',retry);
        }
      }finally{
        if(flow&&/^[A-Za-z0-9_-]{1,128}$/.test(flow)){
          try{await saved.api('DELETE',settingsFlow(flow));}catch{}
        }
      }
    }).finally(()=>{
      state.running=false;
      if(!state.blocked&&state.dirty.size&&this._settingsActive(saved,scope))this._settingsSaveOptions(saved,scope);
    });
  };
  const settingsRoomSelectionBefore=settingsProto._roomSettingsSelection114;
  settingsProto._roomSettingsSelection114=function(saved,name,values){
    const old=JSON.stringify(saved.draft?.[name]);
    const result=settingsRoomSelectionBefore.call(this,saved,name,values);
    if(old!==JSON.stringify(saved.draft?.[name])&&!saved.clientErrors?.has(name))
      this._settingsOptionsEdit(saved,"room",name,saved.draft[name]);
    return result;
  };
  const settingsHomeChangeBefore=settingsProto._homeValueChanged128;
  settingsProto._homeValueChanged128=function(saved,input){
    const name=input.getAttribute('data-hem-home-input128'),old=JSON.stringify(saved.draft?.[name]);
    const result=settingsHomeChangeBefore.call(this,saved,input);
    const field=saved.fields?.find(item=>item.name===name);
    if(!input.checkValidity()||(field?.kind==="number"&&!Number.isFinite(saved.draft[name]))){
      if(saved.optionsAutosave){
        clearTimeout(saved.optionsAutosave.timer);
        saved.optionsAutosave.dirty.delete(name);
        if(saved.optionsAutosave.dirty.size)this._settingsSaveOptions(saved,"home");
      }
      this._settingsOptionsStatus(saved,"home",settingsText(this,"invalid"),true);return result;
    }
    if(old!==JSON.stringify(saved.draft?.[name]))
      this._settingsOptionsEdit(saved,"home",name,saved.draft[name],
        ["number","text"].includes(field?.kind)?450:0);
    return result;
  };
  // Old programmatic entry points now flush drafts; they no longer finish and
  // erase the visible form. Button entities (calibrate/resume/reset) remain explicit.
  settingsProto._submitRoomSettings114=function(saved){this._settingsSaveOptions(saved,"room");};
  settingsProto._saveHomeGeneral128=function(saved){this._settingsSaveOptions(saved,"home");};

  // Floors use native registry writes; update only the edited property or Area.
  settingsProto._settingsRefreshFloor=function(saved){
    const ctx=this._floorContext140(saved.id);
    if(!ctx||saved.connection!==this._hass?.connection){this._floorClose140(false);return;}
    saved.floor=ctx.floor;saved.areas=ctx.areas;
    const pending=saved.floorEdits||new Map();
    for(const [key,selector] of [['name','[data-floor-name140]'],['level','[data-floor-level140]'],['icon','[data-floor-icon140]']]){
      const input=saved.node.querySelector(selector);
      if(input&&!pending.has(key)&&input!==_roomOptionsDeepFocus114())input.value=ctx.floor[key]??"";
    }
    for(const input of saved.node.querySelectorAll('[data-floor-area140]')){
      const id=input.getAttribute('data-floor-area140');
      if(!pending.has('area:'+id))input.checked=ctx.areas.some(area=>area.area_id===id&&area.floor_id===saved.id);
    }
  };
  settingsProto._settingsFloorEdit=function(saved,input,immediate=false){
    if(this._floorDialog140!==saved||!this.isConnected||this._hass?.user?.is_admin!==true||
       saved.connection!==this._hass.connection||input.disabled)return;
    let key,value;
    if(input.hasAttribute('data-floor-area140')){key='area:'+input.getAttribute('data-floor-area140');value=input.checked;}
    else if(input.hasAttribute('data-floor-name140')){key='name';value=input.value.trim();}
    else if(input.hasAttribute('data-floor-level140')){key='level';value=input.value.trim()===''?null:Number(input.value);}
    else if(input.hasAttribute('data-floor-icon140')){key='icon';value=input.value.trim()||null;}
    else return;
    const status=saved.node.querySelector('[data-floor-status140]');
    const valid=input.checkValidity()&&(key!=='name'||value&&value.length<=100)&&
      (key!=='level'||value===null||Number.isSafeInteger(value)&&Math.abs(value)<=100)&&
      (key!=='icon'||value===null||/^mdi:[a-z0-9-]{1,90}$/.test(value));
    saved.floorEdits ||= new Map();
    if(!saved.floorEdits.has(key)){
      const prior=key.startsWith('area:')?saved.areas.some(area=>area.area_id===key.slice(5)&&area.floor_id===saved.id):
        (saved.floor[key]??null);
      if(valid&&prior===value)return;
    }
    if(!valid){
      const pending=saved.floorEdits.get(key)||{revision:0};
      clearTimeout(pending.timer);pending.invalid=true;pending.dirty=false;
      saved.floorEdits.set(key,pending);
      status.textContent=this._floorWords140().invalid;status.setAttribute('role','alert');return;
    }
    const edit=saved.floorEdits.get(key)||{revision:0};clearTimeout(edit.timer);
    if(edit.value!==value||edit.invalid){edit.value=value;edit.revision++;edit.dirty=true;edit.invalid=false;}
    saved.floorEdits.set(key,edit);
    status.textContent=settingsText(this,"saving");status.setAttribute('role','status');
    const send=()=>{
      if(edit.running||!edit.dirty||edit.invalid)return;
      edit.running=true;
      this._settingsQueue('floor:'+saved.id,async()=>{
        const active=()=>this._floorDialog140===saved&&saved.connection===this._hass?.connection&&
          this.isConnected&&this._hass?.user?.is_admin===true;
        if(!active()){edit.dirty=false;return;}
        const call=this._hass.callWS.bind(this._hass);
        const [floors,areas]=await Promise.all([call({type:'config/floor_registry/list'}),call({type:'config/area_registry/list'})]);
        if(!active())return;
        if(!Array.isArray(floors)||!Array.isArray(areas)||!floors.some(f=>f.floor_id===saved.id))throw Error('Floor changed');
        const value=edit.value,revision=edit.revision;edit.dirty=false;
        if(edit.invalid)return;
        if(key.startsWith('area:')){
          const id=key.slice(5),area=areas.find(a=>(a.area_id||a.id)===id);
          if(!area||!this._floorContext140(saved.id)?.areas.some(a=>a.area_id===id))throw Error('Area changed');
          if(value||area.floor_id===saved.id)
            await call({type:'config/area_registry/update',area_id:id,floor_id:value?saved.id:null});
        }else await call({type:'config/floor_registry/update',floor_id:saved.id,[key]:value});
        if(active()&&edit.revision===revision){
          if(key.startsWith('area:'))saved.areas=saved.areas.map(area=>area.area_id===key.slice(5)?
            {...area,floor_id:value?saved.id:null}:area);
          else saved.floor={...saved.floor,[key]:value};
          saved.floorEdits.delete(key);status.textContent=settingsText(this,"saved");
        }
        if(active())this._floorFetch140(true);
      }).catch(()=>{
        edit.dirty=false;
        if(this._floorDialog140===saved){
          status.textContent=settingsText(this,"failed");status.setAttribute('role','alert');
          const retry=document.createElement('button');retry.type='button';retry.textContent=settingsText(this,"retry");
          retry.onclick=()=>{edit.dirty=true;send();};status.append(' ',retry);
        }
      }).finally(()=>{edit.running=false;if(edit.dirty&&!edit.invalid&&this._floorDialog140===saved)send();});
    };
    if(immediate||key.startsWith('area:'))send();else edit.timer=setTimeout(send,450);
  };
  const settingsFloorOpenBefore=settingsProto._floorOpen140;
  settingsProto._floorOpen140=function(id){
    const result=settingsFloorOpenBefore.call(this,id),saved=this._floorDialog140;
    if(!result||!saved)return result;
    saved.node.querySelector('[data-floor-save140]')?.remove();
    const selector='[data-floor-name140],[data-floor-level140],[data-floor-icon140],[data-floor-area140]';
    saved.node.addEventListener('input',event=>{
      const input=event.target.closest?.(selector);if(input)this._settingsFloorEdit(saved,input);
    });
    saved.node.addEventListener('change',event=>{
      const input=event.target.closest?.(selector);if(input)this._settingsFloorEdit(saved,input,true);
    });
    return result;
  };
  // Dispose timers and unsent jobs on removal, owner change or navigation.
  for(const [method,property] of [['_closeRoomSettings114','_roomSettingsDialog114'],
      ['_closeHomeSettings128','_homeSettingsDialog128'],['_closeHemControllerSettings126','_hemControllerDialog126'],
      ['_floorClose140','_floorDialog140']]){
    const prior=settingsProto[method];
    settingsProto[method]=function(...args){
      const saved=this[property];
      if(saved){
        saved.settingsClosed=true;clearTimeout(saved.optionsAutosave?.timer);
        for(const edit of saved.nativeEdits?.values()||[]){clearTimeout(edit.timer);clearTimeout(edit.confirmTimer);}
        for(const edit of saved.floorEdits?.values()||[])clearTimeout(edit.timer);
      }
      return prior.apply(this,args);
    };
  }
  /* HEM_SETTINGS_AUTOSAVE_B7_END */
