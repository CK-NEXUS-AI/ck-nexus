"""Attachment quarantine decisions for untrusted Gmail content."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True, slots=True)
class AttachmentDecision:
    filename: str
    allowed_for_parser_sandbox: bool
    reason: str
    quarantine_required: bool = True
    execute_on_host: bool = False
    sha256: str | None = None
    detected_type: str | None = None
    declared_mime: str | None = None


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
_EXPECTED_MIME = {
    ".csv": frozenset({"text/csv", "text/plain"}),
    ".docx": frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ),
    ".json": frozenset({"application/json", "text/json"}),
    ".md": frozenset({"text/markdown", "text/plain"}),
    ".pdf": frozenset({"application/pdf"}),
    ".pptx": frozenset(
        {"application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    ),
    ".txt": frozenset({"text/plain"}),
    ".xlsx": frozenset(
        {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    ),
}
_OOXML_MAIN_PART = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}
_ARCHIVE_SUFFIXES = frozenset(
    {".7z", ".apk", ".bz2", ".gz", ".jar", ".rar", ".tar", ".tgz", ".xz", ".zip"}
)
_DANGEROUS_ARCHIVE_SUFFIXES = _ARCHIVE_SUFFIXES | _BLOCKED_SUFFIXES
_DANGEROUS_PREFIXES = (
    b"MZ",
    b"\x7fELF",
    b"#!",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
)
_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 1024
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
_MAX_ARCHIVE_ENTRY_BYTES = 32 * 1024 * 1024
_MAX_EXPANSION_RATIO = 100


def _reject(
    filename: str,
    reason: str,
    *,
    digest: str | None = None,
    detected_type: str | None = None,
    declared_mime: str | None = None,
) -> AttachmentDecision:
    return AttachmentDecision(
        filename,
        False,
        reason,
        sha256=digest,
        detected_type=detected_type,
        declared_mime=declared_mime,
    )


def _normalized_mime(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.split(";", 1)[0].strip().casefold()
    return candidate or None


def _unsafe_member_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name:
        return True
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return True
    return bool(path.parts and ":" in path.parts[0])


def _validate_ooxml(content: bytes, suffix: str) -> tuple[bool, str]:
    if not content.startswith(b"PK\x03\x04"):
        return False, "ooxml_magic_mismatch"
    try:
        with zipfile.ZipFile(io.BytesIO(content), mode="r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > _MAX_ARCHIVE_ENTRIES:
                return False, "archive_entry_limit"

            normalized_names: set[str] = set()
            total_uncompressed = 0
            total_compressed = 0
            for info in infos:
                name = info.filename
                if _unsafe_member_name(name):
                    return False, "archive_unsafe_path"
                folded = name.casefold()
                if folded in normalized_names:
                    return False, "archive_duplicate_entry"
                normalized_names.add(folded)
                if info.flag_bits & 0x1:
                    return False, "archive_encrypted_entry"
                if info.is_dir():
                    continue

                member_suffix = PurePosixPath(name).suffix.casefold()
                if member_suffix in _DANGEROUS_ARCHIVE_SUFFIXES:
                    return False, "archive_nested_or_executable_content"
                if "vbaproject.bin" in folded or folded.endswith(".bin"):
                    return False, "archive_macro_or_binary_part"

                if info.file_size < 0 or info.compress_size < 0:
                    return False, "archive_invalid_size"
                if info.file_size > _MAX_ARCHIVE_ENTRY_BYTES:
                    return False, "archive_entry_too_large"
                total_uncompressed += info.file_size
                total_compressed += info.compress_size
                if total_uncompressed > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    return False, "archive_uncompressed_size_limit"
                if info.file_size:
                    denominator = max(info.compress_size, 1)
                    if info.file_size / denominator > _MAX_EXPANSION_RATIO:
                        return False, "archive_expansion_ratio_limit"

            if total_uncompressed > max(total_compressed, 1) * _MAX_EXPANSION_RATIO:
                return False, "archive_total_expansion_ratio_limit"
            if "[content_types].xml" not in normalized_names:
                return False, "ooxml_missing_content_types"
            required_part = _OOXML_MAIN_PART[suffix]
            if required_part.casefold() not in normalized_names:
                return False, "ooxml_missing_main_part"
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        return False, "malformed_ooxml_archive"
    return True, "ooxml"


def _validate_pdf(content: bytes) -> tuple[bool, str]:
    if not content.startswith(b"%PDF-"):
        return False, "pdf_magic_mismatch"
    tail = content[-2048:]
    if b"%%EOF" not in tail:
        return False, "pdf_missing_eof"
    if b"PK\x05\x06" in content or b"PK\x03\x04" in content:
        return False, "polyglot_signature_detected"
    return True, "pdf"


def _validate_text(content: bytes, suffix: str) -> tuple[bool, str]:
    if any(content.startswith(prefix) for prefix in _DANGEROUS_PREFIXES):
        return False, "dangerous_magic_detected"
    if content.startswith((b"PK\x03\x04", b"%PDF-")) or b"\x00" in content:
        return False, "binary_content_mismatch"
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "text_utf8_required"
    if suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError:
            return False, "malformed_json"
        return True, "json"
    return True, "text"


def evaluate_attachment(
    filename: str,
    *,
    size_bytes: int,
    declared_mime: str | None = None,
    content: bytes | None = None,
) -> AttachmentDecision:
    """Return parser-sandbox eligibility for an attachment.

    Eligibility is fail-closed and requires the exact bytes plus the declared MIME.
    The returned SHA-256 is the parser/quarantine identity and must be checked again
    before parsing with ``verify_attachment_digest``.
    """

    mime = _normalized_mime(declared_mime)
    if not filename or "\x00" in filename or "/" in filename or "\\" in filename:
        return _reject(filename, "unsafe_filename", declared_mime=mime)
    name = PurePosixPath(filename).name
    if not name or name in {".", ".."} or name != filename:
        return _reject(filename, "unsafe_filename", declared_mime=mime)
    if size_bytes < 0 or size_bytes > _MAX_ATTACHMENT_BYTES:
        return _reject(filename, "size_limit_exceeded", declared_mime=mime)

    suffix = PurePosixPath(name).suffix.casefold()
    if suffix in _BLOCKED_SUFFIXES:
        return _reject(filename, "executable_or_script_blocked", declared_mime=mime)
    if suffix not in _ALLOWED_DOCUMENT_SUFFIXES:
        return _reject(filename, "unsupported_type", declared_mime=mime)
    if content is None:
        return _reject(filename, "content_validation_required", declared_mime=mime)

    digest = hashlib.sha256(content).hexdigest()
    if len(content) != size_bytes:
        return _reject(filename, "size_mismatch", digest=digest, declared_mime=mime)
    if mime is None:
        return _reject(filename, "declared_mime_required", digest=digest)
    if mime not in _EXPECTED_MIME[suffix]:
        return _reject(filename, "declared_mime_mismatch", digest=digest, declared_mime=mime)
    if any(content.startswith(prefix) for prefix in _DANGEROUS_PREFIXES):
        return _reject(
            filename,
            "dangerous_magic_detected",
            digest=digest,
            detected_type="executable_or_script",
            declared_mime=mime,
        )

    if suffix in _OOXML_MAIN_PART:
        valid, detected = _validate_ooxml(content, suffix)
    elif suffix == ".pdf":
        valid, detected = _validate_pdf(content)
    else:
        valid, detected = _validate_text(content, suffix)
    if not valid:
        return _reject(
            filename,
            detected,
            digest=digest,
            detected_type=detected,
            declared_mime=mime,
        )

    return AttachmentDecision(
        filename,
        True,
        "content_verified_quarantine_then_parser_sandbox",
        sha256=digest,
        detected_type=detected,
        declared_mime=mime,
    )


def verify_attachment_digest(content: bytes, expected_sha256: str) -> bool:
    """Verify that parser bytes exactly match the digest approved before quarantine."""

    candidate = expected_sha256.strip().casefold()
    if len(candidate) != 64 or any(ch not in "0123456789abcdef" for ch in candidate):
        return False
    actual = hashlib.sha256(content).hexdigest()
    return hmac.compare_digest(actual, candidate)
