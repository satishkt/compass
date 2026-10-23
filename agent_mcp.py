"""Authenticated, stateless Streamable HTTP MCP access to the existing agent runtime."""
import logging
from contextvars import ContextVar

import anyio
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

import agents
from domains import all_domains, get_domain
from store import connection

LOG = logging.getLogger(__name__)
identity = ContextVar('mcp_identity')
domain_scope = ContextVar('mcp_agent', default=None)
server = Server('research-domain-agents', version='1.0.0')

def create_manager():
    return StreamableHTTPSessionManager(server, stateless=True, json_response=True)


class Ask(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=2, max_length=5000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)


class Conversation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(min_length=1, max_length=100)


class Conversations(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mine: bool = False
    query: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=50, ge=1, le=200)


class Scoped(BaseModel):
    model_config = ConfigDict(extra='forbid')
    agent: str | None = Field(default=None, max_length=40, description='Agent ID. Required on the combined /mcp/ endpoint; ignored on an agent endpoint.')


class RecordItem(Scoped):
    type: str = Field(pattern='^(requirement|rule|decision|question|todo|change|source|model|glossary|note)$')
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(default='', max_length=8000)
    fields: dict = Field(default_factory=dict, description='Type-specific fields, e.g. decision: context, alternatives, consequences; change: what, why, impact; requirement: priority, acceptance_criteria')
    decided_by: str | None = Field(default=None, max_length=200, description='Decisions: who made the call. Default: you.')
    assigned_to: str | None = Field(default=None, max_length=200)
    supersedes_ref: str | None = Field(default=None, max_length=20, description='Ref of the accepted item this replaces, e.g. D-003')
    session_id: str | None = Field(default=None, max_length=100, description='Conversation this came from, if any')


class FindKnowledge(Scoped):
    type: str | None = Field(default=None, pattern='^(requirement|rule|decision|question|todo|change|source|model|glossary|note)$')
    status: str | None = Field(default=None, max_length=20, description='accepted, proposed, open, answered, done, logged, superseded, or active (default)')
    query: str | None = Field(default=None, max_length=200)


class ItemRef(Scoped):
    ref: str = Field(min_length=3, max_length=20)


class AnswerQuestion(ItemRef):
    answer: str = Field(min_length=2, max_length=8000)
    promote_to_decision: bool = False


class UpdateTodo(ItemRef):
    status: str = Field(pattern='^(open|done|cancelled)$')


KNOWLEDGE_TOOLS = {
    'record_item': (RecordItem, False, 'Record a requirement, business rule, decision, open question, TODO, change, source, data-model detail or glossary term in the shared project knowledge register. '
                    'Call when the developer makes or confirms an implementation decision (choosing between alternatives, changing a schema, adopting a convention), discovers an open question, or completes or finds a TODO. '
                    'Confirm the wording with the developer first. Decisions, requirements, rules, sources, model and glossary items then wait for an approver in Pipeline Compass.'),
    'find_knowledge': (FindKnowledge, True, 'Search recorded knowledge (accepted decisions, rules, requirements, open questions, TODOs, changes, model). Call before implementing to find decisions and rules that apply.'),
    'get_item': (ItemRef, True, 'Read one knowledge item by ref (e.g. D-004), including its history and links.'),
    'confirm_suggestion': (ItemRef, False, 'Confirm a draft that an ask_* answer suggested recording (see its suggestions list). Only after the developer agrees.'),
    'dismiss_suggestion': (ItemRef, False, 'Discard a draft suggestion the developer does not want recorded.'),
    'answer_question': (AnswerQuestion, False, 'Answer an open question (Q-…). Set promote_to_decision when the answer is a decision that needs approval.'),
    'update_todo': (UpdateTodo, False, 'Mark a TODO (T-…) done, cancelled, or open again.'),
    'export_markdown': (Scoped, True, 'Export the register as spec.md, rules.md, decisions.md, todos.md, model.md (with generated DDL/ERD), sources.md and changes.md, to write into the pipeline repository folder.'),
}


def tool_name(agent):
    return 'ask_' + agent.replace('-', '_')


def visible_domains():
    selected = domain_scope.get()
    return {selected: get_domain(selected)} if selected else all_domains()


@server.list_tools()
async def list_tools():
    domains = await anyio.to_thread.run_sync(visible_domains)
    tools = [Tool(name=tool_name(d.id), description=f'Ask the {d.name} agent: {d.purpose} '
                  'Omit session_id to start a conversation; pass the returned session_id to continue. '
                  'Conversations are shared with the project team and saved. Answers may include suggestions '
                  '(draft knowledge items); confirm them with confirm_suggestion only after the developer agrees.', inputSchema=Ask.model_json_schema(),
                  annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False))
             for d in domains.values()]
    tools.extend([
        Tool(name='list_conversations', description='List shared conversations (and your private ones) within this endpoint’s agent scope.',
             inputSchema=Conversations.model_json_schema(), annotations=ToolAnnotations(readOnlyHint=True)),
        Tool(name='get_conversation', description='Read a saved conversation, including authors and recorded tool events.',
             inputSchema=Conversation.model_json_schema(), annotations=ToolAnnotations(readOnlyHint=True)),
    ])
    tools.extend(Tool(name=name, description=text, inputSchema=model.model_json_schema(),
                      annotations=ToolAnnotations(readOnlyHint=readonly, destructiveHint=False))
                 for name, (model, readonly, text) in KNOWLEDGE_TOOLS.items())
    return tools


def scoped_agent(body, domains):
    agent = domain_scope.get() or body.agent
    if not agent: raise ValueError('Pass agent (an agent ID) on the combined endpoint')
    if agent not in domains: raise ValueError('Unknown agent for this endpoint')
    return agent


def knowledge_tool(name, arguments, domains, owner):
    import knowledge
    model = KNOWLEDGE_TOOLS[name][0]
    body = model.model_validate(arguments)
    agent = scoped_agent(body, domains)
    try:
        if name == 'record_item':
            session = None
            if body.session_id:
                agents.readable(body.session_id, owner); session = body.session_id
            data = body.model_dump(exclude={'agent', 'session_id'})
            item = knowledge.create(agent, data, owner, channel='cursor', source_session=session)
            return {'recorded': knowledge.compact(item), 'note': 'Awaiting approval in Pipeline Compass.' if item['status'] == 'proposed' else 'Recorded.'}
        if name == 'find_knowledge':
            return {'items': [knowledge.compact(i) for i in knowledge.list_items(agent, type=body.type, status=body.status or 'active', query=body.query, limit=50)]}
        if name == 'get_item':
            return knowledge.get(agent, body.ref, detail=True)
        if name == 'confirm_suggestion':
            return knowledge.compact(knowledge.confirm(agent, body.ref, owner))
        if name == 'dismiss_suggestion':
            return knowledge.compact(knowledge.dismiss(agent, body.ref, owner))
        if name == 'answer_question':
            return knowledge.compact(knowledge.answer(agent, body.ref, body.answer, owner, body.promote_to_decision))
        if name == 'update_todo':
            return knowledge.compact(knowledge.set_status(agent, body.ref, body.status, owner))
        if name == 'export_markdown':
            return {'files': knowledge.export_markdown(agent, domains[agent].name)}
    except (LookupError, PermissionError, knowledge.Conflict) as exc:
        raise ValueError(str(exc)) from exc


def execute(name, arguments, index):
    owner = identity.get()
    domains = visible_domains()
    agent = next((key for key in domains if tool_name(key) == name), None)
    if agent:
        body = Ask.model_validate(arguments)
        if body.session_id:
            row = agents.writable(body.session_id, owner)
            if row['agent'] != agent:
                raise ValueError('Conversation belongs to a different agent')
            key = body.session_id
        else:
            key = agents.session(owner, agent)
        result = agents.run(key, owner, body.question, index, channel='cursor')
        return dict(result, session_id=key, suggestions=[{k: s[k] for k in ('ref', 'type', 'title', 'body', 'status')} for s in result['suggestions']])
    if name == 'list_conversations':
        body = Conversations.model_validate(arguments)
        sql, args = "SELECT id,agent,owner,title,visibility,parent,created_at,updated_at FROM agent_sessions WHERE (visibility='shared' OR owner=?) AND parent IS NULL", [owner]
        if body.mine: sql += ' AND owner=?'; args.append(owner)
        if body.query: sql += " AND LOWER(COALESCE(title,'')) LIKE ?"; args.append('%' + body.query.lower() + '%')
        with connection() as db:
            rows = db.all(sql + ' ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 200', tuple(args))
        return {'conversations':[r for r in rows if r['agent'] in domains][:body.limit]}
    if name == 'get_conversation':
        body = Conversation.model_validate(arguments)
        row = agents.readable(body.session_id, owner)
        if row['agent'] not in domains:
            raise ValueError('Conversation not found in this agent scope')
        with connection() as db:
            events = db.all('SELECT id,kind,role,author,content,created_at FROM agent_events WHERE session_id=? ORDER BY created_at,id', (body.session_id,))
        return {'session_id':row['id'],'agent':row['agent'],'title':row.get('title'),'owner':row['owner'],'events':events}
    if name in KNOWLEDGE_TOOLS:
        return knowledge_tool(name, arguments, domains, owner)
    raise ValueError('Unknown tool for this agent endpoint')


def install(app, index, actor):
    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        import json
        try:
            result = await anyio.to_thread.run_sync(execute, name, arguments or {}, index)
            return CallToolResult(content=[TextContent(type='text',text=json.dumps(result))], structuredContent=result)
        except ValueError as exc:
            return CallToolResult(content=[TextContent(type='text',text=str(exc))],isError=True)
        except Exception:
            LOG.exception('MCP agent tool failed: %s', name)
            return CallToolResult(content=[TextContent(type='text',text='Agent request failed. Any recorded conversation events remain saved; try again or inspect conversation history.')],isError=True)

    async def endpoint(scope, receive, send):
        request = Request(scope)
        try:
            owner = actor(request)
        except Exception as exc:
            if getattr(exc, 'status_code', None) == 401:
                await JSONResponse({'detail':'Databricks authenticated user required.'},status_code=401)(scope,receive,send)
                return
            raise
        # The mount consumes /mcp; the remaining path is either empty or an agent ID.
        from starlette._utils import get_route_path
        selected = get_route_path(scope).strip('/') or None
        if selected:
            try:
                await anyio.to_thread.run_sync(get_domain, selected)
            except ValueError:
                await JSONResponse({'detail':'Unknown agent or setup is incomplete.'},status_code=404)(scope,receive,send)
                return
        user_token = identity.set(owner)
        agent_token = domain_scope.set(selected)
        try:
            await app.state.mcp_manager.handle_request(scope,receive,send)
        finally:
            identity.reset(user_token)
            domain_scope.reset(agent_token)

    app.mount('/mcp', endpoint, name='agent-mcp')
