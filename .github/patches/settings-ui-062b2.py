"""Exact, idempotent source transformation for the reviewed 0.6.2b2 UI fix."""
from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'custom_components/environment_manager/frontend/air-quality-advisor-card.js'
s = p.read_text()
if 'HEM_SETTINGS_LABELS062B2_START' in s:
    print('HEM 062b2 dashboard transformation already present')
    raise SystemExit(0)

def replace(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:120], s.count(old), count)
    s = s.replace(old, new)

replace('        this._areaDeviceIds = new Map();\n        this._configEntryId114 = null;',
        '        this._areaDeviceIds = new Map();\n        this._hemDeviceRegistry062 = new Map();\n        this._configEntryId114 = null;')
replace('        this._areaDeviceIds = roomDevices;\n        this._deviceRegistryLoaded = true;',
        '        this._areaDeviceIds = roomDevices;\n        this._hemDeviceRegistry062 = new Map(entries.filter(device=>typeof device?.id===\"string\").map(device=>[device.id,device]));\n        this._deviceRegistryLoaded = true;')

tree = ast.parse((ROOT/'custom_components/environment_manager/settings_name_catalog.py').read_text())
groups = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
              and any(isinstance(target,ast.Name) and target.id=='GROUP_LABELS' for target in node.targets))
group_names = {locale: [name for key,name in values.items() if key not in ('sleep','humidity','fan','pid')]
               for locale,values in groups.items()}
helper = r'''  /* HEM_SETTINGS_LABELS062B2_START
   * Presentation only. Resolve names from the exact entity/device registry,
   * not an arbitrary split of friendly_name. HA adds device context to the
   * latter; unavailable entities still have useful original/translated names.
   */
  const HEM_CONTEXT_GROUPS062 = __GROUPS__;
  const hemText062=value=>typeof value==="string"?value.trim().replace(/\s+/gu," "):"";
  const hemUnprefix062=(value,prefix)=>{
    const text=hemText062(value),head=hemText062(prefix);
    if(!head||text.length<=head.length||
       text.slice(0,head.length).toLocaleLowerCase()!==head.toLocaleLowerCase())return text;
    const rest=text.slice(head.length);
    // A whole identity at the start only; never remove a substring in a
    // meaningful name, or a degree sign from a temperature/angle unit.
    if(!/^[\s·•°:|—–-]/u.test(rest))return text;
    const cleaned=rest.replace(/^[\s·•°:|—–-]+/u,"");
    return cleaned||text;
  };
  AirQualityAdvisorCard.prototype._hemSettingLabel062=function(id,state,record={},saved={},includeMode=true,fallback=""){
    const attrs=state?.attributes||{},reg=record||{},clean=hemText062;
    const deviceId=reg.device_id||saved.device;
    const device=this._hass?.devices?.[deviceId]||this._hemDeviceRegistry062?.get(deviceId)||{};
    const areaId=saved.area||reg.area_id||device.area_id;
    const areaName=clean(saved.room?.name)||clean(this._hass?.areas?.[areaId]?.name)||
      clean(areaId?safeArray(this._dashboard105?.()?.rooms).find(room=>room.area_id===areaId)?.name:"");
    const sourceNames=[device.name_by_user,device.name,saved.controller?.climate?.attributes?.friendly_name,
      areaName].map(clean).filter(Boolean).sort((a,b)=>b.length-a.length);
    const stripOwner=value=>{
      let text=clean(value);
      for(let round=0;round<3;round++){
        const before=text;
        for(const prefix of sourceNames)text=hemUnprefix062(text,prefix);
        // Integration role prefixes are never entity functionality.
        for(const prefix of ["Home Environment Manager","Home Environment","Environment Manager","Environment"])
          text=hemUnprefix062(text,prefix);
        if(text===before)break;
      }
      return text;
    };
    // HA stores explicit entity names in `name`; name_by_user is retained
    // for older card caches. Device names use their own name_by_user field.
    const custom=clean(reg.name_by_user)||clean(reg.name);
    let localized="";
    if(reg.translation_key&&typeof this._hass?.localize==="function"){
      const key="component.environment_manager.entity."+String(id).split(".")[0]+"."+reg.translation_key+".name";
      try{const value=this._hass.localize(key);if(value&&value!==key)localized=clean(value);}catch{}
    }
    let label=stripOwner(custom||attrs.setting_label||attrs.setting_display_name||
      reg.original_name_unprefixed||localized||reg.original_name||attrs.friendly_name||fallback||id);
    if(!custom){
      const group=clean(attrs.setting_group);
      const locale=String(this._language()||"en");
      const possible=group?[group]:(HEM_CONTEXT_GROUPS062[locale]||HEM_CONTEXT_GROUPS062.en);
      for(const prefix of [...possible].sort((a,b)=>b.length-a.length)){
        // Functional categories use a visible separator. Do not strip words
        // from a sentence such as "Noise threshold" or "Profile selection".
        const tail=label.slice(prefix.length);
        if(label.slice(0,prefix.length).toLocaleLowerCase()===prefix.toLocaleLowerCase()&&
           /^\s*[·•°:|—–-]\s*/u.test(tail)){
          label=hemUnprefix062(label,prefix);break;
        }
      }
    }
    label=label||stripOwner(attrs.friendly_name)||String(id);
    const mode=clean(attrs.operating_mode_label);
    if(includeMode&&!custom&&mode&&hemUnprefix062(label,mode)===label)label=mode+" · "+label;
    return label;
  };
  const hemDoorEco062=field=>{
    const attrs=field.state?.attributes||{},reg=field.reg||{};
    return field.domain==="switch"&&[attrs.setting_key,reg.translation_key,reg.unique_id]
      .some(value=>typeof value==="string"&&/(?:^|_)closed_door_eco$/.test(value));
  };
  const hemRenderNativeRows062=(card,holder,rows,scope)=>{
    if(holder.matches(":focus-within"))return;
    const opened=new Set([...holder.querySelectorAll("[data-hem-full-row127]")]
      .filter(row=>row.querySelector(".hem-full-help127[open]"))
      .map(row=>row.getAttribute("data-hem-full-row127")));
    const html=rows.map(field=>card._hemFullRow127(field,scope)).join("");
    if(holder.innerHTML!==html){
      holder.innerHTML=html;
      for(const row of holder.querySelectorAll("[data-hem-full-row127]")){
        const help=row.querySelector(".hem-full-help127");
        if(help&&opened.has(row.getAttribute("data-hem-full-row127")))help.open=true;
      }
    }
  };
  /* HEM_SETTINGS_LABELS062B2_END */

'''.replace('__GROUPS__',json.dumps(group_names,ensure_ascii=False,separators=(',',':')))
replace('  /* HEM_FULL_REGISTRY_SETTINGS127_START',helper+'  /* HEM_FULL_REGISTRY_SETTINGS127_START')
start=s.index('      const scopedLabel=',s.index('hemFull127._hemFullFields127=function'))
end=s.index('      const field={id,domain,kind,state,reg,disabled:Boolean(reg.disabled_by),label};',start)
s=s[:start]+'''      const label=this._hemSettingLabel062(id,state,reg,saved);
'''+s[end:]
replace('''          label:typeof supplied.setting_label==='string' && supplied.setting_label.trim()
            ? supplied.setting_label.trim():
            typeof supplied.friendly_name==='string' && supplied.friendly_name.trim()
              ? supplied.friendly_name.trim():label,''', '''          label:this._hemSettingLabel062(id,state,this._hass?.entities?.[id]||{},
            {controller:entry},false,label),''')
replace('''      const fieldLabel=field=>field.state.attributes.setting_label ||
        field.state.attributes.friendly_name || field.key.replaceAll('_',' ');''','''      const fieldLabel=field=>this._hemSettingLabel062(field.id,field.state,
        this._hass?.entities?.[field.id]||{},{area,controller:entry},false);''')
replace('''      room:{targets:"Room sensors and comfort",mode:"Equipment, control and PID",
        presence:"Presence and sleep",ventilation:"Windows, ventilation and shades",''','''      room:{targets:"Room sensors and comfort",mode:"Equipment, control and PID",
        presence:"Presence and sleep",ventilation:"Windows, doors, ventilation and shading",''')
replace('''      room:{targets:"Raumsensoren und Komfort",mode:"Geräte, Steuerung und PID",
        presence:"Anwesenheit und Schlaf",ventilation:"Fenster, Lüftung und Beschattung",''','''      room:{targets:"Raumsensoren und Komfort",mode:"Geräte, Steuerung und PID",
        presence:"Anwesenheit und Schlaf",ventilation:"Fenster, Türen, Lüftung und Beschattung",''')
replace('''      room:{targets:"Αισθητήρες χώρου και άνεση",mode:"Συσκευές, έλεγχος και PID",
        presence:"Παρουσία και ύπνος",ventilation:"Παράθυρα, αερισμός και σκίαση",''','''      room:{targets:"Αισθητήρες χώρου και άνεση",mode:"Συσκευές, έλεγχος και PID",
        presence:"Παρουσία και ύπνος",ventilation:"Παράθυρα, πόρτες, αερισμός και σκίαση",''')
replace('climate_devices:"mode",occupancy_sensors:"presence",door_sensors:"presence",',
        'climate_devices:"mode",occupancy_sensors:"presence",door_sensors:"ventilation",')
replace('''    const a=field.state?.attributes||{};
    const key=[a.setting_key,field.reg?.unique_id,field.id,field.label].filter(Boolean).join("_").toLowerCase();''','''    const a=field.state?.attributes||{};
    if(hemDoorEco062(field))return "ventilation";
    const key=[a.setting_key,field.reg?.unique_id,field.id,field.label].filter(Boolean).join("_").toLowerCase();''')
replace('presence|occup|sleep|wake|alarm|away_policy|schedule|closed_door_eco|_start|_end',
        'presence|occup|sleep|wake|alarm|away_policy|schedule|_start|_end')
replace('''    const sources=scope==="room"?
      [...root.querySelectorAll("[data-room-options-group114]")]:[];''','''    const sourceOrder062=["windows","door_sensors","shades"];
    const sources=scope==="room"?
      [...root.querySelectorAll("[data-room-options-group114]")].sort((a,b)=>{
        const rank=node=>{
          const index=sourceOrder062.indexOf(node.getAttribute("data-room-options-group114"));
          return index<0?sourceOrder062.length:index;
        };
        return rank(a)-rank(b);
      }):[];''')
replace('''      if(source.parentElement!==holder)holder.appendChild(source);
    }
    for(const key of keys){''','''      if(source.parentElement!==holder)holder.appendChild(source);
    }
    if(scope==="room"){
      const holder=groups.get("ventilation")?.querySelector("[data-hem-unified-sources141]");
      if(holder&&!holder.contains(_roomOptionsDeepFocus114())){
        const ordered=sourceOrder062.map(name=>sources.find(node=>
          node.getAttribute("data-room-options-group114")===name)).filter(Boolean);
        const actual=[...holder.querySelectorAll(":scope > [data-room-options-group114]")];
        if(ordered.some((source,index)=>actual[index]!==source)){
          let previous=null;
          for(const source of ordered){
            const position=previous?previous.nextElementSibling:holder.firstElementChild;
            if(position!==source)holder.insertBefore(source,position);
            previous=source;
          }
        }
      }
    }
    for(const key of keys){''')
replace('''      let holder=mount.querySelector(":scope > [data-hem-unified-native141]");
      if(rows.length){''','''      const doorSource=scope==="room"&&key==="ventilation"?
        mount.querySelector('[data-room-options-group114="door_sensors"]'):null;
      const paired=doorSource?rows.filter(hemDoorEco062):[];
      const remaining=paired.length?rows.filter(field=>!hemDoorEco062(field)):rows;
      let doorControls=mount.querySelector("[data-hem-door-eco062]");
      if(paired.length){
        if(!doorControls){
          doorControls=document.createElement("div");
          doorControls.className="hem-full-rows127 hem-door-eco062";
          doorControls.setAttribute("data-hem-door-eco062","");
        }
        if(doorSource.nextElementSibling!==doorControls)doorSource.after(doorControls);
        hemRenderNativeRows062(this,doorControls,paired,scope);
      }else doorControls?.remove();
      let holder=mount.querySelector(":scope > [data-hem-unified-native141]");
      if(remaining.length){''')
replace('''        const html=rows.map(field=>this._hemFullRow127(field,scope)).join("");
        if(holder.innerHTML!==html&&!holder.matches(":focus-within"))holder.innerHTML=html;''','''        hemRenderNativeRows062(this,holder,remaining,scope);''')
replace('''    ".hem-unified-native141{padding:3px 0 0}",''','''    ".hem-unified-native141{padding:3px 0 0}",
    ".hem-door-eco062{padding:0;min-width:0}",''')
p.write_text(s)
print('Applied 062b2 dashboard settings grouping and display-only label normalization')
