"""Final display-only unit correction; no physical state or service changes."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
changes=[
 ("    const observedTemp=a.measurements?.temperature ?? a.current_temperature;\n    if (numeric(observedTemp)) add(MOLD_DETAIL_LABELS[this._language()]?.[5] || t.physical,value(observedTemp,' °C'));\n    if (numeric(a.temperature)) add(t.target,value(a.temperature,' °C'));",
  "    const nativeUnit=a.temperature_unit || '°C';\n    const hasMeasuredTemp=numeric(a.measurements?.temperature);\n    const observedTemp=hasMeasuredTemp?a.measurements.temperature:a.current_temperature;\n    if (numeric(observedTemp)) add(MOLD_DETAIL_LABELS[this._language()]?.[5] || t.physical,value(observedTemp,' '+(hasMeasuredTemp?'°C':nativeUnit)));\n    if (numeric(a.temperature)) add(t.target,value(a.temperature,' '+nativeUnit));"),
 ("add(t.target,this._format(a.target_temp_low)+' - '+this._format(a.target_temp_high)+' °C');", "add(t.target,this._format(a.target_temp_low)+' - '+this._format(a.target_temp_high)+' '+nativeUnit);")
]
for filename in ('frontend/air-quality-advisor-card.js','.github/patches/card65.js'):
 path=ROOT/filename;text=path.read_text()
 for old,new in changes:
  if new in text and old not in text:continue
  assert text.count(old)==1,(filename,old)
  text=text.replace(old,new)
 path.write_text(text)
print('PASS: room measurements keep Celsius; native target/readout units remain explicit')
