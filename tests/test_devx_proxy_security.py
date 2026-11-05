from pathlib import Path
from runpy import run_path
from unittest.mock import patch


SCRIPT = Path("ops/vps/scripts/ck-nexus-devx-proxy.py")


def test_legacy_devx_proxy_get_and_post_return_gone() -> None:
    namespace = run_path(str(SCRIPT))
    handler_type = namespace["H"]

    class StubHandler(handler_type):
        def __init__(self) -> None:
            self.errors: list[tuple[int, str | None]] = []

        def send_error(self, code: int, message: str | None = None, explain=None) -> None:
            self.errors.append((code, message))

    for method in ("do_GET", "do_POST"):
        handler = StubHandler()
        getattr(handler, method)()
        assert handler.errors == [(410, "legacy development proxy disabled")]


def test_legacy_devx_proxy_binds_only_to_loopback() -> None:
    with patch("http.server.ThreadingHTTPServer") as server_factory:
        namespace = run_path(str(SCRIPT), run_name="__main__")

    server_factory.assert_called_once_with(("127.0.0.1", 5690), namespace["H"])
    server_factory.return_value.serve_forever.assert_called_once_with()
