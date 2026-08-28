from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATHS = (
    ROOT / "scripts" / "gate_loop_prevention.py",
    ROOT / "scripts" / "p0_observability_check.py",
)


def load_script(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", MODULE_PATHS)
def test_probe_url_guard_accepts_only_loopback(path: Path) -> None:
    module = load_script(path)
    assert module.validate_base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert module.validate_base_url("http://[::1]:8000/") == "http://[::1]:8000"
    assert module.validate_base_url("http://localhost:8000/") == "http://localhost:8000"
    with pytest.raises(module.UnsafeBaseUrl):
        module.validate_base_url("https://example.com")


@pytest.mark.parametrize("path", MODULE_PATHS)
def test_probe_url_guard_refuses_redirects(path: Path) -> None:
    module = load_script(path)
    handler = module.NoRedirectHandler()
    with pytest.raises(module.UnsafeBaseUrl):
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {"Location": "https://example.com/"},
            "https://example.com/",
        )
