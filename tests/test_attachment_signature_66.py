import io
import zipfile

import pytest

from services.email_gateway.attachments import scan_attachment


def _scan(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes(data)
    return scan_attachment(f)


def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "hi")
    return buf.getvalue()


@pytest.mark.parametrize(
    "name,data",
    [
        ("a.pdf", b"%PDF-1.7\n"),
        ("a.docx", _zip_bytes()),
        ("a.xlsx", _zip_bytes()),
        ("a.zip", _zip_bytes()),
        ("a.png", b"\x89PNG\r\n\x1a\nxx"),
        ("a.jpg", b"\xff\xd8\xff\xe0xx"),
        ("a.txt", "สวัสดี hello\n".encode()),
        ("a.csv", b"a,b\n1,2\n"),
        ("a.txt", b""),
    ],
)
def test_valid_content_is_clean(tmp_path, name, data):
    r = _scan(tmp_path, name, data)
    assert r.safe and r.status == "CLEAN", r.reason


@pytest.mark.parametrize(
    "name,data,reason",
    [
        ("a.pdf", b"MZ\x90\x00", "executable_signature"),
        ("a.txt", b"\x7fELF\x02", "executable_signature"),
        ("a.csv", b"#!/bin/sh\n", "executable_signature"),
        ("a.png", b"\xcf\xfa\xed\xfe", "executable_signature"),
        ("a.docx", b"%PDF-1.4", "content_signature_mismatch"),
        ("a.pdf", b"PK\x03\x04", "content_signature_mismatch"),
        ("a.docx", b"not a zip at all", "content_signature_mismatch"),
        ("a.txt", b"PK\x03\x04", "content_signature_mismatch"),
        ("a.txt", b"\x00\x01\x02", "content_signature_mismatch"),
        ("a.csv", b"\xff\xfe\xfa", "content_signature_mismatch"),
        ("a.png", b"\xff\xd8\xff", "content_signature_mismatch"),
        ("a.jpg", b"\x89PNG\r\n\x1a\n", "content_signature_mismatch"),
    ],
)
def test_renamed_or_polyglot_is_quarantined(tmp_path, name, data, reason):
    r = _scan(tmp_path, name, data)
    assert not r.safe and r.status == "QUARANTINE" and r.reason == reason


def test_detected_mime_comes_from_content_not_name(tmp_path):
    r = _scan(tmp_path, "a.txt", b"%PDF-1.7\n")
    assert r.detected_mime == "application/pdf"


@pytest.mark.parametrize("name", ["a.txt", "a.csv"])
def test_invalid_bytes_after_head_window_are_quarantined(tmp_path, name):
    data = b"a" * 4096 + b"\x00" + b"b" * 10
    r = _scan(tmp_path, name, data)
    assert not r.safe and r.reason == "content_signature_mismatch"
    data = b"a" * 4096 + b"\xff\xfe"
    r = _scan(tmp_path, name, data)
    assert not r.safe and r.reason == "content_signature_mismatch"


def test_truncated_utf8_at_eof_is_quarantined(tmp_path):
    r = _scan(tmp_path, "a.txt", b"hello " + "ก".encode()[:2])
    assert not r.safe and r.reason == "content_signature_mismatch"


def test_large_valid_utf8_text_is_clean(tmp_path):
    r = _scan(tmp_path, "a.csv", ("สวัสดี,1\n" * 20000).encode())
    assert r.safe


def test_cp874_text_is_quarantined(tmp_path):
    r = _scan(tmp_path, "a.csv", "สวัสดี,1\n".encode("cp874"))
    assert not r.safe and r.reason == "content_signature_mismatch"


def test_utf16_text_is_quarantined(tmp_path):
    r = _scan(tmp_path, "a.txt", "hello\n".encode("utf-16"))
    assert not r.safe and r.reason == "content_signature_mismatch"


def _archive_bytes(entries, *, compression=zipfile.ZIP_DEFLATED):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buf.getvalue()


@pytest.mark.parametrize("name", ["archive.zip", "document.docx", "workbook.xlsx"])
def test_all_zip_container_extensions_apply_archive_policy(tmp_path, name):
    archive = tmp_path / name
    archive.write_bytes(_archive_bytes([("one.txt", b"ok"), ("two.txt", b"ok")]))
    result = scan_attachment(archive, max_zip_entries=1)
    assert not result.safe and result.reason == "zip_too_many_entries"


@pytest.mark.parametrize("name", ["archive.zip", "document.docx", "workbook.xlsx"])
def test_archive_entry_count_boundary_is_inclusive(tmp_path, name):
    archive = tmp_path / name
    archive.write_bytes(
        _archive_bytes([("one.txt", b"ok")], compression=zipfile.ZIP_STORED)
    )
    result = scan_attachment(
        archive, max_zip_entries=1, max_zip_uncompressed_bytes=2, max_zip_ratio=1.0
    )
    assert result.safe, result.reason


@pytest.mark.parametrize(
    "member",
    [
        "../escape.txt",
        "folder/../../escape.txt",
        "..\\escape.txt",
        "/absolute.txt",
        "C:\\absolute.txt",
    ],
)
def test_archive_path_traversal_is_quarantined(tmp_path, member):
    archive = tmp_path / "unsafe.zip"
    archive.write_bytes(_archive_bytes([(member, b"bad")]))
    result = scan_attachment(archive)
    assert not result.safe and result.reason == "zip_path_traversal"


def test_archive_uncompressed_size_limit_is_enforced_for_office_files(tmp_path):
    archive = tmp_path / "oversized.docx"
    archive.write_bytes(_archive_bytes([("word/document.xml", b"x" * 32)]))
    result = scan_attachment(archive, max_zip_uncompressed_bytes=31)
    assert not result.safe and result.reason == "zip_uncompressed_limit"


def test_archive_compression_ratio_limit_is_enforced_for_office_files(tmp_path):
    archive = tmp_path / "ratio.xlsx"
    archive.write_bytes(_archive_bytes([("xl/sharedStrings.xml", b"A" * 4096)]))
    result = scan_attachment(archive, max_zip_ratio=2.0)
    assert not result.safe and result.reason == "zip_compression_ratio"


def test_nested_zip_member_is_quarantined(tmp_path):
    nested = _archive_bytes([("payload.txt", b"inner")])
    archive = tmp_path / "nested.docx"
    archive.write_bytes(_archive_bytes([("word/embeddings/embedded.zip", nested)]))
    result = scan_attachment(archive)
    assert not result.safe and result.reason == "zip_nested_archive"


def test_malformed_zip_container_is_quarantined_for_office_files(tmp_path):
    archive = tmp_path / "malformed.xlsx"
    archive.write_bytes(b"PK\x03\x04not-a-valid-central-directory")
    result = scan_attachment(archive)
    assert not result.safe and result.reason == "invalid_zip"


def test_corrupt_member_crc_is_quarantined(tmp_path):
    data = bytearray(_archive_bytes([("payload.txt", b"payload")], compression=zipfile.ZIP_STORED))
    local_header_size = 30 + len(b"payload.txt")
    data[local_header_size] ^= 0x01
    archive = tmp_path / "corrupt.zip"
    archive.write_bytes(data)
    result = scan_attachment(archive)
    assert not result.safe and result.reason == "invalid_zip"
