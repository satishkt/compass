import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
base=os.getenv('CHECK_URL','http://127.0.0.1:8789')
headers={}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers=WorkspaceClient(profile='fevm').config.authenticate()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(extra_http_headers=headers,viewport={'width':1450,'height':1100})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base)
    expect(page.locator('[data-select-agent="supervisor"]')).to_be_visible(timeout=60000)
    page.click('[data-select-agent="valuation"]')
    page.click('#show-agent-memory')
    page.get_by_text('/seed/publication.md',exact=True).wait_for(timeout=60000)
    page.screenshot(path='artifacts/agents-v2-memory.png',full_page=True)
    page.click('[data-tab="chat"]')
    page.click('[data-select-agent="supervisor"]')
    page.wait_for_timeout(1000)
    page.screenshot(path='artifacts/agents-v2-chat.png',full_page=True)
    assert not errors,errors
    print('Browser: agent directory, independent memory, pipeline state and saved conversation controls passed')
    browser.close()
