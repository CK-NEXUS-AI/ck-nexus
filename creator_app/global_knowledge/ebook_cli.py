"""Command-line entrypoint for local, rights-gated EPUB knowledge ingestion."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from creator_app.global_knowledge.ebook_ingest import (
    EbookRightsBasis,
    chunk_epub,
    parse_epub,
    parse_pdf,
)
from creator_app.global_knowledge.ebook_store import EbookKnowledgeStore


def _default_db() -> Path:
    home = Path(os.getenv("CKNEXUS_HOME", Path.home() / ".cknexus"))
    return Path(os.getenv("CKNEXUS_EBOOK_DB", home / "data" / "knowledge" / "ebooks.sqlite3"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CK-NEXUS rights-gated EPUB/PDF knowledge tools")
    parser.add_argument(
        "--db", type=Path, default=_default_db(), help="SQLite knowledge index path"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Parse and index a local EPUB")
    ingest.add_argument("path", type=Path)
    ingest.add_argument(
        "--rights-basis",
        choices=[item.value for item in EbookRightsBasis if item is not EbookRightsBasis.UNKNOWN],
        required=True,
    )
    ingest.add_argument("--max-chars", type=int, default=2400)
    search = commands.add_parser("search", help="Search active knowledge chunks")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    commands.add_parser("list", help="List imported documents")
    revoke = commands.add_parser("revoke", help="Hide a source from retrieval without deleting it")
    revoke.add_argument("source_sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = EbookKnowledgeStore(args.db)
    if args.command == "ingest":
        suffix = args.path.suffix.casefold()
        if suffix == ".epub":
            document = parse_epub(args.path)
        elif suffix == ".pdf":
            document = parse_pdf(args.path)
        else:
            raise SystemExit("unsupported file type; use .epub or text-based .pdf")
        rights = EbookRightsBasis(args.rights_basis)
        chunks = chunk_epub(document, rights_basis=rights, max_chars=args.max_chars)
        count = store.ingest(document, chunks)
        result = {
            "status": "ingested" if count else "already_present",
            "title": document.metadata.title,
            "source_sha256": document.sha256,
            "rights_basis": rights.value,
            "chapters": len(document.chapters),
            "chunks_inserted": count,
            "database": str(args.db),
        }
    elif args.command == "search":
        hits = store.search(args.query, limit=args.limit)
        result = {
            "status": "ok",
            "count": len(hits),
            "hits": [
                {
                    "chunk_id": hit.chunk_id,
                    "source_sha256": hit.source_sha256,
                    "title": hit.title,
                    "filename": hit.filename,
                    "chapter_id": hit.chapter_id,
                    "chapter_order": hit.chapter_order,
                    "chunk_order": hit.chunk_order,
                    "rights_basis": hit.rights_basis,
                    "text": hit.text,
                }
                for hit in hits
            ],
        }
    elif args.command == "list":
        result = {"status": "ok", "documents": list(store.list_documents())}
    else:
        result = {
            "status": "revoked"
            if store.revoke(args.source_sha256)
            else "not_found_or_already_revoked"
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
