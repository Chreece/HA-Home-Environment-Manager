"""Browser contract for short settings names and grouped door selections."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
CHROME = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME, "Chromium required for room/door menu UI"
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
                                 args=["--no-sandbox", "--disable-dev-shm-usage"])
    for width in (320, 390, 760):
        page = browser.new_page(viewport={"width": width, "height": 820})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content("""<!doctype html><html><body style="margin:0;background:#222;color:white;
            --primary-text-color:#eee;--secondary-text-color:#bbb;
            --card-background-color:#222;--divider-color:#555"></body></html>""")
        page.add_script_tag(path=str(CARD))
        data = page.evaluate(r"""() => {
            const card = document.createElement('home-environment-manager-card');
            document.body.appendChild(card);
            card._hass = {language:'el', entities:{}, states:{}};
            card._hemFullContext127 = () => ({});
            const id = 'number.room_unoccupied_delay';
            const attributes = {
                friendly_name:'Gästezimmer Environment Παρουσία χώρου · Καθυστέρηση κενού χώρου (λεπτά)',
                setting_display_name:'Παρουσία χώρου · Καθυστέρηση κενού χώρου (λεπτά)',
                setting_group:'Παρουσία χώρου',
                configuration_help:'Επιβεβαιωμένη διάρκεια αδειάσματος του χώρου.',
                min:0, max:240, step:1
            };
            const registry = {
                device_id:'room-device', config_entry_id:'entry',
                platform:'environment_manager',
                unique_id:'entry_area_room_climate_operating_unoccupied_delay_minutes'
            };
            card._hass.entities[id]=registry;
            card._hass.states[id]={state:'10',attributes};
            const saved = {device:'room-device',entryId:'entry',area:'room'};
            const result = {};
            for(const scope of ['home','room','device']){
                const fields=card._hemFullFields127(saved,scope);
                result[scope]=fields.map(f=>f.label);
            }
            card._hass.entities[id]={...registry,name_by_user:'My named control'};
            result.userRename=card._hemFullFields127(saved,'room')[0].label;
            delete card._hass.entities[id].name_by_user;
            const field=card._hemFullFields127(saved,'room')[0];
            const full = card._hemFullRow127(field,'room');
            card.shadowRoot.innerHTML=card._styles()+
                '<div style="width:calc(100vw - 18px);max-width:680px;margin:auto">'+
                '<div class="hem-full-rows127">'+full+'</div></div>';
            const node=card.shadowRoot.querySelector('.hem-full-row127');
            const label=node.querySelector('.hem-full-label127 strong').textContent;
            const item={width:node.getBoundingClientRect().width,
                scroll:node.scrollWidth-node.clientWidth,
                label, doorCSS:card._styles().includes('.hem-room-door062'),
                doorLabel:card._styles().includes('hem-room-door062')};
            return {fields:result, item};
        }""")
        for scope in ("home", "room", "device"):
            assert data["fields"][scope] == ["Καθυστέρηση κενού χώρου (λεπτά)"], data
        assert data["fields"]["userRename"] == "My named control", data
        assert data["item"]["label"] == "Καθυστέρηση κενού χώρου (λεπτά)", data
        assert data["item"]["width"] > 200, data
        assert data["item"]["scroll"] <= 2, data
        assert data["item"]["doorCSS"], data
        assert not errors, errors
        page.close()
    browser.close()
print("PASS: B1 short localized setting labels, user renames, menu geometry and door CSS")
