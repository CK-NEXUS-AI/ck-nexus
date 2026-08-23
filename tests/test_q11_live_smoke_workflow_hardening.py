from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/q11-live-provider-smoke.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_q11_is_manual_and_exact_subject_confirmed() -> None:
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert "confirm_runtime_sha:" in text
    assert "confirm_runtime_subject:" in text
    assert "39f5c1adb9d761ab418cf088ff1f051b1ca731d1" in text
    assert "0525195934f703a8becf8a39f6397b2411e0bb2e" in text
    assert "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52" in text


def test_q11_requires_native_q10_before_provider_access() -> None:
    text = workflow_text()
    q10_step = text.index("Enforce Q10 native Deep Scan prerequisite")
    provider_step = text.index("Run live provider sentinel smoke")
    assert q10_step < provider_step
    assert "codex_security_deep_scan'] == 'PASS'" in text
    assert "production_promotion_allowed'] is True" in text
    assert "codex_security_report_sha256" in text


def test_q11_bounds_execution_and_checks_both_sentinels() -> None:
    text = workflow_text()
    assert "timeout 180s" in text
    assert "grep -q 'P0-AI-001 PASS'" in text
    assert "grep -q 'CK-NEXUS-P0-SMOKE-PASS'" in text


def test_q11_does_not_persist_raw_provider_output() -> None:
    text = workflow_text()
    assert "cat ../q11-smoke.log" not in text
    assert "credential literal detected in captured smoke output" in text
    assert "raw_provider_output_persisted': False" in text
    upload = text.split("- uses: actions/upload-artifact@v4", maxsplit=1)[1]
    assert "q11-smoke.log" not in upload
    assert "Q11_SMOKE_SUMMARY.json" in upload
