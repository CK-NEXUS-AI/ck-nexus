# MVP Acceptance Criteria

## Functional

- [x] `GET /health` returns HTTP 200 and the application version.
- [x] The UI/API loads all four agents and supports direct menu selection.
- [x] Demo Mode completes a run without an API key.
- [x] A completed run persists in local SQLite history and is retrievable by session.
- [x] Session deletion removes product history and Agents SDK memory.
- [x] Live Mode returns a safe configuration error when the key is missing.
- [ ] Live Mode completes one real OpenAI request when a valid project key is configured. `[BLOCKED: API key connector]`

## Security

- [x] Secret scan finds no plaintext key pattern in delivery source and documentation.
- [x] `.env.local` is ignored by version control and Docker context.
- [x] API token enforcement works when configured.
- [x] Oversized bodies, invalid session IDs, and excess run requests are rejected.
- [x] Model output is inserted with `textContent`, not interpreted as HTML.
- [x] Dependency audit reports no known vulnerability in the checked environment.

## Commercial delivery

- [ ] Seller replaces every bracketed license field.
- [ ] Price, support period, update policy, and refund/acceptance terms are explicit.
- [ ] Clean-machine installation is tested on the target operating system.
- [x] ZIP hash, internal checksums, and delivery manifest are generated and verified.
- [ ] Buyer receives setup, operation, backup, and troubleshooting guidance.
