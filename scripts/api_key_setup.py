#!/usr/bin/env python3
"""Secure interactive CK-NEXUS API-key setup. Never prints secret values."""

from __future__ import annotations

import contextlib
import getpass
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

PROVIDERS = {
    "1": (
        "Qwen / Alibaba DashScope",
        Path("/etc/cknexus/qwen.env"),
        "DASHSCOPE_API_KEY",
        "cknexus-mcp.service",
    ),
    "2": (
        "Google Gemini",
        Path("/etc/cknexus/gemini.env"),
        "GEMINI_API_KEY",
        "cknexus-mcp.service",
    ),
    "3": ("OpenAI Admin API", Path("/root/.openai_admin_key"), None, None),
}
BLOCKED = {
    "4": "OpenAI standard API: ยังยืนยันไม่ได้ว่าบริการใดโหลด environment file นี้ จึงไม่บันทึกคีย์",
    "5": (
        "Alibaba Model Studio แยกไฟล์: cknexus-mcp.service มี free-only "
        "UnsetEnvironment ที่บล็อกคีย์นี้อยู่ ต้องอนุมัติการเปลี่ยนนโยบายก่อน"
    ),
    "6": "Ollama local: โดยทั่วไปไม่ต้องใช้ API Key สำหรับ local endpoint",
    "7": "Custom OpenAI-compatible: ต้องระบุบริการ/EnvironmentFile จริงก่อน จึงจะบันทึกได้",
}


def is_api_command(text: str) -> bool:
    return isinstance(text, str) and text.strip().casefold() == "api"


def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(tmp, 0, 0)
        os.replace(tmp, path)
        os.chmod(path, mode)
        os.chown(path, 0, 0)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


def _update_env(path: Path, variable: str, value: str) -> None:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", variable):
        raise ValueError("Invalid environment variable")
    if path.is_symlink():
        raise ValueError("Environment path must not be a symlink")
    if path.exists():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Environment path must be a regular file")
        if info.st_uid != 0:
            raise PermissionError("Environment file must be root-owned")
        old = path.read_text(encoding="utf-8")
    else:
        old = ""
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", value):
        raise ValueError(
            "API Key contains characters not accepted by the safe environment-file writer"
        )
    if path.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(f"{path.name}.backup-{stamp}")
        shutil.copy2(path, backup)
        os.chown(backup, 0, 0)
        os.chmod(backup, 0o600)
    lines = old.splitlines()
    replacement = f"{variable}={value}"
    found = False
    result = []
    for line in lines:
        if line.startswith(variable + "="):
            if not found:
                result.append(replacement)
                found = True
        else:
            result.append(line)
    if not found:
        result.append(replacement)
    content = ("\n".join(result).rstrip("\n") + "\n").encode("utf-8")
    _atomic_write(path, content)


def configure(choice: str, key: str) -> str:
    if not key or "\n" in key or "\r" in key or "\x00" in key:
        raise ValueError("API Key is empty or contains invalid control characters")
    if choice not in PROVIDERS:
        raise ValueError("Provider is not enabled for secure setup")
    name, path, variable, _service = PROVIDERS[choice]
    if choice == "3":
        if not key.startswith("sk-admin-"):
            raise ValueError("OpenAI Admin API Key must start with sk-admin-")
        _atomic_write(path, key.encode("utf-8"))
    else:
        _update_env(path, variable, key)
    return f"PASS: บันทึก {name} แล้ว (ไม่แสดงค่า Key); ตรวจสอบ permission/owner แล้ว"


def main() -> int:
    if os.geteuid() != 0:
        print("BLOCKED: กรุณาใช้ sudo api", file=sys.stderr)
        return 1
    print("CK-NEXUS — Secure API Key Setup")
    print("1) Qwen / Alibaba DashScope")
    print("2) Google Gemini")
    print("3) OpenAI Admin API (คงตำแหน่งเดิม /root/.openai_admin_key)")
    print("4) OpenAI standard API (BLOCKED until service mapping is verified)")
    print("5) Alibaba Model Studio separate key (BLOCKED by current free-only policy)")
    print("6) Ollama local (no key normally required)")
    print("7) Custom OpenAI-compatible (BLOCKED until service mapping is verified)")
    choice = input("เลือกหมายเลข หรือ q เพื่อยกเลิก: ").strip().casefold()
    if choice == "q":
        print("ยกเลิกแล้ว")
        return 0
    if choice in BLOCKED:
        print("BLOCKED: " + BLOCKED[choice])
        return 2
    if choice not in PROVIDERS:
        print("BLOCKED: ตัวเลือกไม่ถูกต้อง")
        return 2
    name, _path, _variable, service = PROVIDERS[choice]
    key = getpass.getpass(f"กรอก API Key สำหรับ {name} (ซ่อนขณะพิมพ์): ")
    try:
        print(configure(choice, key))
    except (OSError, ValueError, PermissionError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        key = ""
    if service:
        answer = input(f"ต้องการ restart {service} เพื่อโหลดค่าใหม่หรือไม่? [y/N]: ").strip().casefold()
        if answer == "y":
            result = subprocess.run(
                ["systemctl", "restart", service],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                print(
                    f"BLOCKED: restart failed (exit {result.returncode}); ตรวจ journal ของ service"
                )
                return 1
            active = subprocess.run(["systemctl", "is-active", "--quiet", service], check=False)
            if active.returncode:
                print("BLOCKED: service ไม่ active หลัง restart")
                return 1
            print(f"PASS: {service} active หลัง restart")
        else:
            print("NOT_TESTED: ยังไม่ได้ restart service; ค่าใหม่อาจยังไม่ถูกโหลด")
    print("NOT_TESTED: ยังไม่ได้ทดสอบ API จริง และไม่มีการเรียก API ที่อาจมีค่าใช้จ่าย")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
