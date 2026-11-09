# CK-NEXUS Unified Capability Fabric V1

Status: additive architecture and typed inventory; no external candidate is auto-installed or auto-executed.

## 1. Non-negotiable separation of concerns

| Class | Meaning | CK-NEXUS owner | Examples |
|---|---|---|---|
| Core | Authority over state, memory policy, permissions, execution grants, evidence and release gates | CK-NEXUS Core / L3 | `control_plane`, `council_authority`, policy and evidence contracts |
| AI provider | Model inference capability; not a tool registry or workflow engine | Provider Router | OpenAI, Gemini, Qwen, Groq, Anthropic |
| AI gateway | Unified provider API, routing, quotas and cost accounting | Provider Broker / Router | Existing LiteLLM |
| Agent framework | Runtime/library for worker reasoning, planning or checkpoints | AGNES worker adapter | LangGraph, Letta (candidates only) |
| Tool | Callable operation with an input/output contract | Connector Fabric / tool authorizer | MCP tools, local CLIs, APIs |
| Plugin | Packaged integration or product extension; may contain tools and UI | Connector Fabric after review | ChatGPT apps/connectors, community extensions |
| Connector | Authenticated protocol bridge to an external system | Connector Fabric | MCP, OpenAPI, GitHub, Gmail |
| Skill | Versioned procedure and capability metadata; no credentials or authority | AGNES Skill Registry | `SKILL.md` packages |
| Workflow engine | Deterministic/event/scheduled workflow execution | n8n Intelligence adapter | n8n; Activepieces is an alternative only |
| Knowledge source | A source of content/claims with provenance and rights | Global Knowledge | e-books, manuals, official docs, datasets |
| Document parser | Converts source bytes into structured text/chunks | Ingestion adapter | lightweight EPUB parser; Docling candidate |
| Vector store | Retrieval index, not canonical memory or policy | Global Knowledge repository | future Postgres/pgvector or separate vector service |
| Observability | Traces, metrics, evaluations and run diagnostics | CK-NEXUS Observability | existing tracing; Langfuse optional |
| Sandbox | Isolated execution environment for untrusted code/tools | Sandbox Executor | current sandbox module |

## 2. Unified request path

`User Goal -> Core Planner -> Capability Catalog -> Policy/Capability Authority -> Provider Router OR Connector Fabric OR AGNES Skill -> (optional n8n workflow) -> Sandbox/Executor -> Evidence Ledger -> Independent Verification -> Result`.

The catalog is a read-only inventory, not a permission database. A provider can generate a plan but cannot grant itself tools. A skill describes a procedure but cannot issue credentials. A plugin or connector is not executable until schema, provenance, risk and policy checks pass. n8n may schedule or execute approved workflow steps but cannot judge Q10 or change release state.

## 3. E-book and document knowledge pipeline

1. Accept a local user-provided file or a source with documented permission; record source URL/file identifier, title, author, publisher, language, rights statement and retrieval time.
2. Hash the original bytes before parsing. Never bypass DRM, access controls, paywalls or publisher restrictions.
3. Parse EPUB with the bounded standard-library adapter. Use Docling as an optional worker for PDF/OCR/Office only after a separate resource and license review.
4. Normalize chapters while preserving chapter order, headings, page/section metadata and source offsets.
5. Chunk by semantic headings with overlap and stable chunk IDs. Store source hash, parser version, chapter ID and rights metadata on every chunk.
6. Create embeddings through the Provider Router; do not tie the knowledge base to one vendor or model dimension. Version embedding model and re-index when dimensions/model change.
7. Store document/chunk index behind Global Knowledge. Retrieval must filter tenant, rights, revocation, freshness and source status before ranking.
8. Answers cite source and chunk IDs. Derived summaries remain derived claims; they never become verified facts or policy.
9. Memory writes are proposals and follow the CK-NEXUS memory policy; imported book text is not automatically user memory.

## 4. External projects: adopt as components, not competing systems

- LiteLLM: keep the existing gateway; fix its known dependency/error path rather than add a second gateway.
- Docling: preferred document parser candidate (MIT code, model-specific licenses); run as a separate worker if resource budget allows.
- LangGraph: optional worker orchestration library only if it fills a measured gap in existing control_plane/AGNES.
- Letta: research/isolated worker only; never replace CK-NEXUS Unified Memory authority.
- Langfuse: optional trace/evaluation exporter; avoid full stack co-location on current VPS.
- RAGFlow: evaluate on separate infrastructure; its official quickstart recommends 16 GB RAM and 50 GB free disk.
- Activepieces/Kestra: workflow alternatives, not parallel installs while n8n is present.

## 5. Adoption gates

`DISCOVERED -> SOURCE_VERIFIED -> LICENSE_REVIEWED -> SBOM/DEPENDENCY_SCAN -> SANDBOXED -> CONTRACT_TESTED -> POLICY_APPROVED -> REGISTERED -> READ_ONLY_CANARY -> EVIDENCE_REVIEW -> OPTIONAL WRITE_ACTIVATION`.

No auto-install based on search rank, stars, an e-book claim, or a vendor benchmark. Record exact release/commit, license, hashes, dependencies, network endpoints, secret requirements, CPU/RAM/disk budget, rollback and test results. External artifact authority is always `NONE`.

## 6. Current deployment constraint

The read-only inspection on 2026-11-09 found 1.9 GiB RAM (about 438 MiB available) and 2.2 GiB free disk (95% used). Do not co-install browser engines, OpenSandbox, heavyweight RAGFlow, Docling model bundles, vector databases or observability stacks here. Keep parsers and indexing as optional isolated workers or move them to a separate compute node. Current Production status remains NO-GO until Q10/Q11/Q12 and release gates are independently satisfied.

## 7. Initial open-learning sources for CK-NEXUS Knowledge

Candidate learning sources selected for license clarity and technical relevance:

- [Dive into Deep Learning](https://github.com/d2l-ai/d2l-en): book text CC BY-SA 4.0; sample/reference code has a separate modified MIT license. Preserve attribution and ShareAlike obligations. Candidate only until a pinned revision is ingested.
- [Hugging Face Transformers Course](https://github.com/huggingface/course): course content repository is Apache-2.0. Candidate only until a pinned revision is ingested.
- Exclude non-commercial or no-derivatives sources from the default commercial CK-NEXUS corpus unless a separate compatible permission is established. Publicly readable is not equivalent to reusable.

No source above is marked ingested in the catalog. A future ingestion report must include revision/commit, source hashes, license file hash, attribution, parser version, chunk count, and retrieval tests.

The local document path now supports EPUB parsing and text-based PDF extraction through the installed Poppler `pdftotext` utility. PDF extraction is bounded by file/output size and a 30-second process timeout. It does not perform OCR; scanned PDFs require a separate, resource-budgeted OCR worker. Extracted chapters/pages are chunked and stored in a local SQLite index only after the operator supplies a permitted rights basis. Search is lexical (not vector/semantic) in this first slice; no embedding model is silently selected.

The first knowledge-search bridge is now available through MCP as `cknexus_knowledge_search` and `cknexus_knowledge_sources`. Both are read-only; results carry source SHA-256 and stable chunk IDs. The MCP service account receives ACL-based read-only traversal to the dedicated knowledge DB file only. These tools do not write personal memory, alter policy, or grant execution authority.

## External capability registry

The canonical machine-readable inventory is config/capability_catalog.json. The current review, verification-state semantics, candidate risk notes and ChatGPT-session-only availability snapshot are maintained in [AGNES External Capability Registry](../AGNES_EXTERNAL_CAPABILITY_REGISTRY.md). The inventory is descriptive only; all external artifacts have authority_scope=NONE and CK-NEXUS Core remains the sole L3 authority.
