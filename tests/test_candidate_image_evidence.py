from pathlib import Path


def test_candidate_image_evidence_never_authorizes_production_promotion():
    workflow = Path(".github/workflows/candidate-production-image.yml").read_text(
        encoding="utf-8"
    )
    assert "'production_promotion_allowed':False" in workflow
    enforced = (
        "x['result']=='PASS_CANDIDATE' and "
        "x['production_promotion_allowed'] is False"
    )
    assert enforced in workflow
