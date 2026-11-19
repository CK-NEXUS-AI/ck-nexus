# CK-NEXUS Public Beta Feedback

## What is enabled

- Public feedback page: `/feedback`
- Public submission API: `POST /api/public-feedback`
- Internal report queue: `GET /api/internal/public-feedback`
- Internal preliminary triage: `POST /api/internal/public-feedback/{feedback_id}/triage`

## Before inviting testers

1. Deploy the reviewed build to a staging environment, not the production control plane.
2. Configure a strong, unique `CKNEXUS_ACCESS_TOKEN` in the server secret store. Internal feedback review fails closed when this token is absent.
3. Keep provider credentials, GitHub credentials, admin endpoints, metrics, and execution tools server-side. Never put secrets in browser JavaScript.
4. Use HTTPS, a persistent encrypted volume, backups, and a single API worker for this SQLite feedback store. The built-in rate limiter is in-process; use an edge/WAF or shared limiter before scaling horizontally.
5. Verify that public testers can only access the intended beta workspace and cannot read other users' sessions, reports, credentials, or admin routes.
6. Publish the privacy notice and support contact before collecting real user reports.

## Report handling

Public submissions accept a category, optional 1–5 rating, title, report, reproduction steps, expected behavior, and explicit consent. Email and IP addresses are not persisted. The form rejects secret-shaped strings, has a honeypot, limits request size through the API middleware, rate-limits submissions, and suppresses duplicate reports for 14 days. Stored reports are purged after 180 days when the store initializes.

Internal review uses `Authorization: Bearer $CKNEXUS_ACCESS_TOKEN`. Preliminary triage assigns a category and priority and returns a reproduction checklist. A report remains `needs_reproduction`; triage does not prove a defect, run untrusted instructions, create code changes, or promote a fix. A human must reproduce the issue, inspect evidence, add a regression test, and approve any code change through the normal review process.

## API examples

```bash
curl -sS -H "Authorization: Bearer $CKNEXUS_ACCESS_TOKEN" \
  http://127.0.0.1:8000/api/internal/public-feedback

curl -sS -X POST \
  -H "Authorization: Bearer $CKNEXUS_ACCESS_TOKEN" \
  http://127.0.0.1:8000/api/internal/public-feedback/fb_<32-hex-id>/triage
```

## Release gate

This feature branch is not a public deployment. Do not announce the beta until the PR has independent review, CI/security checks pass, the application is deployed to an isolated staging URL, access controls are tested with separate tester accounts, and the feedback retention/backup process is verified.

## External tester access limitation

The current application uses one optional global bearer token, not individual tester identities or tenant-scoped authorization. Do not distribute the global `CKNEXUS_ACCESS_TOKEN` to external testers: it grants access to every route protected by that token, not only the beta workspace. The feedback page can be exposed separately, but interactive public beta access remains blocked until per-tester authentication, session ownership checks, and tenant isolation are implemented and independently tested. This is a release blocker, not a manual tester checklist item.


## Staging security boundary (mandatory)

In `staging` and `production`, the application exposes only the public homepage, feedback page, feedback submission API, static web assets, and health probes without authentication. All other paths—including `/development`, `/approval`, `/demo`, OpenAPI/docs, provider and assistant discovery, integrations, Agnes execution/pipelines, runs, sessions, internal feedback reports, and status APIs—require the server-side `CKNEXUS_ACCESS_TOKEN`.

Startup fails if that token is missing in staging or production. Invalid bearer-token attempts are rate-limited per observed client address (10 failures per 60 seconds in one process). This is defense in depth, not a substitute for an edge/WAF rate limiter: configure trusted proxy handling carefully and enforce shared rate limits at the ingress. Never trust client-supplied forwarding headers unless the proxy is explicitly trusted.

This global token is an operator credential, not a tester login. **Never distribute it to beta testers.** The current interactive workspace is not safe for multi-user public access until per-user authentication, session ownership, and tenant isolation exist and are independently tested. Keep the public beta limited to feedback intake until then.
