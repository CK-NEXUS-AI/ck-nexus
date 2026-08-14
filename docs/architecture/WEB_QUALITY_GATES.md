# CK-NEXUS Web Quality Gates

Status: SPEC_ONLY / UI prototype branch

These gates apply to the future Unified Command Center. They are separate from Q01-Q16 release promotion and cannot substitute for Q10 Deep Security.

## WQ01 Semantic structure

PASS requires:

- one main landmark
- explicit navigation landmark
- meaningful heading hierarchy
- native links/buttons/forms where possible
- no clickable generic div/span controls

## WQ02 Keyboard and focus

PASS requires:

- all controls keyboard reachable
- visible focus indicator
- focus order follows task order
- skip link works
- modal focus is contained while open
- Escape closes dismissible modal
- focus returns to invoking control

## WQ03 Responsive usability

PASS requires desktop, tablet and small-screen verification. No essential control may depend on hover. Navigation and contextual inspector must collapse without losing functionality.

## WQ04 Accessible names and status

PASS requires labels/programmatic names for interactive controls and correct use of live-region/status semantics. Color cannot be the only status signal.

Target: WCAG 2.2 AA. Formal conformance must not be claimed until full-page manual and automated assessment is complete.

## WQ05 Performance

Target field thresholds at p75, evaluated separately for mobile and desktop:

- LCP <= 2.5 seconds
- INP <= 200 milliseconds
- CLS <= 0.1

Build budgets should be set after measuring the prototype. Critical operational state should not wait on unnecessary third-party assets.

## WQ06 Browser security

PASS requires a reviewed policy for:

- Content-Security-Policy
- frame-ancestors / clickjacking protection
- X-Content-Type-Options
- Referrer-Policy
- secure cookie/session attributes where applicable
- Cache-Control for sensitive pages and API responses
- restricted CORS origins

Do not deploy a guessed CSP directly in production. Introduce/measure Report-Only policy where needed, then enforce after compatibility review.

## WQ07 Authentication and authorization UX

The UI must never infer authority from hidden buttons. Backend authorization remains authoritative. Every privileged action must fail closed when capability/role/policy state is missing or stale.

## WQ08 Approval UX

Irreversible, security-sensitive, financial and production actions require explicit action labels, target context, risk context and approval expiry. The least destructive action should receive safe default focus for high-impact confirmation dialogs.

## WQ09 Error and uncertainty model

UI must distinguish:

- success
- failed
- blocked by policy
- pending approval
- degraded
- unknown
- unsupported
- timed out
- side-effect outcome uncertain

Unknown or uncertain state is never displayed as success.

## WQ10 Observability

Every important UI action produces or references correlation identifiers that connect frontend action, API request, AGNES execution and evidence record. Sensitive content must be redacted.

## WQ11 Supply-chain and frontend dependencies

Prefer no third-party CDN in the command center. Dependencies must be pinned, reviewed and included in dependency/security evidence. New UI packages require justification relative to native platform capabilities.

## WQ12 Test matrix

Minimum before release candidate:

- semantic/DOM checks
- keyboard navigation test
- focus/modal test
- responsive viewport tests
- accessibility automated scan
- screen-reader smoke test
- reduced-motion test
- high-contrast/forced-colors smoke test
- API failure/degraded-state test
- authorization negative tests
- CSP/security-header verification
- performance lab measurement
- browser smoke tests

## External standards baseline

- W3C WCAG 2.2
- W3C WAI-ARIA Authoring Practices Guide
- OWASP ASVS 5.0
- OWASP Top 10:2025
- OWASP CSP and HTTP Security Headers guidance
- current Core Web Vitals guidance

These sources provide the baseline. CK-NEXUS may impose stricter controls where governance requires them.
