"""Native Databricks memory and immutable conversation delivery."""
import json
import os
import threading
from functools import wraps, lru_cache
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import AlreadyExists

CONFIG = Path(__file__).with_name('agent-resources.json')

@lru_cache(maxsize=1)
def client():
    return WorkspaceClient() if (os.getenv('DATABRICKS_APP_NAME') or os.getenv('AGENT_JOB_RUNTIME')) else WorkspaceClient(profile=os.getenv('DATABRICKS_CONFIG_PROFILE', 'fevm'))

def call(method, path, body=None, query=None):
    return client().api_client.do(method, '/api/2.0/agents/' + path, body=body, query=query) or {}

def resources():
    result=json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    import registry
    for row in registry.definitions():
        result[row['id']]=row['resources']
    return result

def entries(agent, actor='approved'):
    cfg = resources().get(agent)
    if not cfg: return []
    result, token = [], None
    while True:
        page = call('GET', f"memory-stores/{cfg['memory']}/entries", query={'actor_id': actor, **({'page_token': token} if token else {})})
        result.extend(page.get('managed_memory_entries', []))
        token = page.get('next_page_token')
        if not token: return result

def put(agent, path, content, description='Human approved'):
    cfg = resources()[agent]
    try:
        return call('POST', f"memory-stores/{cfg['memory']}/entries", {'actor_id':'approved','path':path,'content':content,'description':description})
    except Exception as exc:
        if not isinstance(exc,AlreadyExists) and getattr(exc, 'error_code', '') not in ('ALREADY_EXISTS', 'RESOURCE_ALREADY_EXISTS'): raise
        existing = next((m for m in entries(agent) if m['path']==path), None)
        if existing and existing['content']==content: return existing
        raise


_locks = {}
_guard = threading.Lock()

def serialized(fn):
    @wraps(fn)
    def wrapped(session_id):
        with _guard: lock = _locks.setdefault(session_id, threading.Lock())
        with lock: return fn(session_id)
    return wrapped

@serialized
def flush(session_id):
    from store import connection
    with connection() as db:
        session = db.one('SELECT * FROM agent_sessions WHERE id=?', (session_id,))
        events = db.all('SELECT * FROM agent_events WHERE session_id=? ORDER BY created_at, id', (session_id,))
    cfg = resources().get(session['agent'])
    if not cfg: return {'pending': len(events), 'mode':'local journal; native resources not configured'}
    base = f"session-stores/{cfg['sessions']}/sessions"
    try:
        call('GET', base + '/' + session_id)
    except Exception as exc:
        if getattr(exc, 'error_code', '') not in ('NOT_FOUND', 'RESOURCE_DOES_NOT_EXIST'): raise
        call('POST', base, {'actor_id':'candidate','metadata':{'agent':session['agent'],'parent':session['parent'] or '', 'provenance':'application conversation'}}, {'session_id':session_id})
    delivered, token = set(), None
    while True:
        page = call('GET', base + '/' + session_id + '/items', query={'order_by':'create_time asc', **({'page_token':token} if token else {})})
        for item in page.get('items', page.get('session_items', [])):
            data = item.get('data', {})
            if isinstance(data, str): data = json.loads(data)
            delivered.add(data.get('event_id'))
        token = page.get('next_page_token')
        if not token: break
    for event in events:
        if event['id'] not in delivered:
            call('POST', base + '/' + session_id + '/items:append', {'items':[{'data':{'event_id':event['id'],'type':event['kind'],'role':event['role'],'content':event['content'],'timestamp':event['created_at']}}]})
        with connection() as db:
            db.execute('UPDATE agent_events SET synced=1 WHERE id=?', (event['id'],))
    return {'pending':0,'mode':'native session store'}

def retry_pending():
    from store import connection
    with connection() as db:
        rows = db.all('SELECT DISTINCT session_id FROM agent_events WHERE synced=0')
    for row in rows:
        try: flush(row['session_id'])
        except Exception:
            import logging
            logging.getLogger(__name__).warning('Native session delivery pending for %s',row['session_id'])

def _entry(agent, path, actor='approved', known=None):
    return next((m for m in (entries(agent, actor) if known is None else known) if m['path'] == path), None)

def upsert(agent, path, content, description='Knowledge register', known=None):
    """Create the approved entry, or update content/description in place when the path already exists.
    `known` is an optional prefetched entry list, kept current, so a batch lists the store once."""
    existing = _entry(agent, path, known=known)
    if not existing:
        created = put(agent, path, content, description)
        if known is not None: known.append(dict(created or {}, path=path, content=content))
        return created
    if existing['content'] == content: return existing
    return client().api_client.do('PATCH', '/api/2.0/agents/' + existing['name'], query={'update_mask': 'content,description'},
                                  body={'content': content, 'description': description}) or {}

def remove(agent, path, known=None):
    existing = _entry(agent, path, known=known)
    if existing:
        client().api_client.do('DELETE', '/api/2.0/agents/' + existing['name'])
        if known is not None: known.remove(existing)
