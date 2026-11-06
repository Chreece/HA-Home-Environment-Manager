"""Beta107: distinct, consistently sized room readings in real Chromium.

The production card receives deterministic native/average sensor fixtures.
No Home Assistant service, physical device, or network request is used. An
optional HEM_TEST_SCREENSHOT_DIR saves 590px/320px layout review images.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "frontend/air-quality-advisor-card.js"


def baseline_fixture():
    """Reuse only fixture definitions; importing Beta87 runs its whole suite."""
    path = ROOT / ".github/tests/test_beta87_compact_browser.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = []
    collecting = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "row":
            collecting = True
        if collecting and isinstance(node, ast.With):
            break
        if collecting:
            nodes.append(node)
    assert nodes and not any(isinstance(node, ast.With) for node in nodes)
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    assert {"rooms", "states", "data"} <= namespace.keys()
    return deepcopy(namespace["data"])


def evidence(value, ids):
    return {
        "value": value,
        "source_ids": ids,
        "source_count": len(ids),
        "trend": [
            {"t": 1793760000, "v": value - 0.4},
            {"t": 1793760900, "v": value - 0.2},
            {"t": 1793761800, "v": value},
        ],
    }


data = baseline_fixture()
states = {"sensor.hem": {"state": "ready", "attributes": {"dashboard": data}}}
room_specs = [
    ("Badezimmer", 19.4, 57.2, 59, 49, None),
    ("Gästezimmer", 19.3, 56.1, 63, 25, None),
    ("Küche", 21.4, 52.4, 60, None, None),
    ("Schlafzimmer", 17.4, 58.5, None, 10, None),
    ("Wohnzimmer", 20.0, 54.2, 59, None, 1),
]
for room, (name, temperature, humidity, mold, lux, pm25) in zip(data["rooms"], room_specs):
    area = room["area_id"]
    room.update(name=name, status="safe" if area == "room4" else "unknown", action=None)
    room["windows"] = []
    room["readings"] = []
    room["environment"]["measurement_evidence"] = measurements = {}
    for metric, value, unit in (
        ("temperature", temperature, "°C"),
        ("humidity", humidity, "%"),
    ):
        ids = [f"sensor.{area}_{metric}_a", f"sensor.{area}_{metric}_b"]
        measurements[metric] = evidence(value, ids)
        room["readings"].append({
            "metric": metric, "value": value, "unit": unit,
            "available": True, "name": metric.title(),
        })
        for index, entity_id in enumerate(ids):
            states[entity_id] = {"state": str(value + (-0.2 if index == 0 else 0.2)),
                "attributes": {"friendly_name": f"{name} {metric} {index + 1}",
                               "unit_of_measurement": unit}}
    if mold is not None:
        # This indication deliberately has no native source. It remains a
        # span beside clickable buttons, which exposed Beta105's font reset.
        room["readings"].append({
            "metric": "mold", "value": mold, "unit": "%",
            "available": True, "name": "Mold indication",
        })
    for metric, value, unit, label in (
        ("illuminance", lux, "lx", "Light"),
        ("pm25", pm25, "µg/m³", "PM2.5"),
    ):
        if value is None:
            continue
        entity_id = f"sensor.{area}_{metric}"
        room["readings"].append({
            "metric": metric, "value": value, "unit": unit,
            "available": True, "name": label, "entity_id": entity_id,
        })
        measurements[metric] = evidence(value, [entity_id])
        states[entity_id] = {"state": str(value), "attributes": {
            "friendly_name": f"{name} {label}", "unit_of_measurement": unit}}
data["summary"] = {"safe": 1, "attention": 0, "unknown": 4}
data["outdoor"].update(status="safe", blockers=[], warnings=[])
data["outdoor"]["weather"] = [{
    "condition": "partlycloudy", "temperature_c": 8.9, "wind_kmh": 17,
}]
data["outdoor"]["readings"] = [{
    "metric": "aqi", "value": 13, "unit": "US AQI", "available": True,
}]

# A plain unregistered <ha-icon> has zero intrinsic width in these standalone
# tests. Supply HA's size-variable behavior so real icon widths participate in
# overflow checks. The SVG glyphs are fixture stand-ins, not production code.
ICON_FIXTURE = """() => {
  const glyphs = {
    'mdi:home-outline':'<path d="M3 10 12 3l9 7v11h-6v-7H9v7H3z"/>',
    'mdi:thermometer':'<path d="M9 14.5V5a3 3 0 0 1 6 0v9.5a5 5 0 1 1-6 0Z"/><path d="M12 8v10"/>',
    'mdi:water-percent':'<path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z"/><path d="m9 18 6-6"/><circle cx="9" cy="12" r=".7"/><circle cx="15" cy="18" r=".7"/>',
    'mdi:water-alert-outline':'<path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z"/><path d="M12 10v5m0 3v.5"/>',
    'mdi:brightness-5':'<circle cx="12" cy="12" r="6"/><path d="M12 1v3m0 16v3M1 12h3m16 0h3M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2"/>',
    'mdi:blur':'<circle cx="7" cy="7" r="1"/><circle cx="12" cy="7" r="1"/><circle cx="17" cy="7" r="1"/><circle cx="7" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="17" cy="12" r="1"/><circle cx="7" cy="17" r="1"/><circle cx="12" cy="17" r="1"/><circle cx="17" cy="17" r="1"/>',
    'mdi:approximately-equal':'<path d="M3 8c6-7 12 7 18 0M3 16c6-7 12 7 18 0"/>',
    'mdi:chevron-down':'<path d="m6 9 6 6 6-6"/>',
    'mdi:chevron-up':'<path d="m6 15 6-6 6 6"/>',
    'mdi:check':'<path d="m4 12 5 5L20 6"/>',
    'mdi:check-circle-outline':'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
    'mdi:close':'<path d="m6 6 12 12M6 18 18 6"/>',
    'mdi:help-circle-outline':'<circle cx="12" cy="12" r="9"/><path d="M9 8a3 3 0 0 1 6 0c0 3-3 2-3 6m0 3v.5"/>',
  };
  customElements.define('ha-icon', class extends HTMLElement {
    static get observedAttributes() { return ['icon']; }
    constructor() { super(); this.attachShadow({mode:'open'}); }
    connectedCallback() { this.draw(); }
    attributeChangedCallback() { this.draw(); }
    draw() {
      this.shadowRoot.innerHTML = '<style>:host{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)}svg{width:100%;height:100%;display:block}</style>' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
        (glyphs[this.getAttribute('icon')] || '<circle cx="12" cy="12" r="8"/><path d="M12 7v6m0 3v.5"/>') + '</svg>';
    }
  });
}"""

LAYOUT_REPORT = """() => {
  const rect = el => {
    const r = el.getBoundingClientRect();
    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
  };
  const visible = el => el.getClientRects().length && rect(el).width > 0 &&
    getComputedStyle(el).visibility !== 'hidden';
  const frame = document.getElementById('card-frame');
  const root = card.shadowRoot;
  return {
    viewport:innerWidth, pageScroll:document.documentElement.scrollWidth,
    frameWidth:frame.clientWidth, frameScroll:frame.scrollWidth,
    rows:[...root.querySelectorAll('.hem-room-glance87')].map(row => {
      const all = [...row.querySelectorAll('.hem-room-metric107')];
      return {
        name:row.querySelector('.hem-room-name87').textContent, box:rect(row),
        clientWidth:row.clientWidth, scrollWidth:row.scrollWidth, total:all.length,
        leaves:[...row.querySelectorAll(':scope > ha-icon,.hem-room-name87,.hem-room-metric107,.hem-room-active87 .hem-hint87,.hem-room-alerts87 .hem-hint87,.hem-compact-extra87')]
          .filter(visible).map(el=>({name:el.className || el.getAttribute('icon'),box:rect(el)})),
        metrics:all.filter(visible).map(el=>{
          const style=getComputedStyle(el);
          const value=el.querySelector('.hem-room-metric-value107');
          const icon=el.querySelector(':scope > ha-icon');
          return {
            text:el.textContent,tag:el.tagName,box:rect(el),
            clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,
            font:style.fontSize,padding:[style.paddingLeft,style.paddingRight],
            border:style.borderLeftWidth,borderStyle:style.borderLeftStyle,
            value:value ? {text:value.textContent,font:getComputedStyle(value).fontSize,
              weight:getComputedStyle(value).fontWeight,box:rect(value)} : null,
            icon:icon && visible(icon) ? {size:getComputedStyle(icon).getPropertyValue('--mdc-icon-size').trim(),box:rect(icon)} : null,
            parts:[...el.children].filter(visible).map(part=>({name:part.className || part.tagName,box:rect(part)})),
          };
        }),
      };
    }),
  };
}"""


def px(value):
    return float(value.removesuffix("px"))


def assert_layout(report, label):
    assert report["pageScroll"] <= report["viewport"] + 1, (label, "page overflow", report)
    assert report["frameScroll"] <= report["frameWidth"] + 1, (label, "card overflow", report)
    metrics = []
    for row in report["rows"]:
        context = (label, row["name"], row)
        assert 2 <= len(row["metrics"]) <= row["total"] <= 4, context
        assert row["box"]["height"] <= 55, ("room must stay on one row", *context)
        assert row["scrollWidth"] <= row["clientWidth"] + 1, ("row overflow", *context)
        if report["frameWidth"] >= 480:
            assert len(row["metrics"]) == row["total"], ("wide card lost a reading", *context)
        leaves = sorted(row["leaves"], key=lambda leaf: leaf["box"]["left"])
        for first, second in zip(leaves, leaves[1:]):
            assert first["box"]["right"] <= second["box"]["left"] + 0.5, (
                "header elements overlap", first, second, *context)
        centers = []
        for metric in row["metrics"]:
            box = metric["box"]
            assert row["box"]["left"] <= box["left"] < box["right"] <= row["box"]["right"], context
            assert metric["scrollWidth"] <= metric["clientWidth"] + 1, ("reading clipped", metric, *context)
            assert metric["value"] and metric["value"]["text"].strip(), context
            assert metric["icon"], ("metric icon missing", metric, *context)
            assert px(metric["border"]) >= 0.75 and metric["borderStyle"] != "none", context
            assert min(map(px, metric["padding"])) >= 1, context
            for part in metric["parts"]:
                assert box["left"] - 0.5 <= part["box"]["left"] and part["box"]["right"] <= box["right"] + 0.5, (
                    "reading content clipped", metric, part, *context)
            centers.append((box["top"] + box["bottom"]) / 2)
            metrics.append(metric)
        assert max(centers) - min(centers) <= 1, ("metrics wrap or misalign", *context)
        for first, second in zip(row["metrics"], row["metrics"][1:]):
            assert second["box"]["left"] - first["box"]["right"] >= 1.5, (
                "readings need visible separation", first, second, *context)
    assert len({metric["font"] for metric in metrics}) == 1, ("button/span font mismatch", label, metrics)
    assert len({metric["value"]["font"] for metric in metrics}) == 1, ("value font mismatch", label, metrics)
    assert len({metric["value"]["weight"] for metric in metrics}) == 1, ("value weight mismatch", label, metrics)
    assert len({metric["icon"]["size"] for metric in metrics}) == 1, ("icon size mismatch", label, metrics)
    widths = [metric["icon"]["box"]["width"] for metric in metrics]
    assert max(widths) - min(widths) <= 0.25, ("metric icons shrink inconsistently", label, metrics)
    heights = [metric["box"]["height"] for metric in metrics]
    assert max(heights) - min(heights) <= 0.25, ("button/span height mismatch", label, metrics)


chrome = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or (
    shutil.which("chromium") or shutil.which("google-chrome")
)
assert chrome and Path(chrome).is_file(), "Chromium required (or set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH)"
screenshot_dir = os.environ.get("HEM_TEST_SCREENSHOT_DIR")
if screenshot_dir:
    screenshot_dir = Path(screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 590, "height": 990})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content("""<!doctype html><html><head><style>
      *{box-sizing:border-box}body{margin:0;background:#111;color:#ddd;font-family:Arial,sans-serif}
      :root{--primary-text-color:#eee;--secondary-text-color:#aaa;--primary-color:#03a9f4;
      --card-background-color:#202020;--secondary-background-color:#292929;--divider-color:#444}
      #card-frame{width:100%;max-width:100%}
    </style></head><body><main id="card-frame"></main></body></html>""")
    page.evaluate(ICON_FIXTURE)
    page.add_script_tag(path=str(CARD))
    page.evaluate("""({states}) => {
      window.info=[];window.calls=[];
      window.card=document.createElement('home-environment-manager-card');
      document.getElementById('card-frame').append(card);
      card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
      card._hass={language:'el',states,localize:()=>undefined,callWS:async()=>({}),
        callService:(...args)=>{calls.push(args);return Promise.resolve()}};
      card._config={entity:'sensor.hem'};card._renderContent(true);
    }""", {"states": states})
    assert not errors, errors
    # Produce both requested review widths even when the first layout
    # assertion exposes a regression and stops the remainder of the test.
    if screenshot_dir:
        for width in (590, 320):
            page.set_viewport_size({"width": width, "height": 990})
            page.locator('#card-frame').screenshot(path=str(screenshot_dir / f"room-metrics-{width}.png"))
        page.set_viewport_size({"width": 590, "height": 990})
    assert page.locator('.hem-room-fold87:not([open])').count() == 5
    assert page.locator('span.hem-room-metric107').count() == 4
    assert page.locator('button.hem-room-metric107').count() == 14

    # Check the target screenshot width first, then all supported mobile sizes.
    for width in (590, 320, 360, 390, 480, 800):
        page.set_viewport_size({"width": width, "height": 990})
        page.evaluate("document.getElementById('card-frame').style.width='100%'")
        report = page.evaluate(LAYOUT_REPORT)
        assert_layout(report, f"viewport {width}")
    # Lovelace can give the card a narrow column in a desktop-sized viewport.
    page.set_viewport_size({"width": 1280, "height": 990})
    for width in (320, 390):
        page.evaluate("width=>document.getElementById('card-frame').style.width=width+'px'", width)
        report = page.evaluate(LAYOUT_REPORT)
        if screenshot_dir and width == 320:
            page.locator('#card-frame').screenshot(path=str(screenshot_dir / "room-metrics-desktop-column-320.png"))
        assert_layout(report, f"desktop column {width}")

    page.set_viewport_size({"width": 590, "height": 990})
    page.evaluate("document.getElementById('card-frame').style.width='100%'")
    row = page.locator('[data-room-fold87="room0"]')
    for metric in ("temperature", "humidity"):
        trigger = row.locator(f'[data-hem-average105="{metric}"]')
        assert trigger.locator('.hem-avg-marker105').count() == 1
        previous = page.evaluate("info")
        trigger.click()
        assert row.get_attribute("open") is None, "average click expanded room"
        assert page.evaluate("info") == previous, "average click opened a native source"
        popup = page.locator('.hem-avg-dialog105')
        popup.wait_for(state="visible")
        assert popup.locator('.hem-avg-line105').count() == 1
        expected = [f"sensor.room0_{metric}_a", f"sensor.room0_{metric}_b"]
        actual = popup.locator('[data-hem-source105]').evaluate_all(
            "nodes=>nodes.map(node=>node.getAttribute('data-hem-source105'))")
        assert actual == expected, (metric, actual, expected)
        popup.locator(f'[data-hem-source105="{expected[0]}"]').click()
        assert page.evaluate("info") == previous, "Contributor click should open its recorded trend first"
        assert page.evaluate("card._averageDialog105.entity122") == expected[0]
        page.evaluate("card._renderContent(true)")
        assert popup.is_visible() and row.get_attribute("open") is None
        popup.locator(f'[data-open-entity122="{expected[0]}"]').click()
        assert page.evaluate("info") == previous + [expected[0]]
        assert popup.count() == 0
    for area, entity_id in (("room0", "sensor.room0_illuminance"), ("room4", "sensor.room4_pm25")):
        source_row = page.locator(f'[data-room-fold87="{area}"]')
        trigger = source_row.locator(f'.hem-room-metric107[data-hem-source105="{entity_id}"]')
        assert trigger.locator('.hem-avg-marker105').count() == 0
        previous = page.evaluate("info")
        trigger.click()
        assert page.evaluate("info") == previous, "Single-source click should open its recorded trend first"
        assert page.evaluate("card._averageDialog105.entity122") == entity_id
        popup = page.locator('.hem-avg-dialog105')
        assert popup.is_visible()
        popup.locator(f'[data-open-entity122="{entity_id}"]').click()
        assert page.evaluate("info") == previous + [entity_id]
        assert source_row.get_attribute("open") is None, "native click expanded room"
        assert page.locator('.hem-avg-dialog105').count() == 0
    row.locator('.hem-room-name87').click()
    assert row.get_attribute("open") is not None
    assert row.locator('.hem-room-body87').is_visible()
    row.locator('.hem-room-name87').click()
    assert row.get_attribute("open") is None
    assert page.evaluate("calls") == [], "read-only metric interactions sent a service call"
    assert not errors, errors
    browser.close()

print("BETA107_SEPARATE_UNIFORM_ROOM_METRICS_RESPONSIVE_NATIVE_AVERAGES=PASS")
