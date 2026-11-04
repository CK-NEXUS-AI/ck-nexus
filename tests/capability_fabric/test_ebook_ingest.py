from __future__ import annotations

import hashlib
import zipfile

import pytest

from creator_app.global_knowledge.ebook_ingest import (
    EbookChapter,
    EbookDocument,
    EbookIngestError,
    EbookMetadata,
    EbookRightsBasis,
    chunk_epub,
    parse_epub,
)


def _make_epub(path, *, spine_href: str = "Text/chapter.xhtml") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            (
                '<?xml version="1.0"?><container '
                'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                '<rootfiles><rootfile full-path="OEBPS/content.opf"/>'
                "</rootfiles></container>"
            ),
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
              <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>CK-NEXUS Test Book</dc:title><dc:creator>Test Author</dc:creator>
                <dc:language>th</dc:language><dc:rights>CC0 test fixture</dc:rights>
              </metadata>
              <manifest>
                <item id="c1" href="Text/chapter.xhtml"
                      media-type="application/xhtml+xml"/>
              </manifest>
              <spine><itemref idref="c1"/></spine>
            </package>""",
        )
        archive.writestr(
            "OEBPS/Text/chapter.xhtml",
            (
                "<html><head><title>บทที่หนึ่ง</title>"
                "<script>ignore-me</script></head><body>"
                "<h1>บทที่หนึ่ง</h1>"
                "<p>ความรู้สำหรับทดสอบ CK-NEXUS</p></body></html>"
            ),
        )


def test_parse_epub_preserves_metadata_order_text_and_hash(tmp_path) -> None:
    path = tmp_path / "knowledge.epub"
    _make_epub(path)
    result = parse_epub(path)
    assert result.metadata.title == "CK-NEXUS Test Book"
    assert result.metadata.creators == ("Test Author",)
    assert result.metadata.language == "th"
    assert result.metadata.rights == "CC0 test fixture"
    assert result.chapters[0].order == 0
    assert "ความรู้สำหรับทดสอบ CK-NEXUS" in result.chapters[0].text
    assert "ignore-me" not in result.chapters[0].text
    assert result.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_parse_epub_rejects_doctype_and_external_entities(tmp_path) -> None:
    path = tmp_path / "hostile.epub"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<!DOCTYPE container [
              <!ENTITY xxe SYSTEM "file:///etc/passwd">
            ]>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles>
            </container>""",
        )
    with pytest.raises(EbookIngestError, match="malformed or unreadable"):
        parse_epub(path)


def test_rejects_non_epub_and_path_traversal(tmp_path) -> None:
    bad = tmp_path / "bad.epub"
    bad.write_text("not a zip", encoding="utf-8")
    with pytest.raises(EbookIngestError):
        parse_epub(bad)
    with pytest.raises(EbookIngestError, match="unsafe archive path"):
        from creator_app.global_knowledge.ebook_ingest import _safe_archive_path

        _safe_archive_path("../../etc/passwd")


def test_rejects_oversized_archive(tmp_path) -> None:
    path = tmp_path / "oversized.epub"
    path.write_bytes(b"x" * (100 * 1024 * 1024 + 1))
    with pytest.raises(EbookIngestError, match="size"):
        parse_epub(path)


def test_chunking_requires_rights_basis() -> None:
    document = EbookDocument(
        filename="owned.epub",
        sha256="a" * 64,
        metadata=EbookMetadata("Owned", (), "en", None, None, None),
        chapters=(EbookChapter("c1", "c1.xhtml", "Chapter", "A" * 450, 0),),
        total_characters=450,
    )
    with pytest.raises(EbookIngestError, match="rights"):
        chunk_epub(document, rights_basis=EbookRightsBasis.UNKNOWN)


def test_chunking_is_stable_and_records_rights_and_lineage() -> None:
    document = EbookDocument(
        filename="licensed.epub",
        sha256="b" * 64,
        metadata=EbookMetadata("Licensed", (), "en", None, "CC-BY", None),
        chapters=(EbookChapter("c1", "c1.xhtml", "Chapter", "A" * 550, 0),),
        total_characters=550,
    )
    chunks = chunk_epub(
        document,
        rights_basis=EbookRightsBasis.OPEN_LICENSE,
        max_chars=200,
        overlap_chars=40,
    )
    again = chunk_epub(
        document,
        rights_basis=EbookRightsBasis.OPEN_LICENSE,
        max_chars=200,
        overlap_chars=40,
    )
    assert len(chunks) >= 3
    assert [chunk.chunk_id for chunk in chunks] == [chunk.chunk_id for chunk in again]
    assert all(chunk.source_sha256 == document.sha256 for chunk in chunks)
    assert all(chunk.rights_basis is EbookRightsBasis.OPEN_LICENSE for chunk in chunks)
    assert all(len(chunk.text) <= 200 for chunk in chunks)


def test_parse_pdf_rejects_invalid_file(tmp_path) -> None:
    from creator_app.global_knowledge.ebook_ingest import parse_pdf

    path = tmp_path / "invalid.pdf"
    path.write_text("not a PDF", encoding="utf-8")
    with pytest.raises(EbookIngestError):
        parse_pdf(path)
