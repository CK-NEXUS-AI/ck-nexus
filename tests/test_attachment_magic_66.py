import pytest

from creator_app.gmail_governance.attachments import evaluate_attachment


def ok(name, head):
    return evaluate_attachment(name, size_bytes=10, head=head).allowed_for_parser_sandbox


def test_legacy_call_without_head_unchanged():
    assert evaluate_attachment("a.pdf", size_bytes=10).allowed_for_parser_sandbox


@pytest.mark.parametrize("name,head", [
    ("a.pdf", b"%PDF-1.7"), ("a.docx", b"PK\x03\x04xx"), ("a.xlsx", b"PK\x03\x04"),
    ("a.txt", b"hello"), ("a.csv", b"a,b\n1,2"), ("a.json", b"{}"),
])
def test_matching_content_allowed(name, head):
    assert ok(name, head)


@pytest.mark.parametrize("name,head", [
    ("a.pdf", b"MZ\x90\x00"), ("a.txt", b"\x7fELF"), ("a.docx", b"MZ"),
    ("a.pdf", b"PK\x03\x04"), ("a.docx", b"%PDF-1.4"), ("a.txt", b"PK\x03\x04"),
    ("a.csv", b"#!/bin/sh"), ("a.json", b"\x00\x01"),
])
def test_polyglot_or_renamed_rejected(name, head):
    d = evaluate_attachment(name, size_bytes=10, head=head)
    assert not d.allowed_for_parser_sandbox and d.reason == "content_signature_mismatch"
    assert d.quarantine_required and not d.execute_on_host
