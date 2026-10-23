import json, os
from pathlib import Path
import httpx
base=os.getenv('CHECK_URL','http://127.0.0.1:8788')
headers={}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers=WorkspaceClient(profile='fevm').config.authenticate()
c=httpx.Client(base_url=base,headers=headers,timeout=300)
def post(path,body):
    r=c.post('/api'+path,json=body);r.raise_for_status();return r.json()
key=post('/sessions',{'agent':'supervisor'})['id']
r=post('/chat',{'session_id':key,'question':'Explain how evidence review affects fair-value publication, and how a portfolio price differs from that fair value. Consult Research, Valuation and Portfolio specialists.'})
print('supervisor',key,'delegations',[d['agent'] for d in r['delegations']], 'warning',r.get('warning'),flush=True)
assert len(set(d['agent'] for d in r['delegations']))>=3,r
assert not r.get('warning'),r
history=c.get('/api/sessions/'+key).json()
assert any(e['kind']=='tool_call' for e in history)
assert all(e['synced']==1 for e in history),history
for child in r['delegations']:
    events=c.get('/api/sessions/'+child['session_id']).json()
    assert any(e['role']=='assistant' for e in events)
    assert all(e['synced']==1 for e in events)
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/agents-v2-check.json').write_text(json.dumps(r,indent=2))
print('Cross-domain delegation, separate child conversations and native session delivery passed',flush=True)
