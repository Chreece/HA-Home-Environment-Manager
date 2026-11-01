"""Complete native capability identity metadata; safe and idempotent."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for name in ('equipment_feature_registration.py','.github/patches/stability68.patch'):
 p=ROOT/name;s=p.read_text()
 old='"supported_features", "hvac_modes", "fan_modes", "swing_modes",'
 new='"device_class", "supported_features", "hvac_modes", "fan_modes", "swing_modes",'
 if new not in s:
  assert s.count(old)==1,(name,s.count(old));p.write_text(s.replace(old,new))
print('PASS capability fingerprint includes real humidity device class')
