from __future__ import annotations

import codecs
import hashlib
import lzma
import math
import re
import stat
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".msi",
    ".bat",
    ".cmd",
    ".com",
    ".scr",
    ".ps1",
    ".vbs",
    ".js",
    ".jar",
    ".apk",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".zip"}


_HEAD_BYTES = 512
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_EXEC_MAGIC = (
    b"MZ",
    b"\x7fELF",
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xca\xfe\xba\xbe",
    b"#!",
)
_TEXT_CONTROLS = frozenset({9, 10, 12, 13})
_ZIP_BASED = {".docx", ".xlsx", ".zip"}
_TEXT_EXTENSIONS = {".csv", ".txt"}


def _read_head(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(_HEAD_BYTES)


def _looks_like_text(head: bytes) -> bool:
    if head.startswith(codecs.BOM_UTF8):
        head = head[len(codecs.BOM_UTF8) :]
    try:
        text = codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
    except UnicodeDecodeError:
        return False
    return all(ord(ch) in _TEXT_CONTROLS or unicodedata.category(ch) != "Cc" for ch in text)


def _sniff_mime(head: bytes) -> str:
    """MIME type from content signature only; never from the filename."""
    if head.startswith(_EXEC_MAGIC):
        return "application/x-executable"
    if head.lstrip(b"\xef\xbb\xbf\r\n\t ").startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(_ZIP_MAGIC):
        return "application/zip"
    if head.startswith(_OLE_MAGIC):
        return "application/x-ole-storage"
    if head.startswith(_PNG_MAGIC):
        return "image/png"
    if head.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if _looks_like_text(head):
        return "text/plain"
    return "application/octet-stream"


def _file_is_utf8_text(path: Path) -> bool:
    """Stream the whole file: valid UTF-8 (finalized at EOF), no control chars."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    first = True
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            if first and chunk.startswith(codecs.BOM_UTF8):
                chunk = chunk[len(codecs.BOM_UTF8) :]
            first = False
            try:
                text = decoder.decode(chunk, final=False)
            except UnicodeDecodeError:
                return False
            if any(
                ord(ch) not in _TEXT_CONTROLS and unicodedata.category(ch) == "Cc"
                for ch in text
            ):
                return False
    try:
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def _content_matches_extension(extension: str, head: bytes) -> bool:
    sniffed = _sniff_mime(head)
    if extension == ".pdf":
        return sniffed == "application/pdf"
    if extension in _ZIP_BASED:
        return sniffed == "application/zip"
    if extension == ".png":
        return sniffed == "image/png"
    if extension in {".jpg", ".jpeg"}:
        return sniffed == "image/jpeg"
    if extension in _TEXT_EXTENSIONS:
        return sniffed == "text/plain"
    return False


@dataclass(frozen=True, slots=True)
class AttachmentScanResult:
    safe: bool
    status: str
    reason: str
    sha256: str
    size_bytes: int
    extension: str
    detected_mime: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_policy(
    path: Path, *, max_entries: int, max_uncompressed_bytes: int, max_ratio: float
) -> tuple[bool, str]:
    """Validate ZIP containers without extracting members to the filesystem.

    The same bounded policy is applied to ordinary ZIP files and OOXML files
    (DOCX/XLSX). Member contents are streamed to validate CRC/decompression
    behavior while enforcing the declared and observed output budgets.
    Nested ZIP payloads are rejected to avoid unbounded recursive containers.
    """
    if max_entries < 0 or max_uncompressed_bytes < 0:
        return False, "zip_invalid_policy_limit"
    if not math.isfinite(max_ratio) or max_ratio <= 0:
        return False, "zip_invalid_policy_limit"

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > max_entries:
                return False, "zip_too_many_entries"

            total_compressed = 0
            total_uncompressed = 0
            seen_names: set[str] = set()
            for info in infos:
                filename = info.filename
                normalized = filename.replace("\\", "/")
                parts = normalized.split("/")
                if (
                    not filename
                    or "\x00" in filename
                    or filename.startswith(("/", "\\"))
                    or re.match(r"^[A-Za-z]:", filename)
                    or ".." in parts
                    or "." in parts
                    or "\\" in filename
                ):
                    return False, "zip_path_traversal"

                name_key = normalized.rstrip("/").casefold()
                if name_key in seen_names:
                    return False, "zip_duplicate_entry"
                seen_names.add(name_key)

                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    return False, "zip_symlink_entry"
                if info.flag_bits & 0x41:
                    return False, "zip_encrypted_entry"
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    return False, "zip_unsupported_compression"
                if info.file_size < 0 or info.compress_size < 0:
                    return False, "invalid_zip"

                total_compressed += info.compress_size
                total_uncompressed += info.file_size
                if total_uncompressed > max_uncompressed_bytes:
                    return False, "zip_uncompressed_limit"
                if info.file_size / max(1, info.compress_size) > max_ratio:
                    return False, "zip_compression_ratio"

            if total_uncompressed / max(1, total_compressed) > max_ratio:
                return False, "zip_compression_ratio"

            observed_uncompressed = 0
            for info in infos:
                if info.is_dir():
                    continue
                member_bytes = 0
                with archive.open(info, "r") as member:
                    first = member.read(4)
                    member_bytes += len(first)
                    observed_uncompressed += len(first)
                    if first.startswith(_ZIP_MAGIC):
                        return False, "zip_nested_archive"
                    while chunk := member.read(64 * 1024):
                        member_bytes += len(chunk)
                        observed_uncompressed += len(chunk)
                        if observed_uncompressed > max_uncompressed_bytes:
                            return False, "zip_uncompressed_limit"
                if member_bytes != info.file_size:
                    return False, "invalid_zip"
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        zlib.error,
        lzma.LZMAError,
    ):
        return False, "invalid_zip"
    return True, "zip_safe"


def scan_attachment(
    path: Path,
    *,
    max_size_bytes: int = 25 * 1024 * 1024,
    max_zip_entries: int = 250,
    max_zip_uncompressed_bytes: int = 100 * 1024 * 1024,
    max_zip_ratio: float = 100.0,
) -> AttachmentScanResult:
    path = Path(path)
    size = path.stat().st_size
    extension = path.suffix.casefold()
    digest = _sha256(path)
    head = _read_head(path)
    detected = _sniff_mime(head)

    if extension in BLOCKED_EXTENSIONS:
        return AttachmentScanResult(
            False, "QUARANTINE", "blocked_extension", digest, size, extension, detected
        )
    if extension not in ALLOWED_EXTENSIONS:
        return AttachmentScanResult(
            False, "QUARANTINE", "extension_not_allowlisted", digest, size, extension, detected
        )
    if size > max_size_bytes:
        return AttachmentScanResult(
            False, "QUARANTINE", "file_too_large", digest, size, extension, detected
        )
    if head.startswith(_EXEC_MAGIC):
        return AttachmentScanResult(
            False, "QUARANTINE", "executable_signature", digest, size, extension, detected
        )
    if extension in _TEXT_EXTENSIONS and not _file_is_utf8_text(path):
        return AttachmentScanResult(
            False, "QUARANTINE", "content_signature_mismatch", digest, size, extension, detected
        )
    if not _content_matches_extension(extension, head):
        return AttachmentScanResult(
            False, "QUARANTINE", "content_signature_mismatch", digest, size, extension, detected
        )
    if extension in _ZIP_BASED:
        safe, reason = _zip_policy(
            path,
            max_entries=max_zip_entries,
            max_uncompressed_bytes=max_zip_uncompressed_bytes,
            max_ratio=max_zip_ratio,
        )
        if not safe:
            return AttachmentScanResult(
                False, "QUARANTINE", reason, digest, size, extension, detected
            )
    return AttachmentScanResult(True, "CLEAN", "allowlisted", digest, size, extension, detected)
