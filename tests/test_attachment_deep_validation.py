from __future__ import annotations

import io
import zipfile

from creator_app.gmail_governance.attachments import (
    evaluate_attachment,
    verify_attachment_digest,
)


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _valid_docx() -> bytes:
    return _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "_rels/.rels": b"<Relationships/>",
            "word/document.xml": b"<w:document/>",
        }
    )


def test_attachment_requires_content_and_declared_mime() -> None:
    decision = evaluate_attachment("invoice.pdf", size_bytes=128)
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "content_validation_required"


def test_renamed_executable_is_rejected_by_magic() -> None:
    payload = b"MZ" + (b"x" * 30)
    decision = evaluate_attachment(
        "invoice.pdf",
        size_bytes=len(payload),
        declared_mime="application/pdf",
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "dangerous_magic_detected"


def test_declared_mime_mismatch_is_rejected() -> None:
    payload = b"%PDF-1.7\n%%EOF\n"
    decision = evaluate_attachment(
        "invoice.pdf",
        size_bytes=len(payload),
        declared_mime="text/plain",
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "declared_mime_mismatch"


def test_pdf_zip_polyglot_is_rejected() -> None:
    payload = b"%PDF-1.7\n%%EOF\nPK\x03\x04polyglot"
    decision = evaluate_attachment(
        "invoice.pdf",
        size_bytes=len(payload),
        declared_mime="application/pdf",
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "polyglot_signature_detected"


def test_valid_pdf_is_digest_bound_and_quarantined() -> None:
    payload = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
    decision = evaluate_attachment(
        "invoice.pdf",
        size_bytes=len(payload),
        declared_mime="application/pdf",
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is True
    assert decision.quarantine_required is True
    assert decision.execute_on_host is False
    assert decision.sha256 is not None
    assert verify_attachment_digest(payload, decision.sha256) is True
    assert verify_attachment_digest(payload + b"changed", decision.sha256) is False


def test_valid_ooxml_docx_is_allowed_for_quarantined_parser() -> None:
    payload = _valid_docx()
    decision = evaluate_attachment(
        "document.docx",
        size_bytes=len(payload),
        declared_mime=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is True
    assert decision.detected_type == "ooxml"


def test_ooxml_archive_path_traversal_is_rejected() -> None:
    payload = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"<w:document/>",
            "../payload.txt": b"bad",
        }
    )
    decision = evaluate_attachment(
        "document.docx",
        size_bytes=len(payload),
        declared_mime=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "archive_unsafe_path"


def test_nested_archive_inside_ooxml_is_rejected() -> None:
    payload = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"<w:document/>",
            "word/embeddings/archive.zip": b"PK\x03\x04nested",
        }
    )
    decision = evaluate_attachment(
        "document.docx",
        size_bytes=len(payload),
        declared_mime=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "archive_nested_or_executable_content"


def test_high_expansion_ratio_archive_is_rejected() -> None:
    payload = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "word/document.xml": b"0" * (2 * 1024 * 1024),
        }
    )
    decision = evaluate_attachment(
        "document.docx",
        size_bytes=len(payload),
        declared_mime=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason in {
        "archive_expansion_ratio_limit",
        "archive_total_expansion_ratio_limit",
    }


def test_ooxml_macro_or_binary_part_is_rejected() -> None:
    payload = _zip_bytes(
        {
            "[Content_Types].xml": b"<Types/>",
            "xl/workbook.xml": b"<workbook/>",
            "xl/vbaProject.bin": b"macro",
        }
    )
    decision = evaluate_attachment(
        "workbook.xlsx",
        size_bytes=len(payload),
        declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=payload,
    )
    assert decision.allowed_for_parser_sandbox is False
    assert decision.reason == "archive_macro_or_binary_part"
