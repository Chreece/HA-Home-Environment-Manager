"""Beta78 actual config/options method tests without a running HA instance.

Executes AST-extracted production methods using fake Home Assistant states and
ConfigFlow transaction methods. Verifies menu routing, first-use auto-default,
explicit [] persistence, reconfiguration without duplicate entry, and
three-way preservation of concurrent unrelated settings.
"""
import ast,asyncio,copy,json,sys,types
from pathlib import Path
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
app=ast.parse((ROOT/'config_flow.py').read_text(encoding='utf-8'))
compact=ast.parse((ROOT/'compact_options.py').read_text(encoding='utf-8'))
setup=ast.parse((ROOT/'room_setup.py').read_text(encoding='utf-8'))

def method(tree,cls,name):
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    return next(n for n in node.body
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                and n.name==name)

def assign(cls,tree,source,name,ns):
    node=method(tree,source,name)
    node.decorator_list=[]
    exec(compile(ast.Module(body=[node],type_ignores=[]),
                 source+'.py','exec'),ns)
    setattr(cls,name,ns[name])

pkg=types.ModuleType('beta78_fixture')
pkg.__path__=[]
occupancy=types.ModuleType('beta78_fixture.occupancy_policy')
occupancy.room_sensor_choices=lambda hass,area: (
    ['binary_sensor.bath_a','binary_sensor.bath_b'] if area=='badezimmer'
    else ['binary_sensor.living']
)
sources=types.ModuleType('beta78_fixture.room_sources')
sources.label=lambda hass,eid:eid
setup_module=types.ModuleType('beta78_fixture.room_setup')
sys.modules.update({
    'beta78_fixture':pkg,
    'beta78_fixture.occupancy_policy':occupancy,
    'beta78_fixture.room_sources':sources,
    'beta78_fixture.room_setup':setup_module,
})
# Stubs only for UI interaction plumbing; the methods under test are real.
ha=types.ModuleType('homeassistant');ha.__path__=[]
helpers=types.ModuleType('homeassistant.helpers');helpers.__path__=[]
areas=types.ModuleType('homeassistant.helpers.area_registry')
areas.async_get=lambda hass:N(async_get_area=lambda a:N(name=a) if a in ('badezimmer','wohnzimmer') else None)
helpers.area_registry=areas
sys.modules.update({'homeassistant':ha,'homeassistant.helpers':helpers,
                    'homeassistant.helpers.area_registry':areas})
class Probatio:
    @staticmethod
    def Schema(fields):return fields
defaults={}
def field(key,value=None,*,required=False):
    defaults[key]=copy.deepcopy(value)
    return key
ns={'__name__':'beta78_fixture.config_flow','__package__':'beta78_fixture',
    'probatio':Probatio,'_field':field,'_select':lambda choices,**kw:choices,
    'CONF_AREAS':'areas','CONF_CLIMATE_ROOMS':'climate_rooms',
    'deepcopy':copy.deepcopy}

merge_node=next(n for n in setup.body if isinstance(n,ast.FunctionDef)
                and n.name=='_merge')
exec(compile(ast.Module(body=[merge_node],type_ignores=[]),'room_setup.py','exec'),
     {'deepcopy':copy.deepcopy} if False else ns)
setup_module._merge=ns['_merge']

class UI:
    def __init__(self):
        self.entry=N(entry_id='existing',unique_id='home',
                     data={'areas':['badezimmer','wohnzimmer']},
                     options={'climate_rooms':{'badezimmer':{
                         'enabled':True,'selected_devices':['climate.dry']}}})
        self.config_entry=self.entry
        self.hass=N(states=N(get=lambda eid:N(name=eid)))
        self.edits=[]
        self.created=[]
        self.reloaded=[]
        self._room_occupancy_area=None
    def _get_reconfigure_entry(self):return self.entry
    def _edit_sections(self):
        return ['room_occupancy','general_settings','area_settings',
                'outside_data','delivery','thresholds','climate','pid','setup_rooms']
    def _start_room_setup(self):
        self._values=copy.deepcopy(self._values)
        self._setup_base=copy.deepcopy(self._values)
        self._setup_order=[];self._setup_index=0
    def _device_areas(self):
        return [{'value':'badezimmer','label':'Badezimmer'},
                {'value':'wohnzimmer','label':'Wohnzimmer'}]
    def async_show_menu(self,**kw):return {'type':'menu',**kw}
    def async_show_form(self,**kw):return {'type':'form',**kw}
    def async_abort(self,reason):return {'type':'abort','reason':reason}
    async def async_set_unique_id(self,value,**kw):self.unique_id=value
    def _abort_if_unique_id_mismatch(self):
        assert self.unique_id==self.entry.unique_id
    def async_update_reload_and_abort(self,entry,*,options,reload_even_if_entry_is_unchanged):
        assert entry is self.entry
        assert reload_even_if_entry_is_unchanged is False
        self.edits.append(copy.deepcopy(options))
        return {'type':'abort','reason':'reconfigure_successful'}
    def async_create_entry(self,**kwargs):
        self.created.append(kwargs)
        return {'type':'create_entry',**kwargs}

assign(UI,compact,'CompactOptionsMixin','async_step_room_occupancy',ns)
assign(UI,compact,'CompactOptionsMixin','async_step_room_occupancy_sources',ns)
assign(UI,app,'AirQualityConfigFlow','async_step_reconfigure',ns)
assign(UI,app,'AirQualityConfigFlow','_finish',ns)
ns['ConfigFlowResult']=dict
async def run():
    f=UI()
    first=await f.async_step_reconfigure()
    assert first['type']=='menu' and first['step_id']=='reconfigure'
    assert 'room_occupancy' in first['menu_options'] and 'setup_rooms' in first['menu_options']
    choose=await f.async_step_room_occupancy()
    assert choose['type']=='form'
    assert choose['step_id']=='room_occupancy'
    next_page=await f.async_step_room_occupancy({'room_occupancy_area':'badezimmer'})
    assert next_page['step_id']=='room_occupancy_sources',next_page
    assert defaults['room_occupancy_sensors']==[
        'binary_sensor.bath_a','binary_sensor.bath_b'],defaults
    # Changing another device property concurrently must not be overwritten.
    f.entry.options['climate_rooms']['badezimmer']['external_change']='kept'
    f.entry.options['another_setting']={'foo':42}
    done=await f.async_step_room_occupancy_sources({
        'room_occupancy_sensors':['binary_sensor.bath_b']})
    assert done['type']=='abort' and done['reason']=='reconfigure_successful'
    updated=f.edits[-1]
    assert updated['climate_rooms']['badezimmer']['occupancy_sensors']==[
        'binary_sensor.bath_b']
    assert updated['climate_rooms']['badezimmer']['selected_devices']==['climate.dry']
    assert updated['climate_rooms']['badezimmer']['external_change']=='kept'
    assert updated['another_setting']=={'foo':42}
    assert f.created==[]

    # Explicitly cleared selection remains cleared at the next edit,
    # including when Home Assistant omits the field entirely.
    f2=UI()
    f2.entry.options['climate_rooms']['badezimmer']['occupancy_sensors']=[]
    await f2.async_step_reconfigure()
    f2._room_occupancy_area='badezimmer'
    page=await f2.async_step_room_occupancy_sources()
    assert page['type']=='form' and defaults['room_occupancy_sensors']==[]
    saved=await f2.async_step_room_occupancy_sources({})
    assert saved['type']=='abort'
    assert f2.edits[-1]['climate_rooms']['badezimmer']['occupancy_sensors']==[]

    # Only one room is modified; never force equipment auto_control ON.
    f3=UI()
    await f3.async_step_reconfigure()
    f3._room_occupancy_area='badezimmer'
    await f3.async_step_room_occupancy_sources({'room_occupancy_sensors':[]})
    assert f3.edits[-1]['climate_rooms']['badezimmer']['enabled'] is True
    assert f3.edits[-1]['climate_rooms']['badezimmer'].get('auto_control') is None

asyncio.run(run())
for file in [ROOT/'strings.json',*(ROOT/'translations').glob('*.json')]:
    data=json.loads(file.read_text(encoding='utf-8'))
    menus=data['config']['step']['reconfigure']['menu_options']
    assert 'room_occupancy' in menus and 'setup_rooms' in menus
    assert data['options']['step']['room_occupancy_sources']['data']['room_occupancy_sensors']
    assert all(key in data['config']['step'] for key in menus),file
print('BETA78_MENU_AND_PER_ROOM_CONFIG_EDIT=PASS')
