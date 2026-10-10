from __future__ import annotations

from scripts.n8n_p0_guard import inspect_workflow, is_n8n_workflow


def test_detects_unauthenticated_webhook():
    workflow = {
        "nodes": [{"name": "Evidence Intake", "type": "n8n-nodes-base.webhook", "parameters": {"httpMethod": "POST"}}],
        "connections": {},
    }
    findings = inspect_workflow(workflow, "fixture.json")
    assert len(findings) == 1
    assert "no configured authentication" in findings[0]


def test_detects_cleartext_http_and_literal_bearer_without_echoing_secret():
    workflow = {
        "nodes": [{
            "name": "Run Scanners",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {
                "url": "http://scanner.example/api/scan",
                "headerParameters": {"parameters": [{"name": "Authorization", "value": "Bearer fixture-secret-value"}]},
            },
        }],
        "connections": {},
    }
    findings = inspect_workflow(workflow, "fixture.json")
    assert len(findings) == 2
    assert all("fixture-secret-value" not in finding for finding in findings)


def test_allows_credential_reference_and_https():
    workflow = {
        "nodes": [{
            "name": "Secure Scanner",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {
                "url": "https://scanner.example/api/scan",
                "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $credentials.scannerAuth }}"}]},
            },
        }],
        "connections": {},
    }
    assert inspect_workflow(workflow) == []


def test_workflow_shape_requires_nodes_and_connections():
    assert is_n8n_workflow({"nodes": [], "connections": {}})
    assert not is_n8n_workflow({"nodes": []})
