"""Real Home source discovery, legacy orphans and numeric pollen validation.

The only fixtures are HA registries/states and other integration boundaries;
the production methods are parsed unchanged from room_setup.py.
"""
import ast
import asyncio
import copy
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace as N

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / '.github/tests/test_beta79_general_form.py'))
module = fixture['ns']
UI = fixture['UI']
text = (ROOT / 'custom_components/environment_manager/room_setup.py').read_text()
tree = ast.parse(text)
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RoomSetupMixin')
method = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == '_general_options')

prefix = 'beta79_general'
discovery = sys.modules[prefix + '.discovery']
discovery.outdoor_choices = lambda *args: []
discovery.warning_choices = lambda *args: []
discovery._device_class = lambda h,s: s.attributes.get('device_class')
discovery.entity_area = lambda *args: None

ai = sys.modules[prefix + '.ai_rewrite']
ai.conversation_agent_choices = lambda *args: [{'value':'none'}]
flow = types.ModuleType(prefix + '.config_flow')
flow._tts_player_options = lambda *args: []
sys.modules[flow.__name__] = flow
wake = types.ModuleType(prefix + '.wake_alarm')
wake.wake_source_options = lambda *args: ([], [])
sys.modules[wake.__name__] = wake

source = N(label=lambda h,e:e, native=lambda h,e: True)
module.update(sources=source, CONF_AREAS='areas')
exec(compile(ast.Module(body=[method], type_ignores=[]), str(ROOT/'room_setup.py'), 'exec'), module)
UI._general_options = module['_general_options']
UI._room_source_options = lambda self,h: []

class States:
    def __init__(self, selected): self.values={s.entity_id:s for s in selected}
    def async_all(self, domain):return [s for s in self.values.values() if s.entity_id.startswith(domain + '.')]
    def get(self, entity):return self.values.get(entity)

def state(entity,value,device_class=None):
    return N(entity_id=entity,state=value,
        attributes={'device_class':device_class} if device_class else {})

ui=UI()
ui._values['environment_global']['pollen_entities'] = [ 'sensor.missing_old' ]
ui._values['weather_entities']=['weather.missing']
ui.hass.states=States([
    state('sensor.birch_index','2.1'),
    state('sensor.grass_level','3.0'),
    state('sensor.unrelated_temperature','20',device_class='temperature'),
    state('sensor.outdoor_pollen','2.2'),
    state('sensor.bad_index','nan'),
])
options=ui._general_options()
pollen={o['value'] for o in options['pollen_entities']}
assert {'sensor.birch_index','sensor.grass_level','sensor.outdoor_pollen','sensor.missing_old'} <= pollen,pollen
assert 'sensor.unrelated_temperature' not in pollen
assert 'sensor.bad_index' not in pollen
assert {'value':'weather.missing','label':'weather.missing · unavailable / saved'} in options['weather_entities']

async def scenario():
    # Defaults must *not* auto-enroll every numeric source, even on first setup.
    new=UI();new.hass.states=ui.hass.states
    new._values['environment_global'].pop('pollen_entities')
    form=await module['async_step_setup_general'](new)
    default = fixture['keys']['pollen_entities']
    assert default==['sensor.outdoor_pollen'],default
    # A previously saved unavailable source cannot block an unrelated field.
    current=await module['async_step_setup_general'](ui,{'general_away_cooldown_minutes':15})
    assert current.get('saved'), current
    assert 'sensor.missing_old' in current['saved']['environment_global']['pollen_entities']
    assert current['saved']['occupancy_global']['away_cooldown_minutes']==15
    # A newly selected non-pollen named index is allowed only if numeric and
    # within the selected provider scale.
    good=UI();good.hass.states=ui.hass.states
    good._values['environment_global']['pollen_entities']=[]
    saved=await module['async_step_setup_general'](good,{'pollen_entities':['sensor.birch_index']})
    assert saved.get('saved'),saved
    bad=UI();bad.hass.states=ui.hass.states
    bad._values['environment_global']['pollen_entities']=[]
    denied=await module['async_step_setup_general'](bad,{'pollen_entities':['sensor.grass_level'],'pollen_max_scale':1})
    assert denied.get('errors',{}).get('pollen_entities')=='invalid_room_source',denied
    # The runtime requires scale >= 1. This must be rejected in the editor.
    invalid=UI();invalid.hass.states=ui.hass.states
    denied=await module['async_step_setup_general'](invalid,{'pollen_max_scale':0})
    assert denied.get('errors',{}).get('pollen_high_from')=='invalid_room_source',denied
    valid=UI();valid.hass.states=ui.hass.states
    output=await module['async_step_setup_general'](valid)
    assert output['data_schema']['pollen_max_scale'][1]['min']==1,output['data_schema']['pollen_max_scale']

asyncio.run(scenario())
print('PASS: numeric/non-English pollen choices, no implicit enrollment, orphaned source preservation, scale validation, unrelated saves')
