"""Read-only deployed registry and contextual agent navigation check."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from databricks.sdk import WorkspaceClient

base=os.getenv('CHECK_URL','https://research-memory-poc-7474653807068368.aws.databricksapps.com')
headers=WorkspaceClient(profile='fevm').config.authenticate() if 'databricksapps' in base else {}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(extra_http_headers=headers,viewport={'width':1600,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base)
    response=page.request.get(base+'/api/agents');assert response.ok
    agents=response.json()
    expect(page.locator('[data-select-agent]')).to_have_count(len(agents),timeout=60000)
    expect(page.locator('[data-select-agent]').first).to_have_attribute('data-select-agent','supervisor')
    for agent in agents:
        page.click('[data-select-agent="'+agent['id']+'"]')
        expect(page.locator('#context-title')).to_have_text(agent['name'])
        expect(page.locator('#context-purpose')).to_have_text(agent['purpose'])
        expect(page.locator('#question')).to_have_attribute('placeholder','Ask '+agent['name']+'…')
        expect(page.locator('#memory-agent')).to_have_value(agent['id'])
        expect(page.locator('[data-select-agent][aria-pressed="true"]')).to_have_count(1)
    page.click('[data-select-agent="valuation"]')
    page.fill('#question','Synthetic browser check draft')
    page.click('[data-select-agent="portfolio"]')
    expect(page.locator('#question')).to_have_value('')
    page.click('[data-select-agent="valuation"]')
    expect(page.locator('#question')).to_have_value('Synthetic browser check draft')
    page.fill('#question','')
    expect(page.locator('#saved-sessions option').first).to_have_text('Start a new conversation')
    page.click('[data-select-agent="supervisor"]')
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/agent-workspace-live.png',full_page=True)
    page.set_viewport_size({'width':390,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.click('[data-select-agent="compliance-demo"]')
    expect(page.locator('#context-title')).to_have_text('Compliance Demo')
    assert not errors,errors
    print('Live registry, all',len(agents),'agent contexts, active selection, independent drafts and mobile layout passed')
    browser.close()
