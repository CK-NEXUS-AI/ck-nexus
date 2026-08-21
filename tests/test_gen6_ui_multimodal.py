from creator_app.core.ag_ui_contract import (
    AGUIContract,
    GenerativeUIComponent,
    SteeringAction,
    SteeringCommand,
    UIComponentKind,
    UIEvent,
    UIEventType,
)
from creator_app.core.computer_use_contract import ComputerEnvironment
from creator_app.core.document_layout import (
    BoundingBox,
    DocumentBlock,
    DocumentBlockType,
    DocumentLayoutPolicy,
    DocumentLayoutResult,
    LayoutExtractorReceipt,
)
from creator_app.core.media_provenance import (
    MediaProvenancePolicy,
    MediaProvenanceReceipt,
    ProvenanceMechanism,
    ProvenanceStatus,
)
from creator_app.core.realtime_multimodal import RealtimeModality, RealtimeSession
from creator_app.core.typed_attachments import (
    AttachmentModality,
    AttachmentPolicy,
    AttachmentSensitivity,
    AttachmentTrust,
    TypedAttachment,
)
from creator_app.core.ui_surface_binding import UISurfaceBinding, UISurfaceBindingPolicy


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def test_ag_ui_stream_requires_typed_evidenced_state_events() -> None:
    component = GenerativeUIComponent(
        component_id="progress-1",
        kind=UIComponentKind.PROGRESS,
        data_digest=DIGEST_A,
        evidence_ids=("evd-ui",),
    )
    events = [
        UIEvent(
            event_id="evt-1",
            event_type=UIEventType.RUN_STARTED,
            task_id="task-1",
            run_id="run-1",
            sequence=1,
            evidence_ids=("evd-start",),
        ),
        UIEvent(
            event_id="evt-2",
            event_type=UIEventType.STATE_SNAPSHOT,
            task_id="task-1",
            run_id="run-1",
            sequence=2,
            state_digest=DIGEST_A,
            component=component,
            evidence_ids=("evd-state",),
        ),
        UIEvent(
            event_id="evt-3",
            event_type=UIEventType.STATE_DELTA,
            task_id="task-1",
            run_id="run-1",
            sequence=3,
            state_digest=DIGEST_B,
            previous_state_digest=DIGEST_A,
            evidence_ids=("evd-delta",),
        ),
    ]
    assert AGUIContract.validate_event_stream(events)


def test_ag_ui_rejects_untyped_or_unapproved_steering_effects() -> None:
    component = GenerativeUIComponent(
        component_id="bad",
        kind=UIComponentKind.CHART,
        data_digest=DIGEST_A,
        interactive=True,
        evidence_ids=("evd-ui",),
    )
    assert not AGUIContract.component_allowed(component)

    cancel = SteeringCommand(
        command_id="cmd-1",
        run_id="run-1",
        action=SteeringAction.CANCEL,
    )
    assert not AGUIContract.steering_allowed(cancel)
    assert AGUIContract.steering_allowed(
        cancel.model_copy(update={"governor_approval_id": "approval-1"})
    )


def test_sensitive_external_attachment_requires_approval_and_verification() -> None:
    attachment = TypedAttachment(
        attachment_id="att-1",
        modality=AttachmentModality.IMAGE,
        mime_type="image/png",
        sha256=DIGEST_A,
        size_bytes=1024,
        trust=AttachmentTrust.VERIFIED,
        sensitivity=AttachmentSensitivity.SENSITIVE,
        source_evidence_ids=("evd-att",),
        external_processing_requested=True,
    )
    assert not AttachmentPolicy.accepted(attachment)
    approved = attachment.model_copy(
        update={"external_processing_approval_id": "approval-1"}
    )
    assert AttachmentPolicy.eligible_for_agent_context(approved)


def test_quarantined_attachment_never_enters_agent_context() -> None:
    attachment = TypedAttachment(
        attachment_id="att-1",
        modality=AttachmentModality.DOCUMENT,
        mime_type="application/pdf",
        sha256=DIGEST_A,
        size_bytes=1024,
        source_evidence_ids=("evd-att",),
    )
    assert AttachmentPolicy.accepted(attachment)
    assert not AttachmentPolicy.eligible_for_agent_context(attachment)


def _layout_result(*, version: str = "4.0.0", confidence: float = 0.95) -> DocumentLayoutResult:
    block = DocumentBlock(
        block_id="block-1",
        page=1,
        block_type=DocumentBlockType.TABLE,
        content_digest=DIGEST_B,
        bounding_box=BoundingBox(x0=0.1, y0=0.2, x1=0.8, y1=0.7),
        confidence=confidence,
        evidence_ids=("evd-block",),
    )
    receipt = LayoutExtractorReceipt(
        extractor_id="local-layout-adapter",
        extractor_version=version,
        source_sha256=DIGEST_A,
        result_sha256=DIGEST_B,
        evidence_ids=("evd-layout",),
    )
    return DocumentLayoutResult(
        document_id="doc-1",
        source_sha256=DIGEST_A,
        blocks=(block,),
        extractor_receipt=receipt,
    )


def test_document_layout_requires_pinned_version_confidence_and_evidence() -> None:
    policy = DocumentLayoutPolicy()
    assert policy.ready_for_agent_action(_layout_result())
    assert not policy.ready_for_agent_action(_layout_result(version="latest"))
    assert not policy.ready_for_agent_action(_layout_result(confidence=0.2))


def test_media_provenance_does_not_treat_unverified_marker_as_authentic() -> None:
    unverified = MediaProvenanceReceipt(
        media_sha256=DIGEST_A,
        mechanism=ProvenanceMechanism.C2PA,
        verifier_id="c2pa-verifier",
        verifier_version="1.2.0",
        status=ProvenanceStatus.UNVERIFIED,
        evidence_ids=("evd-media",),
    )
    assert not MediaProvenancePolicy.evaluate(unverified).verified

    verified = unverified.model_copy(
        update={
            "status": ProvenanceStatus.VERIFIED,
            "signer_digest": DIGEST_B,
        }
    )
    decision = MediaProvenancePolicy.evaluate(verified)
    assert decision.verified
    assert not decision.production_activation_allowed


def test_ui_surface_reuses_existing_computer_and_realtime_authority() -> None:
    session = RealtimeSession(
        session_id="rt-1",
        provider="provider-a",
        model="model-a",
        input_modalities={RealtimeModality.AUDIO, RealtimeModality.VIDEO},
        output_modalities={RealtimeModality.AUDIO},
        evidence_ids=["evd-rt"],
    )
    binding = UISurfaceBinding(
        binding_id="bind-1",
        environment=ComputerEnvironment.DESKTOP,
        task_id="task-1",
        run_id="run-1",
        screen_digest=DIGEST_A,
        realtime_session_id="rt-1",
        requested_modalities={RealtimeModality.AUDIO, RealtimeModality.VIDEO},
        prompt_injection_evidence_ids=("evd-screen-scan",),
        evidence_ids=("evd-binding",),
    )
    assert UISurfaceBindingPolicy.bindable(binding, realtime_session=session)
    assert not UISurfaceBindingPolicy.bindable(
        binding.model_copy(update={"prompt_injection_evidence_ids": ()}),
        realtime_session=session,
    )
