from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['mode'] == 'DEMO_NON_PRODUCTION'


def test_claims_are_no_go_by_default():
    r = client.get('/api/claims/public')
    assert r.status_code == 200
    body = r.json()
    assert body['production_classification'] == 'NO_GO'
    assert 'Production Ready' in body['blocked_claims']
