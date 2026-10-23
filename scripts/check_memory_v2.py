"""Approve explicitly synthetic pipeline output, then verify fresh-session recall."""
import os,json
import httpx
from pathlib import Path
base=os.getenv('CHECK_URL','http://127.0.0.1:8789')
headers={}
if 'databricksapps' in base:
    from databricks.sdk import WorkspaceClient
    headers=WorkspaceClient(profile='fevm').config.authenticate()
c=httpx.Client(base_url=base,headers=headers,timeout=240)
def post(path,body):
    r=c.post('/api'+path,json=body);r.raise_for_status();return r.json()
for agent,needle,q,expected in [
    ('supervisor','Northstar','What is the approved synthetic Northstar specialist reporting order?','Research')]:
    r=c.get('/api/agents/'+agent+'/memory');r.raise_for_status();data=r.json()
    candidate=next((m for m in data['candidates'] if needle.lower() in m['content'].lower()),None)
    if candidate:
        post('/agents/'+agent+'/review',{'review_id':candidate['review_id'],'action':'approve'})
        print(agent,'approved native synthetic candidate',flush=True)
    else:
        assert any(needle.lower() in m['content'].lower() for m in data['approved']),(agent,'candidate not yet available')
    s=post('/sessions',{'agent':agent})['id']
    r=post('/chat',{'session_id':s,'question':q})
    assert expected.lower() in r['answer'].lower(),r
    assert any('/learned/' in m['title'] for m in r['sources']),r
    assert not r.get('warning'),r
    Path('artifacts/'+agent+'-memory-recall.json').write_text(json.dumps(r,indent=2))
    print(agent,'fresh-session recall passed',flush=True)
