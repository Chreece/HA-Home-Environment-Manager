"""HEM b11 branding validation: SVG, PNG, locale coverage and safe frontend hooks."""
from __future__ import annotations
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import zlib

ROOT=Path(__file__).resolve().parents[2]
INTEGRATION=ROOT/'custom_components/environment_manager'
CARD=INTEGRATION/'frontend/air-quality-advisor-card.js'
source=CARD.read_text(encoding='utf-8')

for path in (ROOT/'.github/assets/hem-banner.svg',
             ROOT/'.github/assets/hem-mark.svg',
             ROOT/'.github/assets/hem-logo.svg'):
    root=ET.parse(path).getroot()
    assert root.tag.endswith('svg') and root.get('viewBox'), path
    assert path.stat().st_size < 25000, path
banner=(ROOT/'.github/assets/hem-banner.svg').read_text('utf-8')
assert 'Ventilation ready' in banner and 'Humidity' in banner and 'Mold' in banner

assert 'class="hem-brand-mark125"' in source
assert 'class="hem-brand-title125"' in source
assert '>HEM</h2>' in source
assert 'hem-arrival-action124' in source
assert 'hem-arrival-label124' not in source
assert 'data-detail-id="hem-arrival-help125"' not in source
assert 'help.purpose' in source
assert 'HEM_CARD_SETTINGS126_START' in source
assert 'mdi:information-outline' in source
assert '_arrivalAction124(button)' in source
help_map=json.loads(source.split('const ARRIVAL_HELP125=',1)[1].split(';',1)[0])
locales={p.stem for p in (INTEGRATION/'translations').glob('*.json')}
assert locales == set(help_map),(locales-set(help_map),set(help_map)-locales)
assert all(isinstance(v,str) and len(v.strip())>=4 for v in help_map.values())
# Asset validity is independent of the release number. Require a valid beta,
# not one specific manifest version that would break each later beta.
version=json.loads((INTEGRATION/'manifest.json').read_text('utf-8'))['version']
assert isinstance(version,str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+b[0-9]+',version),version

def verify_png(path, size):
    blob=path.read_bytes()
    assert blob[:8]==b'\x89PNG\r\n\x1a\n',(path,'signature')
    position=8
    chunks=[]
    pixel_data=[]
    while position<len(blob):
        length=struct.unpack('>I',blob[position:position+4])[0]
        tag=blob[position+4:position+8]
        payload=blob[position+8:position+8+length]
        actual=struct.unpack('>I',blob[position+8+length:position+12+length])[0]
        assert zlib.crc32(tag+payload)==actual,(path,tag,'crc')
        position+=12+length
        chunks.append(tag)
        if tag==b'IHDR':
            assert struct.unpack('>II',payload[:8])==size,(path,size,payload[:8])
            assert payload[8:10]==b'\x08\x06'
        if tag==b'IDAT':pixel_data.append(payload)
    assert position==len(blob) and chunks[0]==b'IHDR' and chunks[-1]==b'IEND'
    raw=zlib.decompress(b''.join(pixel_data))
    assert len(raw)==size[1]*(size[0]*4+1),(path,'pixel data')
    assert any(raw[i]!=0 for i in range(4,len(raw),4)),(path,'nonempty')
    return blob

brand=INTEGRATION/'brand'
icons=[('icon.png',(256,256)),('icon@2x.png',(512,512)),
       ('dark_icon.png',(256,256)),('dark_icon@2x.png',(512,512)),
       ('logo.png',(400,128)),('logo@2x.png',(800,256)),
       ('dark_logo.png',(400,128)),('dark_logo@2x.png',(800,256))]
for key,dimensions in icons:verify_png(brand/key,dimensions)
assert (brand/'logo.png').read_bytes() != (brand/'dark_logo.png').read_bytes()
print('PASS: HEM b11 branding, 8 PNGs, all 38 locale titles and safe arrival markup')
