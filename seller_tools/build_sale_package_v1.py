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
SALE_DIR = ROOT / "sale_package" / "v1"
OUTER_NAME = "CK-NEXUS-Creator-Source-Sale-Package-v1"
RUNTIME_BASE_COMMIT = "45fde79c717b09f8675645aa541a5834ebd4f433"
EXPECTED_SUBJECT_SHA256 = "51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe"
SUBJECT_PATHS = ["creator_app", "services", "tests", "scripts", "main.py", "pyproject.toml", "uv.lock"]


def run(*args: str, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=capture,
    )


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
    if dirty.returncode != 0:
        raise RuntimeError(dirty.stderr.strip())
    if dirty.stdout.strip():
        raise RuntimeError("Refusing sale build from a dirty working tree")

    head = run("git", "rev-parse", "HEAD")
    if head.returncode != 0:
        raise RuntimeError(head.stderr.strip())
    head_sha = head.stdout.strip()

    ancestor = run("git", "merge-base", "--is-ancestor", RUNTIME_BASE_COMMIT, head_sha)
    if ancestor.returncode != 0:
        raise RuntimeError("Sale branch does not descend from the pinned canonical runtime base")

    subject = runtime_subject_hash()
    if subject != EXPECTED_SUBJECT_SHA256:
        raise RuntimeError(
            "Frozen runtime subject changed; prior Q05/Q08 evidence is stale. "
            f"expected={EXPECTED_SUBJECT_SHA256} actual={subject}"
        )
    return head_sha, subject


def copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def write_checksums(root: Path) -> None:
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(output_dir: Path) -> tuple[Path, str]:
    head_sha, subject_sha = verify_source()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build wheel/sdist first; package_release.py requires both forms under dist/.
    built = run("uv", "build")
    if built.returncode != 0:
        raise RuntimeError(built.stdout + "\n" + built.stderr)

    with tempfile.TemporaryDirectory(prefix="cknexus-sale-v1-") as td:
        tmp = Path(td)
        source_out = tmp / "source-build"
        packaged = run(
            sys.executable,
            "scripts/package_release.py",
            "--output-directory",
            str(source_out),
        )
        if packaged.returncode != 0:
            raise RuntimeError(packaged.stdout + "\n" + packaged.stderr)

        source_zip = next(source_out.glob("CK-NEXUS-Creator-Edition-v0.2.0.zip"))
        source_sidecar = source_zip.with_suffix(".zip.sha256")

        root = tmp / OUTER_NAME
        (root / "SOURCE").mkdir(parents=True)
        (root / "BUYER").mkdir()
        (root / "TRANSACTION").mkdir()
        (root / "PROVENANCE").mkdir()

        shutil.copy2(source_zip, root / "SOURCE" / source_zip.name)
        shutil.copy2(source_sidecar, root / "SOURCE" / source_sidecar.name)
        copytree(SALE_DIR / "buyer", root / "BUYER")
        copytree(SALE_DIR / "transaction", root / "TRANSACTION")
        shutil.copy2(ROOT / "COMMERCIAL_LICENSE_TEMPLATE.md", root / "TRANSACTION")
        shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", root / "PROVENANCE")
        shutil.copy2(SALE_DIR / "RELEASE_IDENTITY.json", root / "PROVENANCE")
        shutil.copy2(SALE_DIR / "CLAIMS_MATRIX.md", root / "PROVENANCE")
        shutil.copy2(ROOT / "RELEASE_STATUS.md", root / "PROVENANCE")
        shutil.copy2(ROOT / "DELIVERY_MANIFEST.txt", root / "PROVENANCE")

        commit_time = run("git", "show", "-s", "--format=%cI", "HEAD").stdout.strip()
        build_info = {
            "schema_version": 1,
            "package": OUTER_NAME,
            "sale_branch_head": head_sha,
            "runtime_base_commit": RUNTIME_BASE_COMMIT,
            "runtime_subject_manifest_sha256": subject_sha,
            "source_archive": source_zip.name,
            "source_archive_sha256": sha256_file(source_zip),
            "package_commit_time": commit_time,
            "production_ready": False,
            "production_status": "NO-GO",
        }
        (root / "PROVENANCE" / "PACKAGE_BUILD_INFO.json").write_text(
            json.dumps(build_info, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        write_checksums(root)

        archive = output_dir / f"{OUTER_NAME}.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(root.parent))

    digest = sha256_file(archive)
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    return archive, digest


def main() -> int:
    output = ROOT.parent / "sale-build"
    if len(sys.argv) > 1:
        output = Path(sys.argv[1]).expanduser().resolve()
    archive, digest = build(output)
    print(f"archive: {archive}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
