"""Exercise agent switching, drafts, history, dynamic discovery and delayed replies."""
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from playwright.async_api import async_playwright, expect

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
BASE=os.getenv('CHECK_URL','http://127.0.0.1:8791')

async def main():
    from domains import DOMAINS
    directory=[dict(id=d.id,name=d.name,purpose=d.purpose,seed_count=len(d.seeds)) for d in DOMAINS.values()]
    directory.append(dict(id='compliance-demo',name='Compliance Demo',purpose='Synthetic supplier compliance policies and exception workflows.',seed_count=2))
    sessions={};events={};request_started=asyncio.Event();reply_release=asyncio.Event()
    headers={}
    if 'databricksapps' in BASE:
        from databricks.sdk import WorkspaceClient
        headers=WorkspaceClient(profile='fevm').config.authenticate()
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True)
        page=await browser.new_page(extra_http_headers=headers,viewport={'width':1600,'height':1080})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        async def mock(route):
            path=route.request.url.split('/api',1)[1]
            body=route.request.post_data_json or {}
            data={}
            if path=='/status':data=dict(mode='Local prototype',user='layout-test',documents=35,memory_counts={},catalog='demo',storage='Test fixture',tracing='Test',model='Test')
            elif path=='/agents':data=directory
            elif path=='/sessions' and route.request.method=='POST':
                key=str(uuid4());sessions[key]=dict(id=key,agent=body['agent'],parent=None,created_at='2026-10-22T10:00:00+00:00');events[key]=[];data={'id':key}
            elif path=='/sessions':data=list(sessions.values())
            elif path.startswith('/sessions/'):
                data=events[path.rsplit('/',1)[1]]
            elif path=='/chat':
                key=body['session_id'];events[key].append(dict(kind='message',role='user',content=body['question']))
                request_started.set();await reply_release.wait()
                answer='SYNTHETIC LAYOUT CHECK: This response belongs only to Valuation.'
                events[key].append(dict(kind='message',role='assistant',content=answer))
                data=dict(answer=answer,trace_id=key,sources=[dict(label='valuation-M1',kind='approved_memory',title='Synthetic test source',content='Synthetic UI fixture.')],delegations=[],warning=None)
            elif path.endswith('/memory'):
                agent=path.split('/')[2];data=dict(approved=[dict(path='/seed/test.md',content='Synthetic baseline for '+agent)],candidates=[])
            elif path.endswith('/pipeline'):data={'dreamer_policy':{'schedule':'daily'}}
            elif path=='/memories':data=[]
            elif path=='/agent-definitions':data=[]
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
        await page.route('**/api/**',mock)
        await page.goto(BASE)
        await expect(page.locator('[data-select-agent]')).to_have_count(6)
        await expect(page.locator('#context-title')).to_have_text('Supervisor')
        assert await page.locator('#agent-select').is_hidden()
        await page.click('[data-select-agent="valuation"]')
        await expect(page.locator('#context-title')).to_have_text('Valuation')
        await expect(page.locator('[data-select-agent="valuation"]')).to_have_attribute('aria-pressed','true')
        await page.fill('#question','A draft for valuation')
        await page.click('[data-select-agent="portfolio"]')
        await expect(page.locator('#question')).to_have_value('')
        await expect(page.locator('#context-title')).to_have_text('Portfolio')
        await page.click('[data-select-agent="valuation"]')
        await expect(page.locator('#question')).to_have_value('A draft for valuation')
        await page.fill('#question','A synthetic layout-check question.')
        await page.click('#send');await asyncio.wait_for(request_started.wait(),timeout=10)
        await page.click('[data-select-agent="portfolio"]')
        await expect(page.locator('#send')).to_be_enabled()
        reply_release.set()
        await page.wait_for_timeout(250)
        await expect(page.locator('#messages')).not_to_contain_text('This response belongs only to Valuation')
        await page.click('[data-select-agent="valuation"]')
        await expect(page.locator('#messages')).to_contain_text('This response belongs only to Valuation')
        await expect(page.locator('#saved-sessions option')).to_have_count(2)
        await expect(page.locator('#evidence')).to_contain_text('valuation-M1')
        await page.click('[data-select-agent="research"]')
        await expect(page.locator('#saved-sessions option')).to_have_count(1)
        await expect(page.locator('#evidence')).to_be_empty()
        await page.click('[data-select-agent="valuation"]')
        await page.click('#show-agent-memory')
        await expect(page.locator('#memory-agent')).to_have_value('valuation')
        await expect(page.locator('#agent-memories')).to_contain_text('Synthetic baseline for valuation')
        await page.click('[data-tab="chat"]')
        directory.append(dict(id='credit-risk',name='Credit Policy',purpose='Synthetic credit policy and review criteria.',seed_count=1))
        await page.click('#refresh-directory')
        await expect(page.locator('[data-select-agent]')).to_have_count(7)
        await page.click('[data-select-agent="credit-risk"]')
        await expect(page.locator('#context-title')).to_have_text('Credit Policy')
        await expect(page.locator('#question')).to_have_attribute('placeholder','Ask Credit Policy…')
        await page.click('#directory-add-agent')
        await expect(page.locator('#create-agent-dialog')).to_be_visible()
        await page.click('#close-create-agent')
        await page.click('[data-tab="chat"]')
        await page.click('[data-select-agent="supervisor"]')
        await page.screenshot(path='artifacts/agent-workspace-desktop.png',full_page=True)
        for width in (1280,900,390):
            await page.set_viewport_size({'width':width,'height':1000})
            assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),width
            await page.locator('[data-select-agent="compliance-demo"]').click()
            await expect(page.locator('#context-title')).to_have_text('Compliance Demo')
        await page.screenshot(path='artifacts/agent-workspace-mobile.png',full_page=True)
        assert not errors,errors
        print('Agent panel, contextual headings/prompts, drafts, session isolation, delayed reply isolation, memory context, dynamic agents and responsive layout passed')
        await browser.close()

if __name__=='__main__':
    Path('artifacts').mkdir(exist_ok=True)
    asyncio.run(main())
