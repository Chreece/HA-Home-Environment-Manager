"""Regression checks for translated controller statuses.

Run from repository root:
    python3 tests/check_controller_status_translations.py

No Home Assistant instance is required; it never touches equipment.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _catalog() -> tuple[set[str], set[str]]:
    tree = ast.parse((ROOT / "controller_status_catalog.py").read_text(encoding="utf-8"))
    found: dict[str, set[str]] = {}
    for item in tree.body:
        if not isinstance(item, ast.Assign) or len(item.targets) != 1:
            continue
        target = item.targets[0]
        if (not isinstance(target, ast.Name)
                or target.id not in {"CONTROLLER_STATUS_CODES", "EQUIPMENT_SENSOR_STATUSES"}):
            continue
        assert isinstance(item.value, ast.Call) and len(item.value.args) == 1
        found[target.id] = set(ast.literal_eval(item.value.args[0]))
    return found["CONTROLLER_STATUS_CODES"], found["EQUIPMENT_SENSOR_STATUSES"]


def main() -> None:
    all_codes, equipment = _catalog()
    assert equipment and equipment <= all_codes
    assert "pid_output_inactive" in equipment
    assert "sleep_room_evidence_unknown" in equipment
    assert "room_not_occupied" in equipment
    assert "startup_warmup" in equipment

    catalogs = [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]
    assert len(catalogs) == 39, "Expected strings.json plus all 38 language files"
    for file in catalogs:
        data = json.loads(file.read_text(encoding="utf-8"))
        status = data["entity"]["sensor"]["equipment_control_status"]["state"]
        assert set(status) == all_codes, f"{file}: missing or extra status codes"
        assert all(isinstance(label, str) and label.strip()
                   and label != key for key, label in status.items()), f"{file}: raw status text"
        assert "_" not in status["pid_output_inactive"], f"{file}: PID state not readable"
    for locale in ("el", "de"):
        raw = (ROOT / "translations" / f"{locale}.json").read_text(encoding="utf-8")
        values = json.loads(raw)["entity"]["sensor"]["equipment_control_status"]["state"]
        assert values["pid_output_inactive"] != json.loads(
            (ROOT / "translations" / "en.json").read_text(encoding="utf-8")
        )["entity"]["sensor"]["equipment_control_status"]["state"]["pid_output_inactive"]
    print(f"PASS: {len(all_codes)} states, {len(equipment)} equipment options, 38 locales")


if __name__ == "__main__":
    main()
