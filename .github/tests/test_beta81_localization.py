"""Beta81: verify all real HA form translation keys and contextual help.

Beta79/80 introduced new form step IDs not shown by some installed custom
integration locales, even though JSON contained those keys. The editing
forms now use the established translated step IDs used since setup.
"""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
locales=[ROOT/"strings.json",*sorted((ROOT/"translations").glob("*.json"))]
assert len(locales)==39,len(locales)
for file in locales:
    j=json.loads(file.read_text(encoding="utf-8"))
    for flow in ("options","config"):
        steps=j[flow]["step"]
        menu=steps["init" if flow=="options" else "reconfigure"]
        assert menu["description"],(file,flow,"menu instructions")
        assert menu["menu_option_descriptions"]["choose_rooms"],(file,flow)
        assert menu["menu_option_descriptions"]["general_settings"],(file,flow)
        for alias in ("setup_rooms","choose_rooms"):
            f=steps[alias]
            assert f["title"] and f["description"],(file,flow,alias)
            assert f["data"]["areas"] and f["data"]["areas"]!="areas",(file,flow,alias)
            assert f["data_description"]["areas"],(file,flow,alias,"help")
        for alias in ("edit_room","room_settings"):
            f=steps[alias]
            assert f["title"] and f["description"],(file,flow,alias)
            for key in ("windows","air_quality","temperature","humidity",
                        "pressure","climate_devices","shades","occupancy_sensors"):
                assert f["data"][key] and f["data_description"][key],(file,flow,alias,key)
        assert steps["setup_general"]["title"],(file,flow,"general title")

# Exact frontend lookup keys: options/config.step.STEP_ID.title/data/data_description.
# The new short editor can therefore render without ever showing raw "areas".
g=json.loads((ROOT/"translations/el.json").read_text(encoding="utf-8"))
assert g["options"]["step"]["setup_rooms"]["title"]=="Επιλογή δωματίων"
assert g["options"]["step"]["setup_rooms"]["data"]["areas"]=="Δωμάτια προς παρακολούθηση"
assert g["options"]["step"]["setup_rooms"]["data_description"]["areas"].startswith("Επίλεξε")
assert g["options"]["step"]["edit_room"]["title"]=="Ρυθμίσεις · {area_name}"
assert g["options"]["step"]["setup_general"]["title"]=="Γενικές ρυθμίσεις"
assert "γενικά όρια ασφαλείας" in g["options"]["step"]["init"]["description"]
for name, expected in [("en","General settings"),("de","Allgemeine Einstellungen"),
                       ("el","Γενικές ρυθμίσεις")]:
    # The actual executor function loads these files; no hardcoded locale map.
    m=json.loads((ROOT/f"translations/{name}.json").read_text(encoding="utf-8"))
    assert m["options"]["step"]["init"]["menu_options"]["setup_general"]==expected
    assert m["options"]["step"]["setup_general"]["title"]==expected

src=ast.parse((ROOT/"reconfigure_rooms.py").read_text(encoding="utf-8"))
k=next(n for n in src.body if isinstance(n,ast.ClassDef) and n.name=="ReconfigureRoomsMixin")
methods={n.name:n for n in k.body if isinstance(n,ast.AsyncFunctionDef)}
for key in ("async_step_setup_rooms","async_step_edit_room","async_step_choose_rooms","async_step_room_settings"):
    assert key in methods,key
for method,step in [("async_step_choose_rooms","setup_rooms"),
                    ("async_step_room_settings","edit_room")]:
    tree=methods[method]
    results=[n.value for n in ast.walk(tree) if isinstance(n,ast.keyword) and n.arg=="step_id"]
    assert any(isinstance(n,ast.Constant) and n.value==step for n in results),(method,step)
print("BETA81_39_CATALOGS_ALL_LOCALIZED_MENU_AND_FORM_FIELDS=PASS")
