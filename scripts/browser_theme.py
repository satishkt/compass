"""Read-only verification of the reference-inspired Databricks theme."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

base = os.getenv('CHECK_URL', 'http://127.0.0.1:8791')
headers = {}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers = WorkspaceClient(profile='fevm').config.authenticate()

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(extra_http_headers=headers, viewport={'width': 1600, 'height': 1080})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(base)
    expect(page.locator('[data-select-agent]').first).to_be_visible(timeout=60000)
    page.evaluate('document.fonts.ready')
    assert page.evaluate('document.fonts.check(\'500 14px "DM Sans"\')')
    assert page.locator('body').evaluate('(e)=>getComputedStyle(e).fontFamily').startswith('"DM Sans"')
    assert page.locator('.nav.active').evaluate('(e)=>getComputedStyle(e).backgroundColor') == 'rgb(255, 54, 33)'
    assert page.locator('html').evaluate('(e)=>getComputedStyle(e).backgroundColor') == 'rgb(246, 247, 249)'
    assert page.request.get(base + '/static/fonts/dm-sans.ttf').ok
    for tab in ['manage-agents', 'review', 'daily-updates', 'sources', 'tables', 'audit', 'chat']:
        page.click('[data-tab="' + tab + '"]')
        expect(page.locator('#' + tab)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.click('#directory-add-agent')
    expect(page.locator('#create-agent-dialog')).to_be_visible(timeout=60000)
    assert 'DM Sans' in page.locator('#create-agent-dialog h2').evaluate('(e)=>getComputedStyle(e).fontFamily')
    page.keyboard.press('Escape')
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/databricks-theme-desktop.png', full_page=True)
    page.set_viewport_size({'width': 390, 'height': 900})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='artifacts/databricks-theme-mobile.png', full_page=True)
    assert not errors, errors
    browser.close()
    print('Databricks palette, local font, all navigation pages, dialog and mobile layout passed')
