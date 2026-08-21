from __future__ import annotations

from pathlib import Path

from creator_app.agnes.execution.sandbox.platform import (
    SandboxPlatformProfile,
    detect_platform_profile,
)


def test_linux_profile_preserves_existing_roots() -> None:
    profile = detect_platform_profile({})
    assert profile.name == "linux"
    assert profile.allows_executable("/usr/bin/python")
    assert not profile.allows_executable("/tmp/python")


def test_termux_profile_is_narrow_and_canonical() -> None:
    profile = detect_platform_profile({"PREFIX": "/data/data/com.termux/files/usr"})
    assert profile.name == "termux_android"
    assert profile.allows_executable("/data/data/com.termux/files/usr/bin/python")
    assert not profile.allows_executable("/data/data/com.termux/files/home/python")
    assert profile.virtual_root_map == (
        (Path("/data/data/com.termux/files/usr"), "/opt/ck-termux-root"),
    )
