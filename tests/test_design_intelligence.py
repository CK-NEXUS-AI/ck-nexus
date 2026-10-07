from creator_app.agnes.design_intelligence import (
    DesignConstraint,
    DesignEvidence,
    DesignProposal,
    DesignVerdict,
    assess_design,
)


def _evidence() -> tuple[DesignEvidence, ...]:
    return (
        DesignEvidence("ev-req", "requirements", "design-1", "User and system requirements"),
        DesignEvidence("ev-sec", "security", "design-1", "Threat and policy review"),
        DesignEvidence("ev-ver", "verification", "design-1", "Usability and acceptance checks"),
    )


def test_governed_complete_design_passes() -> None:
    proposal = DesignProposal(
        proposal_id="design-1",
        goal="Provide a safe evidence-driven control surface",
        users=("operator", "auditor"),
        functions=("inspect state", "trace evidence"),
        constraints=(DesignConstraint("no direct production mutation", True),),
        evidence=_evidence(),
        alternatives_considered=("dashboard", "zoomable control surface"),
        security_reviewed=True,
        accessibility_reviewed=True,
        implementation_feasible=True,
    )

    result = assess_design(proposal)

    assert result.verdict is DesignVerdict.PASS
    assert result.score == 100
    assert result.missing_evidence == ()
    assert result.invariant_failures == ()


def test_blocking_invariant_fails_closed() -> None:
    proposal = DesignProposal(
        proposal_id="design-2",
        goal="Create a control surface",
        users=("operator",),
        functions=("deploy",),
        constraints=(
            DesignConstraint(
                "production mutation requires approval",
                False,
                "prototype bypasses approval",
            ),
        ),
        evidence=_evidence(),
        alternatives_considered=("safe path", "direct path"),
        security_reviewed=True,
        accessibility_reviewed=True,
        implementation_feasible=True,
    )

    result = assess_design(proposal)

    assert result.verdict is DesignVerdict.BLOCKED
    assert result.invariant_failures


def test_missing_evidence_requires_revision() -> None:
    proposal = DesignProposal(
        proposal_id="design-3",
        goal="Improve operator navigation",
        users=("operator",),
        functions=("navigate",),
        constraints=(DesignConstraint("least privilege", True),),
        evidence=(
            DesignEvidence("ev-req", "requirements", "design-3", "Requirements captured"),
        ),
        alternatives_considered=("tabs", "zoom navigator"),
        security_reviewed=True,
        accessibility_reviewed=True,
        implementation_feasible=True,
    )

    result = assess_design(proposal)

    assert result.verdict is DesignVerdict.NEEDS_REVISION
    assert result.missing_evidence == ("security", "verification")


def test_security_review_is_mandatory() -> None:
    proposal = DesignProposal(
        proposal_id="design-4",
        goal="Improve evidence display",
        users=("auditor",),
        functions=("inspect evidence",),
        evidence=_evidence(),
        alternatives_considered=("table", "graph"),
        security_reviewed=False,
        accessibility_reviewed=True,
        implementation_feasible=True,
    )

    result = assess_design(proposal)

    assert result.verdict is DesignVerdict.BLOCKED
    assert result.principles["governed_design"] is False
