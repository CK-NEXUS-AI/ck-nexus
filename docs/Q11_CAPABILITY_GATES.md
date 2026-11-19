# Q11 Capability Gate Architecture

Q11 is evaluated as independently observable capability sub-gates rather than a
single provider-specific boolean.

| Gate | Meaning |
|---|---|
| Q11-A | Credential integrity |
| Q11-B | Runtime execution |
| Q11-C | Provider reachability |
| Q11-D | Provider authorization |
| Q11-E | Provider quota |
| Q11-F | Live provider execution |
| Q11-G | Evidence integrity |

Each gate carries its own status. VERIFIED requires execution evidence bound to
a release/source identity, an evidence artifact SHA-256, a verification method,
and explicit secret-redaction confirmation.

The current release keeps OpenAI as the authoritative live-provider acceptance
condition. Alternative providers may be registered and verified independently,
but they cannot silently substitute for the OpenAI-specific acceptance gate.

Therefore:

- HTTP 429 + insufficient_quota => Q11-E BLOCKED.
- The corresponding OpenAI live execution gate remains BLOCKED until a real
  successful response with the required sentinel is observed.
- Mock responses are never valid live-provider evidence.
- Missing or stale evidence is fail-closed.
- Independent VERIFIED gates remain VERIFIED when another provider gate is
  blocked.
- Q11 overall cannot become VERIFIED without the required authoritative live
  provider evidence.

No API key, token, cookie, credential value, or credential file content is part
of the Q11 evidence schema.
