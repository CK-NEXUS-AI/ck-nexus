from __future__ import annotations

import pytest

from creator_app.global_knowledge import ebook_store as ebook_store_module
from creator_app.global_knowledge.ebook_ingest import (
    EbookChapter,
    EbookDocument,
    EbookMetadata,
    EbookRightsBasis,
    chunk_epub,
)
from creator_app.global_knowledge.ebook_store import EbookKnowledgeStore


@pytest.fixture(autouse=True)
def _allow_test_database_root(tmp_path, monkeypatch):
    monkeypatch.setattr(ebook_store_module, "_ALLOWED_DB_ROOTS", (tmp_path,))


def _document() -> EbookDocument:
    return EbookDocument(
        filename="licensed.epub",
        sha256="c" * 64,
        metadata=EbookMetadata(
            "AI Foundations", ("Author",), "en", "Publisher", "CC BY-SA 4.0", None
        ),
        chapters=(
            EbookChapter(
                "ch1",
                "chapter.xhtml",
                "Transformers",
                "Transformers use attention mechanisms.\nAttention allows token interactions.",
                0,
            ),
        ),
        total_characters=77,
    )


def test_database_path_outside_approved_root_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="outside approved local storage roots"):
        EbookKnowledgeStore(tmp_path.parent / "outside.sqlite3")


def test_store_ingests_once_and_returns_citable_search_hits(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    store = EbookKnowledgeStore(tmp_path / "knowledge.sqlite3")
    assert store.ingest(document, chunks) == len(chunks)
    assert store.ingest(document, chunks) == 0
    hits = store.search("attention")
    assert len(hits) == 1
    assert hits[0].title == "AI Foundations"
    assert hits[0].source_sha256 == document.sha256
    assert hits[0].chapter_id == "ch1"
    assert "attention mechanisms" in hits[0].text
    assert store.list_documents()[0]["chunk_count"] == len(chunks)


def test_revocation_removes_document_from_retrieval_but_keeps_record(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    store = EbookKnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.ingest(document, chunks)
    assert store.revoke(document.sha256) is True
    assert store.search("attention") == ()
    rows = store.list_documents()
    assert len(rows) == 1
    assert rows[0]["revoked"] == 1
    assert store.revoke(document.sha256) is False


def test_store_rejects_foreign_chunks_and_invalid_search(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    store = EbookKnowledgeStore(tmp_path / "knowledge.sqlite3")
    from dataclasses import replace

    with pytest.raises(ValueError, match="source hash"):
        store.ingest(document, (replace(chunks[0], source_sha256="d" * 64),))
    with pytest.raises(ValueError, match="query"):
        store.search(" ")
    with pytest.raises(ValueError, match="limit"):
        store.search("attention", limit=0)


def test_search_treats_sql_injection_text_as_bound_search_terms(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    store = EbookKnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.ingest(document, chunks)

    assert len(store.search("attention")) == 1
    assert store.search("attention' OR 1=1 --") == ()
    assert store.search_readonly("attention' OR 1=1 --") == ()


def test_readonly_search_does_not_create_or_mutate_index(tmp_path) -> None:
    path = tmp_path / "not-created.sqlite3"
    store = EbookKnowledgeStore(path)
    assert store.search_readonly("attention") == ()
    assert store.list_documents_readonly() == ()
    assert not path.exists()


def test_readonly_search_does_not_create_missing_parent_directory(tmp_path) -> None:
    parent = tmp_path / "not-created" / "nested"
    store = EbookKnowledgeStore(parent / "knowledge.sqlite3")

    assert store.search_readonly("attention") == ()
    assert store.list_documents_readonly() == ()
    assert not parent.exists()


def test_readonly_search_uses_existing_index_and_honors_revocation(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    store = EbookKnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.ingest(document, chunks)
    assert len(store.search_readonly("attention")) == 1
    assert len(store.list_documents_readonly()) == 1
    assert store.revoke(document.sha256)
    assert store.search_readonly("attention") == ()


def test_database_file_is_private_to_owner(tmp_path) -> None:
    import os
    import stat

    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    path = tmp_path / "knowledge.sqlite3"
    store = EbookKnowledgeStore(path)
    store.ingest(document, chunks)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_database_rejects_symlink_without_touching_target(tmp_path) -> None:
    target = tmp_path / "target.sqlite3"
    target.write_bytes(b"do not modify")
    link = tmp_path / "knowledge.sqlite3"
    link.symlink_to(target)
    store = EbookKnowledgeStore(link)

    with pytest.raises(OSError):
        store.initialize()

    assert target.read_bytes() == b"do not modify"


def test_initialize_rejects_existing_nonprivate_database_directory_without_chmod(
    tmp_path,
) -> None:
    import stat

    parent = tmp_path / "legacy-knowledge"
    parent.mkdir(mode=0o755)
    parent.chmod(0o755)
    store = EbookKnowledgeStore(parent / "knowledge.sqlite3")

    with pytest.raises(PermissionError, match="existing directory permissions"):
        store.initialize()

    assert stat.S_IMODE(parent.stat().st_mode) == 0o755
    database_entry = parent / "knowledge.sqlite3"
    assert not database_entry.is_symlink()
    assert not database_entry.exists()


def test_existing_database_permissions_are_tightened(tmp_path) -> None:
    import os
    import stat

    path = tmp_path / "knowledge.sqlite3"
    path.touch()
    store = EbookKnowledgeStore(path)
    store.initialize()
    path.chmod(0o644)

    store.list_documents()

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_readonly_apis_reject_symlink_database_path(tmp_path) -> None:
    document = _document()
    chunks = chunk_epub(document, rights_basis=EbookRightsBasis.OPEN_LICENSE)
    target = tmp_path / "target.sqlite3"
    target_store = EbookKnowledgeStore(target)
    target_store.ingest(document, chunks)

    link = tmp_path / "knowledge.sqlite3"
    link.symlink_to(target)
    store = EbookKnowledgeStore(link)

    with pytest.raises(OSError):
        store.search_readonly("attention")
    with pytest.raises(OSError):
        store.list_documents_readonly()
