from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path("ops/vps/scripts/ck-nexus-devx-proxy.py")
SPEC = importlib.util.spec_from_file_location("ck_nexus_devx_proxy", MODULE_PATH)
assert SPEC and SPEC.loader
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)


def test_proxy_accepts_only_origin_form_targets() -> None:
    assert proxy.validated_origin_target("/api/status?mode=read") == "/api/status?mode=read"
    assert proxy.validated_origin_target("http://attacker.invalid/path") is None
    assert proxy.validated_origin_target("//attacker.invalid/path") is None
    assert proxy.validated_origin_target("/safe\\\\host") is None
    assert proxy.validated_origin_target("/safe\r\nX-Injected: yes") is None
    assert proxy.validated_origin_target("/safe#fragment") is None


def test_proxy_response_headers_are_allowlisted_and_crlf_safe() -> None:
    headers = [
        ("Content-Type", "application/json"),
        ("X-Internal", "private"),
        ("Content-Type", "text/plain\r\nX-Injected: yes"),
        ("Content-Length", "12"),
    ]

    assert proxy.safe_response_headers(headers) == [
        ("Content-Type", "application/json"),
        ("Content-Length", "12"),
    ]
