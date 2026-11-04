# CK-NEXUS Local E-book Knowledge Ingestion

Status: installed and tested on the Creator runtime. Production knowledge database is initialized. It contains one revoked synthetic smoke-test document and zero active third-party books; no third-party book has been imported.

## Supported inputs

- EPUB: local archive parsing, OPF metadata, spine-order chapter extraction.
- Text-based PDF: Poppler `pdftotext` extraction with UTF-8, layout preservation, 30-second timeout and output-size limit.
- Scanned/image-only PDF: not supported yet; requires a separate OCR worker and resource review.

## Rights gate

Every ingest requires an explicit `--rights-basis`:

- `public_domain`
- `open_license`
- `user_attested_permission`

The parser does not determine whether a book is legally reusable. Verify the actual license, edition, author attribution and any ShareAlike obligations before importing. Do not ingest DRM-protected, paywalled or unauthorized copies. Unknown rights are rejected.

## Runtime paths

- CLI: `/usr/local/bin/cknexus-ebook`
- Default database: `/var/lib/cknexus-knowledge/ebooks.sqlite3`
- Inbox: `/var/lib/cknexus-knowledge/ebooks/inbox/`
- Runtime modules: `/opt/cknexus-staging-src/creator_app/global_knowledge/ebook_*.py`

## Commands

```bash
# List imported documents
cknexus-ebook list

# Import an EPUB under a verified open license
cknexus-ebook ingest /var/lib/cknexus-knowledge/ebooks/inbox/book.epub --rights-basis open_license

# Import a text-based PDF under a verified open license
cknexus-ebook ingest /var/lib/cknexus-knowledge/ebooks/inbox/book.pdf --rights-basis open_license

# Search indexed chunks and receive source/chunk identifiers
cknexus-ebook search "transformer attention" --limit 10

# Revoke a source from retrieval while retaining its audit/provenance record
cknexus-ebook revoke <64-character-source-sha256>
```

## Data and retrieval model

The SQLite store is separate from personal memory and CK-NEXUS policy state. MCP exposes read-only `cknexus_knowledge_search` and `cknexus_knowledge_sources` tools; the MCP service account has read-only ACL access to this one database file, not the broader Creator data directory. It records source hash, metadata, rights basis, parser version, chapter/page identity and stable chunk IDs. Ingestion is idempotent. Revoked sources are excluded from search but are not physically deleted.

Search is currently lexical/substring retrieval, not vector or semantic retrieval. No embeddings are generated and no AI provider is called during ingestion. The next integration phase is to add a model-neutral embedding adapter behind the existing Provider Router, then connect retrieved chunks to Creator prompts with source citations. Do not write imported book content into personal memory automatically.
