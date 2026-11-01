"""Local SQLite knowledge store for rights-cleared EPUB chunks.

The store is a document index, not CK-NEXUS policy authority or user memory.
Records are append-only; revocation hides a source from retrieval without
physically deleting its provenance or content.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from creator_app.global_knowledge.ebook_ingest import (
    EbookChunk,
    EbookDocument,
    EbookIngestError,
    EbookRightsBasis,
)


@dataclass(frozen=True, slots=True)
class EbookSearchHit:
    chunk_id: str
    source_sha256: str
    title: str
    filename: str
    chapter_id: str
    chapter_order: int
    chunk_order: int
    text: str
    rights_basis: str


class EbookKnowledgeStore:
    """Bounded local store with deterministic citations and source revocation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ebook_documents (
                    source_sha256 TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    title TEXT NOT NULL,
                    creators_json TEXT NOT NULL,
                    language TEXT,
                    publisher TEXT,
                    rights_statement TEXT,
                    rights_basis TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    total_characters INTEGER NOT NULL,
                    ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS ebook_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_sha256 TEXT NOT NULL REFERENCES ebook_documents(source_sha256),
                    chapter_id TEXT NOT NULL,
                    chapter_order INTEGER NOT NULL,
                    chunk_order INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    rights_basis TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    UNIQUE(source_sha256, chapter_id, chunk_order)
                );
                CREATE INDEX IF NOT EXISTS idx_ebook_chunks_source
                    ON ebook_chunks(source_sha256, chapter_order, chunk_order);
                CREATE INDEX IF NOT EXISTS idx_ebook_documents_revoked
                    ON ebook_documents(revoked, rights_basis);
                """
            )

    def ingest(self, document: EbookDocument, chunks: tuple[EbookChunk, ...]) -> int:
        if not chunks:
            raise EbookIngestError("no chunks were supplied for ingestion")
        rights = {chunk.rights_basis for chunk in chunks}
        if len(rights) != 1 or EbookRightsBasis.UNKNOWN in rights:
            raise EbookIngestError("all chunks must carry one explicit rights basis")
        if any(chunk.source_sha256 != document.sha256 for chunk in chunks):
            raise EbookIngestError("chunk source hash does not match the document")
        rights_basis = next(iter(rights)).value
        self.initialize()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT rights_basis, parser_version FROM ebook_documents WHERE source_sha256 = ?",
                (document.sha256,),
            ).fetchone()
            if existing:
                if existing != (rights_basis, document.parser_version):
                    raise EbookIngestError(
                        "existing source hash has conflicting ingestion metadata"
                    )
                return 0
            conn.execute(
                """INSERT INTO ebook_documents (
                    source_sha256, filename, title, creators_json, language, publisher,
                    rights_statement, rights_basis, parser_version, total_characters
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    document.sha256,
                    document.filename,
                    document.metadata.title,
                    json.dumps(document.metadata.creators, ensure_ascii=False),
                    document.metadata.language,
                    document.metadata.publisher,
                    document.metadata.rights,
                    rights_basis,
                    document.parser_version,
                    document.total_characters,
                ),
            )
            conn.executemany(
                """INSERT INTO ebook_chunks (
                    chunk_id, source_sha256, chapter_id, chapter_order, chunk_order,
                    text, rights_basis, parser_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        chunk.chunk_id,
                        chunk.source_sha256,
                        chunk.chapter_id,
                        chunk.chapter_order,
                        chunk.chunk_order,
                        chunk.text,
                        chunk.rights_basis.value,
                        chunk.parser_version,
                    )
                    for chunk in chunks
                ],
            )
        return len(chunks)

    def search(self, query: str, *, limit: int = 10) -> tuple[EbookSearchHit, ...]:
        normalized = " ".join(query.split())
        if not normalized or len(normalized) > 500:
            raise ValueError("query must contain 1..500 characters")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be within 1..50")
        terms = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if not terms:
            raise ValueError("query contains no searchable terms")
        clauses = " AND ".join("c.text LIKE ? COLLATE NOCASE" for _ in terms)
        params = [f"%{term}%" for term in terms]
        params.append(limit)
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                f"""SELECT c.chunk_id, c.source_sha256, d.title, d.filename,
                           c.chapter_id, c.chapter_order, c.chunk_order, c.text, c.rights_basis
                    FROM ebook_chunks c
                    JOIN ebook_documents d ON d.source_sha256 = c.source_sha256
                    WHERE d.revoked = 0 AND {clauses}
                    ORDER BY d.title COLLATE NOCASE, c.chapter_order, c.chunk_order
                    LIMIT ?""",
                params,
            ).fetchall()
        return tuple(EbookSearchHit(*row) for row in rows)

    def list_documents(self) -> tuple[dict[str, object], ...]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT source_sha256, filename, title, language, rights_basis,
                          parser_version, total_characters, ingested_at, revoked,
                          (SELECT count(*) FROM ebook_chunks c
                           WHERE c.source_sha256 = d.source_sha256) AS chunk_count
                   FROM ebook_documents d ORDER BY ingested_at, title"""
            ).fetchall()
        keys = (
            "source_sha256",
            "filename",
            "title",
            "language",
            "rights_basis",
            "parser_version",
            "total_characters",
            "ingested_at",
            "revoked",
            "chunk_count",
        )
        return tuple(dict(zip(keys, row, strict=True)) for row in rows)

    def search_readonly(self, query: str, *, limit: int = 10) -> tuple[EbookSearchHit, ...]:
        """Search an existing index without creating or mutating any database state."""
        normalized = " ".join(query.split())
        if not normalized or len(normalized) > 500:
            raise ValueError("query must contain 1..500 characters")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be within 1..50")
        terms = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if not terms:
            raise ValueError("query contains no searchable terms")
        if not self.path.is_file():
            return ()
        clauses = " AND ".join("c.text LIKE ? COLLATE NOCASE" for _ in terms)
        params = [f"%{term}%" for term in terms]
        params.append(limit)
        uri = self.path.resolve().as_uri() + "?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True, timeout=3.0) as conn:
                rows = conn.execute(
                    f"""SELECT c.chunk_id, c.source_sha256, d.title, d.filename,
                               c.chapter_id, c.chapter_order, c.chunk_order, c.text, c.rights_basis
                        FROM ebook_chunks c
                        JOIN ebook_documents d ON d.source_sha256 = c.source_sha256
                        WHERE d.revoked = 0 AND {clauses}
                        ORDER BY d.title COLLATE NOCASE, c.chapter_order, c.chunk_order
                        LIMIT ?""",
                    params,
                ).fetchall()
        except sqlite3.OperationalError as exc:
            raise RuntimeError(
                "knowledge index is unavailable or has an incompatible schema"
            ) from exc
        return tuple(EbookSearchHit(*row) for row in rows)

    def list_documents_readonly(self) -> tuple[dict[str, object], ...]:
        """List documents from an existing index without initializing or mutating it."""
        if not self.path.is_file():
            return ()
        uri = self.path.resolve().as_uri() + "?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True, timeout=3.0) as conn:
                rows = conn.execute(
                    """SELECT source_sha256, filename, title, language, rights_basis,
                              parser_version, total_characters, ingested_at, revoked,
                              (SELECT count(*) FROM ebook_chunks c
                               WHERE c.source_sha256 = d.source_sha256) AS chunk_count
                       FROM ebook_documents d ORDER BY ingested_at, title"""
                ).fetchall()
        except sqlite3.OperationalError as exc:
            raise RuntimeError(
                "knowledge index is unavailable or has an incompatible schema"
            ) from exc
        keys = (
            "source_sha256",
            "filename",
            "title",
            "language",
            "rights_basis",
            "parser_version",
            "total_characters",
            "ingested_at",
            "revoked",
            "chunk_count",
        )
        return tuple(dict(zip(keys, row, strict=True)) for row in rows)

    def revoke(self, source_sha256: str) -> bool:
        if not re.fullmatch(r"[a-f0-9]{64}", source_sha256):
            raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        self.initialize()
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE ebook_documents SET revoked = 1 WHERE source_sha256 = ? AND revoked = 0",
                (source_sha256,),
            )
        return result.rowcount == 1

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn
