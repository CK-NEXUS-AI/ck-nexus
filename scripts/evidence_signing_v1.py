from __future__ import annotations

import argparse
import json
from pathlib import Path

from creator_app.evidence_signing.bundle import (
    build_evidence_bundle,
    record_system_signature,
    verify_evidence_bundle,
)
from creator_app.evidence_signing.cosign import sign_and_verify_keyless


def _build(args: argparse.Namespace) -> int:
    result = build_evidence_bundle(
        evidence_dir=Path(args.evidence_dir),
        output_dir=Path(args.output_dir),
        repository=args.repository,
        subject_commit=args.subject_commit,
        subject_tree=args.subject_tree,
        scanner=args.scanner,
        scanner_version=args.scanner_version,
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {
                "result": "BUILT",
                "manifest_sha256": result["manifest_sha256"],
                "q10": result["verification_state"]["q10"],
                "production": result["verification_state"]["production"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    result = verify_evidence_bundle(
        evidence_dir=Path(args.evidence_dir),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


def _sign_sigstore(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    manifest_path = output_dir / "evidence-signing-manifest.json"
    bundle_path = output_dir / args.bundle_name

    result = sign_and_verify_keyless(
        manifest_path=manifest_path,
        bundle_path=bundle_path,
        signer_identity=args.signer_identity,
        oidc_issuer=args.oidc_issuer,
        allow_public_transparency_log=args.allow_public_transparency_log,
    )
    state = record_system_signature(
        output_dir=output_dir,
        provider="sigstore-cosign-keyless",
        bundle_filename=result.bundle_path.name,
        signer_identity=result.signer_identity,
    )
    print(
        json.dumps(
            {
                "result": "CRYPTOGRAPHICALLY_VERIFIED",
                "system_signature": state["system_signature"],
                "independent_human_review": state["independent_human_review"],
                "owner_signoff": state["owner_signoff"],
                "q10": state["q10"],
                "production": state["production"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="CK-NEXUS Evidence Signing & Chain-of-Custody V1")
    sub = root.add_subparsers(dest="action", required=True)

    build = sub.add_parser("build", help="Build a deterministic evidence signing bundle")
    build.add_argument("--evidence-dir", required=True)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--repository", required=True)
    build.add_argument("--subject-commit", required=True)
    build.add_argument("--subject-tree", required=True)
    build.add_argument("--scanner", required=True)
    build.add_argument("--scanner-version", required=True)
    build.add_argument("--run-id")
    build.set_defaults(func=_build)

    verify = sub.add_parser("verify", help="Verify artifact hashes and custody chain")
    verify.add_argument("--evidence-dir", required=True)
    verify.add_argument("--output-dir", required=True)
    verify.set_defaults(func=_verify)

    sign = sub.add_parser("sign-sigstore", help="Keyless-sign the manifest with Cosign")
    sign.add_argument("--output-dir", required=True)
    sign.add_argument("--bundle-name", default="evidence-signing.sigstore.json")
    sign.add_argument("--signer-identity", required=True)
    sign.add_argument(
        "--oidc-issuer",
        default="https://token.actions.githubusercontent.com",
    )
    sign.add_argument(
        "--allow-public-transparency-log",
        action="store_true",
        help="Required explicit consent because keyless Sigstore signing is publicly auditable.",
    )
    sign.set_defaults(func=_sign_sigstore)
    return root


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
