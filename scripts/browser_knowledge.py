"""End-to-end browser check of the focus layout: agent switcher, chat capture, approval, shared conversations
and typed starting knowledge.

Run against a LOCAL server started without agent-resources.json, LAKEBASE_HOST or a warehouse, e.g.
CHECK_URL=http://127.0.0.1:8791 .venv/bin/python scripts/browser_knowledge.py
It uses the built-in Platform & Data agent, which has no native resources in that setup. The Add agent form is
filled from the pipeline folder but not submitted, because creating an agent provisions real memory/session stores
and a scheduled memory pipeline in the configured workspace; set CREATE_AGENT=1 to submit it anyway.
Requires a configured model for the capture step. Screenshots go to artifacts/focus-*.png.
"""
import os
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

URL = os.getenv('CHECK_URL', 'http://127.0.0.1:8791')
SCAFFOLD = Path(os.getenv('SCAFFOLD', str(Path.home() / 'Work/position_pipeline_scaffold/pipelines/position_pipeline')))
OUT = Path(__file__).resolve().parent.parent / 'artifacts'
OUT.mkdir(exist_ok=True)
AGENT = 'platform'


def identity(page, user):
    page.click('#user-toggle')
    page.fill('#demo-user', user)
    page.dispatch_event('#demo-user', 'change')
    page.keyboard.press('Escape')
    expect(page.locator('#identity')).to_have_text(user)


def go(page, tab):
    page.click('#apps-toggle')
    page.click(f'#apps-menu [data-tab="{tab}"]')


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.getenv('CHROMIUM') or None)
        page = browser.new_page(viewport={'width': 1500, 'height': 938})
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL)
        identity(page, 'ba@corp.com')

        # 1. Agent switcher (PDF page 3).
        page.click('#agent-switch')
        expect(page.locator('#agent-menu')).to_be_visible()
        expect(page.locator('#agent-options')).to_contain_text('Supervisor · auto-route')
        page.fill('#agent-find', 'platform')
        expect(page.locator('#agent-options [data-select-agent]')).to_have_count(1)
        page.fill('#agent-find', '')
        page.locator(f'#agent-options [data-select-agent="{AGENT}"]').click()
        expect(page.locator('#switch-name')).to_have_text('Platform & Data')
        page.click('#agent-switch')
        expect(page.locator(f'#agent-options .agent-option.selected[data-select-agent="{AGENT}"]')).to_be_visible()
        page.screenshot(path=OUT / 'focus-switcher.png')
        page.keyboard.press('Escape')

        # 2. Focused empty state with the project record bar (PDF page 1).
        expect(page.locator('.welcome h1')).to_have_text('What are we working on?')
        expect(page.locator('#record-chips .record-chip')).to_have_count(6)
        page.screenshot(path=OUT / 'focus-empty.png')

        # 3. Tell the agent a decision; it should offer a capture card, which the user sends for review.
        days = random.randint(30, 400)
        page.fill('#question', f'We decided that all bronze tables land in Unity Catalog under the raw schema, with {days}-day retention. Please record that as a decision.')
        page.click('#send')
        card = page.locator('.capture-card.draft').first
        card.wait_for(timeout=120000)
        card.locator('[data-act="confirm"]').click()
        expect(page.locator('.capture-card.recorded').first).to_contain_text('awaiting review', ignore_case=True)
        expect(page.locator('#record-chips .record-chip.fresh').first).to_be_visible()

        # 4. Conversations drawer (PDF page 2).
        page.click('#history-toggle')
        expect(page.locator('#session-list .session-row.selected')).to_contain_text('bronze tables')
        page.screenshot(path=OUT / 'focus-conversation.png')
        page.click('#close-drawer')

        # 5. The recorder cannot approve; another user can.
        go(page, 'review')
        expect(page.locator('#inbox-review')).to_contain_text(str(days))
        assert page.locator('#inbox-review article', has_text=str(days)).locator('[data-quick-approve]').count() == 0
        identity(page, 'lead@corp.com')
        go(page, 'review')
        page.locator('#inbox-review article', has_text=str(days)).locator('[data-open-item]').click()
        page.click('#detail-body [data-review="approve"]')
        expect(page.locator('#detail-body')).to_contain_text('Accepted')
        page.click('#close-detail')

        # 6. A developer opens the shared conversation from the drawer and sees the accepted decision.
        identity(page, 'dev@corp.com')
        page.click('[data-back]:visible')
        page.click('#history-toggle')
        page.locator('#session-list .session-row', has_text='bronze tables').first.click()
        expect(page.locator('#messages .msg-author').first).to_have_text('ba')
        expect(page.locator('#messages .capture-card').first).to_contain_text('accepted', ignore_case=True)
        expect(page.locator('#new-private')).to_be_disabled()

        # 7. Typed starting knowledge from the pipeline folder, without creating the agent.
        go(page, 'manage-agents')
        page.click('#open-create-agent')
        page.fill('#new-agent-name', 'Position pipeline')
        page.fill('#new-agent-purpose', 'Consolidates public-market and private-market positions for the fund into one canonical positions model.')
        page.click('.seed-editor .remove-seed')
        page.click('#seed-import')
        page.set_input_files('#import-files', [str(f) for f in sorted(SCAFFOLD.glob('*.md'))])
        expect(page.locator('#import-preview')).to_contain_text('Found')
        page.click('#import-submit')
        assert page.locator('#new-agent-seeds .seed-editor').count() > 20
        if os.getenv('CREATE_AGENT') == '1':
            page.click('#submit-create-agent')
            expect(page.locator('#agent-catalog')).to_contain_text('Position pipeline')
        else:
            page.click('#close-create-agent')

        # 8. Small screens.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.click('[data-back]:visible')
        page.screenshot(path=OUT / 'focus-mobile.png')
        browser.close()
    assert not errors, errors
    print('browser focus-layout check passed')


if __name__ == '__main__':
    main()
