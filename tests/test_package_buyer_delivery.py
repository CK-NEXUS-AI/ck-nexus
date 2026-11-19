from pathlib import Path

from scripts.package_buyer_delivery import safe_tracked_file


def test_buyer_delivery_excludes_private_and_runtime_files() -> None:
    excluded = (
        Path(".env"),
        Path(".env.production"),
        Path("secrets/client_secret.json"),
        Path("keys/signing.pem"),
        Path("runtime/state.sqlite3"),
        Path("node_modules/package/index.js"),
        Path("dist/archive.zip"),
    )
    assert all(not safe_tracked_file(path) for path in excluded)


def test_buyer_delivery_keeps_safe_templates_and_source() -> None:
    included = (
        Path(".env.example"),
        Path("creator_app/brain/runtime.py"),
        Path("docs/SECURITY.md"),
        Path("integrations/bridge/src/index.ts"),
    )
    assert all(safe_tracked_file(path) for path in included)
