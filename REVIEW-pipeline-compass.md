# Pipeline Compass: Review and Recommendations

_Reviewed 2026-10-22. Scope: the code in this folder, the deployed app (from the browser-check screenshots in `artifacts/`, because the live browser session was unavailable), and the intended operating model. The pipeline knowledge-base reference is `~/Work/position_pipeline_scaffold/pipelines/position_pipeline` (`~/Work/positions-pipeline` does not exist)._

> **Update (follow-up):** The current agents and `kb/` content are placeholders. Ignore the content-specific remarks (valuation prompts, research KB, branding drift). Conversations should be **shared across users**, and knowledge must be **recordable from both the web UI and Cursor**, with agent-prompted capture and approval. The implementation detail is in **`SPEC-knowledge-capture.md`**.

---

## 1. Summary

The plumbing is solid. It has a durable journal, native session and memory stores per agent, offline consolidation, human approval, MCP access from Cursor, and daily summaries. Those are the right building blocks.

The **product shape does not match the intent yet**:

| Intent | What the app does today |
|---|---|
| One agent **per pipeline** (e.g. `position_pipeline`) | Agents are **business domains** (Valuation, Research, Portfolio, Platform), seeded from the research/valuation app docs |
| Structured register: requirements, rules, decisions (+ who decided), open questions, TODOs, changes | Only **free-text memory**. The consolidation output is one large markdown blob that you approve or reject as a whole |
| Multiple stakeholders building **shared** project knowledge | Conversations are **private to their owner** (`agents.own()`). Other people only see what gets approved into memory |
| BA/DA/Dev each **record** knowledge, including from Cursor | Agents are explicitly told *"You cannot save knowledge"*. MCP has ask/list/get only, no record tools |
| Simple, non-technical UI | The UI exposes pipeline runs, actors, candidates, UTC windows, SHA markers, volume paths, the model name, and a SQL explorer |

The scaffold in `position_pipeline/` (spec / sources / model / rules / transforms / decisions / todos, plus the `.cursorrules` conventions: append-only decisions, model tables as source of truth, generated DDL and ERD) is a **better information model** than the current free-text memory. **The main recommendation is to make that scaffold the schema of each pipeline agent.** The managed memory store then becomes the recall layer *over* that structured register, not the system of record.

---

## 2. Target operating model

```
                    ┌────────────────────── Pipeline Agent: position_pipeline ──────────────────────┐
  BA  ── UI chat ──►│  Ask / Capture  ──►  Knowledge Register (Lakebase, system of record)          │
  DA  ── UI chat ──►│                       requirements · rules · decisions · questions · todos    │
  Dev ── Cursor MCP►│                       changes · sources · model (tables/cols/relationships)   │
                    │        ▲                         │                                             │
                    │        │ approve / edit          │ project approved items                      │
                    │   Review inbox (owner)           ▼                                             │
                    │        ▲                Managed Memory Store (recall, one entry per item)      │
                    │        │ typed candidates        │                                             │
                    │  Offline consolidation ◄── Session store (all conversations)                   │
                    │                                  │                                             │
                    │                         Export → position_pipeline/*.md  (git, .cursorrules)   │
                    └────────────────────────────────────────────────────────────────────────────────┘
          Optional: "Program" agent (today's supervisor) that federates across pipeline agents
```

### Roles

| Role | Primary jobs | Main surface |
|---|---|---|
| **BA** | Capture requirements and business rules from stakeholder sessions, raise open questions, confirm answers | UI: *Ask*, *Capture*, *Register* |
| **Data analyst** | Turn requirements into the canonical model (tables, grain, keys, mappings), raise modelling questions | UI: *Data model*, *Register*; optional live catalog lookup |
| **Developer** | Ask while implementing, record technical decisions and changes, close TODOs | Cursor MCP (`ask`, `record_decision`, `log_change`, `get_model`) |
| **Pipeline owner** | Approve decisions and requirements, resolve conflicts, own the open-question list | UI: *Review inbox*, *Overview* |

Make the role a lightweight per-pipeline membership (owner / contributor / viewer), not a separate app. It changes the defaults (which tab opens, who can approve), not the capabilities.

---

## 3. Knowledge model: make the register first-class

### 3.1 Item types (mirrors the scaffold files)

| Type | Scaffold file | Key fields beyond the common ones | Default lifecycle |
|---|---|---|---|
| `requirement` | spec.md | priority (must/should/could), consumer, acceptance criteria | proposed → accepted → delivered / dropped |
| `rule` | rules.md | track (public / private / consolidation), applies_to (source/table/column), expression | proposed → accepted → superseded |
| `decision` | decisions.md | **decided_by**, decided_on, context, alternatives, consequences | proposed → **accepted** → superseded (append-only, never edited) |
| `question` | todos.md | **asked_by, assigned_to**, due, answer, answered_by | open → answered → (spawns decision / rule / requirement) |
| `todo` | todos.md | assignee, due, linked item | open → done / cancelled |
| `change` | _new_ | what changed, why, linked decision/requirement, impact (model / transform / source) | logged (immutable) |
| `source` | sources.md | platform, path, format, refresh, columns | draft → confirmed |
| `model_entity` | model.md | table, grain, PK, columns (type, nullable, source, transform), relationships | draft → accepted; the DDL and Mermaid ERD are **generated** |
| `glossary` | _new_ | term, definition, synonyms | shared across pipelines (org scope) |

**Common fields on every item:** `id` (human-friendly, e.g. `D-007`, `Q-012`), `pipeline_id`, `type`, `title`, `body`, `status`, `author`, `created_at`, `updated_at`, `version`, `supersedes`, `source_conversation_id` + `source_event_id` (provenance back to the exact chat turn), `confidence` (stated / inferred), and `tags`.

Suggested tables (Lakebase, `knowledge_agent` schema):
`pipelines`, `pipeline_members`, `items`, `item_versions` (full history = the **change log** for free), `item_links` (question → decision, decision → change, rule → model column), `reviews`.

### 3.2 Why this beats today's free-text memory

- **Who decided what, when, and why** becomes queryable. Today `agent_reviews` only records the approver of a blob, and the candidate memory loses the speaker (all sessions are written under actor `candidate`).
- **Per-item review.** The current candidate in `agents-v2-memory.png` is a ~3-page document mixing workflow, user preferences, and backlog items. A reviewer can only approve or reject it whole, which is the biggest usability and quality problem in the memory loop.
- **Open questions and TODOs need state** (open/answered/assigned). Memory text can't be "closed".
- **Diffs, supersession, and conflict detection** become simple queries. They are not LLM guesses.
- The **markdown export** reproduces exactly the `position_pipeline/*.md` files, so `.cursorrules`-driven workflows keep working and git becomes an audit trail.

---

## 4. Managed memory: how to maintain it for this use case

Use **three layers** with clear roles.

| Layer | Store | Contents | Written by |
|---|---|---|---|
| **System of record** | Lakebase register (section 3) | Typed, versioned, attributed items | Capture tool (in chat / MCP), the review inbox, imports |
| **Recall memory** | Databricks managed memory store, one per pipeline | **One entry per approved item**, path by type: `/decisions/D-007.md`, `/rules/R-021.md`, `/questions/Q-012.md`, `/model/position.md`, `/glossary/…` | A projector job that syncs from the register (never hand-written) |
| **Episodic** | Session store + `agent_events` journal | Every conversation turn, tool call, MCP call | Runtime (already in place) |

### 4.1 Write paths

1. **Capture in the moment (primary).** Give agents a `capture` tool (`propose_item(type, title, body, links)`). When a BA says *"private positions are valued with a one-quarter lag"*, the agent replies with an inline card: **"Record as Rule (private track)? [Save] [Edit] [Not now]"**. The user who said it confirms it, so attribution is exact. This replaces the current *"You cannot save knowledge"* instruction.
2. **Offline consolidation (safety net).** Keep the native memory pipeline, but change its policy so it **emits typed candidate items** (JSON matching the item schema, with `source_event_id`). Free-form documents should stop. Candidates land in the review inbox de-duplicated against the register.
3. **Import / seed.** Seed a new pipeline agent by parsing an existing scaffold folder (`spec.md`, `decisions.md`…) into items. That covers *"seed with some base knowledge"* without the current topic-slug form.
4. **Cursor (developer).** MCP tools `record_decision`, `log_change`, `ask_question`, `close_todo` call the same capture API. Items from Cursor are tagged `channel=cursor` and the developer's identity.

### 4.2 Approval policy (risk-based, not all-or-nothing)

| Type | Default |
|---|---|
| question, todo, change | **Auto-accepted** on capture (low risk; they are records of activity, not truths) |
| requirement, rule, model_entity, source | Contributor proposes; **owner or another member approves** (no self-approval) |
| decision | Must name `decided_by`. Accepted when the decider or the owner confirms; append-only; reversal is a new decision that `supersedes` |

Today any user can approve anything, including their own consolidated knowledge (`app.py` `/review`, and the Shared memory callout). That's fine for a POC but should change before multi-stakeholder use.

### 4.3 Recall (read path)

- Today `agents.memory()` loads **all** approved entries into every prompt. That works with three seeds and won't scale to hundreds of rules and decisions.
- Use **structured first, semantic second**. Give the agent tools: `get_items(type, status, tags)`, `get_model(table)`, `open_questions()`, plus `search_knowledge(query)` backed by **Databricks Vector Search** over register items and source docs. That replaces the BM25 `retrieval.Index` and the keyword-substring domain routing (`domains.belongs_to`).
- Always inject a small **pipeline brief** (spec summary, current open questions count, last 5 decisions) instead of the entire memory.
- Rank `accepted` over `proposed`, newest version over superseded. Expose the status in citations (e.g. "per **D-007** (accepted, decided by <owner> 2026-10-12)").

### 4.4 Hygiene jobs (scheduled, alongside the existing daily update)

- **Conflict detector:** a new rule or decision that contradicts an accepted one goes to the inbox as a "Conflict" card, side by side.
- **Staleness:** open questions older than N days without an owner, and decisions referencing changed model columns.
- **Weekly digest per pipeline** (replaces or extends the daily update): new decisions, answered questions, changes, items awaiting review. Address it to the people, not "per agent".
- **Memory projector:** keeps the memory store in sync with the register and deletes the memory entries of superseded or dropped items. That fixes "forget" semantics too.

### 4.5 Memory scopes

- **Pipeline scope** (default): one memory store per pipeline agent.
- **Org scope**: glossary, shared conventions (naming standards, UC catalog layout, SCD policy), and cross-pipeline decisions. One shared store recalled by every pipeline agent.
- **User scope** (optional): personal preferences such as answer style or role. Never shared.

The native `actor_id` partitions (`candidate` / `approved`) are currently used as the approval boundary. Once the register owns approval, the memory store only needs an `approved` projection, which simplifies `native_memory.py` and `agents.candidates()` considerably.

---

## 5. Conversations and context retrieval

- **Default conversations to pipeline-visible** (all members can read), with a "private" toggle. Today `own()` makes every transcript owner-only in the UI and in MCP `get_conversation`, which defeats shared context. Retain owner-only *deletion*.
- Every register item links to its **source conversation and turn**. In the UI, "View source conversation" jumps to and highlights that turn. This is the main way to "retrieve the context" without exposing raw logs everywhere.
- Add a **History** view per pipeline: a timeline of conversations and register changes, filterable by person, type, and date. It replaces both *Activity* (raw audit) and *Daily updates* (file viewer).
- Auto-title conversations (first question summarized) and show the participants. The current "Saved conversations" dropdown lists sessions with no meaningful label.
- Hide tool calls and results behind a "Show steps" disclosure inside a message; don't render them as top-level transcript items.

---

## 6. UI review

### 6.1 What works

- Clean Databricks palette and DM Sans; the visual quality is good.
- Answers with a citation/evidence panel is the right pattern.
- Suggested starter questions per agent.
- The daily summary content is genuinely useful (it surfaced an *unanswered* sub-question in the 2026-10-22 run).

### 6.2 Problems

1. **Too many top-level concepts.** There are seven sidebar tabs, plus an agent-directory column, plus a stats strip, plus an evidence panel, which makes four vertical regions on the main page. *Manage agents* and *Add an agent* duplicate each other.
2. **Implementation leaks into the UI:** "Run offline consolidation", "Pipeline details" (raw JSON), "actor", "candidate", "native", the UTC window, `source-sha256` comments, volume paths, the job link, the model name in the footer, the numeric service identity in the sidebar (`8083820129023134@7474…`), and "Legacy first-cut memory archive".
3. **The Explore tables tab** is a SQL-template console. It's useful for the data analyst, but it doesn't belong in primary nav. Move it into the *Data model* page as "Check against catalog" or expose it only via MCP.
4. **The stats strip** ("35 workspace documents · 3 baseline memories · Human reviewed") is global and decorative. Replace it with actionable counts: *5 open questions · 3 awaiting your review · 2 decisions this week*.
5. **Many manual "Refresh …" buttons** (conversations, agents, memory, directory). Poll or refresh on focus instead.
6. **The agent creation form** asks for an ID slug, retrieval keywords, and memory "topic" slugs. Those are technical. For pipelines, use: *Name, Purpose/intent, Owner, Members, Seed from folder/upload (optional)*. Derive the ID; drop keywords once you have vector search.
7. **The memory review screen** is one long scrolling document with Approve/Reject at the bottom (see `agents-v2-memory.png`). Use per-item cards with **Accept / Edit & accept / Reject / Merge into…** and a diff when the item supersedes something.
8. **Daily updates** is a raw markdown file viewer with date and agent pickers and a "Generate" button. It should be a readable digest inside the pipeline's History, with regeneration hidden in admin.
9. The **"Know something new?"** panel explains the consolidation pipeline in words. Replace it with an actual **Capture** button.
10. **Branding drift:** older screenshots say "Research Memory", the current one "Pipeline Compass", and suggested prompts are still valuation-research ("Atlas", "fair value"). The KB in `kb/` is the research-valuation app, not pipeline content.

### 6.3 Proposed information architecture

**Left nav (global):**
- **Pipelines**: list or search all pipeline agents (pinned or recent first)
- **My inbox**: items awaiting my review, questions assigned to me, @mentions
- **Ask across pipelines** (the current supervisor, renamed; secondary)
- **Admin** (owners only): create pipeline, members, memory jobs, daily-digest schedule, MCP setup, audit log

**Inside a pipeline (top tabs):**

| Tab | Purpose | Replaces |
|---|---|---|
| **Overview** | Intent, status, owner and members, health counts (open questions, pending reviews, recent decisions), latest digest | stats strip, part of Daily updates |
| **Ask** | Chat with inline citations; "Capture" card suggestions; "Show steps" disclosure | Agents & conversations |
| **Register** | Filterable table: Requirements · Rules · Decisions · Questions · TODOs · Changes, with a type filter chip row; click for a detail drawer with history and source conversation | Shared memory (approved part) |
| **Data model** | Canonical tables and columns, relationships, generated ERD and DDL, mapping from sources; optional "check against catalog" | Explore tables |
| **Sources** | Upstream datasets and uploaded documents | Sources |
| **Review** (badge) | Candidate and proposed items as cards, plus conflicts | Shared memory (candidates part) |
| **History** | Timeline of conversations and changes, filter by person, type, and date; open any transcript | Activity + Daily updates |

### 6.4 Wireframe: Pipeline › Ask

```
┌──────────────┬──────────────────────────────────────────────────────────────────────────────┐
│ ◈ Compass    │  position_pipeline  · Draft · Owner: TBD        [Overview][Ask][Register]... │
│              ├───────────────────────────────────────────────┬──────────────────────────────┤
│ Pipelines    │  ▸ Conversation: "Private valuation lag" ▾    │  Open questions (5)          │
│  • position  │                                               │   Q-012 Canonical grain?  ●  │
│  • trades    │  You: Private positions use last reported NAV │   Q-014 Owner for FX?        │
│  • margin    │       rolled forward one quarter.             │  Recent decisions            │
│              │                                               │   D-001 Unified canonical    │
│ My inbox (3) │  Agent: Noted. That conflicts with nothing    │  Cited in this answer        │
│              │  on record. [R-?] ...                         │   spec.md · D-001            │
│ Ask across   │  ┌─────────────────────────────────────────┐  │                              │
│              │  │ Record as Rule · Private track?          │  │                              │
│              │  │ "Private positions: NAV + 1Q roll-fwd"   │  │                              │
│              │  │ [Save]  [Edit]  [Not now]                │  │                              │
│              │  └─────────────────────────────────────────┘  │                              │
│              │  ┌──────────────────────────────────────────┐ │                              │
│ Admin        │  │ Ask or tell position_pipeline…  [Capture▾]│ │                              │
│              │  └──────────────────────────────────────────┘ │                              │
└──────────────┴───────────────────────────────────────────────┴──────────────────────────────┘
```

The `Capture ▾` menu offers *Requirement · Rule · Decision · Question · TODO · Change*. It opens a short form prefilled from the selected message.

### 6.5 Wireframe: Pipeline › Register

```
 [All] [Requirements 8] [Rules 14] [Decisions 6] [Questions 5 open] [TODOs 9] [Changes]   🔍 search
 ┌──────┬──────────────────────────────────────┬───────────┬──────────────┬────────────┬───────┐
 │ ID   │ Title                                │ Status    │ Owner/Decider│ Updated    │ From  │
 ├──────┼──────────────────────────────────────┼───────────┼──────────────┼────────────┼───────┤
 │ D-001│ Unified canonical public+private     │ Accepted  │ Owner TBD    │ 2026-09-15 │ seed  │
 │ Q-012│ What is the canonical grain?         │ Open → DA │ asked by BA  │ 2026-10-20 │ chat  │
 │ R-021│ Private: NAV + 1Q roll-forward       │ Proposed  │ BA           │ 2026-10-22 │ chat  │
 └──────┴──────────────────────────────────────┴───────────┴──────────────┴────────────┴───────┘
 Row click → drawer: body · history (versions) · links · "View source conversation" · [Export .md]
```

### 6.6 Language guide (non-technical copy)

| Current | Suggested |
|---|---|
| Run offline consolidation | _(hidden; runs on schedule)_ / Admin: "Extract knowledge from recent conversations" |
| Offline pipeline candidates | Suggested knowledge to review |
| Approved recall memory | Accepted knowledge |
| Baseline memories | Starting knowledge |
| Agent memory & pipeline | What this pipeline knows |
| Native session delivery pending | _(hide; retry silently, alert admin)_ |
| Delegation / child conversation | "Consulted: Trades pipeline" chip |

---

## 7. Cursor / MCP improvements

- **One MCP server** with a `pipeline` argument (or auto-detect from the open folder's `.pipeline` file or folder name) instead of one server entry per agent (six entries in `cursor-mcp.json`, which grows with every pipeline).
- **Tools:** `ask(pipeline, question, session_id?)`, `search_knowledge`, `get_items(type, status)`, `get_model(table?)`, `open_questions(assigned_to_me?)`, `record_decision`, `log_change`, `ask_question`, `answer_question`, `close_todo`, `export_markdown`.
- **Resources (MCP resources)**: expose `pipeline://position_pipeline/spec`, `/model`, `/decisions` so Cursor can attach them as context without a chat round trip.
- Ship a generated `.cursorrules` / `AGENTS.md` per pipeline that tells Cursor *when* to call `record_decision` (for example, "when you choose between implementation alternatives, record a decision").
- Keep the read-only SQL out of MCP for now, or expose only `describe_table` for the DA and dev case.

---

## 8. Code-level observations

| # | Finding | Where | Suggestion |
|---|---|---|---|
| 1 | Domain set is hard-coded to research/valuation, and the KB is baked into the deployment (`kb/*.md`, indexed at import) | `domains.py`, `app.py:20` `INDEX = Index(ROOT/'kb')` | Pipelines and sources live in the DB and a UC Volume; index into Vector Search; no redeploy to add knowledge |
| 2 | Domain routing by keyword substring (`'api'` matches "capital", "rapid"…) | `domains.belongs_to` | Assign sources to pipelines explicitly; drop keyword routing |
| 3 | All approved memory is stuffed into every system prompt | `agents.run` → `memory(agent)` | Brief + tool-based retrieval (section 4.3) |
| 4 | Agent explicitly cannot record knowledge | `agents.py` prompt, `app.py SYSTEM` | Add a `propose_item` tool with user confirmation |
| 5 | Consolidation output is one unstructured document; whole-blob approve or reject; the review id is the hash of the content | `registry.POLICY`, `agents.candidates`, `app.py /review` | Typed JSON candidates, per-item review |
| 6 | Attribution is lost: sessions are delivered with actor `candidate` and only agent/parent metadata | `native_memory.flush` | Include `owner`, role, and channel (UI/Cursor) in session metadata and in event data |
| 7 | Conversations are owner-only everywhere | `agents.own`, `agent_mcp.get_conversation` | Pipeline-member visibility with a private flag |
| 8 | Self-approval allowed; any user approves any agent | `app.py review_agent_memory` | Per-pipeline roles; block self-approval for decisions, rules, and requirements |
| 9 | Dead or legacy code: `SYSTEM`, `generate`, `generate_traced`, `/api/memories*`, `memories`/`sessions`/`messages` tables, hidden "Legacy memory archive" buttons | `app.py:144-175, 194-245`, `store.py`, `index.html` | Remove; it confuses both users and future maintainers |
| 10 | A new DB connection and Lakebase credential per call (`store.connection` requests a token every time) | `store.py` | Use a pooled connection with token caching or refresh (tokens last ~1h) |
| 11 | Chat is synchronous inside a FastAPI sync endpoint with up to four model rounds plus parallel delegation (~minutes) | `app.py /api/chat`, `agents.run` | Stream responses (SSE) and show progressive status ("Searching decisions…") |
| 12 | The frontend is a 153-line minified-style `app.js` with HTML string templates | `static/app.js` | Before the IA rewrite, move to a small React/Vite app (Databricks Apps template). The register table, drawers, and inbox will need components |
| 13 | Daily update is an LLM summary of everything; nothing feeds back into the register | `daily_updates.py` | Generate the digest *from register deltas* plus conversation highlights, and attach "suggested items" to the review inbox |
| 14 | The status endpoint exposes infra details to all users | `app.py /api/status` | Admin-only |
| 15 | MLflow tracing is only on the unused `generate_traced` path | `app.py` | Trace `agents.run` (tool calls, retrieval, latency) and use MLflow evaluation for answer and citation quality |

---

## 9. Suggested roadmap

**Phase 1: reshape around pipelines (1–2 weeks)**
1. Add the `pipelines`, `pipeline_members`, `items`, `item_versions`, and `item_links` tables; build an importer from the `position_pipeline/` scaffold.
2. Create the `position_pipeline` agent seeded from the scaffold; retire the valuation/research demo agents (or move them to a "demo" workspace).
3. Build the Register tab (read and filter) and the item detail drawer with "View source conversation".
4. Remove the legacy code paths and technical copy; hide Tables, Daily updates, and pipeline JSON behind Admin.

**Phase 2: capture and review (1–2 weeks)**
5. Add the `propose_item` agent tool, inline capture cards, and the Capture menu in the composer.
6. Build the Review inbox with per-item cards, edit-before-accept, the role-based approval policy, and no self-approval.
7. Change the consolidation policy to typed candidates with source event IDs; de-dupe against the register.
8. Make conversations shared by default; build the History timeline.

**Phase 3: recall, Cursor, quality (1–2 weeks)**
9. Build the memory projector (one entry per approved item) and Vector Search retrieval tools; replace the all-memory prompt with a pipeline brief.
10. Consolidate to a single MCP server with record tools and resources; generate `.cursorrules` per pipeline.
11. Add the markdown export, which regenerates `spec/rules/decisions/todos/model.md` (DDL and Mermaid ERD generated from model items) and can optionally commit to git.
12. Add the weekly digest from register deltas, the conflict and staleness jobs, MLflow tracing, and an eval set (e.g. "who decided X?", "what's open for the DA?").

---

## 10. Quick wins (can be done today)

- Replace the stats strip with *Open questions / Awaiting review / Decisions this week*.
- Remove the identity string, model name, and storage mode from the sidebar and footer.
- Drop the "Legacy memory archive" UI and the `/api/memories` endpoints.
- Rename the jargon per the section 6.6 table.
- Swap the valuation starter prompts for pipeline ones: *"What's the canonical grain?"*, *"List open questions"*, *"What did we decide about private-market valuation lag?"*, *"Record a decision…"*.
- Remove the manual Refresh buttons in favor of refresh on tab focus.
- Seed the agent directly from `position_pipeline/*.md` (split by `##` sections, one memory per decision or rule) so the demo reflects the real intent.
