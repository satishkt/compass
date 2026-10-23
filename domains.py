"""Server-owned domain definitions and initial curated memories."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Domain:
    id: str
    name: str
    purpose: str
    keywords: tuple[str, ...]
    seeds: tuple[tuple[str, str, str], ...]

DOMAINS = {
    'valuation': Domain('valuation', 'Valuation', 'Valuation methods, model assumptions, basis validation, fair-value publication, and valuation evidence.', ('valuation', 'dcf', 'fcff', 'fair value', 'discount', 'assumption', 'multiple', 'underwriting'), (
        ('publication', 'A numerical exploratory DCF result is not automatically a published fair value. Publication requires validated basis and review of the exact model and evidence. Older models are not grandfathered in.', 'project-valuation-basis.md'),
        ('numeric-scale', 'Vendor unit labels do not prove the numeric scale. The basis requires an explicit numeric_value_scale: absolute attestation, and Python converts absolute values to millions once.', 'project-valuation-basis.md'),
        ('synthetic-atlas', 'SYNTHETIC DEMO: The fictional Atlas research team reviews valuation assumptions every 30 days. Atlas is not a real investment.', 'synthetic-demo.md'),
    )),
    'research': Domain('research', 'Research & Evidence', 'Research journey, filings, evidence capture, provenance, research packets, and dossier workflow.', ('research', 'evidence', 'filing', 'dossier', 'journey', 'source-cell', 'provenance', 'guidance'), (
        ('journey', 'The research journey has nine stages: Idea, Screen, Understand, Assess, Value, Decide, Position, Monitor, Review. Soft gates guide and warn; they do not block navigation.', 'project-research-journey-design.md'),
        ('evidence-review', 'Before accepting source-cell evidence, check interpretation, units, scaling, currency, period, perimeter, and definition. Exact text anchoring does not prove semantic correctness.', 'project-valuation-evidence-review.md'),
        ('conflicts', 'Conflicting evidence stays unresolved until exactly one candidate is accepted and every alternative is explicitly rejected. Missing decisions remain unresolved.', 'project-valuation-evidence-review.md'),
    )),
    'portfolio': Domain('portfolio', 'Portfolio', 'Portfolio aggregation, accounts, pricing, total return, attribution, positions, and investment signals.', ('portfolio', 'account', 'holding', 'return', 'dividend', 'buyback', 'attribution', 'position', 'pricing'), (
        ('pricing', 'Portfolio pricing and valuation fair value are distinct. A market lookup price must not be presented as a reviewed published fair value.', 'project-portfolio-pricing.md; project-valuation-basis.md'),
        ('requested-categories', 'Historical user request, not a shipped-feature claim: allow named stock categories, membership in multiple categories, and category-level return, attribution, and risk views alongside account aggregation.', 'conversation-f6ee2f70-c940-4a99-b5b5-60bd899dbfe0.md (2026-10-22)'),
        ('requested-total-return', 'Historical user request, not a verified calculation definition: show total return for current holdings and explain price change, dividends, and buyback-related measures. Do not assume buyback yield can simply be added to realized investor total return.', 'conversation-f6ee2f70-c940-4a99-b5b5-60bd899dbfe0.md (2026-10-22)'),
    )),
    'platform': Domain('platform', 'Platform & Data', 'Databricks architecture, data access, deployment, runtime, pipelines, and live catalog exploration.', ('databricks', 'catalog', 'schema', 'table', 'lakebase', 'deployment', 'pipeline', 'runtime', 'warehouse', 'api'), (
        ('catalog-boundary', 'This POC explores only satish_doc_intelligence_catalog. Live table queries must run read-only under the verified end-user identity; never fall back to the application service principal.', 'Verified POC deployment configuration'),
        ('live-results', 'Live row counts and distributions change over time. Store durable ways to find or compute them, not current values, as long-term memory.', 'POC proposal; Databricks memory-pipelines documentation'),
        ('metadata-vs-data', 'Metadata descriptions and live aggregate queries are different evidence sources. Show the executed SQL and timestamp for live results; do not assert table access if no query was executed.', 'POC proposal'),
    )),
    'supervisor': Domain('supervisor', 'Supervisor', 'Delegate across domains, reconcile evidence, coordinate follow-ups, and synthesize a cited cross-domain answer.', (), (
        ('domain-directory', 'Delegate valuation methods, assumptions, and publication to Valuation; research workflow, filings, and evidence to Research & Evidence; holdings, return, and aggregation to Portfolio; Databricks architecture and live tables to Platform & Data.', 'Application domain registry'),
        ('cross-domain-policy', 'For questions spanning domains, delegate to each relevant domain agent and consolidate their answers. Preserve source citations and explain unresolved disagreements rather than choosing an unsupported winner.', 'User-confirmed architecture requirement'),
        ('learning-policy', 'Each domain agent and the supervisor have separate seeded memory, conversation sessions, and offline consolidation pipelines. Pipeline candidates require a user approval before becoming shared recall memory.', 'User-confirmed architecture and approval requirements'),
    )),
}

APPROVED_ACTOR = 'approved'
CANDIDATE_ACTOR = 'candidate'

def all_domains():
    from registry import definitions
    result=dict(DOMAINS)
    for row in definitions():
        if row['status']=='ready':
            result[row['id']]=Domain(row['id'],row['name'],row['purpose'],tuple(row['keywords']),tuple((s['topic'],s['content'],s['source']) for s in row['seeds']))
    return result

def get_domain(agent_id):
    domain=all_domains().get(agent_id)
    if not domain: raise ValueError('Unknown agent or agent setup is not complete')
    return domain

def belongs_to(agent_id, title, content='', *, domain=None):
    if agent_id == 'supervisor': return False
    text = (title + ' ' + content).lower()
    return any(word in text for word in (domain or get_domain(agent_id)).keywords)
