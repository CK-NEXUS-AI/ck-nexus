# CK-NEXUS Tool Discovery System V1

Status: initial discovery-planning and candidate-ranking slice; not production-enabled.

## Purpose

Find candidate tools, MCP servers, APIs, CLIs, SDKs, libraries, web services, and public datasets that could extend CK-NEXUS. Reuse the existing global-knowledge SearXNG connector, tool registry, orchestration, MCP, sandbox, and evidence controls instead of installing a parallel stack.

## Current implementation

- `creator_app/global_knowledge/tool_discovery.py` builds bounded query variants and ranks candidate records by lexical relevance.
- `tests/test_tool_discovery.py` covers query bounds, candidate URL validation, duplicate URL handling, ranking, and review-state disposition.
- The current module accepts candidates supplied by a caller. It does not yet invoke SearXNG, crawl repositories, mutate the operations registry, or install tools.

## Intended flow

1. Decompose a user's capability request into bounded searches (tool integration, API/SDK, MCP server, source repository, and domain-specific connector).
2. Search via existing approved discovery providers and local CK-NEXUS inventory.
3. Normalize candidates and deduplicate canonical URLs.
4. Rank relevance separately from trust and security.
5. Record evidence URL, observation time, capabilities, credentials, write-action flags, license, maintenance signals, and policy decisions.
6. Review supply-chain, license, permissions, data egress, network scope, authentication, and maintenance before sandbox tests.
7. Test in the existing sandbox; attach measured output and hashes to Evidence/Audit.
8. Propose registry integration only after review. Discovery never implies permission to execute.

## Safety invariants

- Unknown tools remain discovery-only; no auto-install, auto-execution, or automatic production promotion.
- An APPROVED discovery record is still subject to runtime policy and least-privilege checks.
- Search relevance score is not a trust, security, or quality score.
- Reject invalid URL schemes and URLs containing embedded credentials.
- Preserve source URLs and timestamps; never present a search snippet as verified fact.
- Respect provider terms, robots policy, rate limits, privacy boundaries, and authorization.
- No access-control bypass, credential scraping, CAPTCHA bypass, or collection of private/hidden data.
- Keep existing user modifications intact; do not reset or clean the worktree.

## Remaining integration work

- Connect the planner to `SearXngDiscoveryAdapter` and approved repository/API discovery sources.
- Add a normalized evidence record and provenance integration.
- Add source-quality and supply-chain review gates, including license and maintenance checks.
- Add a read-only inventory adapter for `config/operations_tool_registry.json` so existing tools win over duplicates.
- Add sandbox conformance probes and explicit approval workflow before any registry write.
- Expose the feature through the existing orchestrator/MCP surface only after API contract and authorization tests.

## Validation boundary

Passing unit tests proves only the planner/ranker behavior. It does not prove external search availability, connector authentication, tool safety, successful installation, or production readiness.
