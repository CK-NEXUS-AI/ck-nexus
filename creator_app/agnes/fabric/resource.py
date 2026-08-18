"""Portable, read-only resource telemetry used by AGNES policy decisions."""

from __future__ import annotations

import os
from pathlib import Path

from .models import ResourceSnapshot


def _meminfo() -> tuple[int | None, int | None]:
    path = Path("/proc/meminfo")
    if not path.exists():
        return None, None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, None
    values: dict[str, int] = {}
    for line in lines:
        key, _, raw = line.partition(":")
        if not raw:
            continue
        token = raw.strip().split()[0]
        if token.isdigit():
            values[key] = int(token) * 1024
    return values.get("MemTotal"), values.get("MemAvailable")


def _psi(resource: str) -> float | None:
    path = Path("/proc/pressure") / resource
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.startswith("some "):
            continue
        fields = dict(item.split("=", 1) for item in line.split()[1:] if "=" in item)
        try:
            return float(fields["avg10"])
        except (KeyError, ValueError):
            return None
    return None


def _thermal() -> float | None:
    roots = sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
    values: list[float] = []
    for path in roots:
        try:
            raw = float(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        values.append(raw / 1000.0 if raw > 1000 else raw)
    return max(values) if values else None


def _zram_present() -> bool:
    try:
        return any(Path("/sys/block").glob("zram*"))
    except OSError:
        return False


def _cgroup_v2_present() -> bool:
    root = Path("/sys/fs/cgroup")
    return (root / "cgroup.controllers").exists()


def snapshot() -> ResourceSnapshot:
    total, available = _meminfo()
    try:
        load_1m = os.getloadavg()[0]
    except (AttributeError, OSError):
        load_1m = None
    return ResourceSnapshot(
        total_ram_bytes=total,
        available_ram_bytes=available,
        load_1m=load_1m,
        memory_psi_avg10=_psi("memory"),
        cpu_psi_avg10=_psi("cpu"),
        io_psi_avg10=_psi("io"),
        thermal_celsius=_thermal(),
        zram_present=_zram_present(),
        # A read-only probe cannot prove delegated controller enforcement.
        # Q12 must create a bounded child cgroup and verify actual limits/readback.
        writable_cgroup_v2=False,
        cgroup_v2_present=_cgroup_v2_present(),
    )
