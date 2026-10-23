import json
import pytest
from fastapi.testclient import TestClient
from databricks.sdk.errors import AlreadyExists
import app
import agents
import native_memory as native
import registry
from domains import all_domains

BODY={'id':'compliance-demo','name':'Compliance Demo','purpose':'Review synthetic compliance policies and evidence requirements.', 'keywords':['compliance','policy'], 'seeds':[{'topic':'exception-review','content':'SYNTHETIC DEMO: Every policy exception requires a documented reason and reviewer approval.','source':'Synthetic compliance handbook'}], 'approve_baseline':True}

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB',str(tmp_path/'registry.sqlite'))
    for key in ('LAKEBASE_HOST','DATABRICKS_APP_NAME','MLFLOW_EXPERIMENT_ID','SERVING_ENDPOINT'):
        monkeypatch.delenv(key,raising=False)
    cloud={'entries':{},'pipelines':[],'store_creates':[],'fail':False}
    def call(method,path,body=None,query=None):
        if method=='POST' and path in ('memory-stores','session-stores'):
            cloud['store_creates'].append(path);return {}
        if method=='GET' and path=='memory-pipelines':return {'memory_pipelines':cloud['pipelines']}
        if method=='POST' and path=='memory-pipelines':
            if cloud['fail']:raise RuntimeError('temporary provisioning failure')
            item=dict(body,name='memory-pipelines/demo-pipeline');cloud['pipelines'].append(item);return item
        if path.endswith('/entries'):
            store=path.split('/')[1]
            if method=='GET':return {'managed_memory_entries':[m for (s,a,p),m in cloud['entries'].items() if s==store and a==query['actor_id']]}
            key=(store,body['actor_id'],body['path'])
            if key in cloud['entries']:raise AlreadyExists('duplicate')
            cloud['entries'][key]=dict(body,name='entries/demo');return cloud['entries'][key]
        raise AssertionError((method,path))
    monkeypatch.setattr(native,'call',call)
    monkeypatch.setattr(native,'flush',lambda key:{'pending':0})
    with TestClient(app.app) as client:yield client,cloud

def test_create_seed_restart_and_supervisor_discovery(setup,monkeypatch):
    c,cloud=setup
    r=c.post('/api/agents',headers={'x-demo-user':'creator'},json=BODY)
    assert r.status_code==202,r.text
    row=c.get('/api/agent-definitions/compliance-demo').json()
    assert row['status']=='ready'
    assert row['created_by']=='creator'
    assert row['resources']['pipeline']=='demo-pipeline'
    assert 'compliance-demo' in all_domains()
    assert c.get('/api/agents/compliance-demo/memory').json()['approved'][0]['content']==BODY['seeds'][0]['content']
    # A new application lifespan reconstructs agents from persisted definitions.
    with TestClient(app.app) as restarted:
        assert 'compliance-demo' in [a['id'] for a in restarted.get('/api/agents').json()]
        def model(messages,tools):
            if 'You are the Supervisor' in messages[0]['content'] and not any(m['role']=='tool' for m in messages):
                assert 'compliance-demo' in tools[0]['function']['parameters']['properties']['domain']['enum']
                return {'role':'assistant','tool_calls':[{'id':'t1','function':{'name':'delegate','arguments':json.dumps({'domain':'compliance-demo','task':'Explain the exception policy'})}}]}
            return {'role':'assistant','content':'Document a reason and reviewer approval [compliance-demo-M1].'}
        monkeypatch.setattr(agents,'completion',model)
        s=restarted.post('/api/sessions').json()['id']
        answer=restarted.post('/api/chat',json={'session_id':s,'question':'What does the compliance demo require?'}).json()
        assert answer['delegations'][0]['agent']=='compliance-demo'
        assert any(m['label']=='compliance-demo-M1' for m in answer['sources'])

def test_failed_setup_resumes_without_recreating_resources(setup):
    c,cloud=setup;cloud['fail']=True
    assert c.post('/api/agents',json=BODY).status_code==202
    row=c.get('/api/agent-definitions/compliance-demo').json()
    assert row['status']=='failed' and row['seeds']==BODY['seeds']
    assert 'compliance-demo' not in [a['id'] for a in c.get('/api/agents').json()]
    cloud['fail']=False
    assert c.post('/api/agent-definitions/compliance-demo/retry').status_code==202
    assert c.get('/api/agent-definitions/compliance-demo').json()['status']=='ready'
    assert len(cloud['store_creates'])==2
    assert len(cloud['pipelines'])==1

def test_validation_duplicate_and_approval(setup):
    c,cloud=setup
    assert c.post('/api/agents',json=dict(BODY,approve_baseline=False)).status_code==400
    assert c.post('/api/agents',json=dict(BODY,id='../unsafe')).status_code==422
    assert c.post('/api/agents',json=dict(BODY,id='supervisor')).status_code==409
    sensitive=[dict(BODY['seeds'][0],content='The API key is sensitive and must never be shared.')]
    assert c.post('/api/agents',json=dict(BODY,seeds=sensitive)).status_code==400
    assert c.post('/api/agents',json=dict(BODY,seeds=BODY['seeds']*2)).status_code==422
    assert c.post('/api/agents',json=BODY).status_code==202
    assert c.post('/api/agents',json=BODY).status_code==409
    assert len(cloud['store_creates'])==2
