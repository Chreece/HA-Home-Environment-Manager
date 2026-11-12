  /* HEM_SETTINGS_AUDIT_B8_START
   * Presentation only. Exact setting identities, never translated label guesses.
   * Fold specialist tuning, not native entities, stored values or safety policy.
   */
  const auditPolicyB8=__POLICY__;
  const auditWordsB8={
    en:{search:'Find a setting',advanced:'Show advanced settings',showing:'Shown',total:'total',empty:'No settings match. Clear the search or show advanced settings.',help:'Advanced settings include specialist models, controller tuning and optional diagnostics. Existing values and protections remain active.'},
    el:{search:'Αναζήτηση ρύθμισης',advanced:'Εμφάνιση προηγμένων ρυθμίσεων',showing:'Εμφανίζονται',total:'σύνολο',empty:'Δεν βρέθηκαν ρυθμίσεις. Καθάρισε την αναζήτηση ή εμφάνισε τις προηγμένες ρυθμίσεις.',help:'Οι προηγμένες ρυθμίσεις περιλαμβάνουν ειδικά μοντέλα, συντονισμό ελεγκτών και προαιρετικά διαγνωστικά. Οι υπάρχουσες τιμές και οι προστασίες παραμένουν ενεργές.'},
    de:{search:'Einstellung suchen',advanced:'Erweiterte Einstellungen anzeigen',showing:'Angezeigt',total:'gesamt',empty:'Keine passenden Einstellungen. Suche leeren oder erweiterte Einstellungen anzeigen.',help:'Erweiterte Einstellungen enthalten Spezialmodelle, Reglerabstimmung und optionale Diagnosen. Gespeicherte Werte und Schutzfunktionen bleiben aktiv.'}
  };
  const auditWords=card=>auditWordsB8[card._language()]||auditWordsB8.en;
  const auditText=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
  const auditKeyB8=field=>{
    const a=field.state?.attributes||{};
    if(a.door_setting_key)return 'door_'+a.door_setting_key;
    if(a.settings_scope==='operating_mode'&&typeof a.setting_key==='string')return 'equipment_'+a.setting_key;
    return field.reg?.translation_key||a.setting_key||'';
  };
  const auditLevelB8=field=>field.domain==='button'?'primary':
    Object.prototype.hasOwnProperty.call(auditPolicyB8.advanced,auditKeyB8(field))?'advanced':'primary';
  const auditMatchesB8=(saved,label)=>!saved.settingsAudit?.query||auditText(label).includes(auditText(saved.settingsAudit.query));
  const auditKeepB8=(saved,field)=>{
    const edit=saved.nativeEdits?.get(field.id);
    return Boolean(edit&&edit.phase!=='saved');
  };
  const auditVisibleB8=(saved,field)=>auditKeepB8(saved,field)||
    (auditMatchesB8(saved,[field.label,field.id,field.state?.attributes?.configuration_help].join(' '))&&
     (auditLevelB8(field)==='primary'||saved.settingsAudit?.advanced||saved.settingsAudit?.query));
  const auditProto=AirQualityAdvisorCard.prototype;
  auditProto._settingsAuditPolicyB8=function(){return auditPolicyB8;};
  auditProto._settingsAuditLevelB8=function(field){return auditLevelB8(field);};
  const auditFieldsBefore=auditProto._hemFullFields127;
  auditProto._hemFullFields127=function(saved,scope){
    const fields=auditFieldsBefore.call(this,saved,scope);
    if(scope!=='home'||!Array.isArray(saved.fields)||saved.unsupported)return fields;
    // Aliases proven to write the same occupancy_global property. Do not
    // confuse local presence with household presence or per-device overrides.
    const options=new Set(saved.fields.filter(f=>f.kind).map(f=>f.name));
    return fields.filter(field=>{
      const alias=auditPolicyB8.home_aliases[auditKeyB8(field)];
      return auditKeepB8(saved,field)||!alias||!options.has(alias);
    });
  };
  const auditRowBefore=auditProto._hemFullRow127;
  auditProto._hemFullRow127=function(field,scope){
    const saved=settingsDialog(this,scope);
    const html=auditRowBefore.call(this,field,scope);
    if(!saved)return html;
    return html.replace('<div ', '<div data-settings-tier-b8="'+auditLevelB8(field)+'" '+
      (auditVisibleB8(saved,field)?'':'hidden ') );
  };
  auditProto._settingsAuditApplyB8=function(saved,scope){
    if(!this._hemFullContext127(saved,scope))return;
    saved.settingsAudit ||= {advanced:false,query:''};
    const words=auditWords(this), node=saved.node;
    let bar=node.querySelector('[data-settings-tools-b8]');
    if(!bar){
      bar=document.createElement('section');bar.className='hem-settings-tools-b8';
      bar.setAttribute('data-settings-tools-b8','');
      bar.innerHTML='<input type="search" data-settings-search-b8 maxlength="100">'+
        '<label><input type="checkbox" data-settings-advanced-b8><span></span></label>'+
        '<small data-settings-count-b8 role="status" aria-live="polite"></small>';
      const body=node.querySelector(scope==='device'?'.hem-controller-body126':
        scope==='home'?'[data-hem-home-form-groups128]':'[data-room-options-groups114]');
      if(!body)return;
      body.before(bar);
      const search=bar.querySelector('input[type="search"]'),advanced=bar.querySelector('input[type="checkbox"]');
      search.value=saved.settingsAudit.query;advanced.checked=saved.settingsAudit.advanced;
      search.addEventListener('input',()=>{
        saved.settingsAudit.query=search.value.slice(0,100);this._settingsAuditApplyB8(saved,scope);
      });
      advanced.addEventListener('change',()=>{
        saved.settingsAudit.advanced=advanced.checked;this._settingsAuditApplyB8(saved,scope);
      });
    }
    const search=bar.querySelector('input[type="search"]'),advanced=bar.querySelector('input[type="checkbox"]');
    search.placeholder=words.search;search.setAttribute('aria-label',words.search);
    advanced.nextElementSibling.textContent=words.advanced;advanced.parentElement.title=words.help;
    const fields=new Map(this._hemFullFields127(saved,scope).map(f=>[f.id,f]));
    let visible=0,total=0,advancedCount=0;
    const focus=_roomOptionsDeepFocus114();
    for(const row of node.querySelectorAll('[data-hem-full-row127]')){
      const field=fields.get(row.getAttribute('data-hem-full-row127'));if(!field)continue;
      const level=auditLevelB8(field);row.setAttribute('data-settings-tier-b8',level);
      row.hidden=!row.contains(focus)&&!auditVisibleB8(saved,field);
      total++;visible+=!row.hidden;advancedCount+=level==='advanced';
    }
    for(const row of node.querySelectorAll('[data-hem-home-field128]')){
      const key=row.getAttribute('data-hem-home-field128'),level=auditPolicyB8.advanced_options[key]?'advanced':'primary';
      const pending=saved.optionsAutosave?.dirty?.has(key)||row.querySelector('[role="alert"]');
      const text=row.textContent+' '+key;
      row.hidden=!row.contains(focus)&&!pending&&!(auditMatchesB8(saved,text)&&
        (level==='primary'||saved.settingsAudit.advanced||saved.settingsAudit.query));
      row.setAttribute('data-settings-tier-b8',level);
      total++;visible+=!row.hidden;advancedCount+=level==='advanced';
    }
    for(const row of node.querySelectorAll('[data-room-options-group114]')){
      const key=row.getAttribute('data-room-options-group114');
      row.hidden=!row.contains(focus)&&!saved.optionsAutosave?.dirty?.has(key)&&
        !auditMatchesB8(saved,row.textContent+' '+key);
      total++;visible+=!row.hidden;
    }
    advanced.parentElement.hidden=advancedCount===0;
    advanced.nextElementSibling.textContent=words.advanced+' ('+advancedCount+')';
    bar.querySelector('[data-settings-count-b8]').textContent=words.showing+' '+visible+' / '+total+' '+words.total;
    // Hide empty categories, never move source controls or lose their listeners.
    for(const group of node.querySelectorAll('[data-hem-unified141]')){
      const rows=[...group.querySelectorAll('[data-hem-full-row127],[data-hem-home-field128],[data-room-options-group114]')];
      if(!rows.length)continue;
      group.hidden=rows.every(row=>row.hidden);
      const count=group.querySelector(':scope > summary .hem-room-options-count114');
      if(count)count.textContent=String(rows.filter(row=>!row.hidden).length);
      // Search expands matches without changing the user's normal accordion state.
      if(saved.settingsAudit.query){
        saved.settingsAudit.expanded ||= new Map();
        const key=group.getAttribute('data-hem-unified141');
        if(!saved.settingsAudit.expanded.has(key))saved.settingsAudit.expanded.set(key,group.open);
        if(!group.hidden)group.open=true;
      }else if(saved.settingsAudit.expanded?.has(group.getAttribute('data-hem-unified141'))){
        group.open=saved.settingsAudit.expanded.get(group.getAttribute('data-hem-unified141'));
      }
    }
    if(!saved.settingsAudit.query)saved.settingsAudit.expanded=null;
    let empty=node.querySelector('[data-settings-empty-b8]');
    if(!empty){empty=document.createElement('p');empty.setAttribute('data-settings-empty-b8','');empty.className='hem-full-notice127';bar.after(empty);}
    empty.textContent=words.empty;empty.hidden=visible>0||total===0;
  };
  const auditRenderBefore=auditProto._hemFullRender127;
  auditProto._hemFullRender127=function(saved,scope){
    const result=auditRenderBefore.call(this,saved,scope);
    this._settingsAuditApplyB8(saved,scope);return result;
  };
  const auditStylesBefore=auditProto._styles;
  auditProto._styles=function(){return auditStylesBefore.call(this)+'<style>'+
    '[data-settings-tier-b8][hidden],[data-hem-unified141][hidden],[data-room-options-group114][hidden],[data-settings-empty-b8][hidden],.hem-settings-tools-b8 label[hidden]{display:none!important}'+
    '.hem-settings-tools-b8{display:flex;align-items:center;flex-wrap:wrap;gap:9px;padding:10px 14px;border-bottom:1px solid var(--aqa-edge);min-width:0}'+
    '.hem-settings-tools-b8 input[type=search]{flex:1 1 180px;min-width:0;max-width:100%;box-sizing:border-box;padding:8px;border:1px solid var(--aqa-edge);border-radius:8px;background:var(--secondary-background-color,#292929);color:inherit}'+
    '.hem-settings-tools-b8 label{display:flex;align-items:center;gap:5px;font-size:12px;cursor:pointer}'+
    '.hem-settings-tools-b8 small{font-size:11px;color:var(--aqa-muted)}'+
    '</style>';};
  /* HEM_SETTINGS_AUDIT_B8_END */
