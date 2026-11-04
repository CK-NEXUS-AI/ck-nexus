# CK-NEXUS Assurance Profile 2026

Status: `MEASURED_NOT_VERIFIED`. This is a cross-framework engineering baseline, not a certification claim.

## Reference frameworks
- ISO/IEC 42001:2023 — AI management systems.
- NIST AI RMF 1.0 + NIST AI 600-1 Generative AI Profile.
- NIST SP 800-218 SSDF v1.1.
- OWASP Top 10:2025 and OWASP GenAI LLM Top 10 2026.
- MITRE ATLAS for AI adversary tactics, techniques and mitigations.
- CSA AI Controls Matrix v1.1 (2026), 247 controls across 18 domains.
- SLSA current specification for software supply-chain provenance.

## Non-normative frontier design inputs
- OpenAI: layered agent safeguards, high-impact confirmations and prompt-injection monitoring.
- Anthropic: proportional capability/risk thresholds, external review, defense in depth and risk reporting.
- Microsoft: fairness, reliability/safety, privacy/security, inclusiveness, transparency, accountability and agent shared responsibility.

## CK-NEXUS elevation rules
1. Every AI system/provider/tool has a named owner and inventory record.
2. Every material AI change requires risk and impact assessment before production.
3. Tool execution is least-privilege and cannot self-approve protected actions.
4. Prompt/tool injection is treated as a first-class threat class.
5. Providers/models/datasets have provenance, supplier risk and an exit path.
6. Release evidence must be exact-subject, reproducible and independently verifiable.
7. UNKNOWN, BLOCKED and missing evidence can never be promoted to PASS.
8. Production adoption requires canonical evidence plus human authorization where required.

Machine-readable source of truth: `config/ai_assurance_controls.json`.
Validation: `python scripts/validate_ai_assurance.py`.
