"""Bounded, local-only EPUB extraction for the Global Knowledge ingestion path.

This module extracts content; it does not grant copyright permission, bypass DRM,
fetch remote files, create embeddings, or write imported text into user memory.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

_MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
_MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
_MAX_MEMBERS = 5000
_MAX_COMPRESSION_RATIO = 200
_MAX_CHAPTER_CHARS = 2_000_000
_MAX_TOTAL_CHARS = 10_000_000


@dataclass(frozen=True, slots=True)
class EbookMetadata:
    title: str
    creators: tuple[str, ...]
    language: str | None
    publisher: str | None
    rights: str | None
    identifier: str | None


@dataclass(frozen=True, slots=True)
class EbookChapter:
    id: str
    href: str
    title: str
    text: str
    order: int


class EbookRightsBasis(StrEnum):
    PUBLIC_DOMAIN = "public_domain"
    OPEN_LICENSE = "open_license"
    USER_ATTESTED_PERMISSION = "user_attested_permission"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EbookChunk:
    chunk_id: str
    source_sha256: str
    chapter_id: str
    chapter_order: int
    chunk_order: int
    text: str
    rights_basis: EbookRightsBasis
    parser_version: str


@dataclass(frozen=True, slots=True)
class EbookDocument:
    filename: str
    sha256: str
    metadata: EbookMetadata
    chapters: tuple[EbookChapter, ...]
    total_characters: int
    parser_version: str = "cknexus-epub-1.0.0"


class EbookIngestError(ValueError):
    """Raised when an EPUB is malformed or exceeds safe parsing limits."""


class _TextExtractor(HTMLParser):
    _BLOCKS = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self._skip_depth += 1
        elif not self._skip_depth and tag.lower() in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif not self._skip_depth and tag.lower() in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts).replace("\r", "\n")
        lines = [re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
        return "\n".join(line for line in lines if line).strip()


def parse_epub(path: str | Path) -> EbookDocument:
    """Parse a local EPUB safely, preserving OPF spine order and source hash."""
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise EbookIngestError("EPUB file is unavailable") from exc
    if size <= 0 or size > _MAX_ARCHIVE_BYTES:
        raise EbookIngestError("EPUB archive size is outside the allowed bounds")
    try:
        raw_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_MEMBERS:
                raise EbookIngestError("EPUB contains too many archive members")
            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
                raise EbookIngestError("EPUB expands beyond the allowed size")
            names = {info.filename for info in infos}
            for info in infos:
                if info.flag_bits & 0x1:
                    raise EbookIngestError("encrypted EPUB members are not supported")
                if info.file_size and info.compress_size == 0:
                    raise EbookIngestError("invalid EPUB compression metadata")
                if (
                    info.compress_size
                    and info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
                ):
                    raise EbookIngestError("EPUB compression ratio exceeds the safe limit")
                _safe_archive_path(info.filename)
            if "META-INF/container.xml" not in names:
                raise EbookIngestError("EPUB container.xml is missing")
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            rootfile = next(
                (
                    node.attrib.get("full-path")
                    for node in container.iter()
                    if _local(node.tag) == "rootfile"
                ),
                None,
            )
            if not rootfile:
                raise EbookIngestError("EPUB package document is missing")
            opf_path = _safe_archive_path(rootfile)
            if opf_path not in names:
                raise EbookIngestError("EPUB package document does not exist")
            opf = ET.fromstring(archive.read(opf_path))
            base_dir = posixpath.dirname(opf_path)
            metadata_node = next((n for n in opf.iter() if _local(n.tag) == "metadata"), None)
            if metadata_node is None:
                raise EbookIngestError("EPUB metadata is missing")
            metadata_values: dict[str, list[str]] = {}
            for node in metadata_node.iter():
                key = _local(node.tag)
                value = " ".join("".join(node.itertext()).split())
                if value:
                    metadata_values.setdefault(key, []).append(value)
            title = _first(metadata_values, "title") or source.stem
            metadata = EbookMetadata(
                title=title,
                creators=tuple(metadata_values.get("creator", ())),
                language=_first(metadata_values, "language"),
                publisher=_first(metadata_values, "publisher"),
                rights=_first(metadata_values, "rights"),
                identifier=_first(metadata_values, "identifier"),
            )
            manifest_node = next((n for n in opf.iter() if _local(n.tag) == "manifest"), None)
            spine_node = next((n for n in opf.iter() if _local(n.tag) == "spine"), None)
            if manifest_node is None or spine_node is None:
                raise EbookIngestError("EPUB manifest or spine is missing")
            manifest: dict[str, tuple[str, str]] = {}
            for item in manifest_node:
                item_id = item.attrib.get("id")
                href = item.attrib.get("href")
                media_type = item.attrib.get("media-type", "")
                if item_id and href:
                    resolved = _safe_archive_path(posixpath.join(base_dir, href))
                    manifest[item_id] = (resolved, media_type)
            chapters: list[EbookChapter] = []
            total_chars = 0
            for itemref in spine_node:
                idref = itemref.attrib.get("idref")
                if not idref or itemref.attrib.get("linear", "yes").lower() == "no":
                    continue
                entry = manifest.get(idref)
                if entry is None:
                    raise EbookIngestError("EPUB spine references an unknown manifest item")
                href, media_type = entry
                if media_type not in {"application/xhtml+xml", "text/html"}:
                    continue
                if href not in names:
                    raise EbookIngestError("EPUB chapter is missing from archive")
                payload = archive.read(href)
                if len(payload) > _MAX_CHAPTER_CHARS * 8:
                    raise EbookIngestError("EPUB chapter exceeds the safe parsing limit")
                parser = _TextExtractor()
                try:
                    parser.feed(payload.decode("utf-8-sig", errors="replace"))
                    text = parser.text()
                except Exception as exc:
                    raise EbookIngestError("EPUB chapter could not be parsed") from exc
                if len(text) > _MAX_CHAPTER_CHARS:
                    raise EbookIngestError("EPUB chapter text exceeds the safe limit")
                if not text:
                    continue
                total_chars += len(text)
                if total_chars > _MAX_TOTAL_CHARS:
                    raise EbookIngestError("EPUB total text exceeds the safe limit")
                chapters.append(
                    EbookChapter(
                        id=idref,
                        href=href,
                        title=_chapter_title(text, len(chapters) + 1),
                        text=text,
                        order=len(chapters),
                    )
                )
            if not chapters:
                raise EbookIngestError("EPUB contains no readable spine chapters")
            return EbookDocument(
                filename=source.name,
                sha256=raw_hash,
                metadata=metadata,
                chapters=tuple(chapters),
                total_characters=total_chars,
            )
    except EbookIngestError:
        raise
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, RuntimeError) as exc:
        raise EbookIngestError("EPUB archive is malformed or unreadable") from exc


def parse_pdf(path: str | Path, *, title: str | None = None) -> EbookDocument:
    """Extract text from a local, text-based PDF using bounded Poppler execution.

    OCR is intentionally not attempted. Scanned/image-only PDFs return a clear
    error and should be processed by a separately reviewed OCR worker.
    """
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise EbookIngestError("PDF file is unavailable") from exc
    if size <= 0 or size > _MAX_ARCHIVE_BYTES:
        raise EbookIngestError("PDF file size is outside the allowed bounds")
    executable = shutil.which("pdftotext")
    if executable is None:
        raise EbookIngestError("Poppler pdftotext is not installed")
    try:
        raw_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryFile() as output:
            subprocess.run(
                [executable, "-enc", "UTF-8", "-layout", str(source), "-"],
                check=True,
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=30,
                close_fds=True,
            )
            output.seek(0)
            extracted = output.read(_MAX_TOTAL_CHARS + 1)
        if len(extracted) > _MAX_TOTAL_CHARS:
            raise EbookIngestError("PDF extracted text exceeds the safe limit")
        text = extracted.decode("utf-8", errors="replace").replace("\r", "\n")
        pages = text.split("\f")
        chapters: list[EbookChapter] = []
        for page_number, page_text in enumerate(pages, start=1):
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in page_text.splitlines()]
            normalized = "\n".join(line for line in lines if line).strip()
            if not normalized:
                continue
            chapters.append(
                EbookChapter(
                    id=f"page-{page_number:05d}",
                    href=f"page:{page_number}",
                    title=_chapter_title(normalized, page_number),
                    text=normalized,
                    order=len(chapters),
                )
            )
        if not chapters:
            raise EbookIngestError("PDF has no extractable text; scanned PDFs require OCR")
        total_chars = sum(len(chapter.text) for chapter in chapters)
        return EbookDocument(
            filename=source.name,
            sha256=raw_hash,
            metadata=EbookMetadata(
                title=(title or source.stem)[:500],
                creators=(),
                language=None,
                publisher=None,
                rights=None,
                identifier=None,
            ),
            chapters=tuple(chapters),
            total_characters=total_chars,
            parser_version="cknexus-pdf-poppler-1.0.0",
        )
    except EbookIngestError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise EbookIngestError("PDF text extraction failed or exceeded its time limit") from exc


def _safe_archive_path(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    if (
        normalized in {"", "."}
        or normalized.startswith("/")
        or normalized == ".."
        or normalized.startswith("../")
    ):
        raise EbookIngestError("EPUB contains an unsafe archive path")
    return normalized


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _first(values: dict[str, list[str]], key: str) -> str | None:
    items = values.get(key, [])
    return items[0] if items else None


def _chapter_title(text: str, order: int) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:160] or f"Chapter {order}"


def chunk_epub(
    document: EbookDocument,
    *,
    rights_basis: EbookRightsBasis,
    max_chars: int = 2400,
    overlap_chars: int = 200,
) -> tuple[EbookChunk, ...]:
    """Create stable paragraph-aware chunks after an explicit rights assertion."""
    if rights_basis is EbookRightsBasis.UNKNOWN:
        raise EbookIngestError("document rights must be established before knowledge ingestion")
    if not 200 <= max_chars <= 10_000:
        raise ValueError("max_chars must be within 200..10000")
    if not 0 <= overlap_chars < max_chars // 2:
        raise ValueError("overlap_chars must be non-negative and less than half max_chars")

    chunks: list[EbookChunk] = []
    for chapter in document.chapters:
        paragraphs = [part.strip() for part in chapter.text.splitlines() if part.strip()]
        pending = ""
        chapter_chunks: list[str] = []
        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                if pending:
                    chapter_chunks.append(pending)
                    pending = ""
                start = 0
                while start < len(paragraph):
                    end = min(start + max_chars, len(paragraph))
                    chapter_chunks.append(paragraph[start:end])
                    if end == len(paragraph):
                        break
                    start = end - overlap_chars
                continue
            candidate = f"{pending}\n{paragraph}" if pending else paragraph
            if len(candidate) <= max_chars:
                pending = candidate
            else:
                if pending:
                    chapter_chunks.append(pending)
                tail = pending[-overlap_chars:] if overlap_chars and pending else ""
                pending = f"{tail}\n{paragraph}".strip() if tail else paragraph
        if pending:
            chapter_chunks.append(pending)
        for index, text in enumerate(chapter_chunks):
            material = f"{document.sha256}:{chapter.id}:{index}".encode()
            chunk_id = "epub-" + hashlib.sha256(material).hexdigest()[:24]
            chunks.append(
                EbookChunk(
                    chunk_id=chunk_id,
                    source_sha256=document.sha256,
                    chapter_id=chapter.id,
                    chapter_order=chapter.order,
                    chunk_order=index,
                    text=text,
                    rights_basis=rights_basis,
                    parser_version=document.parser_version,
                )
            )
    return tuple(chunks)
