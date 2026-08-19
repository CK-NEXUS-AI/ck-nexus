"""Data-governance contracts for retention, purpose limitation and deletion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from creator_app.privacy_firewall import DataClassification


class StorageMode(StrEnum):
    EPHEMERAL = "ephemeral"
    ENCRYPTED_DURABLE = "encrypted_durable"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True, slots=True)
class DataPolicy:
    classification: DataClassification
    allowed_purposes: frozenset[str]
    retention: timedelta
    storage: StorageMode
    external_sharing: bool
    consent_required: bool
    deletion_supported: bool = True

    def __post_init__(self) -> None:
        if self.retention.total_seconds() < 0:
            raise ValueError("retention must not be negative")
        if not self.allowed_purposes:
            raise ValueError("allowed_purposes must not be empty")
        if self.classification in {DataClassification.SECRET, DataClassification.REGULATED}:
            if self.external_sharing:
                raise ValueError("secret/regulated data cannot enable unrestricted sharing")


DEFAULT_DATA_POLICIES: dict[DataClassification, DataPolicy] = {
    DataClassification.PUBLIC: DataPolicy(
        DataClassification.PUBLIC,
        frozenset({"user_request", "research", "content_generation"}),
        timedelta(days=90),
        StorageMode.ENCRYPTED_DURABLE,
        True,
        False,
    ),
    DataClassification.INTERNAL: DataPolicy(
        DataClassification.INTERNAL,
        frozenset({"user_request", "operation"}),
        timedelta(days=30),
        StorageMode.ENCRYPTED_DURABLE,
        False,
        False,
    ),
    DataClassification.PERSONAL: DataPolicy(
        DataClassification.PERSONAL,
        frozenset({"user_request", "personalization"}),
        timedelta(days=30),
        StorageMode.ENCRYPTED_DURABLE,
        False,
        True,
    ),
    DataClassification.SENSITIVE: DataPolicy(
        DataClassification.SENSITIVE,
        frozenset({"user_request"}),
        timedelta(days=1),
        StorageMode.EPHEMERAL,
        False,
        True,
    ),
    DataClassification.SECRET: DataPolicy(
        DataClassification.SECRET,
        frozenset({"credential_execution"}),
        timedelta(),
        StorageMode.FORBIDDEN,
        False,
        True,
    ),
    DataClassification.REGULATED: DataPolicy(
        DataClassification.REGULATED,
        frozenset({"explicit_regulated_workflow"}),
        timedelta(),
        StorageMode.EPHEMERAL,
        False,
        True,
    ),
}


def require_purpose(classification: DataClassification, purpose: str) -> DataPolicy:
    policy = DEFAULT_DATA_POLICIES[classification]
    if purpose not in policy.allowed_purposes:
        raise PermissionError("purpose is not allowed for data classification")
    return policy
