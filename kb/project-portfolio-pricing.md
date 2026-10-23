# Project document: portfolio-pricing

Source: research_val_personal/docs/portfolio-pricing.md
Kind: design document; may describe planned rather than shipped features.

# Portfolio pricing

Accounts, portfolios, holdings, dashboard day changes, manual refresh, and Market Data's default
lookup use `app/backend/portfolio/prices.py:resolve_quotes`.

Quotes are keyed by the exchange-qualified Yahoo symbol so the same listing shares a quote across
accounts, while different listings remain separate. Successful quotes are cached for five minutes
in each backend process; manual portfolio refresh bypasses this cache and the intraday provider cache.

The resolver chooses the newest available daily close from Yahoo and fiscal.ai (Yahoo wins date
ties), then prefers a positive, finite Yahoo intraday price unless its session predates that close.
Funds marked `is_etf` skip fiscal.ai. Daily and intraday prices use unadjusted closes when available,
with pence and other supported minor currency units converted to major units.

If providers fail, the last successful shared quote is retained. Without a shared quote, the
position's stored price is retained. Holdings show a `cached` label for these fallbacks; their price
tooltip identifies the source and timestamp when available. Market Data shows quote dates and
explicitly labels cached provider-failure results.

Market Data's provider-specific options are diagnostics, not alternative portfolio valuation
paths. Its default “Portfolio price” lookup shares the same quote as holdings without modifying
positions. Holdings reads persist changed prices best-effort. Account values inside a portfolio
response use the same in-memory position snapshot as that response's portfolio total.

Visible account and portfolio screens poll every five minutes. This is not a guarantee of a
real-time feed: provider delays, market closures, outages, and separate backend process caches can
still affect freshness.