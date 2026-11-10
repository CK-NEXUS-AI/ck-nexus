from __future__ import annotations

import json
import sys

import pytest

from scripts import q14_candidate_metrics_check as check


class _Response:
    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body.encode()


def test_q14_reads_actual_candidate_health_and_metrics(tmp_path, monkeypatch):
    responses = iter(
        [
            _Response(json.dumps({"status": "ok"})),
            _Response(
                "# TYPE ckn_email_stale_processing_leases gauge\n"
                "ckn_email_stale_processing_leases 1\n"
                "# TYPE ckn_email_outbox_pending gauge\n"
                "ckn_email_outbox_pending 0\n"
            ),
        ]
    )
    monkeypatch.setattr(check, "safe_urlopen", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setenv("CKNEXUS_ACCESS_TOKEN", "staging-token")
    output = tmp_path / "metrics.txt"
    monkeypatch.setattr(sys, "argv", ["q14_candidate_metrics_check.py", "--output", str(output)])
    assert check.main() == 0
    assert "ckn_email_stale_processing_leases 1" in output.read_text()


def test_q14_rejects_missing_or_uninjected_candidate_metric(monkeypatch, tmp_path):
    responses = iter(
        [
            _Response(json.dumps({"status": "ok"})),
            _Response("# TYPE ckn_email_outbox_pending gauge\nckn_email_outbox_pending 0\n"),
        ]
    )
    monkeypatch.setattr(check, "safe_urlopen", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(
        sys,
        "argv",
        ["q14_candidate_metrics_check.py", "--output", str(tmp_path / "metrics.txt")],
    )
    with pytest.raises(SystemExit, match="required candidate metric is missing"):
        check.main()
