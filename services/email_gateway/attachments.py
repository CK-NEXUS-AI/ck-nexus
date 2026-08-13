from __future__ import annotations

import hashlib
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path

BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".msi", ".bat", ".cmd", ".com", ".scr", ".ps1", ".vbs", ".js", ".jar", ".apk"
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".zip"}


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


def _zip_policy(path: Path, *, max_entries: int, max_uncompressed_bytes: int, max_ratio: float) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > max_entries:
                return False, "zip_too_many_entries"
            total_compressed = 0
            total_uncompressed = 0
            for info in infos:
                name = Path(info.filename)
                if name.is_absolute() or ".." in name.parts:
                    return False, "zip_path_traversal"
                total_compressed += max(1, info.compress_size)
                total_uncompressed += info.file_size
                if total_uncompressed > max_uncompressed_bytes:
                    return False, "zip_uncompressed_limit"
            if total_uncompressed / max(1, total_compressed) > max_ratio:
                return False, "zip_compression_ratio"
    except zipfile.BadZipFile:
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
    mime, _ = mimetypes.guess_type(path.name)
    detected = mime or "application/octet-stream"

    if extension in BLOCKED_EXTENSIONS:
        return AttachmentScanResult(False, "QUARANTINE", "blocked_extension", digest, size, extension, detected)
    if extension not in ALLOWED_EXTENSIONS:
        return AttachmentScanResult(False, "QUARANTINE", "extension_not_allowlisted", digest, size, extension, detected)
    if size > max_size_bytes:
        return AttachmentScanResult(False, "QUARANTINE", "file_too_large", digest, size, extension, detected)
    if extension == ".zip":
        safe, reason = _zip_policy(
            path,
            max_entries=max_zip_entries,
            max_uncompressed_bytes=max_zip_uncompressed_bytes,
            max_ratio=max_zip_ratio,
        )
        if not safe:
            return AttachmentScanResult(False, "QUARANTINE", reason, digest, size, extension, detected)
    return AttachmentScanResult(True, "CLEAN", "allowlisted", digest, size, extension, detected)
