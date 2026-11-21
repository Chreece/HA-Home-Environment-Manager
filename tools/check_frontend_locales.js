#!/usr/bin/env node
'use strict';
// Exercise the complete shipped card and check its actual English source
// catalogs. No Home Assistant connection or browser/device commands are used.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const frontend=path.join(root,'custom_components/environment_manager/frontend');
const file=path.join(frontend,'air-quality-advisor-card.js');
const source=fs.readFileSync(file,'utf8');
const data=JSON.parse(fs.readFileSync(path.join(root,'.github/localization/frontend.json'),'utf8'));
for(const filename of data.shared_catalogs){
  const shared=JSON.parse(fs.readFileSync(path.join(root,'.github/localization',filename),'utf8'));
  for(const [text,translations]of Object.entries(shared))
    data.messages[text]={...data.messages[text],...translations};
}
const tags=fs.readdirSync(path.join(root,'custom_components/environment_manager/translations'))
  .filter(name=>name.endsWith('.json')).map(name=>name.slice(0,-5)).sort();
assert.deepEqual(data.languages,tags,'The bundle must cover every supported integration locale');
let acorn;
try {acorn=require('acorn');}
catch {
  // Node ships Acorn for its own tools; use it when no project dependency is installed.
  const holder={exports:{}};
  vm.runInNewContext(process.binding('natives')['internal/deps/acorn/acorn/dist/acorn'],
    {module:holder,exports:holder.exports});
  acorn=holder.exports;
}
const ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'script',locations:true});
const nodes=[];
function visit(node){
  if(!node||typeof node.type!=='string')return;
  nodes.push(node);
  for(const [key,value]of Object.entries(node)){
    if(key==='loc')continue;
    if(Array.isArray(value))for(const child of value)visit(child);
    else if(value&&typeof value==='object')visit(value);
  }
}
visit(ast);
const literal=node=>node?.type==='Literal'?node.value:node?.type==='Identifier'?node.name:undefined;
const english=new Map();
function collect(node){
  if(node?.type==='Literal'&&typeof node.value==='string')english.set(node.value,node.loc.start.line);
  else if(node?.type==='ObjectExpression')for(const prop of node.properties)collect(prop.value);
  else if(node?.type==='ArrayExpression')for(const child of node.elements)collect(child);
}
for(const node of nodes){
  if(node.type==='ObjectExpression'){
    const en=node.properties.find(prop=>literal(prop.key)==='en');
    if(en)collect(en.value);
  }
  if(node.type==='ArrayExpression'&&[2,3].includes(node.elements.length)){
    const [first,second]=node.elements.map(literal);
    if(typeof first==='string'&&typeof second==='string'&&/[Α-ω]/u.test(second)&&!/[Α-ω]/u.test(first))collect(node.elements[0]);
  }
  if(node.type==='CallExpression'&&node.callee?.name==='hemTextB8')collect(node.arguments[0]);
}
const technical=text=>!text.trim()||/^(?:HEM|Home Environment Manager|Home Environment|Home Assistant|Air Quality Advisor|AQI|CO₂|CO2|eCO₂|PM2\.5|PM10|PM1|PM4|TVOC|VOC|NO₂|O₃|SO₂|PID|PWM|HVAC|IMC\s*\/\s*Lambda|Cohen[–-]Coon|°[CF]|K|%|RH|RH\s*\(%\)|m³\/h|µg\/m³|µg\/m3|ppm|ppb|lx|lux|dB|kWh|W|h|min|s|d|m\/s|km\/h|[0-9.,%+−–—\-\s]+)$/i.test(text.trim());
const placeholders=text=>[...new Set(text.match(/\{[a-zA-Z_][a-zA-Z0-9_]*\}/g)||[])].sort();
const sameSpelling=JSON.parse(fs.readFileSync(path.join(root,'.github/localization/frontend_same_spelling.json'),'utf8'));
const equalAllowed=new Map(sameSpelling.entries.map(entry=>{
  assert.ok(entry.reason?.trim(),'Same-spelling exceptions require a linguistic or technical justification');
  assert.ok(entry.source.trim().split(/\s+/u).length<8,'English prose must never be allowlisted as translated');
  for(const language of entry.locales)assert.ok(tags.includes(language)&&language!=='en','Invalid exception locale');
  return [entry.source,new Set(entry.locales)];
}));
const comparable=text=>text.trim().replace(/\s+/gu,' ').toLocaleLowerCase('en');
const missing=[],mismatches=[],englishCopies=[];
// Include incoming backend explanations in the checked-in memory as well as
// card literals. Same-spelling cognates require a reviewed locale-specific
// exception; an explicit English fallback must not count as coverage.
const required=new Set([...english.keys(),...Object.keys(data.messages)].filter(text=>!technical(text)));
for(const text of required)for(const language of tags.filter(tag=>tag!=='en')){
  const translated=data.messages[text]?.[language];
  if(typeof translated!=='string'||!translated.trim())missing.push({language,text,line:english.get(text)||null});
  else {
    if(JSON.stringify(placeholders(text))!==JSON.stringify(placeholders(translated)))
      mismatches.push({language,text,translated});
    if(comparable(text)===comparable(translated)&&
      (text.trim().split(/\s+/u).length>=8||!equalAllowed.get(text)?.has(language)))
      englishCopies.push({language,text,translated,line:english.get(text)||null});
  }
}
const registry=new Map();
const sandbox={HTMLElement:class{},customElements:{get:name=>registry.get(name),define:(name,card)=>registry.set(name,card)},
  window:{},console,Intl,Set,Map,WeakMap,WeakSet,Date,Number,Object,Array,String,Math,JSON,RegExp,Boolean,Promise,
  URL,URLSearchParams,AbortController,setTimeout,clearTimeout};
sandbox.globalThis=sandbox;
vm.createContext(sandbox);
vm.runInContext(source,sandbox,{timeout:20000,filename:file});
const Card=registry.get('home-environment-manager-card');
function card(language){
  const value=Object.create(Card.prototype);
  value._hass={language,states:{},localize:()=>undefined,config:{time_zone:'UTC'}};
  value._config={entity:'sensor.hem'};
  return value;
}
function helpSources(methodName,variableName){
  const method=nodes.find(node=>node.type==='MethodDefinition'&&literal(node.key)===methodName);
  const declarations=method.value.body.body.filter(node=>node.type==='VariableDeclaration')
    .flatMap(node=>node.declarations);
  const catalog=declarations.find(node=>node.id.name===variableName).init;
  return Object.fromEntries(catalog.properties.map(prop=>[literal(prop.key),literal(prop.value.elements[0])]));
}
const metricSources=helpSources('_metricHelp','texts');
const scienceSources=helpSources('_scienceHelp','explanations');
const expected=(text,language)=>language==='en'?text:data.messages[text]?.[language];
const html=text=>String(text).replace(/[&<>"']/g,char=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const sharedHelp=JSON.parse(fs.readFileSync(path.join(root,'.github/localization/backend_help.json'),'utf8'));
const composedHelp=JSON.parse(fs.readFileSync(path.join(root,'.github/localization/backend_composed_help.json'),'utf8'));
const helpSource=Object.keys(sharedHelp).find(text=>text.startsWith('A normal interior doorway'));
const optionSource=Object.keys(sharedHelp).find(text=>text.startsWith('If any selected person/tracker'));
const composedSource=Object.keys(composedHelp)[0];
assert.ok(helpSource&&optionSource&&composedSource,'Shared help regression samples must exist');
const aliasProbes={pt_BR:'pt-br','PT-br':'pt-br',zh_CN:'zh-hans','zh-Hans-CN':'zh-hans',
  zh_TW:'zh-hant','zh-Hant-HK':'zh-hant',no:'nb','fr-CA':'fr'};
for(const [input,resolved]of Object.entries(aliasProbes))
  assert.equal(card(input)._language(),resolved,'Supported regional locale aliases must resolve');
// Server-language option values are write tokens, not translated payloads.
const doorOption='Θέρμανση';
const optionField={state:{attributes:{option_labels_locales:{en:{[doorOption]:'Heating'},el:{[doorOption]:'Θέρμανση'}},options:[doorOption]}}};
const optionBefore=JSON.stringify(optionField);
assert.notEqual(card('fr')._hemFullOptionLabel129(optionField,doorOption),doorOption);
assert.equal(JSON.stringify(optionField),optionBefore,'Option translation must preserve actual Select values');
assert.equal(card('fr')._hemFullOptionLabel129({state:{attributes:{}}},'Custom device preset'),'Custom device preset');
const localizedSetting={attributes:{setting_label:'Θέρμανση',setting_label_locales:{en:'Heating',el:'Θέρμανση'},
  operating_mode_label:'Ψύξη',operating_mode_label_locales:{en:'Cooling',el:'Ψύξη'}}};
const settingsBefore=JSON.stringify(localizedSetting);
const translatedSetting=card('fr')._hemSettingLabel062('number.audit',localizedSetting,{}, {},true);
assert.ok(!translatedSetting.includes('Θέρμανση')&&!translatedSetting.includes('Ψύξη'),
  'Card locale must localize the English source when server metadata lacks that locale');
assert.equal(card('fr')._hemSettingLabel062('number.audit',localizedSetting,{name_by_user:'My boiler'}, {},true),
  'My boiler','A user-defined entity name must remain unchanged');
assert.equal(JSON.stringify(localizedSetting),settingsBefore,'Metadata localization must not mutate entity state');
// Ordinary SettingsMetadata names use the server language and do not publish
// setting_label_locales. Exercise that production shape, not only mode labels.
const ordinaryKey='home_aqi_custom_limit';
const ordinaryPath='component.environment_manager.entity.number.'+ordinaryKey+'.name';
const germanNative=JSON.parse(fs.readFileSync(path.join(root,
  'custom_components/environment_manager/translations/de.json'),'utf8'));
const serverSettingName=germanNative.entity.number[ordinaryKey].name;
const ordinaryState={attributes:{setting_display_name:serverSettingName,setting_key:ordinaryKey,
  setting_group:serverSettingName.split(' · ')[0]}};
const ordinaryRegistry={translation_key:ordinaryKey,original_name:serverSettingName,
  original_name_unprefixed:serverSettingName};
const ordinaryBefore=JSON.stringify(ordinaryState);
const probes=[];
for(const language of tags){
  const value=card(language);
  const nativeCatalog=JSON.parse(fs.readFileSync(path.join(root,
    'custom_components/environment_manager/translations',language+'.json'),'utf8'));
  const viewerName=nativeCatalog.entity.number[ordinaryKey].name;
  value._hass.localize=key=>key===ordinaryPath?viewerName:undefined;
  const ordinaryLabel=value._hemSettingLabel062('number.audit',ordinaryState,ordinaryRegistry,{},false);
  assert.ok(ordinaryLabel.includes(viewerName.split(' · ').at(-1)),
    `${language}: native viewer name must win over server-language setting_display_name`);
  assert.equal(value._hemSettingLabel062('number.audit',ordinaryState,
    {...ordinaryRegistry,name:'My AQI limit'},{},false),'My AQI limit',
    'A user-defined setting name must still take precedence');
  assert.equal(JSON.stringify(ordinaryState),ordinaryBefore,'Name localization must preserve state');
  value._hass.localize=()=>undefined;
  assert.equal(value._arrivalHelp125().purpose,
    expected(card('en')._arrivalHelp125().purpose,language),
    'Arrival help must retain the target, expiry, cancellation, and away-only conditions');
  for(const [metric,text]of Object.entries(metricSources))
    assert.equal(value._metricHelp({metric}),expected(text,language),
      `${language}: ${metric} must show its complete translated explanation`);
  for(const [topic,text]of Object.entries(scienceSources))
    assert.equal(value._scienceHelp(topic),expected(text,language),
      `${language}: ${topic} must not fall back to a generic science description`);
  const sharedField={domain:'select',state:{state:doorOption,attributes:{options:[doorOption],
    configuration_help_locales:{en:helpSource,el:'Server-language help'},
    option_help_locales:{en:{[doorOption]:optionSource},el:{[doorOption]:'Server-language option'}},
    option_labels_locales:{en:{[doorOption]:'Heating'},el:{[doorOption]:doorOption}}}}};
  const sharedBefore=JSON.stringify(sharedField);
  const helpBody=value._hemFullHelpBody127(sharedField,'room');
  assert.ok(helpBody.includes(html(expected(helpSource,language))),'Configuration help must use the card locale');
  assert.ok(helpBody.includes(html(expected(optionSource,language))),'Option help must use the card locale');
  assert.equal(JSON.stringify(sharedField),sharedBefore,'Rendering help must preserve backend state and option values');
  const composedBody=value._hemFullHelpBody127({domain:'number',state:{attributes:{
    configuration_help_locales:{en:composedSource,el:'Server-language composition'}}}},'device');
  for(const paragraph of expected(composedSource,language).split(/\n\s*\n/).filter(text=>text.trim()))
    assert.ok(composedBody.includes(html(paragraph.trim())),'Composed help must retain every translated paragraph');
  const statuses=['air_quality_decision_expired','controller_paused','other_endpoint_acknowledgement_pending'];
  const nativeStates=JSON.parse(fs.readFileSync(path.join(root,'custom_components/environment_manager/translations',language+'.json'),'utf8'))
    .entity.sensor.equipment_control_status.state;
  for(const status of statuses){
    const fallback=value._controllerStatusLabel(status);
    assert.notEqual(fallback,value._controllerStatusLabel('unknown'),'Known status details must not become generic Unknown');
    if(language!=='en')assert.notEqual(fallback,card('en')._controllerStatusLabel(status),
      'Known status details need a bundled translation before native locale loading');
  }
  value._hass.localize=key=>nativeStates[key.split('.').at(-1)];
  for(const status of statuses)
    assert.equal(value._controllerStatusLabel(status),nativeStates[status],
      'Loaded native status translations must retain their detailed meaning');
  const heating=value._measurementActivityB6('temperature','audit',{
    items:[{tone:'heat',label:'heat',active:true,channels:['temperature']}]});
  assert.equal(heating.tone,'heat','Translation must not change activity colors');
  const unrelated=value._measurementActivityB6('humidity','audit',{
    items:[{tone:'heat',label:'heat',active:true,channels:['temperature']}]});
  assert.equal(unrelated.text,'','Translation must not broaden the activity scope');
  const window=value._windowAnnouncementControls6({windowAnnounceId:'switch.audit',windowAnnounce:{state:'on'},
    windowWaitId:'number.audit',windowWait:{state:'5'},entityId:'climate.audit'},'audit','Save');
  if(['pt-BR','zh-Hans','zh-Hant'].includes(language)){
    assert.ok(!window.includes('Window opening wait'),'Existing regional translations must be reachable');
    assert.notEqual(value._arrivalHelp125().purpose,card('en')._arrivalHelp125().purpose);
  }
  probes.push({language,resolved:value._language(),heating:heating.text,aqi:value._outsideAQIHelpB7(),
    eco2:value._metricName('eco2'),metric:value._metricHelp({metric:'co2'}),science:value._scienceHelp('surface')});
}
const result={locales:tags.length,source_messages:required.size,missing:missing.length,
  placeholder_mismatches:mismatches.length,unapproved_english_copies:englishCopies.length,
  metric_help_topics:Object.keys(metricSources).length,science_help_topics:Object.keys(scienceSources).length,
  alias_probes:aliasProbes,missing_messages:missing,placeholder_errors:mismatches,english_copy_errors:englishCopies,runtime_probes:probes};
const report=process.argv.find(arg=>arg.startsWith('--report='))?.slice('--report='.length);
if(report)fs.writeFileSync(report,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({locales:tags.length,source_messages:required.size,missing:missing.length,
  placeholder_mismatches:mismatches.length,unapproved_english_copies:englishCopies.length,runtime_probes:probes.length,
  metric_help_topics:Object.keys(metricSources).length,science_help_topics:Object.keys(scienceSources).length,
  locale_aliases:Object.keys(aliasProbes).length},null,2));
assert.equal(mismatches.length,0,'Translated messages must preserve interpolation placeholders');
assert.equal(englishCopies.length,0,'English fallback copies must not count as translations');
if(!process.argv.includes('--allow-incomplete'))assert.equal(missing.length,0,'Every supported language needs every nontechnical message');
