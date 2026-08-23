from __future__ import annotations

import http.client
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit


class ZeroCostRuntimeUnavailable(RuntimeError):
    """Raised when a zero-API-credit runtime cannot be proven safe and local."""


class _HTTPResponseLike(Protocol):
    status: int

    def read(self) -> bytes: ...


class _HTTPConnectionLike(Protocol):
    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None: ...

    def getresponse(self) -> _HTTPResponseLike: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[[str, int, float], _HTTPConnectionLike]


def _default_connection_factory(host: str, port: int, timeout: float) -> _HTTPConnectionLike:
    return http.client.HTTPConnection(host, port, timeout=timeout)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class ZeroCostRuntimeStatus:
    enabled: bool
    provider: str
    ready: bool
    base_url: str
    model: str
    local_only: bool
    reason: str
    checked_at: str


class LocalOllamaRuntime:
    """Fail-closed Ollama runtime that accepts only proven local models.

    A loopback Ollama API can still proxy Ollama Cloud models. Therefore the
    zero-cost path verifies both the transport and the selected model before it
    is considered ready. Cloud-style model names and remote model metadata are
    rejected. No API key or cloud endpoint is used by this class.
    """

    provider = "ollama-local"
    default_base_url = "http://127.0.0.1:11434"
    default_timeout = 60.0

    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        model: str,
        timeout: float = default_timeout,
        connection_factory: ConnectionFactory = _default_connection_factory,
    ) -> None:
        self.enabled = bool(enabled)
        self.base_url = base_url.strip() or self.default_base_url
        self.model = model.strip()
        self.timeout = min(120.0, max(1.0, float(timeout)))
        self._connection_factory = connection_factory

    @classmethod
    def from_environment(cls) -> LocalOllamaRuntime:
        timeout_raw = os.getenv(
            "CKNEXUS_OLLAMA_TIMEOUT_SECONDS",
            str(cls.default_timeout),
        ).strip()
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = cls.default_timeout

        return cls(
            enabled=_env_bool("CKNEXUS_OLLAMA_ENABLED", False),
            base_url=os.getenv("OLLAMA_BASE_URL", cls.default_base_url),
            model=os.getenv("OLLAMA_MODEL", ""),
            timeout=timeout,
        )

    def status(self) -> ZeroCostRuntimeStatus:
        checked_at = datetime.now(UTC).isoformat()
        if not self.enabled:
            return self._status(False, "disabled", checked_at)
        if not self.model:
            return self._status(False, "OLLAMA_MODEL is not configured", checked_at)
        if self._looks_like_cloud_model(self.model):
            return self._status(
                False,
                "cloud model names are forbidden in zero-cost mode",
                checked_at,
            )

        endpoint = self._loopback_endpoint()
        if endpoint is None:
            return self._status(False, "OLLAMA_BASE_URL must be loopback-only HTTP", checked_at)
        host, port = endpoint

        try:
            payload = self._request_json(host, port, "GET", "/api/tags")
        except ZeroCostRuntimeUnavailable as exc:
            return self._status(False, str(exc), checked_at)

        models = payload.get("models")
        if not isinstance(models, list):
            return self._status(False, "invalid /api/tags response", checked_at)

        selected: dict[str, object] | None = None
        for raw in models:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name", ""))
            model = str(raw.get("model", ""))
            if self.model in {name, model}:
                selected = raw
                break

        if selected is None:
            return self._status(False, "configured model is not installed locally", checked_at)

        if selected.get("remote_model") or selected.get("remote_host"):
            return self._status(False, "remote/cloud model metadata is forbidden", checked_at)

        selected_name = str(selected.get("name", ""))
        selected_model = str(selected.get("model", ""))
        if self._looks_like_cloud_model(selected_name) or self._looks_like_cloud_model(
            selected_model
        ):
            return self._status(False, "cloud model is forbidden in zero-cost mode", checked_at)

        digest = str(selected.get("digest", "")).strip()
        size = selected.get("size")
        if not digest or not isinstance(size, int | float) or size <= 0:
            return self._status(False, "local model metadata is incomplete", checked_at)

        return self._status(True, "verified local Ollama model", checked_at)

    def chat(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        status = self.status()
        if not status.ready:
            raise ZeroCostRuntimeUnavailable(status.reason)

        endpoint = self._loopback_endpoint()
        if endpoint is None:
            raise ZeroCostRuntimeUnavailable("loopback endpoint validation failed")
        host, port = endpoint

        payload = self._request_json(
            host,
            port,
            "POST",
            "/api/chat",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ZeroCostRuntimeUnavailable("invalid local chat response")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ZeroCostRuntimeUnavailable("empty local chat response")
        return content

    def _request_json(
        self,
        host: str,
        port: int,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        connection = self._connection_factory(host, port, self.timeout)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        except (OSError, TimeoutError, http.client.HTTPException) as exc:
            raise ZeroCostRuntimeUnavailable(type(exc).__name__) from exc
        finally:
            connection.close()

        if response.status != 200:
            raise ZeroCostRuntimeUnavailable(f"local Ollama HTTP {response.status}")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZeroCostRuntimeUnavailable("invalid local Ollama JSON") from exc
        if not isinstance(decoded, dict):
            raise ZeroCostRuntimeUnavailable("invalid local Ollama response schema")
        return decoded

    def _loopback_endpoint(self) -> tuple[str, int] | None:
        try:
            parsed = urlsplit(self.base_url)
            port = parsed.port or 11434
        except ValueError:
            return None

        if parsed.scheme.lower() != "http":
            return None
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return None
        if parsed.path not in {"", "/"}:
            return None
        if not 1 <= port <= 65535:
            return None

        host = (parsed.hostname or "").lower()
        if host == "localhost":
            host = "127.0.0.1"
        if host not in {"127.0.0.1", "::1"}:
            return None
        return host, port

    @staticmethod
    def _looks_like_cloud_model(model: str) -> bool:
        value = model.strip().lower()
        return value.endswith("-cloud") or value.endswith(":cloud")

    def _status(self, ready: bool, reason: str, checked_at: str) -> ZeroCostRuntimeStatus:
        return ZeroCostRuntimeStatus(
            enabled=self.enabled,
            provider=self.provider,
            ready=ready,
            base_url=self.base_url,
            model=self.model,
            local_only=True,
            reason=reason,
            checked_at=checked_at,
        )
