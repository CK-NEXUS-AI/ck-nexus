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


_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_EXEC_MAGIC = (b"MZ", b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe",
               b"\xca\xfe\xba\xbe", b"#!")
_TEXT_SUFFIXES = frozenset({".csv", ".json", ".md", ".txt"})


def _content_matches_suffix(suffix: str, head: bytes) -> bool:
    if head.startswith(_EXEC_MAGIC):
        return False
    if suffix == ".pdf":
        return head.lstrip(b"\xef\xbb\xbf\r\n\t ")[:5] == b"%PDF-"
    if suffix in {".docx", ".pptx", ".xlsx"}:
        return head.startswith(_ZIP_MAGIC)
    if suffix in _TEXT_SUFFIXES:
        return not (
            head.startswith(_ZIP_MAGIC) or head.startswith(_OLE_MAGIC) or b"\x00" in head
        )
    return False


def evaluate_attachment(
    filename: str, *, size_bytes: int, head: bytes | None = None
) -> AttachmentDecision:
    if not filename or "\x00" in filename or "/" in filename or "\\" in filename:
        return AttachmentDecision(filename, False, "unsafe_filename")
    name = PurePosixPath(filename).name
    if not name or name in {".", ".."} or name != filename:
        return AttachmentDecision(filename, False, "unsafe_filename")
    if size_bytes < 0 or size_bytes > 25 * 1024 * 1024:
        return AttachmentDecision(filename, False, "size_limit_exceeded")
    suffix = PurePosixPath(name).suffix.casefold()
    if suffix in _BLOCKED_SUFFIXES:
        return AttachmentDecision(filename, False, "executable_or_script_blocked")
    if suffix not in _ALLOWED_DOCUMENT_SUFFIXES:
        return AttachmentDecision(filename, False, "unsupported_type")
    if head is not None and not _content_matches_suffix(suffix, bytes(head[:16])):
        return AttachmentDecision(filename, False, "content_signature_mismatch")
    return AttachmentDecision(filename, True, "quarantine_then_parser_sandbox")
