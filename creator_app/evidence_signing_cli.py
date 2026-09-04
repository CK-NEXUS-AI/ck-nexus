from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from creator_app.evidence_signing import (
    EvidenceCustodyLedger,
    EvidenceSubject,
    SignerType,
    build_manifest,
    unsigned_signature_envelope,
    verify_chain_export,
    verify_manifest,
    write_json,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    subject = EvidenceSubject(
        repository=args.repository,
        commit=args.commit,
        tree=args.tree,
        environment=args.environment,
        scanner=args.scanner,
        scanner_version=args.scanner_version,
        run_id=args.run_id,
    )
    manifest = build_manifest(root=root, subject=subject, artifacts=args.artifact)
    manifest_path = out / "scan-manifest.json"
    write_json(manifest_path, manifest)

    custody_jsonl = out / "chain-of-custody.jsonl"
    custody = EvidenceCustodyLedger(custody_jsonl)
    custody.append(
        action="EVIDENCE_MANIFEST_CREATED",
        actor_type=SignerType.SYSTEM,
        actor_id="ck-nexus-evidence-signing-v1",
        manifest_sha256=manifest["manifest_sha256"],
        metadata={"production_effect": "NONE"},
    )
    custody.export(out / "chain-of-custody.json")

    envelope = unsigned_signature_envelope(manifest["manifest_sha256"])
    write_json(out / "signature-envelope.json", envelope)

    hash_paths = [
        manifest_path,
        out / "chain-of-custody.jsonl",
        out / "chain-of-custody.json",
        out / "signature-envelope.json",
    ]
    sums = "".join(f"{_sha256(path)}  {path.name}\n" for path in hash_paths)
    (out / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "EVIDENCE_BUILT_UNSIGNED",
                "manifest_sha256": manifest["manifest_sha256"],
                "output_dir": str(out),
                "system_signature": "UNSIGNED",
                "independent_human_review": "PENDING",
                "owner_signoff": "PENDING",
                "production_effect": "NONE",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    bundle = Path(args.bundle_dir).resolve()
    manifest = json.loads((bundle / "scan-manifest.json").read_text(encoding="utf-8"))
    chain = json.loads((bundle / "chain-of-custody.json").read_text(encoding="utf-8"))

    manifest_state = verify_manifest(root, manifest)
    chain_state = verify_chain_export(chain)
    valid = bool(manifest_state["valid"] and chain_state["valid"])
    result = {
        "integrity": "PASS" if valid else "FAIL",
        "manifest": manifest_state,
        "chain_of_custody": chain_state,
        "system_signature": "UNSIGNED",
        "independent_human_review": "PENDING",
        "owner_signoff": "PENDING",
        "production_effect": "NONE",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CK-NEXUS evidence signing/custody V1")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build unsigned evidence/custody bundle")
    build.add_argument("--root", required=True)
    build.add_argument("--repository", required=True)
    build.add_argument("--commit", required=True)
    build.add_argument("--tree", required=True)
    build.add_argument("--environment", required=True)
    build.add_argument("--scanner", required=True)
    build.add_argument("--scanner-version", required=True)
    build.add_argument("--run-id")
    build.add_argument("--artifact", action="append", required=True)
    build.add_argument("--output-dir", required=True)
    build.set_defaults(func=_build)

    verify = sub.add_parser("verify", help="verify manifest and custody integrity")
    verify.add_argument("--root", required=True)
    verify.add_argument("--bundle-dir", required=True)
    verify.set_defaults(func=_verify)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
