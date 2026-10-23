"""Authenticated smoke test; synthetic test memory is forgotten afterward."""
from pathlib import Path
import requests
from databricks.sdk import WorkspaceClient
from playwright.sync_api import sync_playwright
w=WorkspaceClient(profile='fevm')
url='https://research-memory-poc-7474653807068368.aws.databricksapps.com'
headers=w.config.authenticate()
c=requests.Session();c.headers.update(headers)
def call(path,body=None):
    r=c.get(url+'/api'+path,timeout=35) if body is None else c.post(url+'/api'+path,json=body,timeout=120)
    r.raise_for_status()
    return r.json()
status=call('/status');assert status['storage']=='Lakebase'
p=call('/memories',{'topic':'deployment-check/review-cadence','content':'The fictional Atlas deployment-check research team reviews valuation assumptions every 13 days.','source':'Synthetic automated deployment verification; not real investment knowledge','confirmed':True})
item=p['id']
try:
    session=call('/sessions',{})['id']
    r=call('/chat',{'session_id':session,'question':'What is the fictional Atlas deployment-check research team valuation review cadence?'})
    assert all(s['id']!=item for s in r['sources'])
    call('/memories/'+item+'/review',{'action':'approve','expected_version':1})
    session=call('/sessions',{})['id']
    r=call('/chat',{'session_id':session,'question':'What is the fictional Atlas deployment-check research team valuation review cadence?'})
    assert '13 days' in r['answer'],r['answer']
    assert any(s['id']==item and s['kind']=='approved_memory' for s in r['sources'])
    assert not r['warning'],r['warning']
    print('Deployed Lakebase loop passed: pending excluded, approved recalled in a fresh session, cited model answer.')
finally:
    current=next(m for m in call('/memories') if m['id']==item)
    call('/memories/'+item+'/review',{'action':'forget','expected_version':current['version']})
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050},extra_http_headers=headers)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url)
    page.get_by_role('heading',name='Your research has a memory.').wait_for()
    page.get_by_text('Databricks',exact=True).wait_for()
    assert page.locator('#demo-user-label').is_hidden()
    page.get_by_role('button',name='What are the research journey stages? ↗').click()
    page.locator('.message.assistant').wait_for(timeout=120000)
    answer = page.locator('.message.assistant').inner_text()
    assert 'Could not complete the request' not in answer, answer
    assert '[D' in answer, answer
    page.locator('#evidence details').first.wait_for()
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/databricks-app.png',full_page=True)
    page.get_by_role('button',name='Explore tables').click()
    page.locator('#operation').select_option('tables')
    page.locator('#schema-name').fill('edd_positions')
    page.get_by_role('button',name='Run query ↗').click()
    page.get_by_role('cell',name='position_snapshot',exact=True).wait_for(timeout=90000)
    assert 'end-user OBO' in page.locator('#table-result').inner_text()
    page.screenshot(path='artifacts/databricks-tables.png',full_page=True)
    assert not errors,errors
    browser.close()
    print('Deployed browser passed: authenticated UI, hidden demo identity, generated answer, source evidence, OBO table explorer, no JS errors.')
