# CK-NEXUS Test Portal

Static GitHub Pages frontend for CK-NEXUS. The connection panel performs only GET /health and GET /api/status. It does not store credentials or issue write operations. The API must use HTTPS and allow browser CORS for the published Pages origin. A successful HTTP response is not Production certification.

The Pages workflow deploys the website/ directory when changes reach main, or when manually dispatched.
