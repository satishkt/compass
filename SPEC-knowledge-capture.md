# Spec: Structured knowledge, capture & approval, shared conversations

_Implementation spec for Pipeline Compass. Companion to `REVIEW-pipeline-compass.md`. The current agents are placeholders, so this spec is content-agnostic: it applies to every agent created through **Add agent**._

Goals:
1. Every agent owns a **structured knowledge register**: requirements, rules, decisions, questions, TODOs, changes, sources, model entities, and glossary terms.
2. Knowledge can be **recorded from the web UI and from Cursor**. The agent **suggests** recording ("This sounds like a decision. Record it?"), and someone **approves** it.
3. **Conversations are visible to all users** of the app (per agent).
4. Seeded knowledge in **Add agent** uses the same structure.

---

## 1. What "free text" means today, and where structure should live

Today, knowledge reaches an agent in three ways:

| Path | Where it's stored | Shape |
|---|---|---|
| Seed memories in **Add agent** | `agent_definitions.seeds` (JSON) → managed memory `/seed/<topic>.md` | `{topic, content, source}`: just a paragraph |
| Offline consolidation | Managed memory, actor `candidate` → `/learned/<sha>.md` on approve | One LLM-written markdown document per run, approved whole |
| Conversations | `agent_events` | Raw turns |

None of these can answer *"list the open questions"*, *"who decided X and when"*, or *"what superseded D-003"*. The only answer is to ask the LLM to read every paragraph and guess.

**Proposal:** add a typed **knowledge register** table in Lakebase as the **system of record**. The managed memory store becomes a **projection** of accepted items, used for recall. Seeds, chat capture, Cursor capture and consolidation all write to the **same register** through the **same API**.

```
 Add agent seeds ─┐
 Chat capture ────┤                         ┌─► managed memory  /decisions/D-004.md  (recall)
 Cursor MCP  ─────┼──► knowledge_items ─────┤
 Consolidation ───┘    (Lakebase, typed,    └─► export  decisions.md / rules.md / todos.md …
                        versioned, attributed)
```

---

## 2. Data model (Lakebase `knowledge_agent` schema; SQLite locally)

```sql
CREATE TABLE IF NOT EXISTS knowledge_items (
  id              TEXT PRIMARY KEY,            -- uuid
  agent_id        TEXT NOT NULL,
  ref             TEXT NOT NULL,               -- human id: D-004, Q-012, R-021 …
  type            TEXT NOT NULL,               -- requirement|rule|decision|question|todo|change|source|model|glossary|note
  title           TEXT NOT NULL,
  body            TEXT NOT NULL,               -- markdown
  fields          TEXT NOT NULL DEFAULT '{}',  -- JSON, type-specific (see §2.1)
  status          TEXT NOT NULL,               -- see §2.2
  recorded_by     TEXT NOT NULL,               -- who typed/confirmed it (x-forwarded-email)
  decided_by      TEXT,                        -- decisions: who made the call (may differ from recorder)
  assigned_to     TEXT,                        -- questions/todos
  approved_by     TEXT,
  approved_at     TEXT,
  channel         TEXT NOT NULL,               -- seed|web|cursor|consolidation|import
  source_session  TEXT,                        -- agent_sessions.id
  source_event    TEXT,                        -- agent_events.id (exact turn)
  supersedes      TEXT,                        -- knowledge_items.id
  version         INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  UNIQUE (agent_id, ref)
);
CREATE INDEX IF NOT EXISTS ki_agent_type_status ON knowledge_items(agent_id, type, status);

-- Every change to an item (edit, status change, approval) = one row. This is your change log / audit.
CREATE TABLE IF NOT EXISTS knowledge_item_history (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL, version INTEGER NOT NULL,
  actor TEXT NOT NULL, action TEXT NOT NULL,   -- create|edit|propose|approve|reject|supersede|answer|close|comment
  snapshot TEXT NOT NULL,                      -- JSON of the item after the action
  note TEXT, created_at TEXT NOT NULL);

-- Links: question → decision that answered it, decision → change that implemented it, rule → model column…
CREATE TABLE IF NOT EXISTS knowledge_links (
  from_item TEXT NOT NULL, to_item TEXT NOT NULL, kind TEXT NOT NULL,  -- answers|implements|relates|conflicts
  created_by TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (from_item, to_item, kind));

-- Who may approve for an agent (owners/approvers). Everyone signed in is a contributor by default.
CREATE TABLE IF NOT EXISTS agent_members (
  agent_id TEXT NOT NULL, user_email TEXT NOT NULL, role TEXT NOT NULL,  -- owner|approver|contributor
  added_by TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (agent_id, user_email));
```

**Ref generation:** use a prefix per type (`REQ`, `R`, `D`, `Q`, `T`, `C`, `S`, `M`, `G`, `N`). Compute `max(ref number)+1` for `(agent_id, type)` and insert; on a `UNIQUE` violation, retry up to 3 times. This works the same on SQLite and Postgres.

### 2.1 Type-specific `fields`

| Type | Fields (JSON) | Required in UI |
|---|---|---|
| requirement | `priority` (must/should/could), `consumer`, `acceptance_criteria` | title, body, priority |
| rule | `track` (free text, e.g. public/private/consolidation), `applies_to` (source/table/column), `expression` | title, body |
| decision | `context`, `alternatives` (list of `{option, reason_rejected}`), `consequences`, `decided_on` | title, decision, **decided_by** |
| question | `answer`, `answered_by`, `answered_at`, `due` | title |
| todo | `due`, `done_at` | title |
| change | `what`, `why`, `impact` (model/transform/source/other) | title, what, why |
| source | `platform`, `path`, `format`, `refresh`, `columns` | title |
| model | `table`, `grain`, `primary_key`, `columns` ([{name,type,nullable,source,transform}]), `relationships` | table |
| glossary | `term`, `synonyms` | term, body |
| note | (none): an escape hatch for anything else | body |

### 2.2 Status lifecycle and approval policy

| Type | States | Needs approval? |
|---|---|---|
| decision, requirement, rule, model, source, glossary | `draft → proposed → accepted \| rejected`; `accepted → superseded` | **Yes.** An owner or approver, **not the recorder** |
| question | `open → answered → closed` | No. Answering is an edit; promoting an answer to a decision creates a new `proposed` decision linked `answers` |
| todo | `open → done \| cancelled` | No |
| change, note | `logged` | No |

Rules:
- `draft` is visible only in the conversation where it was suggested (the capture card). Nothing reaches the register list until a person confirms it.
- **Accepted decisions are immutable.** To reverse one, create a new decision with `supersedes = old.id`. On approval, the old one becomes `superseded`. This matches your `.cursorrules` append-only convention.
- Edits to `proposed` items are allowed and bump `version`. Approval sends `expected_version` (reuse the optimistic-locking pattern already in `app.py /api/memories/{id}/review`).
- Self-approval: block it for approval-required types unless the agent has only one owner and no approvers (POC mode, shown as a warning).

---

## 3. Seeding in Add agent: yes, structure it

Replace the current *Topic / Baseline memory / Source* rows with **typed starting knowledge**. Keep it light. Users shouldn't fill in nine forms to create an agent.

**Step 1 · Define:** Name, What it covers (purpose), **Owner(s)**, optional Approvers. Derive the ID from the name, editable under "Advanced". Remove "Domain keywords" from the main form (keep it under Advanced until retrieval is replaced).

**Step 2 · Starting knowledge.** Offer three ways in, any of which can be combined:

| Option | How | Result |
|---|---|---|
| **Add items** | A row with a **Type** dropdown (Requirement, Rule, Decision, Question, TODO, Source, Glossary, Note) + Title + Details + type-specific fields shown progressively (e.g. Decision shows *Decided by*, *Alternatives*) | One `knowledge_items` row each |
| **Paste or upload documents** (.md/.txt/.docx/.pdf) | The agent **extracts typed candidates** (LLM, same schema), which are shown in a review table before creating | Rows created as `proposed` (or `accepted` if the creator ticks "I'm the owner, accept all") |
| **Import a pipeline folder** (zip, or the existing scaffold layout spec/rules/decisions/todos/model/sources.md) | A deterministic parser: `## D001 — …` → decision, `- [ ]` → todo, `- [x]` → done todo, model tables → model items, and so on | Rows created directly, `channel=import` |

The seeded items created by the agent's owner with **"accept starting knowledge"** checked become `accepted` immediately. This keeps today's "approve baseline" checkbox semantics. Everything else lands `proposed` in the Review inbox.

The original documents also go to a UC Volume `…/agents/<id>/sources/` and into retrieval, so the agent can still cite raw text that wasn't extracted.

**Backend change:** `CreateAgentIn.seeds: list[SeedMemoryIn]` becomes `items: list[ItemIn]` (same model as the capture API, §5). `registry.provision()` inserts the items, then runs the memory projector (§7) instead of `native.put('/seed/…')`.

---

## 4. Shared conversations (visible to all users)

### 4.1 Current behaviour
- `agents.own(key, owner)` filters on `owner=?`. It is used by `/api/sessions/{id}`, `/sync`, `/chat`, MCP `ask_*` (continue), and `get_conversation`.
- `GET /api/sessions` returns only `WHERE owner=?`.
- MCP `list_conversations` also filters by owner.
- `agent_events` has no author column, so it assumes one user per session.

### 4.2 Changes

**Schema:**
```sql
ALTER TABLE agent_sessions ADD COLUMN title TEXT;            -- auto-generated from first question
ALTER TABLE agent_sessions ADD COLUMN visibility TEXT NOT NULL DEFAULT 'shared';  -- shared|private
ALTER TABLE agent_sessions ADD COLUMN updated_at TEXT;
ALTER TABLE agent_events   ADD COLUMN author TEXT;           -- user email for role=user; agent id otherwise
```
Backfill: `UPDATE agent_events SET author=(SELECT owner FROM agent_sessions s WHERE s.id=session_id) WHERE role='user'`; `title` = first 80 chars of the first user message.

**Code (`agents.py`):** split `own()` into two functions:
```python
def readable(key, user):
    row = db.one('SELECT * FROM agent_sessions WHERE id=?', (key,))
    if not row or (row['visibility'] == 'private' and row['owner'] != user): raise ValueError(...)
    return row

def writable(key, user):
    row = readable(key, user)          # shared sessions: anyone can continue
    return row                         # tighten later (e.g. owner + participants) if needed
```
- `event(key, role, content, kind, author=None)`. Pass `owner` for user turns.
- In `run()`, build history with author names so the model knows who said what: `{'role':'user','content':f'[{author}] {content}'}`. This also matters for attribution when the agent proposes a decision ("decided_by" defaults to the person who stated it).
- Child (delegated) sessions inherit the parent's `visibility`.

**API (`app.py`):**
- `GET /api/sessions?agent=<id>&mine=false&q=<text>`: returns shared sessions for the agent plus the caller's private ones, newest `updated_at` first, with `owner`, `title`, `participants` (distinct authors), and `message_count`.
- `GET /api/sessions/{id}` uses `readable`; `POST /api/chat` uses `writable`.
- `PATCH /api/sessions/{id}` `{title?, visibility?}`: owner only.
- `DELETE` is not exposed (the journal is the audit trail). If needed, owners can *hide* their own sessions.

**MCP (`agent_mcp.py`):** `list_conversations` gets `{mine?: bool, query?: str, limit?: int}`; `get_conversation` uses `readable`. Continuing a shared session from Cursor uses `writable`.

**UI:**
- Replace the "Saved conversations" dropdown with a **conversation list** panel: title, started by, participants, last activity, `Mine | Everyone` filter, and search.
- Each user message shows the author's name.
- Composer footer: *"Conversations with this agent are visible to everyone in Pipeline Compass."* plus a **Private** toggle when starting a new one.
- Daily updates already read all sessions; no change needed.

**Privacy guardrails:** keep the existing `SENSITIVE` regex check on user input. Today it applies only to memories; extend it to warn before sending chat messages containing secrets. Note that `x-forwarded-email` is shown to other users now; that's expected in an internal tool.

---

## 5. Capture API (shared by web, Cursor, seeding and consolidation)

```
POST   /api/agents/{agent}/items                 create (draft|proposed|open|logged depending on type)
GET    /api/agents/{agent}/items?type=&status=&q=&assigned_to=&limit=
GET    /api/agents/{agent}/items/{ref}           item + history + links + source conversation pointer
PATCH  /api/agents/{agent}/items/{ref}           edit (expected_version); proposed/open items only
POST   /api/agents/{agent}/items/{ref}/confirm   draft → proposed (or accepted/open/logged per policy)
POST   /api/agents/{agent}/items/{ref}/review    {action: approve|reject, expected_version, note}
POST   /api/agents/{agent}/items/{ref}/answer    questions: {answer, promote_to_decision?: bool}
POST   /api/agents/{agent}/items/{ref}/status    todos: done|cancelled; questions: closed
POST   /api/agents/{agent}/items/{ref}/supersede {new item payload}  → creates proposed replacement
GET    /api/inbox                                proposed items I can approve + questions/todos assigned to me
GET    /api/agents/{agent}/export?format=md      spec/rules/decisions/todos/model/sources/changes .md (zip)
```

`ItemIn` (pydantic): `type`, `title` (3–200), `body` (≤ 8000), `fields: dict`, `decided_by?`, `assigned_to?`, `supersedes?`, `source_session?`, `source_event?`, `channel`. Reuse the existing `SENSITIVE` and "transient result" validators from `app.py`.

Put the logic in a new module `knowledge.py` (create/confirm/review/supersede/list/export + `project_to_memory`). Keep `app.py` and `agent_mcp.py` as thin wrappers so web and Cursor share **one** implementation.

---

## 6. The agent prompts users to record knowledge

### 6.1 New agent tools (domain agents; the supervisor gets read-only `find_knowledge`)

```json
{"name":"suggest_record",
 "description":"Suggest recording a durable item the USER stated or confirmed in this conversation (a decision, requirement, business rule, open question, TODO or change). Do not use for your own guesses. The user must confirm before it is saved.",
 "parameters":{"type":"object","properties":{
   "type":{"enum":["decision","requirement","rule","question","todo","change","source","glossary","note"]},
   "title":{"type":"string"},
   "body":{"type":"string"},
   "fields":{"type":"object"},
   "decided_by":{"type":"string","description":"Person who made the decision, if stated. Default: the user who said it."},
   "supersedes_ref":{"type":"string","description":"Ref of an existing accepted item this replaces, e.g. D-003"}},
 "required":["type","title","body"]}}

{"name":"find_knowledge",
 "description":"Look up recorded items for this agent by type/status/text. Use before answering questions about decisions, requirements, rules, open questions or TODOs, and before suggesting a record (to avoid duplicates and detect conflicts).",
 "parameters":{"type":"object","properties":{"type":{"type":"string"},"status":{"type":"string"},"query":{"type":"string"}}}}
```

`suggest_record` executes `knowledge.create(..., status='draft', channel='web'|'cursor', source_event=<current user event id>)` and returns the draft `ref`. The runtime adds it to the response as `suggestions: [...]`, the same way `sources` and `delegations` are returned today.

### 6.2 Prompt additions (`agents.py` system prompt)

Replace *"You cannot save knowledge… invite the user to use Propose memory"* with:

> You help a project team keep a shared record of requirements, business rules, decisions, open questions, TODOs and changes.
> - When the user **states or confirms** something durable (a choice between options, a rule, a requirement, a new open question, an action item, a change made), call `suggest_record` once per item with a precise title and body. Attribute decisions to the person who made them. Never record your own suggestions unless the user explicitly agrees with them.
> - Call `find_knowledge` first. If an accepted item already covers it, don't suggest a duplicate. If the new statement **contradicts** an accepted item, say so, cite its ref, and suggest a superseding item with `supersedes_ref`.
> - When you mention recorded items, cite their ref and status, e.g. "D-004 (accepted, decided by …)". Distinguish **accepted** from **proposed**.
> - When the user explicitly asks to record something ("record a decision…", "log a TODO…"), call `suggest_record` immediately.
> - Never claim something is approved. Recording creates a draft the user confirms, and approval-required types then wait for an approver.

### 6.3 Web UI flow

```
 You:  We'll use SCD Type 1 in gold; history stays in bronze.  Consumers only need current state.

 Agent: Got it. That's a modelling decision. Nothing on record conflicts with it.
        ┌───────────────────────────────────────────────────────────────┐
        │ 🟧 Decision · draft D-004                                      │
        │ Use SCD Type 1 in the gold canonical model                    │
        │ Context: consumers need current state; history kept in bronze │
        │ Decided by: you ▾        Alternatives: SCD2 (rejected: …)      │
        │ [ Record & send for approval ]  [ Edit ]  [ Dismiss ]          │
        └───────────────────────────────────────────────────────────────┘
```

- **Record & send for approval** calls `/confirm`, so the item becomes `proposed` and appears in the Review inbox with a badge count. Questions, TODOs and changes go straight to `open`/`logged`.
- **Edit** opens the item form inline, prefilled.
- **Dismiss** deletes the draft (store a `dismissed` history row so the agent doesn't re-suggest it in the same session).
- Users can also **capture explicitly** in two ways:
  - **Message action:** hover any message and pick ⋯ → *Record as… Decision / Requirement / Rule / Question / TODO / Change*. It opens the same form prefilled with the message text and links `source_event`.
  - **Composer button:** **＋ Record** next to *Ask* opens the form with a Type picker.
- **Conflict card variant:** when the item supersedes something, the card shows the old item and the new one side by side: *"Replaces D-002 (accepted)."*

### 6.4 Review inbox (replaces today's "Shared memory" page)

- A sidebar item **Review** with a badge. It is also reachable per agent.
- Each item is a card: type chip, ref, title, body, *recorded by / decided by*, **link to the source conversation turn**, and a diff against the superseded item if there is one.
- Actions: **Approve**, **Request changes** (adds a comment, notifies the recorder), **Reject** (reason required), **Edit then approve** (approver edits bump the version and are recorded in history).
- Filter by agent and type; "Assigned to me" for questions and TODOs.
- Consolidation-generated candidates (§8) show up here too, labelled *"Suggested from conversations"*.

### 6.5 Register page per agent (new tab, replaces "Agent memory & pipeline")

Show tabs or chips: **Requirements · Rules · Decisions · Open questions · TODOs · Changes · Model · Glossary**, as tables with Ref, Title, Status, Owner/Decider, Updated, and Channel (web/cursor/seed). A row click opens a drawer with the body, fields, history timeline, links, *View source conversation*, and actions (answer, close, supersede). An **Export markdown** button generates the scaffold-style files (`decisions.md` append-only ordering, `todos.md` with `- [ ]`/`- [x]`, `model.md` with generated DDL and Mermaid).

---

## 7. Managed memory projection (recall)

When an item reaches an **active** state (`accepted`, `open`, `answered`, `logged`), write one memory entry. When it leaves one (`superseded`, `rejected`, `closed`, `cancelled`), update it.

| Item | Memory path | Content |
|---|---|---|
| D-004 accepted | `/decisions/D-004.md` | YAML-ish header (ref, status, decided_by, date, supersedes) + body |
| Q-012 open | `/questions/Q-012.md` | question + status + assignee |
| superseded D-002 | `/decisions/D-002.md` | rewritten with `status: superseded by D-004` (or deleted, if the memory-store API supports deletes in your workspace; verify) |

Implement this as `knowledge.project_to_memory(item)` using `native_memory.put`. `put` currently raises on a changed-content conflict, so add an update path. Call it synchronously after approval, and add a reconcile pass to the existing 30-second background loop in `app.py lifespan` for any failures (same pattern as `native_memory.retry_pending`).

**Recall changes in `agents.run`:**
- Stop loading **all** approved memory into the prompt.
- Inject a short **brief** instead: purpose, counts (open questions, proposed items), the last 5 accepted decisions (ref and title), and the open questions (ref and title).
- The model calls `find_knowledge` for details. That tool queries `knowledge_items` directly (exact, filterable), which is more reliable than semantic recall for structured questions. The memory store remains the recall layer for native memory features and consolidation context.

---

## 8. Offline consolidation: produce typed suggestions

Keep the native memory pipeline (it's the safety net for things nobody captured), but change `registry.POLICY` so that it writes **one candidate entry per item** using a fixed path and format:

```
path: /candidates/<type>/<short-slug>.md
---
type: decision
title: Use SCD Type 1 in gold
decided_by: <email if stated>
source_session: <session id>
source_event: <event id if available>
---
<body>
```

Then add a small ingest step, `knowledge.ingest_candidates(agent)`, which runs after a pipeline run and on the 30-second loop:
1. Read `entries(agent, 'candidate')` under `/candidates/`.
2. Parse the front matter; skip anything already ingested (hash).
3. De-duplicate against `knowledge_items` with `find_knowledge(query=title)`.
4. Insert as `proposed`, `channel='consolidation'`, `recorded_by='consolidation'`.

The candidate memory entries are never recalled directly; only the register-projected entries are. Validate the path and front-matter adherence on a few runs first. If the pipeline model doesn't follow the format reliably, fall back to running the extraction yourself in the daily job (`daily_updates.py` already iterates the day's events per agent), emitting the same JSON schema with a structured-output prompt.

---

## 9. Cursor (MCP) tools

Add these to `agent_mcp.py` per agent endpoint. They call the same `knowledge.py` functions with `channel='cursor'` and identity from the forwarded token.

| Tool | Args | Behaviour |
|---|---|---|
| `ask_<agent>` | question, session_id? | as today; the response now includes `suggestions` (draft refs) |
| `record_item` | type, title, body, fields?, decided_by?, supersedes_ref?, session_id? | Creates **already confirmed** (`proposed` / `open` / `logged`). The developer invoked it explicitly, so no draft step |
| `confirm_suggestion` / `dismiss_suggestion` | ref | For drafts returned by `ask_*` |
| `find_knowledge` | type?, status?, query? | Read the register |
| `get_item` | ref | Item, history and links |
| `answer_question` | ref, answer, promote_to_decision? | |
| `update_todo` | ref, status | |
| `export_markdown` | (none) | Returns spec/decisions/rules/todos/model markdown, so Cursor can write it into the repo folder |

Tool descriptions should tell Cursor *when* to call them, e.g. `record_item`: *"Call when the developer makes or confirms an implementation decision (choosing between alternatives, changing a schema, adopting a convention), or completes/discovers a TODO. Ask the developer to confirm the wording first."*

Ship a snippet for the repo's `.cursorrules`:
```
When you and I settle a technical choice, a schema change, or discover an open question,
call the Pipeline Compass `record_item` tool for agent <id> (type decision|change|question)
after confirming the wording with me. Before implementing, call `find_knowledge` for
accepted decisions and rules that apply.
```

---

## 10. Files to change (implementation checklist)

| File | Change |
|---|---|
| `knowledge.py` (new) | Tables DDL + init, ref generation, create/confirm/edit/review/answer/status/supersede/list/get, policy table (§2.2), `project_to_memory`, `ingest_candidates`, markdown export, scaffold importer |
| `store.py` | Call `knowledge.init()`; add column migrations (`ALTER TABLE … ADD COLUMN IF NOT EXISTS` on Postgres; check `PRAGMA table_info` on SQLite) |
| `agents.py` | `readable`/`writable` replace `own`; `author` on events; author-tagged history; tools `suggest_record`, `find_knowledge`; brief instead of full memory; `suggestions` in result; prompt §6.2 |
| `app.py` | Items, inbox, export endpoints (§5); sessions list/patch (§4.2); `CreateAgentIn.items` and owners; remove legacy `/api/memories*`, `SYSTEM`, `generate*` |
| `registry.py` | Accept typed items + owners at creation; insert `agent_members`; seed via `knowledge.create`; new consolidation `POLICY` (§8) |
| `native_memory.py` | `put` → upsert (update when the path exists); keep `entries` |
| `agent_mcp.py` | New tools (§9); conversation tools use `readable`/`writable`; list filters |
| `daily_updates.py` | Include the day's knowledge-item history (recorded, approved, answered) as a "Decisions & changes" section, sourced from the register, not LLM-inferred |
| `static/*` | Capture card, message ⋯ menu, ＋ Record form, Review inbox, Register tab and drawer, conversation list with authors, typed seed rows in Add agent. Consider moving to React before this; the current single-file `app.js` will struggle with drawers and forms |
| `tests/` | Ref uniqueness under concurrency; policy (no self-approval; questions skip approval); supersede flow; draft never visible outside its session; shared vs private session access; MCP `record_item` attribution; projection on approve/supersede; importer on the `position_pipeline` scaffold |

### Suggested build order
1. `knowledge.py` + tables + REST + Register tab (read and manual create). This alone gives you a structured, shared record.
2. Shared conversations (§4): small and independent; ship early.
3. Review inbox + approval policy + `agent_members` (owners in Add agent).
4. Agent tools `suggest_record`/`find_knowledge` + capture card + message "Record as…".
5. MCP tools + `.cursorrules` snippet.
6. Typed seeding in Add agent + document/folder import.
7. Memory projection + brief-based recall; consolidation → typed candidates.
8. Markdown export; daily update section from the register.

### Acceptance checks
- A BA states a rule in chat; the agent shows a card; the BA confirms → `R-001 proposed`; another user approves → `accepted`; a fresh session from a third user (or Cursor) answers "what are the rules?" citing R-001.
- A developer runs `record_item(type=decision, …)` in Cursor → it appears in the web Review inbox with `channel=cursor` and their identity; once approved, it's in the Register and in `export_markdown`'s `decisions.md`.
- User B opens and continues user A's conversation; the transcript shows both authors.
- Recording a decision that contradicts D-001 produces a supersede card; approval marks D-001 `superseded by D-00x`.
- `find_knowledge(type=question, status=open)` matches the Register's open-questions count.
