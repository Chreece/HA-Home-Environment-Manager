  /* HEM_SETTING_HELP_B9_START
   * Help is presentation only. These controls never emit a value change or
   * invoke an HA service. Keep inputs, validation and category descriptions.
   */
  const settingHelpWordsB9={
    en:{missing:"No additional description is available for this setting.",
      name:"Name of this floor in Home Assistant. Renaming it does not change its rooms or settings.",
      level:"Optional whole-number floor level in Home Assistant. Negative levels can represent basements; leave blank when unspecified.",
      icon:"Optional Material Design icon for this floor, for example mdi:home-floor-1. Leave blank for the default icon.",
      membership:"Select this room to assign its Home Assistant Area to this floor, moving it from another floor if necessary. Clearing it removes only its assignment to this floor."},
    el:{missing:"Δεν υπάρχει πρόσθετη περιγραφή για αυτή τη ρύθμιση.",
      name:"Το όνομα αυτού του ορόφου στο Home Assistant. Η μετονομασία δεν αλλάζει τα δωμάτια ή τις ρυθμίσεις του.",
      level:"Προαιρετικός ακέραιος αριθμός επιπέδου στο Home Assistant. Αρνητικές τιμές μπορούν να δηλώνουν υπόγεια· άφησέ το κενό όταν δεν ορίζεται.",
      icon:"Προαιρετικό εικονίδιο Material Design για τον όροφο, π.χ. mdi:home-floor-1. Άφησέ το κενό για το προεπιλεγμένο εικονίδιο.",
      membership:"Επίλεξε το δωμάτιο για να αντιστοιχίσεις τον χώρο του Home Assistant σε αυτόν τον όροφο, μεταφέροντάς τον από άλλον αν χρειάζεται. Η αποεπιλογή αφαιρεί μόνο την αντιστοίχιση σε αυτόν τον όροφο."},
    de:{missing:"Für diese Einstellung ist keine zusätzliche Beschreibung verfügbar.",
      name:"Name dieser Etage in Home Assistant. Eine Umbenennung ändert weder ihre Räume noch deren Einstellungen.",
      level:"Optionale ganzzahlige Etagenhöhe in Home Assistant. Negative Werte können Kellergeschosse darstellen; bei unbekannter Höhe leer lassen.",
      icon:"Optionales Material-Design-Symbol dieser Etage, zum Beispiel mdi:home-floor-1. Für das Standardsymbol leer lassen.",
      membership:"Diesen Raum auswählen, um seinen Home-Assistant-Bereich dieser Etage zuzuordnen und gegebenenfalls von einer anderen Etage zu verschieben. Abwählen entfernt nur die Zuordnung zu dieser Etage."}
  };
  function settingHelpTextB9(card,key){
    return (settingHelpWordsB9[card._language()]||settingHelpWordsB9.en)[key];
  }
  function settingHelpIdB9(scope,key){return 'hem-help-b9-'+scope+'-'+encodeURIComponent(key);}
  function settingHelpButtonB9(card,scope,key,label){
    const id=settingHelpIdB9(scope,key),name=tr127(card,'help')+' · '+label;
    return '<button type="button" class="hem-setting-info-b9" data-setting-info-b9 '+
      'aria-label="'+escape(name)+'" title="'+escape(tr127(card,'help'))+'" '+
      'aria-expanded="false" aria-controls="'+escape(id)+'">'+
      card._icon('mdi:information-outline')+'</button>';
  }
  function settingHelpPanelB9(card,scope,key,help){
    return '<div id="'+escape(settingHelpIdB9(scope,key))+'" class="hem-setting-help-b9" '+
      'data-setting-help-b9 hidden><p>'+escape(help||settingHelpTextB9(card,'missing'))+'</p></div>';
  }
  function settingHelpHeadingB9(card,scope,key,label,help,heading){
    return '<div class="hem-setting-heading-b9">'+
      (heading||'<strong>'+escape(label)+'</strong>')+
      settingHelpButtonB9(card,scope,key,label)+'</div>'+settingHelpPanelB9(card,scope,key,help);
  }
  function bindSettingHelpB9(saved){
    if(!saved?.node)return;
    saved.settingHelpOpenB9 ||= new Set();
    const node=saved.node;
    const panelFor=button=>[...node.querySelectorAll('[data-setting-help-b9]')]
      .find(panel=>panel.id===button.getAttribute('aria-controls'));
    const setOpen=(button,panel,open)=>{
      panel.hidden=!open;button.setAttribute('aria-expanded',String(open));
      if(open)saved.settingHelpOpenB9.add(panel.id);else saved.settingHelpOpenB9.delete(panel.id);
    };
    if(!saved.settingHelpBoundB9){
      saved.settingHelpBoundB9=true;
      node.addEventListener('click',event=>{
        const button=event.target?.closest?.('[data-setting-info-b9]');
        if(!button||!node.contains(button))return;
        event.preventDefault();event.stopImmediatePropagation();
        const panel=panelFor(button);if(!panel)return;
        const open=panel.hidden;
        // A source-selector summary must open to expose its full-width help,
        // but a help click must never invoke the selector or change its value.
        if(open){const details=button.closest('summary')?.parentElement;
          if(details?.tagName==='DETAILS')details.open=true;}
        setOpen(button,panel,open);
      },true);
      node.addEventListener('keydown',event=>{
        const button=event.target?.closest?.('[data-setting-info-b9]');
        if(event.key!=='Escape'||!button||!node.contains(button)||button.getAttribute('aria-expanded')!=='true')return;
        const panel=panelFor(button);if(!panel)return;
        event.preventDefault();event.stopImmediatePropagation();setOpen(button,panel,false);
      },true);
    }
    for(const button of node.querySelectorAll('[data-setting-info-b9]')){
      const panel=panelFor(button);if(panel)setOpen(button,panel,saved.settingHelpOpenB9.has(panel.id));
    }
  }
  // Preserve expanded help if a form re-renders for validation, or the card
  // refreshes during an in-flight save. Listeners stay local to that dialog.
  for(const name of ['_renderHomeGeneral128','_renderRoomSettingsForm114','_hemFullRender127']){
    const prior=AirQualityAdvisorCard.prototype[name];
    AirQualityAdvisorCard.prototype[name]=function(saved,...args){
      const result=prior.call(this,saved,...args);bindSettingHelpB9(saved);return result;
    };
  }
  const helpFloorOpenB9=AirQualityAdvisorCard.prototype._floorOpen140;
  AirQualityAdvisorCard.prototype._floorOpen140=function(...args){
    const result=helpFloorOpenB9.apply(this,args);bindSettingHelpB9(this._floorDialog140);return result;
  };
  const helpStylesB9=AirQualityAdvisorCard.prototype._styles;
  AirQualityAdvisorCard.prototype._styles=function(){return helpStylesB9.call(this)+'<style>'+
    '.hem-setting-heading-b9{display:flex;align-items:center;gap:8px;min-width:0;width:100%;box-sizing:border-box}'+
    '.hem-setting-heading-b9>strong,.hem-setting-heading-b9>label{flex:1 1 auto;min-width:0;overflow-wrap:break-word}'+
    '.hem-setting-heading-b9>strong{font-size:12px}'+
    'dialog .hem-setting-info-b9{flex:0 0 30px;width:30px;min-width:30px;height:30px;min-height:30px;padding:5px;display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;background:transparent;border:0;color:var(--primary-color,#03a9f4);cursor:pointer;margin-inline-start:auto}'+
    'dialog .hem-setting-info-b9 ha-icon{--mdc-icon-size:18px;width:18px;height:18px;flex:0 0 18px}'+
    '.hem-setting-info-b9:focus-visible{outline:2px solid var(--primary-color,#03a9f4);outline-offset:2px;border-radius:5px}'+
    '.hem-setting-help-b9{width:100%;min-width:0;max-width:100%;box-sizing:border-box}'+
    '.hem-setting-help-b9[hidden]{display:none!important}'+
    '.hem-setting-help-b9 p{font-size:12px;line-height:1.5;margin:5px 0 8px;color:var(--secondary-text-color,#aaa);white-space:pre-line;overflow-wrap:break-word;word-break:normal}'+
    '[data-room-options-group114]>summary>ha-icon:nth-last-child(2){color:var(--secondary-text-color,#aaa)}'+
    '[data-room-options-group114][open]>summary>ha-icon:nth-last-child(2){transform:rotate(180deg)}'+
    '.hem-floor-field-b9{display:grid;gap:5px;min-width:0}'+
    '.hem-floor-field-b9>input{min-width:0;width:100%;box-sizing:border-box;padding:8px;border:1px solid var(--aqa-edge);border-radius:8px;background:var(--secondary-background-color,#292929);color:inherit;font:inherit}'+
    '.hem-floor-room-choice140{display:block}'+
    '.hem-floor-members140>summary{display:flex;align-items:center;gap:6px}'+
    '.hem-floor-members140>summary>span{flex:1;min-width:0}'+
    '</style>';};
  /* HEM_SETTING_HELP_B9_END */
