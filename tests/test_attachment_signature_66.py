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
        ("a.docx", b"PK\x03\x04rest"),
        ("a.xlsx", b"PK\x03\x04rest"),
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
