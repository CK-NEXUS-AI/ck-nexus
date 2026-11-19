# CK-NEXUS Assessor Data Room Checklist X1

Status: PREPARATION
Last reviewed: 2026-09-05

Purpose: prepare one consistent evidence package for independent security reviewers, certification bodies, technical due diligence, and acquisition review without overstating verification status.

## A. Organization and scope

- [ ] Legal/project owner identity
- [ ] Scope statement
- [ ] Sites / operational locations
- [ ] Headcount relevant to certification scope
- [ ] Roles and responsibilities
- [ ] System boundaries
- [ ] Development vs production boundary
- [ ] Interested parties / stakeholders
- [ ] Applicable legal, contractual, and regulatory obligations

## B. System architecture

- [ ] Current architecture diagram
- [ ] Component inventory
- [ ] Trust boundaries
- [ ] Data-flow diagram
- [ ] Authentication/authorization flow
- [ ] Agent/tool execution flow
- [ ] Provider routing flow
- [ ] Evidence pipeline
- [ ] Logging/observability architecture
- [ ] Backup/recovery architecture

## C. Asset and dependency inventory

- [ ] Source repositories
- [ ] Services and runtimes
- [ ] Containers/images
- [ ] Databases/storage
- [ ] Third-party services
- [ ] AI model/provider inventory
- [ ] MCP/tools/connectors inventory
- [ ] SBOM
- [ ] Dependency lock state
- [ ] Supplier/provider risk inventory

## D. AI governance

- [ ] AI system inventory
- [ ] Intended-use statements
- [ ] Known limitations
- [ ] Human oversight model
- [ ] AI risk register
- [ ] Model/provider change process
- [ ] Tool/capability permissions
- [ ] Agent autonomy boundaries
- [ ] Prompt/input/output risk controls
- [ ] Evaluation/monitoring plan
- [ ] Disable/rollback path

## E. Security governance

- [ ] Information-security policy
- [ ] AI governance policy
- [ ] Access-control policy
- [ ] Least-privilege model
- [ ] Separation of duties
- [ ] Secret/credential handling policy
- [ ] Vulnerability management process
- [ ] Secure configuration baseline
- [ ] Change-management process
- [ ] Incident-response process
- [ ] Business-continuity/recovery process

## F. Secure software development

- [ ] Secure SDLC description
- [ ] Code review requirements
- [ ] Branch/release governance
- [ ] CI security controls
- [ ] SAST
- [ ] dependency vulnerability scanning
- [ ] secret scanning
- [ ] IaC/container scanning
- [ ] tests and coverage
- [ ] security regression tests
- [ ] remediation tracking
- [ ] retest evidence
- [ ] release gate criteria

## G. Exact-subject evidence

Frozen Q10 subject:
- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

Required final Q10 evidence remains:
- [ ] native deep security scan on exact frozen subject
- [ ] `scan-manifest.json`
- [ ] `findings.json`
- [ ] `coverage.json`
- [ ] sealed `report.md`
- [ ] native completion/seal receipt
- [ ] exact artifact SHA-256
- [ ] complete coverage evidence
- [ ] exact scan ID
- [ ] artifact guard result
- [ ] fresh evidence-ledger/Darker verification
- [ ] exact tests/receipt
- [ ] machine finalizer
- [ ] evidence-signing verification
- [ ] independent HUMAN review
- [ ] owner HUMAN sign-off

Until complete:
- Q10 = NOT_VERIFIED
- Q11 = BLOCKED
- Q12 = BLOCKED
- Production = NO-GO

## H. Risk management

- [ ] enterprise/project risk register
- [ ] AI-specific risk register
- [ ] security threat model
- [ ] abuse/misuse scenarios
- [ ] supply-chain risks
- [ ] provider/vendor risks
- [ ] data/privacy risks
- [ ] operational risks
- [ ] risk owners
- [ ] treatment plan
- [ ] acceptance criteria
- [ ] residual risk
- [ ] review cadence

## I. Evidence integrity

- [ ] evidence manifest
- [ ] artifact hashes
- [ ] timestamps
- [ ] subject identifiers
- [ ] scanner/tool versions
- [ ] environment identifiers
- [ ] chain-of-custody record
- [ ] signature verification
- [ ] tamper-detection result
- [ ] reviewer identity
- [ ] reviewer decision
- [ ] owner decision

## J. External-assessment package

For each assessor/provider:
- [ ] scope sent
- [ ] frozen subject disclosed where relevant
- [ ] NDA status
- [ ] rules of engagement
- [ ] required access
- [ ] deliverables
- [ ] independent human review confirmed
- [ ] exact commit/tree support confirmed
- [ ] remediation/retest terms
- [ ] indicative timeline
- [ ] quotation received
- [ ] no paid action authorized without owner approval

## K. Buyer / due-diligence package

Only development-stage truthful claims:
- [ ] product overview
- [ ] architecture
- [ ] source/IP scope
- [ ] roadmap
- [ ] known limitations
- [ ] security posture
- [ ] open findings
- [ ] current verification state
- [ ] licensing/dependency inventory
- [ ] transfer exclusions
- [ ] credentials/tokens/private keys explicitly excluded

Never claim:
- [ ] "Production Certified"
- [ ] "Q10 Passed"
- [ ] "Fully Verified"
- [ ] "Officially Certified"

unless external and internal authority gates have actually completed.

## L. Recommended folder structure

```
assessor-data-room/
  00-index/
  01-scope/
  02-architecture/
  03-assets/
  04-ai-governance/
  05-risk/
  06-security-policies/
  07-secure-sdlc/
  08-sbom-supply-chain/
  09-tests-scans/
  10-findings-remediation/
  11-observability-incidents/
  12-backup-recovery/
  13-evidence-integrity/
  14-independent-review/
  15-owner-signoff/
```

Each evidence item should include subject, source, observed_at, hash where applicable, and verification state.
