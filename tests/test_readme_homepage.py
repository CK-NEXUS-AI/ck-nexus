from pathlib import Path


def test_readme_presents_one_canonical_ck_nexus_product() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert readme.startswith("# CK-NEXUS\n")
    assert "Governed Autonomous AI Operating System" in readme
    assert "CK-NEXUS is one platform with one canonical application runtime" in readme
    assert "Agnes" in readme
    assert "Creator Workspace" in readme
    assert "**/development** is an internal evidence dashboard" in readme
    assert "production_status = NO-GO" in readme


def test_readme_does_not_present_engineering_phases_as_product_sections() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    headings = [line for line in readme.splitlines() if line.startswith("#")]
    forbidden_headings = (
        "Creator Edition",
        "R7 Credential Broker",
        "R9–R11 Canonical Implementation",
        "AGNES Execution Kernel Phase",
        "System Development Dashboard",
    )
    assert not any(any(label in heading for label in forbidden_headings) for heading in headings)


def test_readme_points_to_authoritative_status_and_runtime_documents() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    for path in (
        "RELEASE_STATUS.md",
        "docs/Q10_Q16_CLOSURE_CONTRACT.md",
        "docs/CK_NEXUS_UNIFIED_OPERATIONS_CONTRACT_V1.md",
        "docs/INTEGRATION_HUB.md",
        "docs/DEVELOPMENT_COUNCIL.md",
        "docs/RELEASE_CHECKLIST.md",
    ):
        assert path in readme
    assert "python3 -m creator_app.unified" in readme
