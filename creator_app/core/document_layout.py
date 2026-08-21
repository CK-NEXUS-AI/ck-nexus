from __future__ import annotations

from enum import StrEnum
import re

from pydantic import BaseModel, Field


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DocumentBlockType(StrEnum):
    TEXT = "text"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    EQUATION = "equation"
    SIGNATURE = "signature"
    IMAGE = "image"


class BoundingBox(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    def valid(self) -> bool:
        return self.x1 > self.x0 and self.y1 > self.y0


class DocumentBlock(BaseModel):
    block_id: str = Field(min_length=1, max_length=128)
    page: int = Field(ge=1)
    block_type: DocumentBlockType
    content_digest: str
    bounding_box: BoundingBox
    confidence: float = Field(ge=0, le=1)
    evidence_ids: tuple[str, ...] = ()


class LayoutExtractorReceipt(BaseModel):
    extractor_id: str = Field(min_length=1, max_length=128)
    extractor_version: str = Field(min_length=1, max_length=128)
    source_sha256: str
    result_sha256: str
    network_used: bool = False
    external_processing_approval_id: str | None = None
    evidence_ids: tuple[str, ...] = ()


class DocumentLayoutResult(BaseModel):
    document_id: str
    source_sha256: str
    blocks: tuple[DocumentBlock, ...]
    extractor_receipt: LayoutExtractorReceipt
    raw_text_persisted: bool = False


class DocumentLayoutPolicy(BaseModel):
    minimum_confidence: float = Field(default=0.65, ge=0, le=1)

    def ready_for_agent_action(self, result: DocumentLayoutResult) -> bool:
        receipt = result.extractor_receipt
        if not _SHA256.fullmatch(result.source_sha256):
            return False
        if receipt.source_sha256 != result.source_sha256:
            return False
        if not _SHA256.fullmatch(receipt.result_sha256):
            return False
        if receipt.extractor_version.strip().lower() in {"latest", "main", "head"}:
            return False
        if not receipt.evidence_ids or result.raw_text_persisted:
            return False
        if receipt.network_used and not receipt.external_processing_approval_id:
            return False
        if not result.blocks:
            return False
        block_ids = [block.block_id for block in result.blocks]
        if len(block_ids) != len(set(block_ids)):
            return False
        for block in result.blocks:
            if not _SHA256.fullmatch(block.content_digest):
                return False
            if not block.bounding_box.valid():
                return False
            if block.confidence < self.minimum_confidence or not block.evidence_ids:
                return False
        return True
