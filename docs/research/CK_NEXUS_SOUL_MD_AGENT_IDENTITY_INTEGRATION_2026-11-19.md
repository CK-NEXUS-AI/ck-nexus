# CK-NEXUS SOUL.md Agent Identity Integration

Date: 2026-11-19
Status: IMPLEMENTED LOCALLY — TESTING REQUIRED — NOT RUNTIME/PRODUCTION VERIFIED

## Design

CK-NEXUS adopts the SOUL.md concept as versioned, role-specific behavioral guidance. A shared document establishes common principles; each built-in AI team role has a separate role document. The base Agent loads its role document at construction, exposes the combined guidance through `soul_guidance()`, and reports only version/hash/role metadata in `status()`. TeamDirector includes the guidance and metadata in normal task and peer-message contexts; team listings expose the role/version/hash metadata.

## Security boundary

SOUL.md is not an authorization mechanism. It grants no tools, credentials, approvals, leases, or execution permissions. Policy Kernel, capability checks, approvals, sandboxing, and tenant isolation remain authoritative. SOUL text is trusted only as a repository-controlled local template; external or user-submitted SOUL documents must not be loaded as executable policy.

## Files

- `creator_app/ai_team/soul.py`: bounded local loader, role validation, required sections, SHA-256 fingerprint.
- `creator_app/ai_team/souls/common.md`: shared identity and safety principles.
- `creator_app/ai_team/souls/{director,engineer,guardian,analyst,researcher,designer,connector}.md`: role-specific guidance.
- `creator_app/ai_team/agent.py`: loads guidance when an Agent instance is created and exposes it to the caller.
- `tests/test_agent_soul.py`: role coverage, loading, metadata, and path rejection.

## Not claimed

No API endpoint, enrollment QR, external SOUL import, persistent registry, database migration, model system-prompt injection, or production activation is included in this slice. The current team agents are deterministic Python handlers rather than live LLM prompt runners; the guidance is now carried in their dispatch context for a future model-backed runtime to consume. That future prompt integration still requires explicit implementation and tests.
