"""Prompt library and generated-asset metadata contracts for AGNES.

The library stores metadata and content-addressed references. Raw provider
credentials are never part of these records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssetKind(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    DATA = "data"
    CODE = "code"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    prompt_id: str
    name: str
    template: str
    tags: tuple[str, ...] = ()
    input_schema_ref: str | None = None
    owner_scope: str = "workspace"
    version: str = "1"

    def __post_init__(self) -> None:
        if not self.prompt_id.strip() or not self.name.strip() or not self.template.strip():
            raise ValueError("prompt_id, name and template must not be empty")


@dataclass(frozen=True, slots=True)
class AssetRecord:
    asset_id: str
    kind: AssetKind
    content_digest: str
    media_type: str
    size_bytes: int
    created_by_run_id: str
    provider_id: str | None = None
    model_id: str | None = None
    parent_asset_ids: tuple[str, ...] = ()
    evidence_digest: str | None = None
    retention_class: str = "workspace"

    def __post_init__(self) -> None:
        if not self.asset_id.strip() or not self.content_digest.strip():
            raise ValueError("asset_id and content_digest must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")
