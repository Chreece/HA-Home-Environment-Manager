from pathlib import Path
import json,hashlib,runpy,subprocess
root=Path.cwd();source=root/'custom_components/environment_manager'
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
p=source/'frontend/air-quality-advisor-card.js'
assert blob(p)== 'bb9212d6ba832a73f241b6420b9b4bf30ba7dcd2','Frontend baseline moved'
s=p.read_text();assert s.endswith('\n})();\n')
policy=json.loads((source/'frontend/settings-audit-policy.json').read_text())
block=Path('.github/b8-ui.js').read_text().replace('__POLICY__',json.dumps(policy,separators=(',',':')))
p.write_text(s[:-6]+block+'\n})();\n')
p=Path('.github/tests/test_061b7_mode_settings_card.py');s=p.read_text();anchor='        gain=modal.locator(\'[data-hem-full-value127="number.gain_0_heat"]\')';assert s.count(anchor)==2
s=s.replace(anchor,'        modal.locator("[data-settings-advanced-b8]").check()\n'+anchor,1);p.write_text(s)
p=Path('.github/tests/test_062b3_door_ui.py');s=p.read_text();a="            paired=group.locator('[data-hem-door-eco062]')";assert s.count(a)==1
p.write_text(s.replace(a,a+'\n            dialog.locator("[data-settings-advanced-b8]").check()'))
p=source/'manifest.json';s=p.read_text();assert '0.6.2b7' in s;p.write_text(s.replace('0.6.2b7','0.6.2b8'))
p=Path('.github/workflows/validate.yml');s=p.read_text();a='      - name: B7 direct settings saves and pending-value preservation\n';assert s.count(a)==1
p.write_text(s.replace(a,'      - name: B8 settings inventory, advanced presentation and exact duplicate aliases\n        run: |\n          python -I .github/scripts/audit_settings.py --check\n          python -I .github/tests/test_062b8_settings_audit.py\n'+a))
runpy.run_path('.github/scripts/audit_settings.py',run_name='__main__')
expected=json.loads(Path('.github/b8-expected.json').read_text())
for path,digest in expected.items():
 actual=blob(Path(path));assert actual==digest,(path,actual,digest)
print('All changed files match locally tested source')
