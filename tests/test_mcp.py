import json

import pytest
from fastapi.testclient import TestClient

import agents
import app
import native_memory
from store import connection


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('KNOWLEDGE_DB',str(tmp_path/'mcp.sqlite'))
    for key in ('LAKEBASE_HOST','DATABRICKS_APP_NAME','MLFLOW_EXPERIMENT_ID','SERVING_ENDPOINT'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(native_memory,'flush',lambda key: {'pending':0})
    monkeypatch.setattr(agents,'memory',lambda agent: [])
    with TestClient(app.app) as c:
        yield c


def rpc(client, path, method, params=None, user='alice'):
    return client.post(path,headers={'Accept':'application/json, text/event-stream','x-demo-user':user},
                       json={'jsonrpc':'2.0','id':1,'method':method,'params':params or {}})


def test_agent_scoped_mcp_journals_and_continues_owned_conversations(client):
    path='/mcp/valuation'
    initialized=rpc(client,path,'initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'test','version':'1'}})
    assert initialized.json()['result']['serverInfo']['name']=='research-domain-agents'
    names={t['name'] for t in rpc(client,path,'tools/list').json()['result']['tools']}
    assert names=={'ask_valuation','get_conversation','list_conversations','record_item','find_knowledge','get_item','confirm_suggestion','dismiss_suggestion','answer_question','update_todo','export_markdown'}
    result=rpc(client,path,'tools/call',{'name':'ask_valuation','arguments':{'question':'What is fair value?'}}).json()['result']
    assert not result.get('isError')
    key=result['structuredContent']['session_id']
    again=rpc(client,path,'tools/call',{'name':'ask_valuation','arguments':{'question':'What about review?','session_id':key}}).json()['result']
    assert again['structuredContent']['session_id']==key
    history=rpc(client,path,'tools/call',{'name':'get_conversation','arguments':{'session_id':key}}).json()['result']
    assert [e['role'] for e in history['structuredContent']['events']]==['user','assistant','user','assistant']
    with connection() as db:
        assert db.one('SELECT agent,owner FROM agent_sessions WHERE id=?',(key,))=={'agent':'valuation','owner':'alice'}
    shared=rpc(client,path,'tools/call',{'name':'get_conversation','arguments':{'session_id':key}},'bob').json()['result']
    assert not shared.get('isError') and shared['structuredContent']['owner']=='alice'
    denied=rpc(client,'/mcp/portfolio','tools/call',{'name':'get_conversation','arguments':{'session_id':key}}).json()['result']
    assert denied['isError']
    denied=rpc(client,'/mcp/portfolio','tools/call',{'name':'ask_portfolio','arguments':{'question':'Question','session_id':key}}).json()['result']
    assert denied['isError']
    assert rpc(client,path,'tools/call',{'name':'ask_supervisor','arguments':{'question':'Question'}}).json()['result']['isError']


def test_dynamic_agent_directory_validation_and_identity(client):
    import registry
    body=app.CreateAgentIn(id='new-domain',name='New Domain',purpose='A synthetic domain for testing MCP discovery.',keywords=['demo'],
                           seeds=[{'topic':'baseline','content':'Synthetic initial domain knowledge.','source':'test'}],approve_baseline=True)
    registry.create(body,'creator');registry.save('new-domain',status='ready',resources={})
    names={t['name'] for t in rpc(client,'/mcp/','tools/list').json()['result']['tools']}
    assert {'ask_supervisor','ask_valuation','ask_new_domain'}<=names
    names={t['name'] for t in rpc(client,'/mcp/new-domain','tools/list').json()['result']['tools']}
    assert 'ask_new_domain' in names and 'ask_supervisor' not in names
    assert rpc(client,'/mcp/unknown','tools/list').status_code==404
    assert rpc(client,'/mcp/valuation','tools/call',{'name':'ask_valuation','arguments':{'question':'x','owner':'bob'}}).json()['result']['isError']


def test_mcp_rejects_missing_deployed_identity_and_cross_origin(client,monkeypatch):
    import agent_mcp
    from domains import DOMAINS
    monkeypatch.setattr(agent_mcp,'get_domain',lambda agent: DOMAINS[agent])
    monkeypatch.setenv('DATABRICKS_APP_NAME','research-memory-poc')
    monkeypatch.setenv('PUBLIC_APP_URL','https://example.databricksapps.com')
    assert rpc(client,'/mcp/valuation','tools/list').status_code==401
    headers={'Accept':'application/json, text/event-stream','x-forwarded-user':'alice'}
    body={'jsonrpc':'2.0','id':1,'method':'tools/list'}
    assert client.post('/mcp/valuation',headers=headers,json=body).status_code==200
    headers['Origin']='https://untrusted.example'
    assert client.post('/mcp/valuation',headers=headers,json=body).status_code==403
