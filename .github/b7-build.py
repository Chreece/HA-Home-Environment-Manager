from pathlib import Path
import hashlib, json, runpy
p=Path('custom_components/environment_manager/frontend/air-quality-advisor-card.js')
def blob(path):
 b=path.read_bytes();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert blob(p)=='857e5f7993193e3acef2c6613f6624021febef71', 'Frontend base changed'
s=p.read_text()
# Preserve intentional action buttons, but editable values no longer need Apply.
s=s.replace('''      '<button type="button" data-hem-full-apply127="'+escape(field.id)+'" '+
      'data-hem-full-target127="'+scope+'" '+(enabled?"":"disabled")+'>'+''','''      ((domain==="switch"||domain==="button")?'<button type="button" data-hem-full-apply127="'+escape(field.id)+'" '+
      'data-hem-full-target127="'+scope+'" '+(enabled?"":"disabled")+'>'+''')
s=s.replace('''        tr127(this,domain==="button"?"press":"apply"))+'</button></div>'+''','''        tr127(this,domain==="button"?"press":"apply"))+'</button>':"")+'</div>'+''')
s=s.replace("    save.disabled=blocked||!saved.fields||saved.clientErrors.size>0;\n    save.textContent=_roomOptionsWord114(this,busy&&saved.fields?'saving':'save');", "    if(save){\n      save.disabled=blocked||!saved.fields||saved.clientErrors.size>0;\n      save.textContent=_roomOptionsWord114(this,busy&&saved.fields?'saving':'save');\n    }")
# Keep old save hooks callable for compatibility, but never render their UI.
s=s.replace('data-room-options-save114 disabled','data-room-options-save114 hidden disabled')
s=s.replace('data-hem-home-save128 disabled','data-hem-home-save128 hidden disabled')
s=s.replace('data-floor-save140>','data-floor-save140 hidden>')
# Registry updates must not dismiss a floor editor while autosaving it.
s=s.replace('''      if(this._floorDialog140&&!this._floorDialog140.busy){
        this._floorClose140(false);
      }''','''      if(this._floorDialog140&&!this._floorDialog140.busy){
        this._settingsRefreshFloor?.(this._floorDialog140);
      }''')
# Purpose-specific copy replaces the formerly contradictory save instructions.
s=s.replace('escape(hemTiming141(this,0,found.length))','escape(settingsDescription(this,"device",key))')
s=s.replace('if(small)small.textContent=hemTiming141(this,draft,rows.length);','if(small)small.textContent=settingsDescription(this,scope,key);')
s=s.replace('escape(homeWord128(this,"draft"))','escape(settingsDescription(this,"home",category))')
s=s.replace('escape(hemWord126(this,"immediateShort"))','escape(settingsDescription(this,scope,category))')
s=s.replace('''en:"All settings are organized by function and apply immediately.",
      el:"Όλες οι ρυθμίσεις είναι οργανωμένες ανά λειτουργία και εφαρμόζονται αμέσως.",
      de:"Alle Einstellungen sind nach Funktion geordnet und werden sofort übernommen.",
    }[this._language()]||"All settings are organized by function and apply immediately."''','''en:"Control methods, comfort targets, operating limits and protection for this device.",
      el:"Μέθοδοι ελέγχου, στόχοι άνεσης, όρια λειτουργίας και προστασία αυτής της συσκευής.",
      de:"Regelverfahren, Komfortziele, Betriebsgrenzen und Schutz für dieses Gerät.",
    }[this._language()]||"Control methods, comfort targets, operating limits and protection for this device."''')
s=s.replace('Source selections are saved with Save. HEM device settings apply immediately.','Outdoor sources, comfort limits, household presence and notification policies.')
s=s.replace('Quellen mit Speichern sichern. HEM-Geräteeinstellungen gelten sofort.','Außenquellen, Komfortgrenzen, Anwesenheit im Haushalt und Benachrichtigungen.')
s=s.replace('Οι επιλογές πηγών αποθηκεύονται με «Αποθήκευση». Οι ρυθμίσεις συσκευής HEM εφαρμόζονται αμέσως.','Εξωτερικές πηγές, όρια άνεσης, παρουσία στο σπίτι και πολιτικές ειδοποιήσεων.')
# Remove obsolete timing subtitles, including legacy renderer fallback text.
s=s.replace('HEM settings below apply immediately. Source selections above use Save.','Sensors, comfort limits and operating policies for this room.')
s=s.replace('HEM-Einstellungen unten werden sofort übernommen. Für die Sensorauswahl oben Speichern wählen.','Sensoren, Komfortgrenzen und Betriebsregeln für diesen Raum.')
s=s.replace('Οι παρακάτω ρυθμίσεις HEM εφαρμόζονται αμέσως. Οι επιλογές αισθητήρων πιο πάνω αποθηκεύονται με «Αποθήκευση».','Αισθητήρες, όρια άνεσης και πολιτικές λειτουργίας αυτού του χώρου.')
block=Path('.github/b7-autosave.js').read_text()
s=s.replace('\n})();\n', '\n'+block+'\n})();\n')
assert s.count('HEM_SETTINGS_AUTOSAVE_B7_START')==1
p.write_text(s)

runpy.run_path('.github/b7-migrate-tests.py', run_name='__main__')
p=Path('.github/workflows/validate.yml')
assert blob(p)=='d16c641e110dbf0cba6220bee74c1580ce886fc9', 'CI base changed'
s=p.read_text()
anchor='      - name: B1 concise settings labels and door UI in Chromium'
assert s.count(anchor)==1
s=s.replace(anchor, '      - name: B7 direct settings saves and pending-value preservation\n        run: python -I .github/tests/test_062b7_autosave.py\n'+anchor)
p.write_text(s)
p=Path('custom_components/environment_manager/manifest.json')
s=p.read_text();assert '"version": "0.6.2b6"' in s
p.write_text(s.replace('"version": "0.6.2b6"','"version": "0.6.2b7"'))
expected=json.loads(Path('.github/b7-expected.json').read_text())
for path, digest in expected.items():
 actual=blob(Path(path))
 assert actual==digest,(path, actual, digest)
print('All',len(expected),'changed files match locally verified source')
