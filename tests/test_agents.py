import json
import pytest
import agents
from domains import DOMAINS
from retrieval import Index
from pathlib import Path
from store import init, connection

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB',str(tmp_path/'test.sqlite'))
    monkeypatch.delenv('LAKEBASE_HOST',raising=False)
    init(); agents.init()
    monkeypatch.setattr(agents.native,'resources',lambda:{})
    monkeypatch.setattr(agents.native,'flush',lambda key: {'pending':0})

def test_isolated_seed_memories():
    assert len(DOMAINS)==5
    assert 'nine stages' in str(agents.memory('research'))
    assert 'nine stages' not in str(agents.memory('portfolio'))

def test_supervisor_delegates_and_records_every_exchange(monkeypatch):
    def model(messages, tools):
        system=messages[0]['content']
        if 'You are the Supervisor' in system and not any(m['role']=='tool' for m in messages):
            return {'role':'assistant','content':None,'tool_calls':[{'id':'t1','type':'function','function':{'name':'delegate','arguments':json.dumps({'domain':'valuation','task':'Check publication'})}}]}
        return {'role':'assistant','content':'Publication requires basis validation [valuation-M1].'}
    monkeypatch.setattr(agents,'completion',model)
    key=agents.session('alice')
    result=agents.run(key,'alice','How should publication work?',Index(Path('kb')))
    assert result['delegations'][0]['agent']=='valuation'
    child=result['delegations'][0]['session_id']
    with connection() as db:
        events=db.all('SELECT * FROM agent_events WHERE session_id=?',(key,))
        child_events=db.all('SELECT * FROM agent_events WHERE session_id=?',(child,))
    assert [e['kind'] for e in events]==['message','tool_call','tool_result','message']
    assert len(child_events)==2
    assert 'Supervisor-generated task' in child_events[0]['content']
    assert agents.readable(child,'bob')['parent']==key
    private=agents.session('alice','valuation',visibility='private')
    with pytest.raises(ValueError): agents.readable(private,'bob')

def test_failed_model_retains_user_turn_and_error(monkeypatch):
    def fail(*args): raise RuntimeError('unavailable')
    monkeypatch.setattr(agents,'completion',fail)
    key=agents.session('alice','research')
    with pytest.raises(RuntimeError): agents.run(key,'alice','Remember review cadence',Index(Path('kb')))
    with connection() as db: events=db.all('SELECT * FROM agent_events WHERE session_id=?',(key,))
    assert [e['kind'] for e in events]==['message','error']
    assert events[0]['content']=='Remember review cadence'

def test_candidate_never_recalled(monkeypatch):
    monkeypatch.setattr(agents.native,'resources',lambda:{'valuation':{'memory':'test'}})
    monkeypatch.setattr(agents.native,'entries',lambda agent, actor='approved':[{'path':'/x','content':actor}])
    assert agents.memory('valuation')[0]['content']=='approved'

def test_pipeline_candidate_approval_boundary(monkeypatch):
    from fastapi.testclient import TestClient
    import app
    monkeypatch.delenv('MLFLOW_EXPERIMENT_ID',raising=False)
    monkeypatch.setattr(agents.native,'resources',lambda:{'valuation':{'memory':'test'}})
    pending=[{'name':'native/candidate/1','path':'/demo.md','content':'Synthetic Northstar reviews assumptions every 21 days.'}]
    approved=[]
    monkeypatch.setattr(agents.native,'entries',lambda agent,actor='approved': approved if actor=='approved' else pending)
    monkeypatch.setattr(agents.native,'put',lambda agent,path,content,description: approved.append({'path':path,'content':content}))
    with TestClient(app.app) as c:
        data=c.get('/api/agents/valuation/memory').json()
        assert data['approved']==[]
        digest=data['candidates'][0]['review_id']
        assert c.post('/api/agents/valuation/review',json={'review_id':'stale','action':'approve'}).status_code==409
        r=c.post('/api/agents/valuation/review',headers={'x-demo-user':'any-reviewer'},json={'review_id':digest,'action':'approve'})
        assert r.status_code==200
        data=c.get('/api/agents/valuation/memory').json()
        assert len(data['approved'])==1 and not data['candidates']
        assert c.post('/api/agents/valuation/review',json={'review_id':digest,'action':'approve'}).status_code==409

def test_native_approval_retry_is_idempotent(monkeypatch):
    import native_memory
    from databricks.sdk.errors import AlreadyExists
    monkeypatch.setattr(native_memory,'resources',lambda:{'valuation':{'memory':'test'}})
    def duplicate(*args,**kwargs): raise AlreadyExists('entry exists')
    monkeypatch.setattr(native_memory,'call',duplicate)
    monkeypatch.setattr(native_memory,'entries',lambda agent:[{'path':'/learned/test.md','content':'Same approved fact'}])
    assert native_memory.put('valuation','/learned/test.md','Same approved fact')['content']=='Same approved fact'
    with pytest.raises(AlreadyExists): native_memory.put('valuation','/learned/test.md','Different fact')
