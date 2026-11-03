"""Beta101: native weather warnings show event, description and all attributes."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import runpy
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
baseline = runpy.run_path(str(ROOT / ".github/tests/test_beta87_compact_browser.py"))
states = deepcopy(baseline["states"])
dashboard = deepcopy(baseline["data"])
entity = "sensor.wesseling_weather_warning"
name = "Wesseling, Stadt Warnung"
attributes = {
    "warning_1_name": "Sturmböen",
    "warning_1_description": "Amtliche WARNUNG vor STURMBÖEN; Fenster schließen.",
    "warning_1_start": "2026-11-03T16:00:00+01:00",
    "warning_1_end": "2026-11-03T22:00:00+01:00",
    "warning_1_level": 3,
    "provider_data": {
        "category": "Wind",
        "nested": ["<img src=x onerror=alert(1)>", {"level": 3}],
    },
    "friendly_name": name,
}
states[entity] = {"state": "on", "attributes": attributes}
dashboard["outdoor"]["warnings"] = [
    {"entity_id": entity, "name": name, "active": True},
]
dashboard["outdoor"]["blockers"] = [
    {"code": "active_warning", "label": name, "value": ""},
    {"code": "weather_cold", "label": "Temperature", "value": "6°C"},
]
states["sensor.hem"]["attributes"].update(
    dashboard=dashboard, warning_sources=[entity],
)
chrome = shutil.which("chromium") or shutil.which("google-chrome")
assert chrome, "Chromium is required"
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=chrome, headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    page = browser.new_page(viewport={"width": 590, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(
        '<html><body style="margin:0;background:#111;color:white"></body></html>'
    )
    page.add_script_tag(path=str(ROOT / "frontend/air-quality-advisor-card.js"))
    page.evaluate("""({states}) => {
        window.info = [];
        window.card = document.createElement('home-environment-manager-card');
        document.body.append(card);
        card.addEventListener('hass-more-info', ev => info.push(ev.detail.entityId));
        card._hass = {language:'el', states, localize:() => undefined};
        card._config = {entity:'sensor.hem'};
        card._renderContent(true);
    }""", {"states": states})
    chip = page.locator("details.hem-warning101")
    assert chip.count() == 1
    summary = chip.locator(":scope > summary")
    assert "Sturmböen" in summary.inner_text()
    assert "Amtliche WARNUNG" in summary.get_attribute("title")
    assert name not in summary.inner_text()
    assert page.locator(".hem-outside-details87").count() == 1
    assert page.locator(".outside .outside-alerts .reason").count() >= 2
    summary.click()
    pop = page.locator(".hem-floating-info87.hem-wx-pop101")
    pop.wait_for(state="visible", timeout=4000)
    assert pop.is_visible()
    assert pop.locator(".hem-wx-row101").count() == len(attributes) + 1
    assert "warning_1_description" in pop.inner_text()
    assert "warning_1_start" in pop.inner_text()
    assert "provider_data" in pop.inner_text()
    assert "nested" in pop.inner_text()
    assert page.evaluate("document.querySelector('img[onerror]')") is None
    pop.locator("[data-open-weather-entity101]").click()
    assert page.evaluate("info") == [entity]
    summary.click()
    # Native source data changes without the dashboard's revision changing.
    page.evaluate("""() => {
        const states = {...card._hass.states};
        states['sensor.wesseling_weather_warning'] = {
            ...states['sensor.wesseling_weather_warning'],
            attributes: {
                ...states['sensor.wesseling_weather_warning'].attributes,
                warning_1_name:'Starkregen',
                warning_1_description:'Regenwarnung',
            }
        };
        card.hass = {...card._hass, states};
    }""")
    page.wait_for_timeout(100)
    chip = page.locator("details.hem-warning101")
    observed=page.evaluate("""() => {
        const e=card._hass.states['sensor.wesseling_weather_warning'];
        const warning=card._state()[1].attributes.dashboard.outdoor.warnings[0];
        const info=card._weatherContent101(warning);
        return {
          nativeName:e.attributes.warning_1_name,
          computedName:info.name,
          rendered:card.shadowRoot.querySelector('details.hem-warning101')?.textContent,
          signatureFresh:card._controllerSignature()===card._shownControllerSignature,
          pendingRender:card._pendingRender,
          focusedEditor:!!card._focusedEditor,
          renderError:card._lastRenderError
        };
    }""")
    assert "Starkregen" in chip.locator(":scope > summary").inner_text(),observed
    chip.locator(":scope > summary").click()
    page.locator(".hem-floating-info87.hem-wx-pop101").wait_for(state="visible", timeout=4000)
    assert "Regenwarnung" in page.locator(".hem-floating-info87").inner_text()
    # Two warnings may share friendly names; their exact native IDs remain distinct.
    page.evaluate("""() => {
        const states = {...card._hass.states};
        states['sensor.second_warning'] = {
            state:'on', attributes:{friendly_name:'Wesseling, Stadt Warnung',
              warning_1_name:'Glätte', warning_1_description:'Glättewarnung'}
        };
        states['sensor.hem'] = {...states['sensor.hem'], attributes:{
          ...states['sensor.hem'].attributes,
          warning_sources:['sensor.wesseling_weather_warning','sensor.second_warning'],
          dashboard:{...states['sensor.hem'].attributes.dashboard,
            outdoor:{...states['sensor.hem'].attributes.dashboard.outdoor,
              warnings:[
                {entity_id:'sensor.wesseling_weather_warning',name:'Same name',active:true},
                {entity_id:'sensor.second_warning',name:'Same name',active:true}
              ]}}
        }};
        card.hass = {...card._hass, states};
    }""")
    page.wait_for_function(
        "() => card.shadowRoot.querySelectorAll('details.hem-warning101').length === 2",
        timeout=4000,
    )
    warnings = page.locator("details.hem-warning101")
    assert warnings.count() == 2
    assert "Starkregen" in warnings.nth(0).inner_text()
    assert "Glätte" in warnings.nth(1).inner_text()
    page.set_viewport_size({"width": 360, "height": 740})
    warnings.nth(1).locator(":scope > summary").click()
    pop = page.locator(".hem-floating-info87.hem-wx-pop101")
    pop.wait_for(state="visible", timeout=4000)
    assert pop.is_visible()
    assert pop.bounding_box()["width"] <= 360
    assert not errors, errors
    browser.close()
print("BETA101_WEATHER_WARNING_EVENT_AND_COMPLETE_NATIVE_ATTRIBUTES=PASS")
