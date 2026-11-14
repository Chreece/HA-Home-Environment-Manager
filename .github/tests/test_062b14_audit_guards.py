"""B14: prevent regression in HA callback and privileged identity guards.

The mobile review handler is invoked by HA's async event bus, so it must be
marked @callback before it calls hass.async_create_task. The dashboard owner
must remain behind the pre-existing exact recommendation ACL check.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
init=ast.parse((ROOT/"__init__.py").read_text(encoding="utf-8"))
handlers=[node for node in ast.walk(init) if isinstance(node,ast.FunctionDef)
          and node.name=="_pid_mobile_review_action"]
assert len(handlers)==1
handler=handlers[0]
assert any(isinstance(d,ast.Name) and d.id=="callback"
           for d in handler.decorator_list), "HA sync event listener must run on the event loop"
assert any(isinstance(node,ast.Attribute) and node.attr=="async_create_task"
           for node in ast.walk(handler))

source=(ROOT/"dashboard_api.py").read_text(encoding="utf-8")
assert "@callback\ndef websocket_dashboard" in source
assert source.index("connection.user") < source.index('result["owner_entry_id"]')
assert source.index("check_entity(entity_id, POLICY_READ)") < source.index(
    'result["owner_entry_id"]')
assert source.index("manager.entry.entry_id != entry_id") < source.index(
    'result["owner_entry_id"]')
assert 'result["controllers"] = controller_inventory(manager)' in source

faults=(ROOT/"device_faults.py").read_text(encoding="utf-8")
assert "OFFLINE_NOTICE_DELAY_SECONDS = 180" in faults
assert 'watched[upstream].add(spec.identifier)' in faults
assert "self._offline_logged" in faults
assert 'return await async_submit_hub' in faults
assert "return notified" in faults
print("HEM_B14_AUDIT_GUARDS=PASS")
