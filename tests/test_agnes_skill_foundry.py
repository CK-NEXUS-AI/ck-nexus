from pathlib import Path
import pytest
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_skill_foundry import FoundryState, SkillFoundry


def foundry(tmp_path:Path)->SkillFoundry:
    return SkillFoundry(AppendOnlyLedger(tmp_path/'foundry.jsonl'))


def candidate(store:SkillFoundry,**kw):
    values=dict(skill_id='demo.skill',version='1.0.0',source_url='https://agentskills.io/demo',checksum='a'*64,license_id='MIT',has_executable_scripts=True,requests_credentials=False,requests_network=False)
    values.update(kw)
    return store.discover(**values)


def test_executable_candidate_starts_quarantined(tmp_path:Path):
    c=candidate(foundry(tmp_path))
    assert c.state is FoundryState.QUARANTINED


def test_full_assessment_requires_human_approval(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s)
    c=s.record_security_scan(c.candidate_id,passed=True,evidence_ref='scan:1')
    c=s.record_sandbox_test(c.candidate_id,passed=True,evidence_ref='sandbox:1')
    c=s.record_benchmark(c.candidate_id,passed=True,evidence_ref='bench:1')
    c=s.record_compatibility(c.candidate_id,passed=True,evidence_ref='compat:1')
    assert c.state is FoundryState.AWAITING_APPROVAL
    with pytest.raises(PermissionError): s.approve(c.candidate_id,approved_by='AGNES',evidence_ref='approval:bad')
    c=s.approve(c.candidate_id,approved_by='human_governor',evidence_ref='approval:1')
    assert c.state is FoundryState.REGISTERABLE


def test_failed_security_scan_rejects_and_cannot_continue(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s)
    c=s.record_security_scan(c.candidate_id,passed=False,evidence_ref='scan:bad',reasons=('secret exposure',))
    assert c.state is FoundryState.REJECTED
    with pytest.raises(RuntimeError): s.record_sandbox_test(c.candidate_id,passed=True,evidence_ref='sandbox:1')


def test_missing_evidence_fails_closed(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s)
    with pytest.raises(ValueError,match='evidence_ref'): s.record_security_scan(c.candidate_id,passed=True,evidence_ref='')


def test_unknown_source_remains_quarantined(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s,source_url='https://unknown.invalid/skill',has_executable_scripts=False)
    assert c.state is FoundryState.QUARANTINED
    assert any('allowlist' in reason for reason in c.reasons)


def test_ledger_is_append_only_and_tamper_evident(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s)
    s.record_security_scan(c.candidate_id,passed=True,evidence_ref='scan:1')
    assert s.ledger.verify().entries==2 and s.ledger.verify().valid


def test_foundry_never_auto_activates(tmp_path:Path):
    s=foundry(tmp_path); c=candidate(s)
    raw=s.ledger.path.read_text(encoding='utf-8')
    assert '"auto_activate": false' in raw
    assert '"auto_install": false' in raw
