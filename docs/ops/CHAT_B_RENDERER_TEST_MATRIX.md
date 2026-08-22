# Chat B Renderer Verification Matrix

Development-only verification matrix for Issue #125.

| Case | Expected | Current |
| --- | --- | --- |
| No WebGL | CSS_FALLBACK | PASS on Node mock |
| WebGL + no Three.js | CSS_FALLBACK | PASS by contract |
| WebGL + Three.js | THREE_WEBGL | PASS on Node mock |
| Invalid truth label | downgrade to INFERRED | PASS |
| Invalid motion label | render idle | PASS |
| Missing agent id | drop record | PASS |
| Destroyed adapter | reject applyProjection | PASS |
| Raw credential access | none | PASS by static scope |
| Executor/production mutation | none | PASS by static scope |
| Chat A State Projector binding | exact handoff required | BLOCKED/PENDING |
| Browser WebGL smoke on live preview | required | PENDING |
| GitHub CI/security exact head | required | PENDING |

The adapter must remain unbound to any newly invented runtime endpoint until Chat A publishes an exact-SHA public projection contract.
