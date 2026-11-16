"""B23: real card door position/window pills and recorded mold trend clicks.

Browser runs isolated HA snapshots, never service calls or real devices.
Covers compact and expanded mold readings, door metadata/popover, mobile layout
and no accidental room expansion while opening a derived historical trend.
"""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import runpy
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
states = deepcopy(runpy.run_path(str(ROOT / ".github/tests/test_beta114_interactive_trends.py"))["fixture"]())
room = states["sensor.hem"]["attributes"]["dashboard"]["rooms"][0]
START = 1793520000
room["windows"] = [{
    "entity_id":"binary_sensor.window", "name":"Balcony window",
    "opened":False,
}]
room["readings"].append({
    "entity_id":"derived.mold_living", "name":"Estimated surface humidity",
    "metric":"mold", "value":74.25, "unit":"%", "available":True,
    "details":{"calibration_factor":0.5, "estimated_surface_c":15.3},
})
room["environment"]["mold_trend"] = {
    "value":74.25, "source_ids":[], "source_count":0,
    "trend":[
        {"t":START, "v":68.5},
        {"t":START+900, "v":70.25},
        {"t":START+1800, "v":74.25},
    ],
}
room["environment"]["door_context"] = {
    "boundary":"closed", "eco_active":False,
    "contacts":[{
        "entity_id":"binary_sensor.door", "kind":"interior",
        "health":"ok", "state":"closed",
    }],
    "connections":[], "advisories":[],
}
states["binary_sensor.window"] = {
    "state":"off", "attributes":{"device_class":"window","friendly_name":"Balcony window"}
}
states["binary_sensor.door"] = {
    "state":"off", "attributes":{"device_class":"door","friendly_name":"Living room door"}
}
CHROME = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
                                 args=["--no-sandbox","--disable-dev-shm-usage"])
    for language,width in [("el",320),("en",390),("de",760)]:
        page = browser.new_page(viewport={"width":width,"height":900})
        errors = []
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.set_content('<style>body{margin:0;background:#202020;color:#eee;'
                         '--primary-text-color:#eee;--secondary-text-color:#bbb;'
                         '--card-background-color:#222;--secondary-background-color:#292929;'
                         '--primary-color:#03a9f4;--divider-color:#444}</style>')
        page.add_script_tag(path=str(CARD))
        page.evaluate(r"""({language,states})=>{
          window.calls=[];window.info=[];
          window.card=document.createElement('home-environment-manager-card');
          document.body.appendChild(card);
          card.addEventListener('hass-more-info',event=>info.push(event.detail.entityId));
          card._config={entity:'sensor.hem'};
          card._hass={language,states,connection:{},user:{is_admin:true},
            config:{time_zone:'Europe/Berlin'},localize:()=>undefined,
            callWS:async()=>({}),
            callService:(...args)=>{calls.push(args);throw Error('No device writes in card audit')}};
          card._renderContent(true);
        }""",{"language":language,"states":states})
        row = page.locator('[data-room-fold87="living"]')
        assert row.count()==1 and row.get_attribute("open") is None
        compact = row.locator(':scope > summary [data-hem-average105="mold"][data-average-area105="living"]')
        assert compact.count()==1, "Mold has data but is not a trend button"
        compact.click()
        assert row.get_attribute("open") is None, "Mold reading opened the room, not its trend"
        popup = page.locator('.hem-avg-dialog105')
        expect(popup).to_be_visible()
        assert page.evaluate("card._averageDialog105.metric") == "mold"
        assert page.evaluate("card._averageDialog105.entity122") is None
        assert page.evaluate("card._averageDialog105.model114.points.length") == 3
        assert "74.25" in popup.inner_text().replace(",", "."), popup.inner_text()
        assert popup.locator('[data-hem-source105]').count()==0, "A fake mold sensor appeared"
        popup.locator('[data-close-avg105]').click()
        row.locator('.hem-room-name87').click()
        assert row.get_attribute("open") is not None
        # v0.7.1 keeps both sensor types in one Windows & doors panel.
        contacts = row.locator('.window-section.hem-windows-doors071')
        assert contacts.count()==1
        assert contacts.locator('.window-list .window.hem-door-contact071.closed').count()==1
        assert "Living room door" in contacts.inner_text()
        assert "Balcony window" in contacts.inner_text()
        assert contacts.locator('[data-hem-source105="binary_sensor.door"]').count()==1
        contacts.locator('[data-hem-source105="binary_sensor.door"]').click()
        assert page.evaluate("info")[-1] == "binary_sensor.door"
        assert row.get_attribute("open") is not None
        detailed = row.locator('.metric-number[data-hem-average105="mold"]')
        assert detailed.count()==1, "Calibrated mold detail has no historical click"
        detailed.click()
        expect(popup).to_be_visible()
        assert page.evaluate("card._averageDialog105.metric") == "mold"
        assert row.get_attribute("open") is not None
        popup.locator('[data-close-avg105]').click()
        detailed.focus()
        detailed.press("Enter")
        expect(popup).to_be_visible()
        assert row.get_attribute("open") is not None
        popup.locator('[data-close-avg105]').click()
        assert page.evaluate("calls.length")==0
        assert not errors,errors
        page.close()
    browser.close()
print("PASS B23: mold click opens recorded trend without unfolding; unified window/door icons, matching pills, EN/EL/DE, zero services")
