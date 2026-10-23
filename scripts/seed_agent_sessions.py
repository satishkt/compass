"""Seed provenance-labelled historical transcripts, never invent assistant responses."""
import sys, uuid, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from domains import belongs_to
from native_memory import call, resources
root=Path(__file__).resolve().parents[1]
for agent,cfg in resources().items():
    files=[p for p in (root/'kb').glob('conversation-*.md') if agent=='supervisor' or belongs_to(agent,p.name,p.read_text())]
    if not files: continue
    key=str(uuid.uuid5(uuid.NAMESPACE_URL,'research-poc-v3-history-'+agent))
    base=f"session-stores/{cfg['sessions']}/sessions"
    try: call('GET',base+'/'+key)
    except Exception as exc:
        if getattr(exc,'error_code','') not in ('NOT_FOUND','RESOURCE_DOES_NOT_EXIST'): raise
        call('POST',base,{'actor_id':'candidate','metadata':{'provenance':'Historical project conversation excerpts; requests are not implemented facts'}},{'session_id':key})
    existing=call('GET',base+'/'+key+'/items').get('session_items',[])
    if existing: print(agent,'already seeded');continue
    for p in files:
        call('POST',base+'/'+key+'/items:append',{'items':[{'data':{'type':'message','role':'user','content':'Historical user requests, not verified shipped features. Source: '+p.name+'\n'+p.read_text(),'provenance':'imported historical excerpt'}}]})
    print(agent,len(files),'historical excerpt files seeded',flush=True)
