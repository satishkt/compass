import json
from pathlib import Path
import pytest
import agents
import daily_updates as daily
from store import init,connection

@pytest.fixture
def journal(tmp_path,monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB',str(tmp_path/'daily.sqlite'))
    monkeypatch.delenv('LAKEBASE_HOST',raising=False)
    init();agents.init()
    monkeypatch.setattr(daily,'config',lambda:{'timezone':'Asia/Dubai'})
    session=agents.session('private-user','valuation')
    with connection() as db:
        db.execute('INSERT INTO agent_events (id, session_id, kind, role, content, created_at, synced) VALUES (?, ?, ?, ?, ?, ?, ?)',('event-1',session,'message','user','SYNTHETIC DEMO: Atlas reviews assumptions every 14 days. api_key=should-never-export','2026-10-21T20:01:00+00:00',1))
        db.execute('INSERT INTO agent_events (id, session_id, kind, role, content, created_at, synced) VALUES (?, ?, ?, ?, ?, ?, ?)',('event-2',session,'message','assistant','This correction was recorded for approval, not yet shared.','2026-10-22T19:59:00+00:00',1))
        db.execute('INSERT INTO agent_events (id, session_id, kind, role, content, created_at, synced) VALUES (?, ?, ?, ?, ?, ?, ?)',('outside',session,'message','user','Outside the Dubai calendar day.','2026-10-22T20:00:00+00:00',1))
    return daily.LocalArchive(tmp_path/'archive')

def test_calendar_window_redaction_and_idempotent_write(journal):
    calls=[]
    def summarize(text):
        calls.append(text)
        assert 'should-never-export' not in text and 'Outside the Dubai' not in text
        assert '[REDACTED]' in text
        return '## Decisions and corrections\nUser stated a synthetic Atlas review cadence of 14 days; approval remains pending. [event-1]'
    result=daily.generate('2026-10-22','valuation',archive=journal,summarizer=summarize)
    content=journal.read('valuation/2026-10-22.md')
    assert result[0]['status']=='written'
    assert '2 across 1 conversations' in content
    assert 'private-user' not in content
    assert 'not approved agent memory' in content
    assert daily.generate('2026-10-22','valuation',archive=journal,summarizer=summarize)[0]['status']=='unchanged'
    assert len(calls)==1

def test_includes_supervisor_custom_agents_and_empty_days(journal):
    from app import CreateAgentIn
    import registry
    body=CreateAgentIn(id='new-domain',name='New Domain',purpose='A synthetic domain used to test daily archive discovery.',keywords=['demo'],seeds=[{'topic':'baseline','content':'Synthetic baseline knowledge for the domain.','source':'Synthetic test'}],approve_baseline=True)
    registry.create(body,'creator');registry.save('new-domain',status='ready',resources={})
    results=daily.generate('2026-10-20',archive=journal,summarizer=lambda text:pytest.fail('Empty days should not invoke the model'))
    assert {'supervisor','new-domain','valuation'} <= {r['agent'] for r in results}
    assert 'No recorded conversation activity' in journal.read('new-domain/2026-10-20.md')

def test_chunking_keeps_all_content_and_avoids_retrieved_document_copy():
    event={'id':'e1','session_id':'s','kind':'tool_result','role':'tool','created_at':'now','content':json.dumps([{'id':'doc','title':'Policy','content':'Do not paste a complete retrieved document'}])}
    evidence=daily.conversation_evidence(event)
    assert 'Policy' in evidence and 'Do not paste' not in evidence
    parts=daily.chunks(['a'*70000])
    assert len(parts)==3 and sum(p.count('a') for p in parts)==70000
    with pytest.raises(ValueError):daily.relative_path('../escape',daily.parse_day('2026-10-22'))
    with pytest.raises(ValueError):daily.parse_day('../../bad')

def test_model_failure_does_not_write_invented_summary(journal):
    def fail(text):raise RuntimeError('model unavailable')
    with pytest.raises(RuntimeError):daily.generate('2026-10-22','valuation',archive=journal,summarizer=fail)
    assert journal.read('valuation/2026-10-22.md') is None

def test_daily_update_api_limits_job_and_volume_paths(journal,monkeypatch):
    from fastapi.testclient import TestClient
    import app,native_memory
    cfg={'timezone':'Asia/Dubai','volume_root':'/Volumes/demo/archive/updates','job_id':123,'workspace_host':'https://example.databricks.com'}
    monkeypatch.setattr(daily,'config',lambda:cfg)
    class Files:
        root=cfg['volume_root']
        def read(self,path):
            assert path=='valuation/2026-10-22.md'
            return '# Valuation daily update'
    monkeypatch.setattr(daily,'VolumeArchive',Files)
    class API:
        def do(self,method,path,**kwargs):
            if method=='POST':
                assert kwargs['body']=={'job_id':123,'job_parameters':{'date':'2026-10-22','agent':'valuation'}}
                return {'run_id':456}
            return {'job_id':999,'state':{}}
    class Client:api_client=API()
    monkeypatch.setattr(native_memory,'client',lambda:Client())
    with TestClient(app.app) as c:
        assert c.get('/api/agents/valuation/daily-update?day=2026-10-22').json()['path']=='/Volumes/demo/archive/updates/valuation/2026-10-22.md'
        assert c.get('/api/agents/valuation/daily-update?day=../../secrets').status_code==400
        assert c.post('/api/daily-updates/run',json={'day':'2026-10-22','agent':'valuation'}).status_code==202
        assert c.post('/api/daily-updates/run',json={'day':'2026-10-22','agent':'unknown'}).status_code==400
        assert c.get('/api/daily-updates/runs/456').status_code==404
