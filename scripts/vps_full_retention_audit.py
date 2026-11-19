#!/usr/bin/env python3
"""Read-only CK-NEXUS VPS retention and storage audit."""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import pwd
import stat
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

SCAN_ROOTS = (Path("/root"), Path("/opt"), Path("/srv"))
PRUNE_NAMES = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache",
    ".npm", ".cargo", ".rustup",
}
PROTECTED_PREFIXES = (
    "/root/ck-nexus-q10-canonical",
    "/root/ck-nexus-q10-evidence",
    "/root/ck-nexus-helper-evidence",
    "/root/ck-nexus-master-controller-v1",
    "/opt/viro/q10-online",
    "/root/.ssh",
    "/root/.config/gh",
)
SECRET_HINTS = (
    "hosts.yml", ".ssh/", ".env", "secret", "token", "credential",
    "id_rsa", "id_ed25519", "private_key",
)


def run(args: list[str], timeout: int = 30) -> dict[str, object]:
    try:
        proc = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "rc": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"rc": -1, "stdout": "", "stderr": type(exc).__name__}


def safe_stat(path: Path) -> dict[str, object]:
    try:
        st = path.stat()
        return {
            "path": str(path),
            "size": st.st_size,
            "mode": oct(stat.S_IMODE(st.st_mode)),
            "owner": pwd.getpwuid(st.st_uid).pw_name,
            "group": grp.getgrgid(st.st_gid).gr_name,
            "mtime": datetime.fromtimestamp(st.st_mtime, UTC).isoformat(),
        }
    except Exception as exc:
        return {"path": str(path), "error": type(exc).__name__}


def dir_size(path: Path) -> int | None:
    result = run(["du", "-x", "-s", "-B1", str(path)], timeout=120)
    if result["rc"] != 0:
        return None
    try:
        return int(str(result["stdout"]).split()[0])
    except Exception:
        return None


def protected(path: Path) -> bool:
    p = str(path)
    return any(p == prefix or p.startswith(prefix + "/") for prefix in PROTECTED_PREFIXES)


def secret_like(path: Path) -> bool:
    low = str(path).lower()
    return any(hint.lower() in low for hint in SECRET_HINTS)


def find_git_repos() -> list[Path]:
    repos: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for current, dirs, _files in os.walk(root):
            cur = Path(current)
            dirs[:] = [
                name for name in dirs
                if name not in PRUNE_NAMES or name == ".git"
            ]
            if ".git" in dirs:
                repos.add(cur)
                dirs.remove(".git")
            if len(cur.parts) - len(root.parts) >= 5:
                dirs[:] = []
    return sorted(repos)


def git_repo_info(repo: Path) -> dict[str, object]:
    def git(*parts: str) -> dict[str, object]:
        return run(["git", "-C", str(repo), *parts], timeout=30)

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    status_result = git("status", "--porcelain=v1", "--untracked-files=normal")
    status_lines = str(status_result["stdout"]).splitlines() if status_result["rc"] == 0 else []
    remote = git("remote", "get-url", "origin")
    return {
        "path": str(repo),
        "protected": protected(repo),
        "size_bytes": dir_size(repo),
        "head": head["stdout"] if head["rc"] == 0 else None,
        "tree": tree["stdout"] if tree["rc"] == 0 else None,
        "branch": branch["stdout"] if branch["rc"] == 0 else None,
        "dirty_entries": len(status_lines),
        "dirty_sample": status_lines[:30],
        "origin": remote["stdout"] if remote["rc"] == 0 else None,
    }


def top_level_storage() -> list[dict[str, object]]:
    rows = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        try:
            children = sorted(root.iterdir(), key=lambda p: p.name)
        except Exception:
            continue
        for child in children:
            if child.is_dir():
                rows.append({
                    "path": str(child),
                    "size_bytes": dir_size(child),
                    "protected": protected(child),
                    "recommendation": (
                        "KEEP_PROTECTED" if protected(child)
                        else "REVIEW_STORAGE"
                    ),
                })
            else:
                item = safe_stat(child)
                item["protected"] = protected(child)
                item["recommendation"] = (
                    "KEEP_PROTECTED" if protected(child)
                    else "REVIEW_FILE"
                )
                rows.append(item)
    return rows


def duplicate_scan() -> list[dict[str, object]]:
    by_size: dict[int, list[Path]] = defaultdict(list)
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            cur = Path(current)
            dirs[:] = [d for d in dirs if d not in PRUNE_NAMES]
            if protected(cur) or secret_like(cur):
                dirs[:] = []
                continue
            for name in files:
                path = cur / name
                if secret_like(path):
                    continue
                try:
                    size = path.stat().st_size
                except Exception:
                    continue
                if 0 < size <= 50 * 1024 * 1024:
                    by_size[size].append(path)

    digest_map: dict[str, list[str]] = defaultdict(list)
    for _size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                h = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        h.update(chunk)
                digest_map[h.hexdigest()].append(str(path))
            except Exception:
                continue
    return [
        {"sha256": digest, "paths": paths}
        for digest, paths in digest_map.items()
        if len(paths) > 1
    ]


def large_files() -> list[dict[str, object]]:
    rows = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            cur = Path(current)
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules"}]
            for name in files:
                path = cur / name
                if secret_like(path):
                    continue
                try:
                    size = path.stat().st_size
                except Exception:
                    continue
                if size >= 100 * 1024 * 1024:
                    rows.append({
                        "path": str(path),
                        "size_bytes": size,
                        "protected": protected(path),
                    })
    return sorted(rows, key=lambda item: int(item["size_bytes"]), reverse=True)


def credential_metadata() -> list[dict[str, object]]:
    paths = [
        Path("/root/.config/gh/hosts.yml"),
        Path("/root/.ssh/authorized_keys"),
        Path("/root/.ssh/id_rsa"),
        Path("/root/.ssh/id_ed25519"),
    ]
    return [safe_stat(path) for path in paths if path.exists()]


def zombies() -> dict[str, object]:
    result = run(["ps", "-eo", "pid=,ppid=,stat=,comm=,args="])
    lines = []
    parents = Counter()
    if result["rc"] == 0:
        for line in str(result["stdout"]).splitlines():
            parts = line.strip().split(None, 4)
            if len(parts) < 4:
                continue
            pid, ppid, state, comm = parts[:4]
            if "Z" in state:
                lines.append({
                    "pid": pid,
                    "ppid": ppid,
                    "state": state,
                    "comm": comm,
                })
                parents[ppid] += 1
    return {
        "count": len(lines),
        "parent_counts": dict(parents.most_common(20)),
        "sample": lines[:100],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report: dict[str, object] = {
        "schema_version": 1,
        "kind": "CKNEXUS_VPS_READ_ONLY_RETENTION_AUDIT",
        "created_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "deletion_performed": False,
        "system": {
            "uname": run(["uname", "-a"]),
            "os_release": run(["cat", "/etc/os-release"]),
            "uptime": run(["uptime"]),
            "disk": run(["df", "-hP"]),
            "inodes": run(["df", "-iP"]),
            "memory": run(["free", "-h"]),
            "failed_services": run(["systemctl", "--failed", "--no-pager"]),
            "updates": run(["apt", "list", "--upgradable"], timeout=60),
        },
        "zombies": zombies(),
        "git_repositories": [git_repo_info(repo) for repo in find_git_repos()],
        "top_level_storage": top_level_storage(),
        "large_files_100mb_plus": large_files(),
        "duplicate_groups_unprotected": duplicate_scan(),
        "credential_file_metadata_only": credential_metadata(),
        "docker": {
            "version": run(["docker", "--version"]),
            "system_df": run(["docker", "system", "df"]),
            "containers": run([
                "docker", "ps", "-a",
                "--format", "{{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}",
            ]),
            "images": run([
                "docker", "images",
                "--format", "{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.Size}}",
            ]),
            "volumes": run(["docker", "volume", "ls", "--format", "{{.Name}}"]),
        },
        "protected_paths": list(PROTECTED_PREFIXES),
        "policy": {
            "keep_protected": True,
            "do_not_read_secret_contents": True,
            "do_not_delete": True,
            "cleanup_requires_separate_human_review": True,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(json.dumps({
        "status": "AUDIT_COMPLETE_READ_ONLY",
        "output": str(output),
        "sha256": digest,
        "git_repositories": len(report["git_repositories"]),
        "zombies": report["zombies"]["count"],
        "large_files_100mb_plus": len(report["large_files_100mb_plus"]),
        "duplicate_groups_unprotected": len(report["duplicate_groups_unprotected"]),
        "deletion_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
