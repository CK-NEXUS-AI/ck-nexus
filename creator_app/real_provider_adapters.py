from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import Request, urlopen

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.provider_router import ProviderCapabilities, ProviderKind

_SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
)


class ProviderBoundaryViolation(ValueError):
    pass


def sanitize_outbound_prompt(prompt: str) -> str:
    text = prompt.strip()
    if not text:
        raise ValueError("provider prompt cannot be empty")
    if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
        raise ProviderBoundaryViolation(
            "outbound prompt contains credential-like material"
        )
    return text


def _extract_openai_text(payload: dict[str, Any]) -> str:
    direct = str(payload.get("output_text") or "").strip()
    if direct:
        return direct
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = str(message.get("content") or "").strip()
        if content:
            return content
    for item in payload.get("output") or []:
        for part in item.get("content") or []:
            text = str(part.get("text") or "").strip()
            if text:
                return text
    raise RuntimeError("provider response did not contain text output")


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    for block in payload.get("content") or []:
        if block.get("type") == "text":
            text = str(block.get("text") or "").strip()
            if text:
                return text
    raise RuntimeError("Anthropic response did not contain text output")


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    direct = str(payload.get("output_text") or "").strip()
    if direct:
        return direct
    outputs = payload.get("outputs") or payload.get("output") or []
    if isinstance(outputs, dict):
        outputs = [outputs]
    for item in outputs:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                return text
            content = item.get("content") or []
            if isinstance(content, dict):
                content = [content]
            for part in content:
                if isinstance(part, dict):
                    text = str(part.get("text") or "").strip()
                    if text:
                        return text
    raise RuntimeError("Gemini response did not contain text output")


@dataclass(frozen=True, slots=True)
class ProviderHTTPContract:
    provider_id: str
    endpoint: str
    credential_id: CredentialId
    model: str
    protocol: str
    max_output_tokens: int = 512

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("provider model is required")
        if self.max_output_tokens < 1 or self.max_output_tokens > 8192:
            raise ValueError("max_output_tokens must be within 1..8192")


class BrokeredHTTPProviderAdapter:
    kind = ProviderKind.CLOUD

    def __init__(
        self,
        broker: CredentialBroker,
        contract: ProviderHTTPContract,
        *,
        timeout_seconds: int = 90,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.broker = broker
        self.contract = contract
        self.name = contract.provider_id
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urlopen
        self.capabilities = ProviderCapabilities(
            features=frozenset({"text", "brokered-auth", "scoped-session"}),
            models=(contract.model,),
        )

    @property
    def credential_binding_id(self) -> str:
        return self.contract.credential_id.value

    @property
    def official_host(self) -> str:
        from urllib.parse import urlsplit

        return (urlsplit(self.contract.endpoint).hostname or "").lower()

    @property
    def consumer(self) -> str:
        return f"provider.{self.name}"

    def is_available(self) -> bool:
        return self.broker.is_configured(
            self.contract.credential_id, consumer=self.consumer
        )

    def _scoped_key(self) -> str:
        token = self.broker.issue_scoped_token(
            self.contract.credential_id,
            consumer=self.consumer,
            provider=self.name,
            scopes=frozenset({"inference.invoke"}),
            ttl_seconds=30,
            max_uses=1,
        )
        lease = self.broker.acquire_scoped(
            token.token,
            self.contract.credential_id,
            consumer=self.consumer,
            provider=self.name,
            required_scopes=frozenset({"inference.invoke"}),
        )
        return lease.reveal(consumer=self.consumer)

    def _request(self, prompt: str, key: str) -> Request:
        prompt = sanitize_outbound_prompt(prompt)
        c = self.contract
        if c.protocol == "gemini_interactions":
            body = {"model": c.model, "input": prompt, "store": False}
            headers = {"Content-Type": "application/json", "x-goog-api-key": key}
        elif c.protocol == "anthropic_messages":
            body = {
                "model": c.model,
                "max_tokens": c.max_output_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            headers = {
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }
        elif c.protocol == "openai_responses":
            body = {"model": c.model, "input": prompt}
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
        elif c.protocol == "openai_chat":
            body = {
                "model": c.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": c.max_output_tokens,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
        else:
            raise ValueError("unsupported provider protocol")
        return Request(
            c.endpoint, data=json.dumps(body).encode(), headers=headers, method="POST"
        )

    async def invoke(self, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError(f"{self.name} credential is not configured")
        key = self._scoped_key()
        request = self._request(prompt, key)

        def call() -> dict[str, Any]:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))

        payload = await asyncio.to_thread(call)
        if self.contract.protocol == "anthropic_messages":
            return _extract_anthropic_text(payload)
        if self.contract.protocol == "gemini_interactions":
            return _extract_gemini_text(payload)
        return _extract_openai_text(payload)


@dataclass(frozen=True, slots=True)
class ProviderProbeEvidence:
    provider: str
    model: str
    success: bool
    output_digest: str | None
    error_code: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "output_digest": self.output_digest,
            "error_code": self.error_code,
            "raw_output_stored": False,
        }


async def probe_provider(adapter: BrokeredHTTPProviderAdapter) -> ProviderProbeEvidence:
    try:
        output = await adapter.invoke("Reply with the single word OK.")
    except Exception as exc:
        return ProviderProbeEvidence(
            provider=adapter.name,
            model=adapter.contract.model,
            success=False,
            output_digest=None,
            error_code=type(exc).__name__,
        )
    return ProviderProbeEvidence(
        provider=adapter.name,
        model=adapter.contract.model,
        success=True,
        output_digest=hashlib.sha256(output.encode()).hexdigest(),
        error_code=None,
    )


def build_real_provider_adapter(
    provider_id: str,
    broker: CredentialBroker,
    *,
    model: str,
    timeout_seconds: int = 90,
    opener: Callable[..., Any] | None = None,
) -> BrokeredHTTPProviderAdapter:
    pid = provider_id.strip().lower()
    definitions = {
        "gemini": (
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            CredentialId.GEMINI_API_KEY,
            "gemini_interactions",
        ),
        "anthropic": (
            "https://api.anthropic.com/v1/messages",
            CredentialId.ANTHROPIC_API_KEY,
            "anthropic_messages",
        ),
        "groq": (
            "https://api.groq.com/openai/v1/responses",
            CredentialId.GROQ_API_KEY,
            "openai_responses",
        ),
        "deepseek": (
            "https://api.deepseek.com/chat/completions",
            CredentialId.DEEPSEEK_API_KEY,
            "openai_chat",
        ),
        "openrouter": (
            "https://openrouter.ai/api/v1/chat/completions",
            CredentialId.OPENROUTER_API_KEY,
            "openai_chat",
        ),
    }
    try:
        endpoint, credential_id, protocol = definitions[pid]
    except KeyError as exc:
        raise ValueError(f"unsupported real provider: {pid}") from exc
    return BrokeredHTTPProviderAdapter(
        broker,
        ProviderHTTPContract(pid, endpoint, credential_id, model, protocol),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
