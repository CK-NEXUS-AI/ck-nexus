from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = ROOT / "sales_kit" / "v1.1"
OUTER_NAME = "CK-NEXUS-Seller-Sales-Kit-v1.1"
BUYER_PACKAGE_SOURCE_HEAD = "bacd5b40f577fd5b13322c0c11cfe9f82326fb5f"
RUNTIME_BASE_COMMIT = "45fde79c717b09f8675645aa541a5834ebd4f433"
EXPECTED_SUBJECT_SHA256 = "51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe"
SUBJECT_PATHS = ["creator_app", "services", "tests", "scripts", "main.py", "pyproject.toml", "uv.lock"]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=ROOT, check=False, text=True, capture_output=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def runtime_subject_hash() -> str:
    p = run("git", "ls-tree", "-r", "HEAD", "--", *SUBJECT_PATHS)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git ls-tree failed")
    return hashlib.sha256(p.stdout.encode()).hexdigest()


def verify_source() -> tuple[str, str]:
    dirty = run("git", "status", "--porcelain")
    if dirty.returncode != 0 or dirty.stdout.strip():
        raise RuntimeError("Refusing seller-kit build from a dirty working tree")
    head = run("git", "rev-parse", "HEAD")
    if head.returncode != 0:
        raise RuntimeError(head.stderr.strip())
    head_sha = head.stdout.strip()
    ancestor = run("git", "merge-base", "--is-ancestor", BUYER_PACKAGE_SOURCE_HEAD, head_sha)
    if ancestor.returncode != 0:
        raise RuntimeError("Seller-kit branch does not descend from the verified Buyer Package source head")
    subject = runtime_subject_hash()
    if subject != EXPECTED_SUBJECT_SHA256:
        raise RuntimeError(f"Runtime subject changed: expected={EXPECTED_SUBJECT_SHA256} actual={subject}")
    return head_sha, subject


def build(output_dir: Path) -> tuple[Path, str]:
    head_sha, subject_sha = verify_source()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cknexus-seller-kit-") as td:
        tmp = Path(td)
        root = tmp / OUTER_NAME
        shutil.copytree(KIT_DIR, root)
        build_info = {
            "schema_version": 1,
            "package": OUTER_NAME,
            "seller_kit_head": head_sha,
            "buyer_package_source_head": BUYER_PACKAGE_SOURCE_HEAD,
            "runtime_base_commit": RUNTIME_BASE_COMMIT,
            "runtime_subject_manifest_sha256": subject_sha,
            "internal_only": True,
        }
        (root / "BUILD_INFO.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8")
        lines = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS.txt":
                lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
        (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        archive = output_dir / f"{OUTER_NAME}.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(root.parent))
    digest = sha256_file(archive)
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, digest


def main() -> int:
    output = ROOT.parent / "seller-sales-kit-build"
    if len(sys.argv) > 1:
        output = Path(sys.argv[1]).expanduser().resolve()
    archive, digest = build(output)
    print(f"archive: {archive}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
