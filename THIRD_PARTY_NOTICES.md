# Third-party notices

CK-NEXUS uses third-party software. Those components remain governed by their own upstream license terms; the CK-NEXUS commercial license does not replace them.

## Exact production runtime evidence

- Runtime/deployment subject: `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f`
- Verified runtime source SHA: `4cf17cd3befaafeaf64cd4c149739133aa220f73`
- Runtime license workflow run: `31818388980`
- Evidence artifact ID: `9225934333`
- Evidence artifact digest: `sha256:89e799dcc1c152394711e1bf6bd260f5c7cabeafffd44752220db15fcf3d163e`
- Exact installed Python runtime distributions inspected: **55**
- Distributions without detected installed license evidence: **0**

The verifier inspected installed distribution metadata plus installed LICENSE/LICENCE/COPYING/NOTICE files inside the exact production Docker runtime. The proprietary `ck-nexus-creator` distribution is excluded from the third-party count. The final production packaging workflow re-exports the exact runtime inventory and installed license files into the customer package after all Q10-Q16 production gates pass.

This is technical release evidence. It does not state that external legal counsel reviewed every license obligation. Transaction-specific legal interpretation/review remains the seller/buyer responsibility where required by the sale terms.

## Runtime dependency families

The exact runtime includes the locked direct and transitive dependencies required by CK-NEXUS, including OpenAI/OpenAI Agents, FastAPI/Uvicorn, MCP, PostgreSQL drivers, Redis, SQLAlchemy, Stripe, cryptography, HTTP clients, validation libraries and their transitive runtime dependencies. Exact names, versions and detected license files are generated from the production image rather than maintained manually.

## Referenced external container images

The source/deployment definition references, but the source archive does not itself redistribute, these pinned external images. Their upstream terms apply when pulled/deployed:

- `python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`
- `postgres:16-alpine@sha256:44c4ee9810eff91f7eab4d822642e01115b1a9eccce4bcbdde7604752d68eac6`
- `redis:7-alpine@sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2`
- `caddy:2.10-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d`

Optional developer/operator tools that are not installed in the production image are outside the 55-distribution runtime inventory. If additional tools are redistributed with a customer delivery, regenerate notices for that exact delivery artifact.
