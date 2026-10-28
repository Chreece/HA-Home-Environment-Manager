"""Reproducible one-time Beta68 build from immutable Beta66 and Beta67 inputs."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(sys.argv[1]).resolve()
assert json.loads((ROOT/'manifest.json').read_text())['version']=='0.6.0b67'
hashes={
 '.github/scripts/apply_beta66.py':'951fda5cdbc57d1e08cb6712032303113ebf2f62eeff5db2bfa766a8ca71389d',
 '.github/patches/equipment_window66.py':'88fe998c0b9372178ad8b8e0a0261c95fa7d07be5d1e7df6bae7ae198537ce96',
 '.github/patches/card66.tsv':'77d2941e8f6619f5011ae864e6b65dc0772d8ea1c09a644c95627fd41feb5fc6',
 '.github/patches/card66.js':'39eaa176087fa0ab3d025504e029c9a45c06fddf436611835291df708ae4957a',
 '.github/tests/test_beta66_windows.py':'ffd10e71c78a53fa6808efea98aad8359909f6fe21a8bd5d33f1883eeb2d0754',
 '.github/tests/test_beta66_browser.py':'d8dab3273bdf8159cab17ad46cfc3541277d1ce2702743686f44583363f18427',
}
for name,expected in hashes.items():
 assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==expected,name
 if name!='.github/scripts/apply_beta66.py':
  (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(BASE/name,ROOT/name)
# All AQI identity/detection/options implementation must remain unchanged.
aqis=('aqi_sources.py','aqi_names.py','compact_options.py','device_controls.py',
      'select.py','number.py','environment_extended.py','environment.py')
before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in aqis}
source=(BASE/'.github/scripts/apply_beta66.py').read_text()
source=source.replace("in ('0.6.0b65','0.6.0b66')","in ('0.6.0b67','0.6.0b68')")
source=source.replace("meta['version']='0.6.0b66'","meta['version']='0.6.0b68'")
exec(compile(source,'verified_beta66_feature_restore','exec'),{
 '__file__':str(ROOT/'.github/scripts/apply_beta66.py'),'__name__':'__main__'})
patch=ROOT/'.github/patches/stability68.patch'
subprocess.run(['git','apply','--check',str(patch)],cwd=ROOT,check=True)
subprocess.run(['git','apply',str(patch)],cwd=ROOT,check=True)
for path,digest in before.items():
 assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,('AQI implementation changed',path)
meta=json.loads((ROOT/'manifest.json').read_text())
assert meta['domain']=='environment_manager' and meta['version']=='0.6.0b68'
assert len(list((ROOT/'translations').glob('*.json')))==38
print('PASS: Beta66 features restored; Beta67 AQI unchanged; bounded update patch applied')
