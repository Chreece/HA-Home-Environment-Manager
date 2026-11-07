"""HEM b11 Chromium: logo + HEM header and independent translated arrival bubble."""
from __future__ import annotations
import os, runpy, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
existing=runpy.run_path(str(ROOT/'.github/tests/test_061b4_arrival_card.py'))
icons=runpy.run_path(str(ROOT/'.github/tests/test_061b1_room_fold.py'))['icon_fixture']()
executable=os.environ.get('CHROME_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
assert executable,'Chromium required'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=executable,headless=True,
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    for lang,needle in [('en','Prepare the home environment'),('de','Wohnumgebung'),('el','Προετοιμασία')]:
        page=browser.new_page(viewport={'width':375,'height':950})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content("""<!doctype html><html><head><style>
            *{box-sizing:border-box}
            body{margin:8px;background:#111;color:#eee;font-family:Arial,sans-serif;
              --primary-text-color:#eee;--secondary-text-color:#aaa;
              --card-background-color:#222;--secondary-background-color:#292929;--divider-color:#444}
            main{width:359px;max-width:100%;margin:0 auto}
            </style></head><body><main></main></body></html>""")
        page.evaluate(icons)
        page.add_script_tag(path=str(ROOT/'custom_components/environment_manager/frontend/air-quality-advisor-card.js'))
        page.evaluate(existing['SETUP'],existing['fixture'](lang))
        page.wait_for_function("Boolean(card._lastState)")
        heading=page.locator('.card-heading h2')
        expect(heading).to_have_text('HEM')
        assert 'Home Environment' in heading.get_attribute('aria-label')
        expect(page.locator('.hem-brand-mark125 svg')).to_be_visible()
        action=page.locator('.hem-arrival-action124')
        expect(action).to_be_enabled()
        assert not action.inner_text().strip(),(lang,'arrival label must not be visible')
        assert action.get_attribute('aria-label')
        assert page.locator('.hem-arrival-help125').count()==0
        assert needle in action.get_attribute('title')
        assert needle in action.get_attribute('aria-label')
        assert page.evaluate('calls.length')==0
        for width in (320,375,665):
            page.set_viewport_size({'width':width,'height':950})
            page.locator('main').evaluate('(e,width)=>e.style.width=Math.min(width-16,625)+"px"',width)
            page.evaluate('card._renderContent(true)')
            assert page.evaluate('document.documentElement.scrollWidth')<=width,(lang,width)
            head=page.locator('.card-heading').bounding_box()
            controls=page.locator('.header-actions').bounding_box()
            assert head and controls
            assert controls['x']+controls['width']<=head['x']+head['width']+1,(lang,width,head,controls)
            assert page.locator('.card-heading h2').inner_text()=='HEM'
            assert page.locator('.hem-arrival-action124').inner_text().strip()==''
        action.click()
        page.wait_for_function('calls.length===1&&!card._arrivalRequest124')
        assert page.evaluate('calls[0]')==['button','press',{'entity_id':existing['PREPARE']}]
        assert not errors,errors
        page.close()
    browser.close()
print('PASS: HEM b12 HEM header, icon-only arrival and localized tooltip in Chromium')
