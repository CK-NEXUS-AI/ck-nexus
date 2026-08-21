# CK-NEXUS Gen 6.5 — UI + Multimodal V1

Status: Post-P0 development only. Not production evidence.

## Purpose

Add a typed presentation/perception layer without creating a second execution authority. Gen 6.5 reuses the Gen 6.1 Computer Use and realtime multimodal contracts and keeps CK-NEXUS Governor/Policy as the only authority for mutation.

## Contracts

- `ag_ui_contract.py`: typed state/events/components and live steering. Commands request changes; visible state changes only after events.
- `typed_attachments.py`: digest-bound image/audio/video/document envelopes with quarantine, sensitivity and external-processing approval.
- `document_layout.py`: page/block/bounding-box/confidence evidence with pinned extractor identity and no raw-text persistence by default.
- `media_provenance.py`: provenance verification receipts that never infer authenticity from an absent/unverified marker.
- `ui_surface_binding.py`: binds browser/desktop/mobile and realtime modalities to the existing governed Gen 6.1 contracts.

## Security invariants

- no arbitrary HTML, JavaScript, script execution or model-provided renderer code
- interactive components are limited to typed form/approval surfaces
- unverified/quarantined attachments cannot enter agent context
- personal/sensitive external processing requires explicit approval
- UI surfaces require screenshot prompt-injection evidence
- provider/verifier versions must be pinned where evidence depends on them
- production mutation remains disabled

## Production boundary

No provider calls, OCR invocation, media-verifier invocation, browser/desktop/mobile execution or production deployment is introduced by these contracts. No PR #14 change and no Q10/Q11/Q12 promotion. Production remains NO-GO.
