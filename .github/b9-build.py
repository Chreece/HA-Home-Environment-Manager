from pathlib import Path
import hashlib
P=Path('custom_components/environment_manager/frontend/air-quality-advisor-card.js')
content=P.read_text()
def replace(old,new,count=1):
 global content
 assert content.count(old)==count,(old[:120],content.count(old),count)
 content=content.replace(old,new)
replace('''    const help=typeof a.configuration_help==="string"?a.configuration_help.trim():"";''','''    const help=(typeof a.configuration_help==="string"?a.configuration_help.trim():"")||settingHelpTextB9(this,"missing");''')
replace('''         escape(tr127(this,"help"))+'">'+''','''         escape(tr127(this,"help"))+'" aria-label="'+escape(tr127(this,"help")+' · '+field.label)+'">'+''')
replace('''      (kind==="boolean"?"":'<div class="hem-full-label127"><strong>'+escape(label)+'</strong></div>')+
      '<div class="hem-home-editor128">'+editor+'</div>'+
      (help?'<p class="hem-home-helper128">'+escape(help)+'</p>':"")+''','''      settingHelpHeadingB9(this,"home",name,label,help,kind==="boolean"?editor:null)+
      (kind==="boolean"?"":'<div class="hem-home-editor128">'+editor+'</div>')+''')
replace('''        '</span>'+this._icon('mdi:chevron-down')+'</summary>'+
        '<div class="hem-room-options-group-body114"><div data-room-options-mount114></div>'+''','''        '</span>'+this._icon('mdi:chevron-down')+
        settingHelpButtonB9(this,"room",name,label)+'</summary>'+
        '<div class="hem-room-options-group-body114">'+settingHelpPanelB9(this,"room",name,helper)+
        '<div data-room-options-mount114></div>'+''')
replace('''        native.computeHelper=()=>helper;''','''        // HEM owns the help disclosure; ha-form must not repeat it inline.
        native.computeHelper=()=>"";''')
replace('''        mount.innerHTML=(helper?'<p class="hem-room-options-helper115">'+escape(helper)+'</p>':'')+
          '<input type="search"''','''        mount.innerHTML='<input type="search"''')
replace('''      return '<div class="hem-floor-room-choice140"><label>'+''','''      return '<div class="hem-floor-room-choice140"><div class="hem-setting-heading-b9"><label>'+''')
replace('''        '</button></div>';
    }).join("");
    node.innerHTML='<header class="hem-floor-dialog-head140">''','''        '</button>'+settingHelpButtonB9(this,"floor",floorId+"/"+area.area_id,area.name)+
        '</div>'+settingHelpPanelB9(this,"floor",floorId+"/"+area.area_id,settingHelpTextB9(this,"membership"))+'</div>';
    }).join("");
    node.innerHTML='<header class="hem-floor-dialog-head140">''')
replace('''      '<label>'+escape(words.name)+'<input type="text" data-floor-name140 required maxlength="100" value="'+
      escape(floor.name)+'"></label>'+
      '<label>'+escape(words.level)+'<input type="number" data-floor-level140 step="1" '+
      'value="'+(floor.level===null?'':escape(floor.level))+'"></label>'+
      '<label>'+escape(words.icon)+'<input type="text" data-floor-icon140 maxlength="94" '+
      'placeholder="mdi:home-floor-1" value="'+escape(toIcon)+'"></label></section>'+
      '<details class="hem-floor-members140" open><summary>'+
      this._icon("mdi:floor-plan")+' '+escape(words.members)+' · '+ctx.areas.filter(a=>
        a.floor_id===floorId).length+'</summary>'+
      '<p>'+escape(words.note)+'</p>'+''','''      '<div class="hem-floor-field-b9">'+settingHelpHeadingB9(this,"floor","name",words.name,settingHelpTextB9(this,"name"))+
      '<input type="text" data-floor-name140 aria-label="'+escape(words.name)+'" required maxlength="100" value="'+escape(floor.name)+'"></div>'+
      '<div class="hem-floor-field-b9">'+settingHelpHeadingB9(this,"floor","level",words.level,settingHelpTextB9(this,"level"))+
      '<input type="number" data-floor-level140 aria-label="'+escape(words.level)+'" step="1" value="'+(floor.level===null?'':escape(floor.level))+'"></div>'+
      '<div class="hem-floor-field-b9">'+settingHelpHeadingB9(this,"floor","icon",words.icon,settingHelpTextB9(this,"icon"))+
      '<input type="text" data-floor-icon140 aria-label="'+escape(words.icon)+'" maxlength="94" placeholder="mdi:home-floor-1" value="'+escape(toIcon)+'"></div></section>'+
      '<details class="hem-floor-members140" open><summary>'+
      this._icon("mdi:floor-plan")+'<span>'+escape(words.members)+' · '+ctx.areas.filter(a=>
        a.floor_id===floorId).length+'</span>'+settingHelpButtonB9(this,"floor","members",words.members)+'</summary>'+
      settingHelpPanelB9(this,"floor","members",words.note)+''')
block=Path('.github/b9-help.js').read_text()
assert content.endswith('\n})();\n')
content=content[:-6]+block+'\n})();\n'
P.write_text(content)
p=Path('custom_components/environment_manager/manifest.json');s=p.read_text();assert '0.6.2b8' in s;p.write_text(s.replace('0.6.2b8','0.6.2b9'))
p=Path('.github/workflows/validate.yml');s=p.read_text();anchor='      - name: B8 settings inventory, advanced presentation and exact duplicate aliases';assert s.count(anchor)==1
p.write_text(s.replace(anchor,'      - name: B9 on-demand setting help in every menu\n        run: python -I .github/tests/test_062b9_settings_help.py\n'+anchor))
