import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from retrieval import Index, tokens
from store import connection, init
from tables import build_query, run_query

ROOT = Path(__file__).resolve().parent
INDEX = Index(ROOT / 'kb')
LOG = logging.getLogger(__name__)

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def audit(db, actor, action, target, detail=None):
    db.execute('INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?)', (uid(), actor, action, target, json.dumps(detail or {}), now()))

def actor(request: Request):
    if os.getenv('DATABRICKS_APP_NAME'):
        # Prefer the email so authorship ("decided by", "recorded by") is readable; the user header is an opaque ID.
        user = request.headers.get('x-forwarded-email') or request.headers.get('x-forwarded-user')
        if not user:
            raise HTTPException(401, 'Databricks authenticated user required.')
        return user
    # Local-only simulation; deployed mode never trusts this header.
    return request.headers.get('x-demo-user', 'local-researcher')[:150]

@asynccontextmanager
async def lifespan(app):
    init()
    import agents
    agents.init()
    if os.getenv('MLFLOW_EXPERIMENT_ID'):
        import mlflow
        mlflow.set_tracking_uri('databricks')
        mlflow.set_experiment(experiment_id=os.environ['MLFLOW_EXPERIMENT_ID'])
    import asyncio
    async def deliver_outbox():
        import native_memory, knowledge
        ticks = 0
        while True:
            await asyncio.sleep(30)
            ticks += 1
            await asyncio.to_thread(native_memory.retry_pending)
            import registry
            await asyncio.to_thread(registry.resume_pending)
            try:
                await asyncio.to_thread(knowledge.project_pending)
                # Typed consolidation candidates change at most daily; check every ~10 minutes.
                if ticks % 20 == 1:
                    for agent in list(native_memory.resources()):
                        await asyncio.to_thread(knowledge.ingest_candidates, agent)
            except Exception:
                LOG.warning('Knowledge projection or candidate ingestion failed; will retry', exc_info=True)
    task = asyncio.create_task(deliver_outbox())
    try:
        from agent_mcp import create_manager
        app.state.mcp_manager = create_manager()
        async with app.state.mcp_manager.run():
            yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass

app = FastAPI(title='Pipeline Compass', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

from agent_mcp import install as install_mcp
install_mcp(app, INDEX, actor)

@app.middleware('http')
async def harden(request, call_next):
    if request.method in ('POST', 'PUT', 'DELETE'):
        origin = request.headers.get('origin')
        expected_origin = os.getenv('PUBLIC_APP_URL', '').rstrip('/') if os.getenv('DATABRICKS_APP_NAME') else str(request.base_url).rstrip('/')
        if origin and origin.rstrip('/') != expected_origin:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Cross-origin writes are blocked.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/')
def home(): return FileResponse(ROOT / 'static/index.html')

@app.get('/api/status')
def status(user=Depends(actor)):
    import knowledge
    return {'user': user, 'mode': 'Databricks' if os.getenv('DATABRICKS_APP_NAME') else 'Local prototype', 'model': os.getenv('SERVING_ENDPOINT') or 'Source excerpts (no model configured)', 'documents': len(list((ROOT / 'kb').glob('*.md'))), 'passages': len(INDEX.passages), 'inbox': knowledge.inbox(user)['count'], 'storage': 'Lakebase' if os.getenv('LAKEBASE_HOST') else 'SQLite', 'catalog': os.getenv('POC_CATALOG', 'satish_doc_intelligence_catalog'), 'tables_enabled': bool(os.getenv('DATABRICKS_WAREHOUSE_ID')), 'tracing': 'MLflow + audit' if os.getenv('MLFLOW_EXPERIMENT_ID') else 'Application audit'}

@app.get('/api/sources')
def sources(user=Depends(actor)):
    manifest = json.loads((ROOT / 'kb/manifest.json').read_text())
    return {'files': [{'name': f.name, 'bytes': f.stat().st_size, 'historical': f.name.startswith('conversation-')} for f in sorted((ROOT / 'kb').glob('*.md'))], 'manifest': manifest}

@app.get('/api/sources/{name}')
def source(name: str, user=Depends(actor)):
    if Path(name).name != name or not name.endswith('.md'):
        raise HTTPException(404)
    path = ROOT / 'kb' / name
    if not path.is_file(): raise HTTPException(404)
    return {'name': name, 'content': path.read_text()}

class AgentSessionIn(BaseModel):
    agent: str = 'supervisor'
    visibility: str = Field(default='shared', pattern='^(shared|private)$')

@app.post('/api/sessions')
def create_session(body: AgentSessionIn = AgentSessionIn(), user=Depends(actor)):
    import agents
    try: return {'id': agents.session(user, body.agent, visibility=body.visibility)}
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get('/api/sessions')
def all_sessions(agent: str = '', mine: bool = False, q: str = '', include_children: bool = False, user=Depends(actor)):
    sql, args = "SELECT * FROM agent_sessions WHERE (visibility='shared' OR owner=?)", [user]
    if agent: sql += ' AND agent=?'; args.append(agent)
    if mine: sql += ' AND owner=?'; args.append(user)
    if not include_children: sql += ' AND parent IS NULL'
    if q: sql += ' AND LOWER(COALESCE(title, \'\')) LIKE ?'; args.append('%'+q.lower()+'%')
    sql += ' ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 200'
    with connection() as db:
        rows = db.all(sql, tuple(args))
        if rows:
            marks = ','.join('?'*len(rows))
            stats = db.all(f"SELECT session_id, author, COUNT(*) AS n FROM agent_events WHERE kind='message' AND role='user' AND session_id IN ({marks}) GROUP BY session_id, author", tuple(r['id'] for r in rows))
            for r in rows:
                mine_stats = [x for x in stats if x['session_id']==r['id']]
                r['participants'] = sorted({x['author'] for x in mine_stats if x['author']})
                r['message_count'] = sum(x['n'] for x in mine_stats)
    return rows

@app.get('/api/sessions/{session}')
def session_messages(session: str, user=Depends(actor)):
    import agents
    try: agents.readable(session, user)
    except ValueError: raise HTTPException(404)
    with connection() as db:
        return db.all('SELECT * FROM agent_events WHERE session_id=? ORDER BY created_at, id', (session,))

@app.get('/api/sessions/{session}/items')
def session_items(session: str, user=Depends(actor)):
    import agents, knowledge
    try: agents.readable(session, user)
    except ValueError: raise HTTPException(404)
    # Include suggestions made by specialists the supervisor consulted from this conversation.
    with connection() as db: children = [r['id'] for r in db.all('SELECT id FROM agent_sessions WHERE parent=?', (session,))]
    return [i for key in [session] + children for i in knowledge.list_items(session=key)]

class SessionPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    visibility: str | None = Field(default=None, pattern='^(shared|private)$')

@app.patch('/api/sessions/{session}')
def update_session(session: str, body: SessionPatch, user=Depends(actor)):
    import agents
    try: row = agents.readable(session, user)
    except ValueError: raise HTTPException(404)
    if row['owner'] != user: raise HTTPException(403, 'Only the person who started this conversation can change it.')
    with connection() as db:
        if body.title is not None: db.execute('UPDATE agent_sessions SET title=? WHERE id=?', (body.title.strip(), session))
        if body.visibility is not None: db.execute('UPDATE agent_sessions SET visibility=? WHERE id=? OR parent=?', (body.visibility, session, session))
        audit(db, user, 'update_conversation', session, body.model_dump(exclude_none=True))
        return db.one('SELECT * FROM agent_sessions WHERE id=?', (session,))

@app.post('/api/sessions/{session}/sync')
def sync_session(session: str, user=Depends(actor)):
    import agents, native_memory
    try: agents.readable(session, user)
    except ValueError: raise HTTPException(404)
    return native_memory.flush(session)

class ChatIn(BaseModel):
    session_id: str
    question: str = Field(min_length=2, max_length=5000)

@app.post('/api/chat')
def chat(body: ChatIn, user=Depends(actor)):
    import agents
    try: return agents.run(body.session_id, user, body.question, INDEX)
    except ValueError as exc: raise HTTPException(404, str(exc))
    except Exception:
        LOG.exception('Agent execution failed')
        raise HTTPException(502, 'Agent execution failed. Your message and error event were saved; retry or inspect conversation history.')

SENSITIVE = re.compile(r'(?i)(\bpassword\b|\bsecret\b|api[_ -]?key|bearer\s+|dapi[a-z0-9]{10}|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{3}-\d{2}-\d{4}\b)')

@app.get('/api/audit')
def audit_log(user=Depends(actor)):
    with connection() as db:
        return db.all('SELECT * FROM audit ORDER BY created_at DESC LIMIT 100')

class TableIn(BaseModel):
    operation: str
    schema_name: str = ''
    table: str = ''
    column: str = ''
    confirm_scan: bool = False

@app.post('/api/tables/query')
def table_query(body: TableIn, request: Request, user=Depends(actor)):
    if body.operation in ('count', 'distribution') and not body.confirm_scan:
        raise HTTPException(400, 'Confirm the aggregate scan; it may scan a large table.')
    sql = build_query(body.operation, body.schema_name, body.table, body.column)
    result = run_query(sql, request.headers.get('x-forwarded-access-token'))
    with connection() as db:
        audit(db, user, 'table_query', result['statement_id'], {'sql': sql, 'identity': result['identity']})
    return result

@app.get('/api/agents')
def agent_list(user=Depends(actor)):
    from domains import all_domains
    import native_memory
    cfg = native_memory.resources()
    return [dict(id=d.id,name=d.name,purpose=d.purpose,keywords=d.keywords,seed_count=len(d.seeds),resources=cfg.get(d.id)) for d in all_domains().values()]

@app.get('/api/agents/{agent}/memory')
def agent_memory(agent: str, user=Depends(actor)):
    import agents, native_memory
    from domains import get_domain
    try: get_domain(agent)
    except ValueError: raise HTTPException(404)
    return {'approved':agents.memory(agent),'candidates':agents.candidates(agent) if native_memory.resources().get(agent) else []}

class CandidateReview(BaseModel):
    review_id: str
    action: str = Field(pattern='^(approve|reject)$')

@app.post('/api/agents/{agent}/review')
def review_agent_memory(agent: str, body: CandidateReview, user=Depends(actor)):
    import agents, native_memory
    candidates = agents.candidates(agent)
    entry = next((m for m in candidates if m['review_id']==body.review_id),None)
    if not entry: raise HTTPException(409, 'Candidate changed or was already reviewed. Reload memory.')
    if body.action == 'approve':
        if SENSITIVE.search(entry['content']): raise HTTPException(400, 'Candidate contains sensitive content; reject it.')
        native_memory.put(agent,'/learned/'+body.review_id+'.md',entry['content'],'Human approved consolidation')
    with connection() as db:
        db.execute('INSERT INTO agent_reviews VALUES (?, ?, ?, ?, ?, ?)',(body.review_id,agent,entry['content'],body.action,user,now()))
        audit(db,user,'agent_memory_'+body.action,body.review_id,{'agent':agent})
    return {'status':body.action}

@app.post('/api/agents/{agent}/consolidate')
def consolidate(agent: str, user=Depends(actor)):
    import native_memory
    cfg = native_memory.resources().get(agent)
    if not cfg: raise HTTPException(400,'Native pipeline is not configured locally.')
    with connection() as db:
        sessions = db.all('SELECT DISTINCT s.id FROM agent_sessions s JOIN agent_events e ON e.session_id=s.id WHERE s.agent=? AND e.synced=0',(agent,))
    for session in sessions: native_memory.flush(session['id'])
    return native_memory.call('POST',f"memory-pipelines/{cfg['pipeline']}/run",{})

@app.get('/api/agents/{agent}/pipeline')
def pipeline(agent: str, user=Depends(actor)):
    import native_memory
    cfg=native_memory.resources().get(agent)
    if not cfg: return {'mode':'local journal only'}
    return native_memory.call('GET',f"memory-pipelines/{cfg['pipeline']}")

@app.get('/api/agents/{agent}/pipeline/runs/{run}')
def pipeline_run(agent: str, run: str, user=Depends(actor)):
    import native_memory
    cfg=native_memory.resources().get(agent)
    if not cfg: raise HTTPException(404)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',run): raise HTTPException(400)
    return native_memory.call('GET',f"memory-pipelines/{cfg['pipeline']}/runs/{run}")

class SeedMemoryIn(BaseModel):
    topic: str = Field(min_length=2,max_length=100,pattern=r'^[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)*$')
    content: str = Field(min_length=12,max_length=6000)
    source: str = Field(min_length=3,max_length=500)

class ItemIn(BaseModel):
    type: str = Field(pattern='^(requirement|rule|decision|question|todo|change|source|model|glossary|note)$')
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(default='', max_length=8000)
    fields: dict = Field(default_factory=dict)
    decided_by: str | None = Field(default=None, max_length=200)
    assigned_to: str | None = Field(default=None, max_length=200)
    supersedes_ref: str | None = Field(default=None, max_length=20)
    source_session: str | None = Field(default=None, max_length=100)
    source_event: str | None = Field(default=None, max_length=100)
    accepted: bool | None = None   # import only: False when the source folder marks a decision as not yet accepted
    done: bool = False       # import only: a completed TODO in the source folder

class CreateAgentIn(BaseModel):
    id: str = Field(min_length=3,max_length=40,pattern=r'^[a-z][a-z0-9-]+$')
    name: str = Field(min_length=3,max_length=80)
    purpose: str = Field(min_length=20,max_length=1500)
    keywords: list[str] = Field(default_factory=list,max_length=20)
    seeds: list[SeedMemoryIn] = Field(default_factory=list,max_length=20)
    items: list[ItemIn] = Field(default_factory=list,max_length=500)
    owners: list[str] = Field(default_factory=list,max_length=20)
    approvers: list[str] = Field(default_factory=list,max_length=50)
    approve_baseline: bool = False

    @model_validator(mode='after')
    def clean(self):
        self.name=self.name.strip()
        self.purpose=self.purpose.strip()
        if len(self.name)<3 or len(self.purpose)<20: raise ValueError('Provide an agent name and a meaningful description.')
        if not self.keywords:
            self.keywords=[w for w in re.findall(r'[a-z0-9]{3,}',self.name.lower())] or [self.id]
        self.keywords=list(dict.fromkeys(k.strip().lower() for k in self.keywords))
        if any(not k or len(k)>80 for k in self.keywords): raise ValueError('Keywords must contain 1–80 characters each.')
        if len({s.topic for s in self.seeds})!=len(self.seeds): raise ValueError('Each baseline memory needs a unique topic.')
        if not self.seeds and not self.items: raise ValueError('Add at least one starting knowledge item.')
        return self

@app.post('/api/agents',status_code=202)
def add_agent(body: CreateAgentIn, tasks: BackgroundTasks, user=Depends(actor)):
    import registry, knowledge
    if body.seeds and not body.approve_baseline: raise HTTPException(400,'Approve the baseline memories before creating this shared agent.')
    for seed in body.seeds:
        if SENSITIVE.search(seed.content+' '+seed.source): raise HTTPException(400,'Remove credentials or personal data from baseline memories and sources.')
        if re.search(r'(?i)\b(row count|rows today|current price|live query result)\b',seed.content): raise HTTPException(400,'Transient query results are not durable baseline memories.')
    for item in body.items:
        try: knowledge.validate(item.model_dump())
        except ValueError as exc: raise HTTPException(400,f'{item.title}: {exc}')
    try: row=registry.create(body,user)
    except ValueError as exc: raise HTTPException(409,str(exc))
    knowledge.set_members(body.id,[user]+body.owners,body.approvers,user)
    # Accepting starting knowledge is the creator's explicit approval; otherwise items wait in the review inbox.
    knowledge.import_items(body.id,[import_payload(i) for i in body.items],user,accept=body.approve_baseline,channel='seed')  # projected once setup is ready
    tasks.add_task(registry.provision,body.id)
    return row

def import_payload(item):
    data=item.model_dump(exclude={'accepted','done'})
    data['_accepted']=item.accepted is not False
    data['_done']=item.done
    return data

@app.get('/api/agent-definitions')
def agent_definitions(user=Depends(actor)):
    import registry
    return registry.definitions()

@app.get('/api/agent-definitions/{agent}')
def agent_definition(agent: str,user=Depends(actor)):
    import registry
    try: return registry.get(agent)
    except ValueError: raise HTTPException(404,'Agent definition not found.')

@app.post('/api/agent-definitions/{agent}/retry',status_code=202)
def retry_agent(agent: str,tasks: BackgroundTasks,user=Depends(actor)):
    import registry
    try: row=registry.get(agent)
    except ValueError: raise HTTPException(404,'Agent definition not found.')
    if row['status']=='failed':
        registry.save(agent,status='creating')
        tasks.add_task(registry.provision,agent)
        with connection() as db: audit(db,user,'retry_agent_setup',agent)
    return registry.get(agent)

class DailyUpdateIn(BaseModel):
    day: str = ''
    agent: str = ''

@app.get('/api/daily-updates')
def daily_update_config(user=Depends(actor)):
    import daily_updates
    from domains import all_domains
    cfg=daily_updates.config()
    return {'configured':bool(cfg.get('job_id')),'volume_root':cfg.get('volume_root'),'job_id':cfg.get('job_id'),'job_url':cfg.get('workspace_host','').rstrip('/')+'/jobs/'+str(cfg['job_id']) if cfg.get('job_id') else None,'timezone':cfg.get('timezone','Asia/Dubai'),'schedule':cfg.get('schedule'),'default_date':daily_updates.parse_day().isoformat(),'agents':[{'id':d.id,'name':d.name} for d in all_domains().values()]}

@app.get('/api/agents/{agent}/daily-update')
def read_daily_update(agent: str, day: str = '', user=Depends(actor)):
    import daily_updates
    from domains import get_domain
    try:
        get_domain(agent)
        stamp=daily_updates.parse_day(day)
        relative=daily_updates.relative_path(agent,stamp)
    except ValueError as exc: raise HTTPException(400,str(exc))
    archive=daily_updates.VolumeArchive()
    text=archive.read(relative)
    if text is None: raise HTTPException(404,'No daily update has been written for this agent and date.')
    return {'agent':agent,'date':stamp.isoformat(),'path':archive.root+'/'+relative,'content':text}

@app.post('/api/daily-updates/run',status_code=202)
def run_daily_updates(body: DailyUpdateIn,user=Depends(actor)):
    import daily_updates,native_memory
    from domains import get_domain
    cfg=daily_updates.config()
    if not cfg.get('job_id'): raise HTTPException(503,'Daily update job is not configured.')
    try:
        stamp=daily_updates.parse_day(body.day)
        if body.agent:get_domain(body.agent)
    except ValueError as exc:raise HTTPException(400,str(exc))
    result=native_memory.client().api_client.do('POST','/api/2.1/jobs/run-now',body={'job_id':cfg['job_id'],'job_parameters':{'date':stamp.isoformat(),'agent':body.agent}})
    with connection() as db:audit(db,user,'daily_update_run',str(result['run_id']),{'agent':body.agent or 'all','date':stamp.isoformat()})
    return {'run_id':result['run_id'],'job_url':cfg['workspace_host'].rstrip('/')+'/jobs/'+str(cfg['job_id'])+'/runs/'+str(result['run_id'])}

@app.get('/api/daily-updates/runs/{run_id}')
def daily_update_run(run_id: int,user=Depends(actor)):
    import daily_updates,native_memory
    result=native_memory.client().api_client.do('GET','/api/2.1/jobs/runs/get',query={'run_id':run_id})
    if result.get('job_id')!=daily_updates.config().get('job_id'):raise HTTPException(404)
    return {'run_id':run_id,'state':result.get('state',{}),'run_page_url':result.get('run_page_url')}

# ---------- Knowledge register ----------

def knowledge_call(fn, *args, **kwargs):
    import knowledge
    try: return fn(*args, **kwargs)
    except LookupError as exc: raise HTTPException(404, str(exc))
    except PermissionError as exc: raise HTTPException(403, str(exc))
    except knowledge.Conflict as exc: raise HTTPException(409, str(exc))
    except ValueError as exc: raise HTTPException(400, str(exc))

def known_agent(agent):
    from domains import get_domain
    try: return get_domain(agent)
    except ValueError: raise HTTPException(404, 'Unknown agent or agent setup is not complete.')

@app.get('/api/agents/{agent}/items')
def list_items(agent: str, type: str = '', status: str = '', q: str = '', assigned_to: str = '', user=Depends(actor)):
    import knowledge
    known_agent(agent)
    return {'items': knowledge.list_items(agent, type=type or None, status=status or None, query=q or None, assigned_to=assigned_to or None),
            'counts': knowledge.counts(agent), 'members': knowledge.members(agent)}

@app.post('/api/agents/{agent}/items', status_code=201)
def create_item(agent: str, body: ItemIn, user=Depends(actor)):
    import knowledge
    known_agent(agent)
    if body.source_session:
        import agents
        try: agents.readable(body.source_session, user)
        except ValueError: raise HTTPException(404, 'Source conversation not found.')
    item = knowledge_call(knowledge.create, agent, body.model_dump(exclude={'accepted', 'done'}), user, channel='web',
                          source_session=body.source_session, source_event=body.source_event)
    with connection() as db: audit(db, user, 'record_' + item['type'], agent + ':' + item['ref'])
    return item

@app.get('/api/agents/{agent}/items/{ref}')
def get_item(agent: str, ref: str, user=Depends(actor)):
    import knowledge
    item = knowledge_call(knowledge.get, agent, ref, detail=True)
    item['can_approve'], item['approval_note'] = knowledge.approval_rights(agent, user, item)
    return item

class ItemPatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, max_length=8000)
    fields: dict | None = None
    decided_by: str | None = Field(default=None, max_length=200)
    assigned_to: str | None = Field(default=None, max_length=200)
    expected_version: int

@app.patch('/api/agents/{agent}/items/{ref}')
def edit_item(agent: str, ref: str, body: ItemPatch, user=Depends(actor)):
    import knowledge
    return knowledge_call(knowledge.edit, agent, ref, body.model_dump(exclude={'expected_version'}), user, body.expected_version)

class ConfirmIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, max_length=8000)
    fields: dict | None = None
    decided_by: str | None = Field(default=None, max_length=200)
    assigned_to: str | None = Field(default=None, max_length=200)

@app.post('/api/agents/{agent}/items/{ref}/confirm')
def confirm_item(agent: str, ref: str, body: ConfirmIn = ConfirmIn(), user=Depends(actor)):
    import knowledge
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    item = knowledge_call(knowledge.confirm, agent, ref, user, changes or None)
    with connection() as db: audit(db, user, 'record_' + item['type'], agent + ':' + item['ref'])
    return item

@app.post('/api/agents/{agent}/items/{ref}/dismiss')
def dismiss_item(agent: str, ref: str, user=Depends(actor)):
    import knowledge
    return knowledge_call(knowledge.dismiss, agent, ref, user)

class ItemReviewIn(BaseModel):
    action: str = Field(pattern='^(approve|reject|request_changes)$')
    expected_version: int
    note: str = Field(default='', max_length=2000)

@app.post('/api/agents/{agent}/items/{ref}/review')
def review_item(agent: str, ref: str, body: ItemReviewIn, user=Depends(actor)):
    import knowledge
    item = knowledge_call(knowledge.review, agent, ref, body.action, user, body.expected_version, body.note)
    with connection() as db: audit(db, user, 'knowledge_' + body.action, agent + ':' + ref, {'note': body.note})
    return item

class AnswerIn(BaseModel):
    answer: str = Field(min_length=2, max_length=8000)
    promote_to_decision: bool = False

@app.post('/api/agents/{agent}/items/{ref}/answer')
def answer_item(agent: str, ref: str, body: AnswerIn, user=Depends(actor)):
    import knowledge
    return knowledge_call(knowledge.answer, agent, ref, body.answer, user, body.promote_to_decision)

class StatusIn(BaseModel):
    status: str = Field(pattern='^(open|done|cancelled|closed)$')

@app.post('/api/agents/{agent}/items/{ref}/status')
def item_status(agent: str, ref: str, body: StatusIn, user=Depends(actor)):
    import knowledge
    return knowledge_call(knowledge.set_status, agent, ref, body.status, user)

@app.post('/api/agents/{agent}/items/{ref}/supersede', status_code=201)
def supersede_item(agent: str, ref: str, body: ItemIn, user=Depends(actor)):
    import knowledge
    data = dict(body.model_dump(exclude={'accepted', 'done'}), supersedes_ref=ref)
    return knowledge_call(knowledge.create, agent, data, user, channel='web')

class MembersIn(BaseModel):
    owners: list[str] = Field(default_factory=list, max_length=20)
    approvers: list[str] = Field(default_factory=list, max_length=50)

@app.get('/api/agents/{agent}/members')
def get_members(agent: str, user=Depends(actor)):
    import knowledge
    return knowledge.members(agent)

@app.put('/api/agents/{agent}/members')
def put_members(agent: str, body: MembersIn, user=Depends(actor)):
    import knowledge
    known_agent(agent)
    current = knowledge.members(agent)
    owners = {m['user_email'] for m in current if m['role'] == 'owner'}
    if owners and user.lower() not in owners: raise HTTPException(403, 'Only an owner can change owners and approvers.')
    if not body.owners: raise HTTPException(400, 'Keep at least one owner.')
    with connection() as db:
        db.execute('DELETE FROM agent_members WHERE agent_id=?', (agent,))
        audit(db, user, 'update_members', agent, body.model_dump())
    knowledge.set_members(agent, body.owners, body.approvers, user)
    return knowledge.members(agent)

@app.get('/api/inbox')
def inbox(user=Depends(actor)):
    import knowledge
    from domains import all_domains
    return knowledge.inbox(user, set(all_domains()))

class ParseIn(BaseModel):
    files: dict[str, str] = Field(max_length=50)
    classify: bool = False
    agent: str = ''
    name: str = Field(default='', max_length=80)
    purpose: str = Field(default='', max_length=1500)

@app.post('/api/knowledge/parse')
def parse_files(body: ParseIn, user=Depends(actor)):
    import knowledge
    if sum(len(v) for v in body.files.values()) > 2_000_000: raise HTTPException(400, 'Upload at most 2 MB of text.')
    classify = None
    if body.classify:
        name, purpose = body.name or 'new', body.purpose or 'project knowledge'
        if body.agent:
            domain = known_agent(body.agent)
            name, purpose = domain.name, domain.purpose
        classify = lambda filename, text: knowledge.classify_document(filename, text, name, purpose)
    try: items = knowledge.parse_files(body.files, classify)
    except RuntimeError as exc: raise HTTPException(400, str(exc))
    except (ValueError, httpx.HTTPError):
        LOG.exception('Document classification failed')
        raise HTTPException(502, 'The agent could not classify this document. Try again, or import it as notes.')
    return {'items': [dict({k: v for k, v in i.items() if not k.startswith('_')}, accepted=i.get('_accepted'), done=i.get('_done', False), source_file=i.get('_source')) for i in items],
            'classified': bool(classify) and any(f.rsplit('/', 1)[-1].lower() not in knowledge.SCAFFOLD_FILES for f in body.files)}

class ImportIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=500)
    accept: bool = False

@app.post('/api/agents/{agent}/items/import', status_code=201)
def import_into(agent: str, body: ImportIn, tasks: BackgroundTasks, user=Depends(actor)):
    import knowledge
    known_agent(agent)
    owners = {m['user_email'] for m in knowledge.members(agent) if m['role'] in ('owner', 'approver')}
    accept = body.accept and (not owners or user.lower() in owners)
    result = knowledge_call(knowledge.import_items, agent, [import_payload(i) for i in body.items], user, accept=accept)
    with connection() as db: audit(db, user, 'import_knowledge', agent, {'count': result['created'], 'skipped': result['skipped'], 'accepted': accept})
    # The register is updated; copying items into the agent's memory store continues in the background.
    tasks.add_task(knowledge.project_pending, result['created'] + 20, agent)
    return {'created': result['created'], 'skipped': result['skipped'], 'accepted': accept}

@app.get('/api/agents/{agent}/export')
def export_items(agent: str, user=Depends(actor)):
    import knowledge
    return {'files': knowledge.export_markdown(agent, known_agent(agent).name)}

@app.get('/api/agents/{agent}/export.zip')
def export_zip(agent: str, user=Depends(actor)):
    import io, zipfile, knowledge
    from fastapi.responses import Response
    files = knowledge.export_markdown(agent, known_agent(agent).name)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items(): archive.writestr(f'{agent}/{name}', content)
    return Response(buffer.getvalue(), media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{agent}-knowledge.zip"'})
