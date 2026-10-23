"""Exercise agent creation and baseline seeding through the browser, then real recall/delegation."""
import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import httpx
base=os.getenv('CHECK_URL','http://127.0.0.1:8790')
agent_id=os.getenv('CHECK_AGENT_ID','compliance-demo')
headers={}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers=WorkspaceClient(profile='fevm').config.authenticate()
Path('artifacts').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(extra_http_headers=headers,viewport={'width':1440,'height':1100})
    errors=[]
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.goto(base)
    page.click('[data-tab="manage-agents"]')
    page.locator('#agent-catalog .agent-card').first.wait_for(timeout=60000)
    with httpx.Client(base_url=base,headers=headers,timeout=240) as api:
        definitions=api.get('/api/agent-definitions').json()
        if not any(a['id']==agent_id for a in definitions):
            page.click('#open-create-agent')
            page.fill('#new-agent-name','Compliance Demo')
            page.fill('#new-agent-id',agent_id)
            page.fill('#new-agent-purpose','Answer questions about fictional supplier compliance policies, exception workflows and evidence requirements. All baseline conventions are synthetic demonstrations.')
            page.fill('#new-agent-keywords','compliance, supplier, policy, exception, evidence')
            first=page.locator('.seed-editor').nth(0)
            first.locator('[data-seed-topic]').fill('supplier-evidence')
            first.locator('[data-seed-content]').fill('SYNTHETIC DEMO: A new supplier review requires two documented evidence checks before approval.')
            first.locator('[data-seed-source]').fill('Synthetic compliance handbook, supplier review')
            page.click('#add-agent-seed')
            second=page.locator('.seed-editor').nth(1)
            second.locator('[data-seed-topic]').fill('exceptions')
            second.locator('[data-seed-content]').fill('SYNTHETIC DEMO: A policy exception requires a written reason and an independent reviewer approval.')
            second.locator('[data-seed-source]').fill('Synthetic compliance handbook, policy exceptions')
            page.check('#approve-agent-baseline')
            page.screenshot(path='artifacts/create-agent-form.png',full_page=True)
            page.click('#submit-create-agent')
        card=page.locator('.agent-card').filter(has=page.locator('[data-chat-agent="'+agent_id+'"]'))
        card.wait_for(timeout=240000)
        expect(card).to_contain_text('2 baseline memories')
        card.locator('[data-memory-agent]').click()
        page.get_by_text('/seed/supplier-evidence.md',exact=True).wait_for(timeout=60000)
        page.screenshot(path='artifacts/created-agent-memory.png',full_page=True)
        page.reload()
        expect(page.locator('#agent-select option[value="'+agent_id+'"]')).to_have_count(1,timeout=60000)
        r=api.post('/api/sessions',json={'agent':agent_id});r.raise_for_status();session=r.json()['id']
        r=api.post('/api/chat',json={'session_id':session,'question':'In the synthetic compliance demo, how many documented evidence checks does a new supplier review require?'});r.raise_for_status();direct=r.json()
        assert 'two' in direct['answer'].lower() or '2' in direct['answer'],direct
        assert any(s['label']==agent_id+'-M1' or s['title']=='/seed/supplier-evidence.md' for s in direct['sources']),direct
        r=api.post('/api/sessions',json={'agent':'supervisor'});r.raise_for_status();session=r.json()['id']
        r=api.post('/api/chat',json={'session_id':session,'question':'Ask the Compliance Demo specialist: how many documented evidence checks are required for a new supplier review in its synthetic baseline?'});r.raise_for_status();supervisor=r.json()
        assert any(d['agent']==agent_id for d in supervisor['delegations']),supervisor
        assert not direct.get('warning') and not supervisor.get('warning'),(direct,supervisor)
        Path('artifacts/create-agent-check.json').write_text(json.dumps({'direct':direct,'supervisor':supervisor},indent=2))
        print('UI creation, two approved baseline memories, reload persistence, direct recall and supervisor delegation passed',flush=True)
    assert not errors,errors
    browser.close()
