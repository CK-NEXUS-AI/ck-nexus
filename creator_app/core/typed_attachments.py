from __future__ import annotations

from enum import StrEnum
import re

from pydantic import BaseModel, Field


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AttachmentModality(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class AttachmentTrust(StrEnum):
    QUARANTINED = "quarantined"
    VERIFIED = "verified"


class AttachmentSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"


class TypedAttachment(BaseModel):
    attachment_id: str = Field(min_length=1, max_length=128)
    modality: AttachmentModality
    mime_type: str = Field(min_length=1, max_length=128)
    sha256: str
    size_bytes: int = Field(ge=0, le=256 * 1024 * 1024)
    trust: AttachmentTrust = AttachmentTrust.QUARANTINED
    sensitivity: AttachmentSensitivity = AttachmentSensitivity.INTERNAL
    executable: bool = False
    source_evidence_ids: tuple[str, ...] = ()
    external_processing_requested: bool = False
    external_processing_approval_id: str | None = None


class AttachmentPolicy:
    _PREFIXES = {
        AttachmentModality.IMAGE: ("image/",),
        AttachmentModality.AUDIO: ("audio/",),
        AttachmentModality.VIDEO: ("video/",),
        AttachmentModality.DOCUMENT: (
            "application/pdf",
            "application/json",
            "text/",
            "application/vnd.openxmlformats-officedocument",
        ),
    }

    @classmethod
    def accepted(cls, attachment: TypedAttachment) -> bool:
        if not _SHA256.fullmatch(attachment.sha256):
            return False
        if attachment.executable or not attachment.source_evidence_ids:
            return False
        if not attachment.mime_type.startswith(cls._PREFIXES[attachment.modality]):
            return False
        if (
            attachment.external_processing_requested
            and attachment.sensitivity
            in {AttachmentSensitivity.PERSONAL, AttachmentSensitivity.SENSITIVE}
            and not attachment.external_processing_approval_id
        ):
            return False
        return True

    @staticmethod
    def eligible_for_agent_context(attachment: TypedAttachment) -> bool:
        return (
            AttachmentPolicy.accepted(attachment)
            and attachment.trust == AttachmentTrust.VERIFIED
        )
