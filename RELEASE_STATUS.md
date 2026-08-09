# Release Status — CK-NEXUS R14 Cognitive Brain Runtime

Decision: **DEVELOPMENT CANDIDATE / NO-GO FOR PRODUCTION CLAIMS**

Baseline R13 commit: `540590a6174febd10031d7af7f62b1adf5d35276`
R14 branch: `r14-cognitive-brain-runtime`

## R14 changes

- OpenAI Agents SDK credentials are now scoped per run through Credential Broker and `OpenAIProvider`; no process-global OpenAI key mutation remains.
- OpenAI uses the Responses model path through the current Agents SDK provider contract.
- Sensitive trace payload capture is disabled; trace export is disabled by default and requires explicit configuration.
- Default `OPENAI_MODEL` is `gpt-5.6-sol` and remains environment-overridable; live model/account access is still a runtime gate.
- n8n is retired from active CK-NEXUS runtime, compose, integration status, VPS bring-up and P0 routing/security execution paths.
- Email routing/outbox APIs remain CK-NEXUS-owned and are validated directly.

## Current local verification

- R14 non-billing regression: **168/168 PASS**.
- Python compile: **PASS**.
- JavaScript syntax: **PASS**.
- Shell syntax: **PASS**.
- Internal tracked-file secret scan: **PASS**.
- Full suite in this host: **174 PASS / 3 ERROR**, all three caused by unavailable `aiosqlite` in the host environment.
- Ruff/Bandit/pip-audit: **BLOCKED** in this host because the binaries/modules are not installed.

## Production blockers

Production Ready remains prohibited until the exact R14 release identity has evidence for:

1. fully provisioned dependency environment and full test suite;
2. Ruff, Bandit and dependency audit;
3. live OpenAI/provider AI001;
4. live PostgreSQL/Redis distributed idempotency;
5. delegated cgroup v2 enforcement on staging Linux;
6. backup/restore, observability and clean-machine deployment gates.

Historical R4-R13 documents remain lineage evidence and do not override the R14 architecture.
