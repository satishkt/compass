"""Browser-level workflow verification against the local prototype."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1050})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8787')
    page.get_by_role('heading', name='Your research has a memory.').wait_for()
    page.get_by_role('button', name='＋ Propose memory').first.click()
    page.locator('#memory-topic').fill('browser-demo/review-cadence')
    page.locator('#memory-content').fill('The synthetic browser demo team reviews assumptions every 17 days.')
    page.locator('#memory-source').fill('Synthetic browser workflow check')
    page.locator('#memory-confirm').check()
    page.get_by_role('button', name='Submit for approval').click()
    page.get_by_role('heading', name='browser-demo/review-cadence').wait_for()
    card = page.locator('.memory-card').filter(has=page.get_by_role('heading',name='browser-demo/review-cadence'))
    card.get_by_role('button', name='Approve', exact=True).click()
    card.get_by_text('approved · version 2').wait_for()
    page.get_by_role('button', name='Ask the knowledge base').click()
    page.locator('#demo-user').fill('browser-second-user')
    page.locator('#demo-user').press('Tab')
    page.locator('#question').fill('How often does the synthetic browser demo team review assumptions?')
    page.get_by_role('button', name='Ask ↗', exact=True).click()
    page.locator('.message.assistant').last.wait_for(timeout=120000)
    assert '17 days' in page.locator('.message.assistant').last.inner_text()
    assert 'approved memory' in page.locator('#evidence').inner_text()
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/local-learning-loop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='artifacts/local-mobile.png',full_page=True)
    # Clean up synthetic browser memory through the user-facing forget control.
    page.get_by_role('button', name='Shared memory').click()
    page.on('dialog', lambda d: d.accept())
    page.locator('.memory-card').filter(has=page.get_by_role('heading',name='browser-demo/review-cadence')).get_by_role('button',name='Forget').click()
    page.get_by_text('Memory content removed from the store',exact=False).wait_for()
    assert not errors, errors
    print('Browser workflow passed: propose, approve, cross-user recall, forget, responsive layout; no JS errors.')
    browser.close()
