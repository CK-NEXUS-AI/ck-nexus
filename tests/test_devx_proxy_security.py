from pathlib import Path


def test_legacy_devx_proxy_is_disabled_without_an_upstream_contract() -> None:
    source = Path("ops/vps/scripts/ck-nexus-devx-proxy.py").read_text(encoding="utf-8")

    assert 'self.send_error(410, "legacy development proxy disabled")' in source
    assert "HTTPConnection(" not in source
    assert "self.path" not in source
    assert "send_header(" not in source
    assert 'ThreadingHTTPServer(("127.0.0.1", 5690), H)' in source
