import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agents
import app
import knowledge
import native_memory
from retrieval import Index
from store import connection

SCAFFOLD = Path.home() / 'Work/position_pipeline_scaffold/pipelines/position_pipeline'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB', str(tmp_path / 'knowledge.sqlite'))
    for key in ('LAKEBASE_HOST', 'DATABRICKS_APP_NAME', 'MLFLOW_EXPERIMENT_ID', 'SERVING_ENDPOINT'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(native_memory, 'resources', lambda: {})
    monkeypatch.setattr(native_memory, 'flush', lambda key: {'pending': 0})
    with TestClient(app.app) as c:
        yield c


def as_user(user): return {'x-demo-user': user}


def record(c, user, **body):
    return c.post('/api/agents/valuation/items', headers=as_user(user), json={'type': 'decision', 'title': 'Use SCD Type 1 in gold', 'body': 'Consumers only need current state.', **body})


def test_decision_needs_someone_else_to_approve(client):
    item = record(client, 'ba@corp.com').json()
    assert item['ref'] == 'D-001' and item['status'] == 'proposed' and item['decided_by'] == 'ba@corp.com'
    review = lambda user, action='approve', note='': client.post('/api/agents/valuation/items/D-001/review', headers=as_user(user), json={'action': action, 'expected_version': 1, 'note': note})
    assert review('ba@corp.com').status_code == 403
    assert client.get('/api/inbox', headers=as_user('owner@corp.com')).json()['count'] == 1
    assert client.get('/api/inbox', headers=as_user('ba@corp.com')).json()['count'] == 0
    assert review('owner@corp.com', 'reject').status_code == 400  # reason required
    approved = review('owner@corp.com').json()
    assert approved['status'] == 'accepted' and approved['approved_by'] == 'owner@corp.com'
    assert client.patch('/api/agents/valuation/items/D-001', headers=as_user('owner@corp.com'), json={'title': 'Changed', 'expected_version': 2}).status_code == 403
    detail = client.get('/api/agents/valuation/items/D-001', headers=as_user('dev@corp.com')).json()
    assert [h['action'] for h in detail['history']] == ['create', 'approve']


def test_members_restrict_approval(client):
    client.put('/api/agents/valuation/members', headers=as_user('lead@corp.com'), json={'owners': ['lead@corp.com'], 'approvers': ['arch@corp.com']})
    record(client, 'ba@corp.com')
    review = lambda user: client.post('/api/agents/valuation/items/D-001/review', headers=as_user(user), json={'action': 'approve', 'expected_version': 1})
    assert review('random@corp.com').status_code == 403
    assert client.put('/api/agents/valuation/members', headers=as_user('random@corp.com'), json={'owners': ['random@corp.com']}).status_code == 403
    assert review('arch@corp.com').json()['status'] == 'accepted'


def test_questions_todos_and_changes_skip_approval(client):
    q = record(client, 'da@corp.com', type='question', title='What is the canonical grain?', assigned_to='ba@corp.com').json()
    assert q['status'] == 'open' and q['ref'] == 'Q-001'
    assert client.get('/api/inbox', headers=as_user('ba@corp.com')).json()['assigned'][0]['ref'] == 'Q-001'
    answered = client.post('/api/agents/valuation/items/Q-001/answer', headers=as_user('ba@corp.com'), json={'answer': 'One row per position per day.', 'promote_to_decision': True}).json()
    assert answered['status'] == 'answered' and answered['decision']['status'] == 'proposed'
    assert answered['decision']['decided_by'] == 'ba@corp.com'
    t = record(client, 'dev@corp.com', type='todo', title='Add _ingested_at to bronze').json()
    assert client.post(f"/api/agents/valuation/items/{t['ref']}/status", headers=as_user('dev@corp.com'), json={'status': 'done'}).json()['status'] == 'done'
    assert record(client, 'dev@corp.com', type='change', title='Renamed pos_id to position_id').json()['status'] == 'logged'


def test_supersede_replaces_accepted_decision(client):
    record(client, 'ba@corp.com')
    client.post('/api/agents/valuation/items/D-001/review', headers=as_user('owner@corp.com'), json={'action': 'approve', 'expected_version': 1})
    new = client.post('/api/agents/valuation/items/D-001/supersede', headers=as_user('ba@corp.com'), json={'type': 'decision', 'title': 'Use SCD Type 2 in gold', 'body': 'Audit needs history.'}).json()
    assert new['supersedes_ref'] == 'D-001' and new['status'] == 'proposed'
    client.post('/api/agents/valuation/items/D-002/review', headers=as_user('owner@corp.com'), json={'action': 'approve', 'expected_version': 1})
    old = client.get('/api/agents/valuation/items/D-001', headers=as_user('x')).json()
    assert old['status'] == 'superseded' and old['superseded_by_ref'] == 'D-002'
    decisions = knowledge.export_markdown('valuation')['decisions.md']
    assert 'D-001' in decisions and '**Superseded by:** D-002' in decisions


def test_refs_unique_under_concurrency(client):
    errors = []
    def write(i):
        try: knowledge.create('valuation', {'type': 'rule', 'title': f'Rule number {i}', 'body': 'x'}, 'u')
        except Exception as exc: errors.append(exc)
    threads = [threading.Thread(target=write, args=(i,)) for i in range(12)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert not errors
    refs = [i['ref'] for i in knowledge.list_items('valuation', type='rule')]
    assert sorted(refs) == [f'R-{n:03d}' for n in range(1, 13)]


def test_validation_blocks_secrets_and_transient_values(client):
    assert record(client, 'u', body='The api_key is abc').status_code == 400
    assert record(client, 'u', body='The row count today is 12').status_code == 400
    assert record(client, 'u', type='unknown').status_code == 422


def test_agent_suggests_record_and_user_confirms(client, monkeypatch):
    def model(messages, tools):
        if not any(m['role'] == 'tool' for m in messages):
            assert '[alice@corp.com] We decided' in messages[-1]['content']
            assert {t['function']['name'] for t in tools} >= {'suggest_record', 'find_knowledge'}
            return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 't1', 'function': {'name': 'suggest_record', 'arguments': json.dumps({'type': 'decision', 'title': 'Private positions use NAV rolled forward one quarter', 'body': 'Agreed with the BA.'})}}]}
        return {'role': 'assistant', 'content': 'I suggested recording this decision.'}
    monkeypatch.setattr(agents, 'completion', model)
    key = client.post('/api/sessions', headers=as_user('alice@corp.com'), json={'agent': 'valuation'}).json()['id']
    result = client.post('/api/chat', headers=as_user('alice@corp.com'), json={'session_id': key, 'question': 'We decided private positions use NAV rolled forward one quarter.'}).json()
    draft = result['suggestions'][0]
    assert draft['status'] == 'draft' and draft['decided_by'] == 'alice@corp.com' and draft['source_session'] == key
    # Drafts stay on their conversation card; they are not part of the shared register yet.
    assert not client.get('/api/agents/valuation/items', headers=as_user('bob')).json()['items']
    assert client.get(f'/api/sessions/{key}/items', headers=as_user('bob')).json()[0]['ref'] == draft['ref']
    confirmed = client.post(f"/api/agents/valuation/items/{draft['ref']}/confirm", headers=as_user('alice@corp.com'), json={'title': 'Private positions: NAV + 1Q roll-forward'}).json()
    assert confirmed['status'] == 'proposed' and confirmed['title'] == 'Private positions: NAV + 1Q roll-forward'
    assert client.get('/api/agents/valuation/items', headers=as_user('bob')).json()['counts']['awaiting_review'] == 1


def test_find_knowledge_is_cited_and_brief_injected(client, monkeypatch):
    knowledge.create('valuation', {'type': 'question', 'title': 'Which FX source applies?', 'body': ''}, 'da')
    seen = {}
    def model(messages, tools):
        seen['system'] = messages[0]['content']
        if not any(m['role'] == 'tool' for m in messages):
            return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 't1', 'function': {'name': 'find_knowledge', 'arguments': json.dumps({'type': 'question'})}}]}
        return {'role': 'assistant', 'content': 'Open: [Q-001].'}
    monkeypatch.setattr(agents, 'completion', model)
    key = agents.session('alice', 'valuation')
    result = agents.run(key, 'alice', 'What questions are open?', Index(Path('kb')))
    assert 'Open questions: [Q-001] Which FX source applies?' in seen['system']
    assert any(s['label'] == 'Q-001' and s['kind'] == 'knowledge_item' for s in result['sources'])


def test_mcp_record_item_is_attributed_to_cursor(client):
    def rpc(path, name, args, user='dev@corp.com'):
        return client.post(path, headers={'Accept': 'application/json, text/event-stream', 'x-demo-user': user},
                           json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}).json()['result']
    result = rpc('/mcp/valuation', 'record_item', {'type': 'decision', 'title': 'Use Auto Loader for bronze', 'body': 'File arrival is irregular.'})
    assert not result.get('isError'), result
    item = knowledge.get('valuation', result['structuredContent']['recorded']['ref'])
    assert item['channel'] == 'cursor' and item['recorded_by'] == 'dev@corp.com' and item['status'] == 'proposed'
    found = rpc('/mcp/valuation', 'find_knowledge', {'query': 'auto loader'})['structuredContent']['items']
    assert found[0]['ref'] == item['ref']
    assert rpc('/mcp/', 'find_knowledge', {})['isError']  # combined endpoint needs an agent
    assert rpc('/mcp/', 'find_knowledge', {'agent': 'valuation'})['structuredContent']['items']
    files = rpc('/mcp/valuation', 'export_markdown', {})['structuredContent']['files']
    assert 'Use Auto Loader for bronze' in files['decisions.md']


def test_create_agent_with_typed_starting_knowledge(client, monkeypatch):
    import registry
    monkeypatch.setattr(registry, 'provision', lambda agent: registry.save(agent, status='ready'))
    body = {'id': 'positions', 'name': 'Position pipeline', 'purpose': 'Consolidate public and private market positions into a canonical model.',
            'owners': ['lead@corp.com'], 'approve_baseline': True,
            'items': [{'type': 'decision', 'title': 'Canonical model unifies public and private', 'body': 'One model.', 'decided_by': 'lead@corp.com'},
                      {'type': 'question', 'title': 'Who owns the FX rates?'},
                      {'type': 'decision', 'title': 'Draft decision from folder', 'body': 'x', 'accepted': False}]}
    r = client.post('/api/agents', headers=as_user('creator@corp.com'), json=body)
    assert r.status_code == 202, r.text
    items = {i['title']: i for i in knowledge.list_items('positions')}
    assert items['Canonical model unifies public and private']['status'] == 'accepted'
    assert items['Who owns the FX rates?']['status'] == 'open'
    assert items['Draft decision from folder']['status'] == 'proposed'
    roles = {m['user_email']: m['role'] for m in knowledge.members('positions')}
    assert roles == {'creator@corp.com': 'owner', 'lead@corp.com': 'owner'}
    assert client.post('/api/agents', json=dict(body, id='empty', items=[])).status_code == 422


@pytest.mark.skipif(not SCAFFOLD.exists(), reason='position_pipeline scaffold not present')
def test_parse_position_pipeline_scaffold(client):
    files = {p.name: p.read_text() for p in SCAFFOLD.glob('*.md')}
    items = client.post('/api/knowledge/parse', headers=as_user('u'), json={'files': files}).json()['items']
    kinds = {}
    for i in items: kinds.setdefault(i['type'], []).append(i)
    assert kinds['decision'][0]['title'].startswith('Canonical positions model') and kinds['decision'][0]['accepted'] is True
    assert len(kinds['todo']) == 11 and sum(t['done'] for t in kinds['todo']) == 1
    assert any('Out of scope' in r['title'] for r in kinds['requirement'])
    assert not any(i['title'].startswith('table_name_') or i['title'].startswith('source_name_') for i in items)


def test_projection_and_candidate_ingest(client, monkeypatch):
    store = {}
    monkeypatch.setattr(native_memory, 'resources', lambda: {'valuation': {'memory': 'm'}})
    monkeypatch.setattr(native_memory, 'upsert', lambda agent, path, content, description='', known=None: store.__setitem__(path, content))
    monkeypatch.setattr(native_memory, 'remove', lambda agent, path, known=None: store.pop(path, None))
    candidate = {'path': '/candidates/rule/fx.md', 'content': '---\ntype: rule\ntitle: Convert private NAV to USD at month-end rate\nsource_session: s1\n---\nStated by the BA.'}
    monkeypatch.setattr(native_memory, 'entries', lambda agent, actor='approved': [candidate] if actor == 'candidate' else [])
    q = knowledge.create('valuation', {'type': 'question', 'title': 'Which FX source applies?', 'body': ''}, 'da')
    assert '/register/question/Q-001.md' in store
    knowledge.set_status('valuation', q['ref'], 'closed', 'da')
    assert '/register/question/Q-001.md' not in store
    assert knowledge.ingest_candidates('valuation') == 1 and knowledge.ingest_candidates('valuation') == 0
    rule = knowledge.list_items('valuation', type='rule')[0]
    assert rule['status'] == 'proposed' and rule['channel'] == 'consolidation' and rule['source_session'] == 's1'
    assert '/register/rule/R-001.md' not in store  # proposed items are not recalled until approved
    knowledge.review('valuation', 'R-001', 'approve', 'owner', 1)
    assert 'status: accepted' in store['/register/rule/R-001.md']


def test_parse_decided_by_questions_owners_glossary_and_changes():
    files = {
        'decisions.md': '## D001 — Use Auto Loader (2026-10-01)\n\n**Decision:** Ingest with Auto Loader.\n\n**Decided by:** Priya Nair\n\n**Status:** Accepted\n',
        'todos.md': '## Open questions\n\n- [ ] Who owns FX rates? (owner: Omar)\n\n## TODOs\n\n- [ ] Add DQ checks @dev.lead due 2026-11-01\n- [x] Create raw schema\n',
        'spec.md': '## Requirements\n\n- (must) Publish positions by 07:00 Dubai time\n- Support restatements (should)\n',
        'glossary.md': '- **Grain** — the level of detail of one row\n',
        'changes.md': '## C001 — Renamed position_id to position_key (2026-10-05)\n\n**What:** Renamed the column.\n\n**Why:** Align with naming standard.\n\n**Impact:** model\n',
    }
    items = knowledge.parse_files(files)
    by = {(i['type'], i['title']): i for i in items}
    assert by[('decision', 'Use Auto Loader')]['decided_by'] == 'Priya Nair'
    question = by[('question', 'Who owns FX rates?')]
    assert question['assigned_to'] == 'Omar'
    todo = by[('todo', 'Add DQ checks')]
    assert todo['assigned_to'] == 'dev.lead' and todo['fields']['due'] == '2026-11-01' and not todo['_done']
    assert by[('todo', 'Create raw schema')]['_done']
    assert by[('requirement', 'Publish positions by 07:00 Dubai time')]['fields']['priority'] == 'must'
    assert by[('requirement', 'Support restatements')]['fields']['priority'] == 'should'
    assert by[('glossary', 'Grain')]['body'] == 'the level of detail of one row'
    change = by[('change', 'Renamed position_id to position_key')]
    assert change['fields'] == {'why': 'Align with naming standard.', 'impact': 'model', 'changed_on': '2026-10-05'}


def test_free_form_document_is_classified_by_the_model(client, monkeypatch):
    seen = []

    def fake_model(system, text, max_tokens=6000):
        seen.append((system, text))
        return {'items': [
            {'type': 'decision', 'title': 'Land bronze tables in the raw schema', 'body': 'All bronze tables land in raw.', 'decided_by': 'Priya', 'accepted': True},
            {'type': 'question', 'title': 'Who approves schema changes?', 'body': 'Not yet decided.', 'assigned_to': 'Omar'},
            {'type': 'todo', 'title': 'Set up the raw schema', 'body': 'Create the schema.', 'done': True},
            {'type': 'rule', 'title': 'Our password is hunter2', 'body': 'leaked'},
            {'type': 'unknown', 'title': 'Not a valid type', 'body': ''},
            {'type': 'decision', 'title': 'Land bronze tables in the raw schema', 'body': 'duplicate'},
        ]}
    monkeypatch.setattr(knowledge, 'model_json', fake_model)
    files = {'workshop-notes.md': '# Workshop\n\nWe agreed bronze lands in raw.', 'todos.md': '- [ ] Write runbook\n'}
    r = client.post('/api/knowledge/parse', json={'files': files, 'classify': True, 'agent': 'platform'}).json()
    titles = [(i['type'], i['title']) for i in r['items']]
    assert ('todo', 'Write runbook') in titles  # pipeline-folder files skip the model
    assert titles.count(('decision', 'Land bronze tables in the raw schema')) == 1
    assert ('question', 'Who approves schema changes?') in titles
    assert not any('password' in t for _, t in titles) and not any(k == 'unknown' for k, _ in titles)
    done = next(i for i in r['items'] if i['title'] == 'Set up the raw schema')
    assert done['done'] and r['classified']
    assert len(seen) == 1 and 'Platform & Data' in seen[0][0] and 'untrusted data' in seen[0][0]
    created = client.post('/api/agents/platform/items/import', json={'items': r['items'], 'accept': False}).json()
    assert created['created'] == len(r['items'])
    statuses = {i['title']: i['status'] for i in client.get('/api/agents/platform/items?status=').json()['items']}
    assert statuses['Land bronze tables in the raw schema'] == 'proposed' and statuses['Who approves schema changes?'] == 'open'
    assert statuses['Set up the raw schema'] == 'done'


def test_classification_without_a_model_is_reported(client):
    r = client.post('/api/knowledge/parse', json={'files': {'notes.md': '# Notes\n\nSomething.'}, 'classify': True})
    assert r.status_code == 400 and 'configured model' in r.json()['detail']


def test_reimport_skips_existing_items_and_bad_item_rolls_back(client):
    items = [{'type': 'decision', 'title': 'Use Auto Loader for bronze', 'body': 'Agreed.'},
             {'type': 'todo', 'title': 'Create the raw schema', 'body': ''}]
    first = client.post('/api/agents/platform/items/import', json={'items': items, 'accept': True}).json()
    assert first['created'] == 2 and first['skipped'] == 0
    again = client.post('/api/agents/platform/items/import', json={'items': items + [{'type': 'rule', 'title': 'Bronze is never filtered', 'body': ''}], 'accept': True}).json()
    assert again['created'] == 1 and again['skipped'] == 2
    bad = items[:0] + [{'type': 'rule', 'title': 'Another valid rule', 'body': ''}, {'type': 'rule', 'title': 'The password is hunter2', 'body': ''}]
    assert client.post('/api/agents/platform/items/import', json={'items': bad}).status_code == 400
    titles = [i['title'] for i in client.get('/api/agents/platform/items?status=').json()['items']]
    assert sorted(titles) == ['Bronze is never filtered', 'Create the raw schema', 'Use Auto Loader for bronze']


def test_batch_projection_lists_the_memory_store_once(client, monkeypatch):
    listings, writes = [], []
    monkeypatch.setattr(native_memory, 'resources', lambda: {'platform': {'memory': 'm'}})
    monkeypatch.setattr(native_memory, 'entries', lambda agent, actor='approved': listings.append(agent) or [])
    monkeypatch.setattr(native_memory, 'put', lambda agent, path, content, description: writes.append(path) or {'name': 'memory-stores/m/entries/' + path, 'path': path})
    items = [{'type': 'rule', 'title': f'Rule number {n}', 'body': ''} for n in range(5)]
    created = knowledge.import_items('platform', items, 'ba', accept=True)
    assert created['created'] == 5 and not writes  # import itself never calls the memory store
    assert knowledge.project_pending(50, 'platform') == 5
    assert listings == ['platform'] and len(writes) == 5
    assert knowledge.project_pending(50, 'platform') == 0


def test_lakebase_credential_is_reused(monkeypatch):
    import store
    calls = []

    class Client:
        def __init__(self, **kwargs):
            self.api_client = self

        def do(self, method, path, body=None):
            calls.append(path); return {'token': f'token-{len(calls)}'}

    import databricks.sdk
    monkeypatch.setattr(databricks.sdk, 'WorkspaceClient', Client)
    monkeypatch.setenv('LAKEBASE_ENDPOINT', 'projects/x/branches/y/endpoints/z')
    monkeypatch.setenv('LAKEBASE_USER', 'app-sp')
    monkeypatch.setattr(store, '_CREDENTIAL', {'token': None, 'user': None, 'expires': 0.0})
    assert store._lakebase_login() == ('app-sp', 'token-1')
    assert store._lakebase_login() == ('app-sp', 'token-1') and len(calls) == 1
    assert store._lakebase_login(refresh=True) == ('app-sp', 'token-2')
