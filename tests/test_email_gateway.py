

@pytest.mark.parametrize(
    ("member_name", "expected_reason"),
    [
        ("../escape.txt", "zip_path_traversal"),
        ("folder/../../escape.txt", "zip_path_traversal"),
        (r"folder\\..\\escape.txt", "zip_path_traversal"),
        ("/absolute.txt", "zip_path_traversal"),
        (r"C:\\absolute.txt", "zip_path_traversal"),
    ],
)
def test_attachment_quarantine_rejects_archive_path_traversal(
    tmp_path: Path, member_name: str, expected_reason: str
):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(member_name, "payload")

    result = scan_attachment(archive)

    assert result.safe is False
    assert result.status == "QUARANTINE"
    assert result.reason == expected_reason


def test_attachment_quarantine_enforces_entry_count_limit(tmp_path: Path):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    archive = tmp_path / "many-entries.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as handle:
        handle.writestr("one.txt", "1")
        handle.writestr("two.txt", "2")

    result = scan_attachment(archive, max_zip_entries=1)

    assert result.safe is False
    assert result.reason == "zip_too_many_entries"


def test_attachment_quarantine_enforces_actual_uncompressed_byte_limit(tmp_path: Path):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    archive = tmp_path / "uncompressed-limit.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as handle:
        handle.writestr("payload.txt", "A" * 1024)

    result = scan_attachment(
        archive,
        max_zip_uncompressed_bytes=100,
        max_zip_ratio=1000,
    )

    assert result.safe is False
    assert result.reason == "zip_uncompressed_limit"


def test_attachment_quarantine_rejects_nested_zip_members(tmp_path: Path):
    import io
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w", compression=zipfile.ZIP_STORED) as inner:
        inner.writestr("payload.txt", "nested")

    archive = tmp_path / "nested.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as outer:
        outer.writestr("inner.zip", nested.getvalue())

    result = scan_attachment(archive)

    assert result.safe is False
    assert result.reason == "zip_nested_archive"


def test_attachment_quarantine_applies_archive_policy_to_office_documents(tmp_path: Path):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    document = tmp_path / "document.docx"
    with zipfile.ZipFile(document, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("word/document.xml", "<document />")
        archive.writestr("../outside.txt", "not safe")

    result = scan_attachment(document)

    assert result.safe is False
    assert result.reason == "zip_path_traversal"


def test_attachment_quarantine_rejects_corrupt_zip_payload(tmp_path: Path):
    from services.email_gateway.attachments import scan_attachment

    archive = tmp_path / "corrupt.zip"
    archive.write_bytes(b"PK\x03\x04" + b"not-a-valid-zip")

    result = scan_attachment(archive)

    assert result.safe is False
    assert result.reason == "invalid_zip"


def test_attachment_quarantine_rejects_duplicate_case_insensitive_names(tmp_path: Path):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    archive = tmp_path / "duplicate-names.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as handle:
        handle.writestr("Readme.txt", "first")
        handle.writestr("README.TXT", "second")

    result = scan_attachment(archive)

    assert result.safe is False
    assert result.reason == "zip_duplicate_entry"
