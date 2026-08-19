"""Attachment quarantine decisions for untrusted Gmail content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True, slots=True)
class AttachmentDecision:
    filename: str
    allowed_for_parser_sandbox: bool
    reason: str
    quarantine_required: bool = True
    execute_on_host: bool = False


_BLOCKED_SUFFIXES = frozenset(
    {
        ".apk",
        ".bat",
        ".cmd",
        ".com",
        ".dll",
        ".dmg",
        ".exe",
        ".jar",
        ".js",
        ".msi",
        ".ps1",
        ".scr",
        ".sh",
    }
)
_ALLOWED_DOCUMENT_SUFFIXES = frozenset(
    {".csv", ".docx", ".json", ".md", ".pdf", ".pptx", ".txt", ".xlsx"}
)


def evaluate_attachment(filename: str, *, size_bytes: int) -> AttachmentDecision:
    name = PurePosixPath(filename).name
    if not name or name != filename.replace("\\", "/").split("/")[-1]:
        return AttachmentDecision(filename, False, "unsafe_filename")
    if size_bytes < 0 or size_bytes > 25 * 1024 * 1024:
        return AttachmentDecision(filename, False, "size_limit_exceeded")
    suffix = PurePosixPath(name).suffix.casefold()
    if suffix in _BLOCKED_SUFFIXES:
        return AttachmentDecision(filename, False, "executable_or_script_blocked")
    if suffix not in _ALLOWED_DOCUMENT_SUFFIXES:
        return AttachmentDecision(filename, False, "unsupported_type")
    return AttachmentDecision(filename, True, "quarantine_then_parser_sandbox")
