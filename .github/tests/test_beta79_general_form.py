"""Beta79 consolidated General settings uses actual RoomSetupMixin method.

Smoke tests schema completeness, pollen/threshold storage, invalid ranges and
that opening the form itself does not mutate configuration. No service calls.
"""
import ast,asyncio,copy,sys,types
from pathlib import Path
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
tree=ast.parse((ROOT/'room_setup.py').read_text(encoding='utf-8'))
klass=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='RoomSetupMixin')
node=next(x for x in klass.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='async_step_setup_general')
keys={}
class P:
    @staticmethod
    def Schema(x):return x
class Selectors:
    class NumberSelectorMode:
        BOX='box'
    def NumberSelectorConfig(self,**kw):return kw
    def NumberSelector(self,config):return ('number',config)
    def BooleanSelector(self):return ('bool',)
sel=Selectors()
def field(k,v):
    keys[k]=v
    return k
def select(items,**kwargs):return ('select',items)
configkeys={
'CONF_WEATHER':'weather_entities','CONF_OUTDOOR':'outdoor_sensors',
'CONF_WARNINGS':'weather_warnings','CONF_NOTIFY_TARGETS':'notify_entities',
'CONF_MEDIA_PLAYERS':'media_players','CONF_TTS_ENGINE':'tts_engine',
'CONF_AI_AGENT':'ai_conversation_agent','CONF_LANGUAGE':'language',
'CONF_USE_MOLD':'use_mold_indicator','CONF_AWAY_WINDOWS_ALERT':'away_open_window_alert',
'CONF_AWAY_WINDOWS_PERSONS':'away_windows_target_people',
'CONF_AWAY_WINDOWS_DELIVERY':'away_windows_delivery_channels',
'CONF_HUB':'use_announcement_hub','CONF_OCCUPANCY_GLOBAL':'occupancy_global',
'CONF_ENVIRONMENT_GLOBAL':'environment_global','CONF_THRESHOLDS':'thresholds',
}
limits={
'outdoor_aqi':50.,'outdoor_co2':800.,'outdoor_pm25':15.,'outdoor_pm10':45.,
'outdoor_voc':500.,'outdoor_voc_parts':500.,'outdoor_no2':25.,'outdoor_o3':100.,
'outdoor_so2':40.,'indoor_aqi':100.,'indoor_co2':1000.,'indoor_pm25':25.,
' indoor_pm10'.strip():45.,'indoor_voc':500.,'indoor_voc_parts':500.,
'indoor_humidity':65.,'indoor_mold':70.,'min_outdoor_temp':5.,
'max_outdoor_temp':32.,'max_outdoor_humidity':85.,'max_wind_kmh':35.,
'max_age_minutes':90.,
}
pkg=types.ModuleType('beta79_general');pkg.__path__=[]
languages=types.ModuleType('beta79_general.languages')
languages.SUPPORTED_LANGUAGE_TAGS=('en','el')
languages.resolve_language=lambda x:x
ai=types.ModuleType('beta79_general.ai_rewrite')
ai.DEFAULT_AGENT='none'
tts=types.ModuleType('beta79_general.tts_languages')
tts.language_options=lambda hass,x:[{'value':'auto','label':'Auto'}]
tts.preferred_language=lambda hass,engine,choice:'auto'
hub=types.ModuleType('beta79_general.hub_delivery')
hub.hub_installed=lambda hass:False
sys.modules.update({
 'beta79_general':pkg,'beta79_general.languages':languages,
 'beta79_general.ai_rewrite':ai,'beta79_general.tts_languages':tts,
 'beta79_general.hub_delivery':hub,
})
ns={'__name__':'beta79_general.room_setup','__package__':'beta79_general',
    'Any':object,'selector':sel,'probatio':P,'field':field,'select':select,
    'deepcopy':copy.deepcopy,'math':__import__('math'),
    '_merge':lambda base,edited,current:edited,'DEFAULT_THRESHOLDS':limits}
ns.update(configkeys)
exec(compile(ast.Module(body=[node],type_ignores=[]),'room_setup.py','exec'),ns)
real=ns['async_step_setup_general']

class UI:
    def __init__(self):
        self._values={
          'weather_entities':['weather.home'],
          'outdoor_sensors':['sensor.outdoor'],
          'weather_warnings':[],
          'notify_entities':[],
          'media_players':[],
          'tts_engine':None,
          'ai_conversation_agent':'none',
          'language':'auto',
          'use_mold_indicator':False,
          'away_open_window_alert':False,
          'occupancy_global':{
            'occupied_rooms_entity':'input_text.occupied_rooms',
            'occupied_rooms_attribute':'',
            'source_stale_minutes':120,
            'home_policy':'any_home',
          },
          'environment_global':{
            'pollen_entities':[], 'pollen_high_from':3.,
            'pollen_max_scale':5.,'pollen_avoid_ventilation':False,
          },
          'thresholds':copy.deepcopy(limits),
        }
        self.config_entry=N(data={},options=copy.deepcopy(self._values))
        self.hass=N()
        self._setup_order=[];self._setup_index=0;self._editing=True
        self._setup_base=copy.deepcopy(self._values)
        self.saved=0
    def _general_options(self):
        return {
          'weather_entities':[{'value':'weather.home'}],
          'outdoor_sensors':[{'value':'sensor.outdoor'}],
          'weather_warnings':[],
          'notify_entities':[],
          'media_players':[],
          'tts_engine':[{'value':'none'}],
          'ai_conversation_agent':[{'value':'none'}],
          'pollen_entities':[],
          'general_room_occupancy_sensors':[],
          'general_home_trackers':[],
          'general_occupied_rooms_entity':[
               {'value':'none'},{'value':'input_text.occupied_rooms'}],
          'general_sleep_rooms_entity':[{'value':'none'}],
          'away_windows_target_people':[],
          'away_windows_delivery_channels':[{'value':'mobile_notification'}],
        }
    def _room_attribute_options(self,hass,entity):
        return [{'value':'__state__'}]
    def async_show_form(self,**kw):return kw
    def async_abort(self,reason):return {'abort':reason}
    async def _finish(self):
        self.saved+=1
        return {'saved':copy.deepcopy(self._values)}

async def run():
    ui=UI()
    page=await real(ui)
    assert page['step_id']=='setup_general'
    assert ui.saved==0
    assert all('global_threshold_'+k in page['data_schema'] for k in limits)
    assert all(k in page['data_schema'] for k in (
       'general_occupied_rooms_entity','general_sleep_rooms_entity',
       'general_home_trackers','general_room_occupancy_sensors',
       'general_home_policy','general_source_stale_minutes',
       'pollen_high_from','pollen_max_scale','pollen_avoid_ventilation',
       'weather_entities','outdoor_sensors','notify_entities',
    ))
    assert keys['global_threshold_indoor_humidity']==65.
    assert keys['general_source_stale_minutes']==120
    new=await real(ui,{
      'global_threshold_indoor_humidity':62.,
      'general_source_stale_minutes':90.,
      'pollen_high_from':2.,
      'pollen_max_scale':7.,
      'pollen_avoid_ventilation':True,
    })
    assert ui.saved==1,new
    saved=new['saved']
    assert saved['thresholds']['indoor_humidity']==62.
    assert saved['thresholds']['indoor_co2']==1000.
    assert saved['occupancy_global']['source_stale_minutes']==90.
    assert saved['environment_global']['pollen_high_from']==2.
    assert saved['environment_global']['pollen_max_scale']==7.
    assert saved['environment_global']['pollen_avoid_ventilation'] is True
    invalid=UI()
    bad=await real(invalid,{'global_threshold_min_outdoor_temp':50.})
    assert bad['errors']['global_threshold_min_outdoor_temp']=='temperature_range',bad['errors']
    assert invalid.saved==0
    print('BETA79_GENERAL_CONSOLIDATED_SCHEMA_AND_VALIDATION=PASS')

asyncio.run(run())
