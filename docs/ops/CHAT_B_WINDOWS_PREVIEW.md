# Chat B Windows Preview Boundary

Status: development-only preview guidance. This document is not release or production evidence.

## Verified host capability

The authorized Windows worker can run the CK-NEXUS UI development toolchain with portable Git, Node.js, uv, and Python 3.12. Desktop Commander connectivity is treated only as a development transport.

## Renderer policy

1. Keep the existing CSS/perspective Cognitive Digital Twin as the mandatory fallback.
2. Detect WebGL capability before selecting a 3D backend.
3. Select THREE_WEBGL only when both WebGL and an explicitly supplied Three.js runtime are present.
4. Treat VRM support as an additional capability, never as a prerequisite for the safe fallback.
5. Do not fetch Three.js, VRM, GLB, textures, voices, or avatars from arbitrary runtime CDNs.
6. Do not let renderer state become a second authority for task, agent, policy, verification, or evidence state.
7. Bind runtime visualization only to the verified public State Projector contract handed off by Chat A.

## Truth boundary

Renderer inputs are limited to OBSERVED, INFERRED, SIMULATED, and VERIFIED. Unknown truth labels are downgraded to INFERRED. Unknown motion labels are rendered as idle. Private chain-of-thought, raw prompts, raw credentials, approval secrets, and production secrets are out of scope.

## Current blocker

Chat A has not yet published the exact public State Projector contract for Chat B consumption. The renderer adapter therefore remains contract-ready but unbound to a new backend endpoint. Existing UI runtime behavior is not replaced.

## Production boundary

No production merge, deploy, Production Ready claim, Q10/Q11/Q12 promotion, or production evidence rebinding is authorized by this development work.
