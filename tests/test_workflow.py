import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
import app
from tables import build_query

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB', str(tmp_path/'test.sqlite'))
    for key in ('LAKEBASE_HOST', 'DATABRICKS_APP_NAME', 'SERVING_ENDPOINT', 'MLFLOW_EXPERIMENT_ID'):
        monkeypatch.delenv(key, raising=False)
    import native_memory
    monkeypatch.setattr(native_memory, 'resources', lambda: {})
    with TestClient(app.app) as c:
        yield c

def session(c, user):
    return c.post('/api/sessions', headers={'x-demo-user':user}).json()['id']

def ask(c,user,s,q):
    return c.post('/api/chat', headers={'x-demo-user':user}, json={'session_id':s,'question':q})

def test_sessions_are_shared_unless_private(client):
    a=session(client,'alice')
    assert ask(client,'bob',a,'What is research?').status_code==200
    events=client.get(f'/api/sessions/{a}',headers={'x-demo-user':'carol'}).json()
    assert [e['author'] for e in events if e['role']=='user']==['bob']
    listed=client.get('/api/sessions',headers={'x-demo-user':'carol'}).json()
    assert listed[0]['id']==a and listed[0]['participants']==['bob'] and listed[0]['title']=='What is research?'
    private=client.post('/api/sessions',headers={'x-demo-user':'alice'},json={'agent':'research','visibility':'private'}).json()['id']
    assert client.get(f'/api/sessions/{private}',headers={'x-demo-user':'bob'}).status_code==404
    assert ask(client,'bob',private,'Can I join?').status_code==404
    assert private not in [r['id'] for r in client.get('/api/sessions',headers={'x-demo-user':'bob'}).json()]
    assert client.patch(f'/api/sessions/{a}',headers={'x-demo-user':'bob'},json={'title':'Renamed'}).status_code==403
    assert client.patch(f'/api/sessions/{a}',headers={'x-demo-user':'alice'},json={'visibility':'private'}).json()['visibility']=='private'
    assert client.get(f'/api/sessions/{a}',headers={'x-demo-user':'bob'}).status_code==404

def test_legacy_memory_archive_removed(client):
    assert client.post('/api/memories',json={}).status_code in (404,405)

def test_deployed_auth_requires_verified_user(client,monkeypatch):
    monkeypatch.setenv('DATABRICKS_APP_NAME','test')
    assert client.get('/api/status',headers={'x-demo-user':'admin'}).status_code==401

def test_sql_templates_confined():
    assert 'COUNT(*)' in build_query('count','sales','orders')
    with pytest.raises(HTTPException):build_query('count','sales; DROP TABLE x','orders')
    with pytest.raises(HTTPException):build_query('count','other.sales','orders')
    with pytest.raises(HTTPException):build_query('delete','sales','orders')
    assert 'LIMIT 50' in build_query('distribution','sales','orders','status')

def test_scan_confirmation_and_csrf(client):
    assert client.post('/api/tables/query',json={'operation':'count','schema_name':'sales','table':'orders'}).status_code==400
    assert client.post('/api/sessions',headers={'Origin':'https://other.example'}).status_code==403

def test_retrieval_citations(client):
    s=session(client,'alice')
    r=ask(client,'alice',s,'What are the stages of the research journey?')
    assert r.status_code==200
    assert r.json()['sources']
    assert '[supervisor-M1]' in r.json()['answer']

def test_proxy_origin_uses_configured_public_url(client, monkeypatch):
    monkeypatch.setenv('DATABRICKS_APP_NAME', 'test')
    monkeypatch.setenv('PUBLIC_APP_URL', 'https://research.example.com')
    # The runtime Host is internal behind the Apps proxy. A valid public Origin must pass.
    assert client.post('/api/unknown', headers={'Origin':'https://research.example.com'}).status_code==404
    assert client.post('/api/unknown', headers={'Origin':'https://untrusted.example.com'}).status_code==403
