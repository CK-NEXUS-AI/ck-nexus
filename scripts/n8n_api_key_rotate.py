#!/usr/bin/env python3
"""Safely adopt a newly created n8n API key after verifying it against local n8n.

n8n itself issues/revokes API keys in Settings > n8n API. This helper validates
and atomically propagates a replacement to CK-NEXUS consumers; it never logs
key material and never revokes the old key automatically.
"""
from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import os
import stat
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

KEY_FILE = Path('/root/.config/n8n/api_key')
API_URL = 'http://127.0.0.1:5678/api/v1/workflows?limit=1'
TIMEOUT = 8


def validate_key(key: str) -> tuple[bool, str]:
    if not key or any(c in key for c in '\r\n\x00'):
        return False, 'invalid_input'
    request = urllib.request.Request(
        API_URL,
        headers={'X-N8N-API-KEY': key, 'Accept': 'application/json'},
        method='GET',
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return False, f'http_{response.status}'
            data = json.loads(response.read(1_000_000))
            if not isinstance(data, dict) or not isinstance(data.get('data'), list):
                return False, 'invalid_response_shape'
            return True, 'verified'
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        return False, f'http_{status}'
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, 'connection_error'
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, 'invalid_json'


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RuntimeError('refusing symlink key path')
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=str(path.parent))
    tmp = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(tmp, 0, 0)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
        os.chown(path, 0, 0)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


def rotate(path: Path, candidate: str) -> tuple[bool, str]:
    if os.geteuid() != 0:
        return False, 'must_run_as_root'
    ok, reason = validate_key(candidate)
    if not ok:
        return False, f'candidate_rejected_{reason}'
    old = path.read_bytes() if path.exists() else None
    backup = None
    if old is not None:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0:
            return False, 'unsafe_existing_key_file'
        stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
        backup = path.with_name(f'{path.name}.backup-{stamp}')
        # Exclusive creation avoids overwriting a previous backup.
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, old)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.chown(backup, 0, 0)
        os.chmod(backup, 0o600)
    try:
        atomic_write(path, candidate.encode('utf-8'))
        ok_after, reason_after = validate_key(path.read_text(encoding='utf-8').strip())
        if not ok_after:
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old)
            return False, f'post_write_verification_failed_{reason_after}'
    except Exception:
        if old is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, old)
        raise
    return True, 'rotated_and_verified'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate or safely adopt a replacement n8n API key'
    )
    parser.add_argument(
        '--check', action='store_true', help='validate installed key without changing files'
    )
    args = parser.parse_args()
    if os.geteuid() != 0:
        print('BLOCKED: run as root')
        return 1
    if args.check:
        try:
            current = KEY_FILE.read_text(encoding='utf-8').strip()
        except OSError:
            print('FAIL: installed_key_unreadable')
            return 1
        ok, reason = validate_key(current)
        print('PASS: installed_key_verified' if ok else f'FAIL: installed_key_{reason}')
        return 0 if ok else 2
    print('CK-NEXUS n8n API key adoption')
    print('Create a replacement key in n8n Settings > n8n API first.')
    print('The candidate is tested against local n8n before the current file is changed.')
    candidate = getpass.getpass('Paste replacement n8n API key (hidden): ').strip()
    if not candidate:
        print('BLOCKED: empty candidate')
        return 2
    try:
        ok, status = rotate(KEY_FILE, candidate)
    except Exception as exc:
        print(f'FAIL: {type(exc).__name__}; key file was restored if a prior key existed')
        return 1
    finally:
        candidate = ''
    print(('PASS: ' if ok else 'BLOCKED: ') + status)
    if ok:
        print('Consumers read the shared key file automatically; no service restart required.')
        print(
            'NOT_AUTOMATED: revoke the old key in n8n Settings > n8n API ' +
            'after confirming callers work.'
        )
        print('External Cloudflare 403 is a separate issue and is not changed by this script.')
        return 0
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
