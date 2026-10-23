import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
base=os.getenv('CHECK_URL','http://127.0.0.1:8789')
headers={}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers=WorkspaceClient(profile='fevm').config.authenticate()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(extra_http_headers=headers,viewport={'width':1450,'height':1100})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base)
    page.click('[data-tab="daily-updates"]')
    expect(page.locator('#daily-schedule')).to_contain_text('/Volumes/',timeout=60000)
    page.select_option('#daily-agent','valuation')
    page.fill('#daily-date','2026-10-22')
    page.click('#view-daily-update')
    if os.getenv('EXPECT_WRITTEN'):
        expect(page.locator('#daily-content')).to_contain_text('Daily update: 2026-10-22',timeout=60000)
        expect(page.locator('#daily-file-path')).to_contain_text('/valuation/2026-10-22.md')
    else:
        expect(page.locator('#daily-content')).not_to_have_text('Choose an agent and date to view its daily update.',timeout=60000)
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/daily-updates-ui.png',full_page=True)
    assert not errors,errors
    print('Daily updates browser controls, schedule and Markdown view passed')
    browser.close()
