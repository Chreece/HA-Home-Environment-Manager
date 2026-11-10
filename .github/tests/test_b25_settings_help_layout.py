"""Browser regression for the HEM settings info disclosure in every menu.

Covers the actual production renderer and stylesheet in Chromium. A narrow
details element previously forced long help text into one character per line.
No Home Assistant backend, write service, or device is contacted.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "custom_components/environment_manager/frontend/air-quality-advisor-card.js"
CHROME = os.getenv("CHROME_BIN") or shutil.which("chromium") or shutil.which("google-chrome")
assert CHROME, "Chromium is required for the B25 settings info layout test"

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, headless=True,
                                 args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 390, "height": 850})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content("""<!doctype html><html><head><style>
      body { margin: 0; background: #151515; color: #eee;
             font: 14px/1.5 Arial, sans-serif;
             --card-background-color: #252525;
             --secondary-background-color: #292929;
             --divider-color: #494949;
             --primary-color: #00a8ce;
             --primary-text-color: #eee;
             --secondary-text-color: #bbb; }
      * { box-sizing: border-box; }
    </style></head><body></body></html>""")
    page.add_script_tag(path=str(CARD))

    # Use the shipped rendering function: the same rows are embedded in
    # Home, Room, and Device menus, including the b24 unified accordion.
    setup = r"""({scope, language}) => {
      let card = document.querySelector('home-environment-manager-card');
      if (!card) {
        card = document.createElement('home-environment-manager-card');
        document.body.appendChild(card);
      }
      card._hass = {language};
      const longHelp = [
        'Schlafzimmer Environment Manager: Announce errors when the device has',
        'an unexpected state after stopping. Keep the full explanation readable',
        'even on smaller screens. Longer names like',
        'Wiederherstellungsbenachrichtigungen and',
        'Προτροπή ανοίγματος παραθύρων must not form a vertical column.',
        'A second sentence remains inside the same settings row.'
      ].join(' ');
      const field = {
        id: 'switch.hem_native_announce_device_errors',
        label: 'Schlafzimmer Environment Manager · Announce device errors',
        domain: 'switch', disabled: false,
        state: {state: 'off', attributes: {configuration_help: longHelp}},
        reg: {unique_id: 'example_announce_device_errors'}
      };
      const row = card._hemFullRow127(field, scope);
      card.shadowRoot.innerHTML = card._styles() +
        '<style>ha-icon{display:inline-block;vertical-align:middle}' +
        '.b25-fixture{width:calc(100vw - 24px);max-width:680px;margin:12px auto}' +
        '</style>' +
        '<div class="b25-fixture">' +
        '<details class="hem-room-options-group114 hem-full-category127 hem-unified141" open>' +
        '<summary>Announcements and errors</summary>' +
        '<div class="hem-full-rows127">' + row + '</div></details>' +
        '<p class="hem-room-options-helper115">Room settings explanation with full-width text.</p>' +
        '<p class="hem-home-helper128">Home settings explanation with full-width text.</p>' +
        '</div>';
    }"""

    for width in (320, 390, 760):
        page.set_viewport_size({"width": width, "height": 850})
        for scope in ("device", "room", "home"):
            for language in ("en", "el", "de"):
                page.evaluate(setup, {"scope": scope, "language": language})
                panel = page.locator("home-environment-manager-card").locator(".hem-full-help127")
                expect(panel).to_have_count(1)
                summary = panel.locator(":scope > summary")
                expect(summary.locator("strong")).to_contain_text("Schlafzimmer")
                expect(panel).not_to_have_attribute("open", "")
                summary.click()
                expect(panel).to_have_attribute("open", "")
                geo = page.evaluate(r"""() => {
                  const root = document.querySelector('home-environment-manager-card').shadowRoot;
                  const p = root.querySelector('.hem-full-help-body127 p');
                  const row = root.querySelector('.hem-full-row127');
                  const details = root.querySelector('.hem-full-help127');
                  const group = root.querySelector('.hem-room-options-group114');
                  const editor = row.querySelector('.hem-full-editor127 button');
                  const roomHelper = root.querySelector('.hem-room-options-helper115');
                  const homeHelper = root.querySelector('.hem-home-helper128');
                  return {
                    paragraphWidth: p.getBoundingClientRect().width,
                    paragraphHeight: p.getBoundingClientRect().height,
                    paragraphOverflow: p.scrollWidth - p.clientWidth,
                    detailsWidth: details.getBoundingClientRect().width,
                    rowWidth: row.getBoundingClientRect().width,
                    groupWidth: group.getBoundingClientRect().width,
                    rowOverflow: row.scrollWidth - row.clientWidth,
                    roomHelperWidth: roomHelper.getBoundingClientRect().width,
                    homeHelperWidth: homeHelper.getBoundingClientRect().width,
                    editorEnabled: !editor.disabled,
                    categoryOpen: group.open,
                    helpOpen: details.open,
                  };
                }""")
                label = f"{scope}/{language}/{width}px: {geo}"
                assert geo["paragraphWidth"] >= 175, label
                assert geo["paragraphWidth"] >= geo["rowWidth"] - 28, label
                assert geo["paragraphHeight"] < 320, label
                assert geo["paragraphOverflow"] <= 2, label
                assert geo["rowOverflow"] <= 2, label
                assert geo["detailsWidth"] <= geo["groupWidth"] - 18, label
                assert geo["roomHelperWidth"] >= 180, label
                assert geo["homeHelperWidth"] >= 180, label
                assert geo["editorEnabled"] and geo["categoryOpen"] and geo["helpOpen"], label
                summary.click()
                expect(panel).not_to_have_attribute("open", "")
                assert not errors, errors

    browser.close()

print("PASS: HEM Home/Room/Device settings info full-width in EN/EL/DE at 320/390/760px")
