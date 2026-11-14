"""Backend/frontend Home settings step contract; use production async menu method.

The previous browser fixture invented 'setup_general' as a menu option although
the real menu exposes 'general_settings'. This regression executes the actual
ReconfigureRoomsMixin methods without contacting a Home Assistant instance.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "custom_components/environment_manager"
CARD = PYTHON / "frontend/air-quality-advisor-card.js"
SETUP = PYTHON / "reconfigure_rooms.py"
FLOW = PYTHON / "config_flow.py"


def method(tree: ast.Module, class_name: str, name: str) -> ast.AsyncFunctionDef:
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == class_name)
    node = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef)
                and n.name == name)
    return node


config = ast.parse(FLOW.read_text(encoding="utf-8"))
flow_mixin = next(n for n in config.body if isinstance(n, ast.ClassDef)
                  and n.name == "_FlowMixin")
assert isinstance(flow_mixin.bases[0], ast.Name)
assert flow_mixin.bases[0].id == "ReconfigureRoomsMixin", (
    "Settings menu provider changed; inspect its actual route before shipping"
)

tree = ast.parse(SETUP.read_text(encoding="utf-8"))
names = ("_room_edit_menu", "async_step_general_settings")
nodes = [method(tree, "ReconfigureRoomsMixin", name) for name in names]
ns = {
    "_locale_menu": lambda language: (
        "Επιλογή δωματίων", "Γενικές ρυθμίσεις", "Ρυθμίσεις · {area_name}"
    ),
}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SETUP), "exec"), ns)

class Options:
    context = {"language": "el"}

    def __init__(self):
        self.hass = SimpleNamespace(
            config=SimpleNamespace(language="en"),
            async_add_executor_job=self.executor,
        )
        self.general_calls = 0

    async def executor(self, fn, *args):
        return fn(*args)

    def _selected_edit_rooms(self):
        return [("wohnzimmer", "Wohnzimmer"), ("badezimmer", "Badezimmer")]

    async def async_step_setup_general(self, user_input=None):
        self.general_calls += 1
        return {"type": "form", "step_id": "setup_general",
                "data_schema": [{"name": "weather_entities",
                                 "selector": {"select": {"multiple": True}}}]}


async def verify():
    options = Options()
    menu = await ns["_room_edit_menu"](options)
    assert list(menu) == [
        "choose_rooms", "edit_room_wohnzimmer", "edit_room_badezimmer",
        "general_settings",
    ], menu
    assert "setup_general" not in menu
    assert menu["general_settings"] == "Γενικές ρυθμίσεις"
    form = await ns["async_step_general_settings"](options)
    assert form["step_id"] == "setup_general" and options.general_calls == 1
    source = CARD.read_text(encoding="utf-8")
    home = source.split("/* HEM_HOME_SETTINGS128_START", 1)[1].split(
        "/* HEM_HOME_SETTINGS128_END", 1)[0]
    assert 'options.includes("general_settings")' in home
    assert 'next_step_id:"general_settings"' in home
    assert 'form.step_id!=="setup_general"' in home or (
        'form.step_id!=="setup_general"' in source
    )
    assert 'next_step_id:"setup_general"' not in home

    # The monitored-room Options menu's choose_rooms handler deliberately
    # returns the long-established setup_rooms form. A B10 frontend expecting
    # choose_rooms as the FORM step will reject every valid HA response.
    chooser = method(tree, "ReconfigureRoomsMixin", "async_step_choose_rooms")
    shown = [node for node in ast.walk(chooser)
             if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Attribute) and
             node.func.attr == "async_show_form"]
    assert len(shown) == 1
    steps = [kw.value.value for kw in shown[0].keywords
             if kw.arg == "step_id" and isinstance(kw.value, ast.Constant)]
    assert steps == ["setup_rooms"], steps
    assert "next_step_id:'choose_rooms'" in source
    assert "['setup_rooms','choose_rooms'].includes(form.step_id)" in source
    assert "hem-settings-source-actions-b15" in source
    print("PASS: real backend choose_rooms menu -> setup_rooms form -> Home UI")


asyncio.run(verify())
