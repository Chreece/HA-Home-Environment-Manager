"""Regression for the actual Configure and native Reconfigure menu entrypoints.

Beta79 crashed *before returning a menu* because both paths passed the removed
_room_menu_placeholders attribute. Compile and invoke the exact production
async_step_* functions, with __getattr__ deliberately raising on that field.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
tree = ast.parse((ROOT / "config_flow.py").read_text(encoding="utf-8"))
methods = {}
for class_def in tree.body:
    if not isinstance(class_def, ast.ClassDef):
        continue
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and (
            (class_def.name, node.name) in {
                ("AirQualityConfigFlow", "async_step_reconfigure"),
                ("AirQualityOptionsFlow", "async_step_init"),
            }
        ):
            methods[node.name] = node

assert set(methods) == {"async_step_init", "async_step_reconfigure"}
ns = {"Any": object, "ConfigFlowResult": dict}
exec(compile(ast.Module(body=list(methods.values()), type_ignores=[]),
             "config_flow.py", "exec"), ns)

class MenuUI:
    def __init__(self):
        self.config_entry = SimpleNamespace(
            data={"areas": ["badezimmer"]},
            options={"climate_rooms": {"badezimmer": {"enabled": True}}},
        )
        self._values = {}
        self._start_calls = 0
        self._menu_calls = 0

    def __getattr__(self, name):
        # This reproduces the exact crash behavior of ReconfigureRoomsMixin.
        if name == "_room_menu_placeholders":
            raise AttributeError(name)
        raise AttributeError(name)

    def _get_reconfigure_entry(self):
        return self.config_entry

    def _start_room_setup(self):
        self._start_calls += 1
        assert self._values["areas"] == ["badezimmer"]

    async def _room_edit_menu(self):
        self._menu_calls += 1
        return {
            "choose_rooms": "Επιλογή δωματίων",
            "edit_room_badezimmer": "Ρυθμίσεις · Badezimmer",
            "general_settings": "Γενικές ρυθμίσεις",
        }

    def async_show_menu(self, **kwargs):
        return kwargs

async def run():
    options = MenuUI()
    page = await ns["async_step_init"](options)
    assert page["step_id"] == "init"
    assert list(page["menu_options"]) == [
        "choose_rooms", "edit_room_badezimmer", "general_settings"
    ], page
    assert "description_placeholders" not in page, page
    assert options._start_calls == options._menu_calls == 1
    assert options._values["climate_rooms"]["badezimmer"]["enabled"] is True

    reconfigure = MenuUI()
    page = await ns["async_step_reconfigure"](reconfigure)
    assert page["step_id"] == "reconfigure"
    assert list(page["menu_options"]) == [
        "choose_rooms", "edit_room_badezimmer", "general_settings"
    ], page
    assert "description_placeholders" not in page, page
    assert reconfigure._start_calls == reconfigure._menu_calls == 1
    assert reconfigure._reconfigure_initialized is True
    # Re-entering a menu must not wipe edits in progress.
    reconfigure._values["example_draft"] = ["preserve"]
    again = await ns["async_step_reconfigure"](reconfigure)
    assert again["step_id"] == "reconfigure"
    assert reconfigure._values["example_draft"] == ["preserve"]
    assert reconfigure._start_calls == 1
    assert reconfigure._menu_calls == 2
    print("BETA80_OPTIONS_AND_NATIVE_RECONFIGURE_MENU_NO_500=PASS")

asyncio.run(run())
