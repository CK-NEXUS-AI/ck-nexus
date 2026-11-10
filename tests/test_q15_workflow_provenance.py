from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "candidate-automated-gates.yml"
)


def test_q15_binds_q16_artifact_to_exact_workflow_path_and_candidate_sha():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'gh api "repos/$GITHUB_REPOSITORY/actions/runs/$Q16_RUN_ID"' in text
    assert "run['head_sha']==sys.argv[2]" in text
    assert "run['event']=='workflow_dispatch'" in text
    assert "run['path']=='.github/workflows/candidate-production-image.yml'" in text
