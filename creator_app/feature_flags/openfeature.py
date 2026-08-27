"""Provider-neutral OpenFeature v0.9.0 evaluation bridge for CK-NEXUS.

This is not a feature-flag control plane or permission authority. It implements a
small, dependency-free evaluation boundary aligned with the stabilized
OpenFeature evaluation/provider contracts while keeping CK-NEXUS as the sole
authority for permissions, verification, release, and Production mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

OPENFEATURE_SPEC_VERSION = "0.9.0"


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("provider name must not be empty")


@dataclass(frozen=True, slots=True)
class ResolutionDetails:
    value: object
    reason: str = "STATIC"
    variant: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class FlagEvaluationDetails:
    flag_key: str
    value: object
    default_value: object
    provider_name: str
    reason: str
    variant: str | None
    error_code: str | None
    default_used: bool
    evidence_digest: str
    authority: str = "CK-NEXUS"
    permission_granted: bool = False
    verification_upgrade_allowed: bool = False
    production_mutation_allowed: bool = False


class FeatureProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata: ...

    def resolve_boolean_value(
        self,
        flag_key: str,
        default_value: bool,
        context: dict[str, object],
    ) -> ResolutionDetails: ...

    def resolve_string_value(
        self,
        flag_key: str,
        default_value: str,
        context: dict[str, object],
    ) -> ResolutionDetails: ...

    def resolve_number_value(
        self,
        flag_key: str,
        default_value: int | float,
        context: dict[str, object],
    ) -> ResolutionDetails: ...

    def resolve_object_value(
        self,
        flag_key: str,
        default_value: dict[str, object],
        context: dict[str, object],
    ) -> ResolutionDetails: ...


class NoOpProvider:
    """OpenFeature-style no-op provider: always resolves to the supplied default."""

    metadata = ProviderMetadata(name="ck-nexus-no-op")

    @staticmethod
    def _default(value: object) -> ResolutionDetails:
        return ResolutionDetails(value=value, reason="DEFAULT")

    def resolve_boolean_value(
        self,
        flag_key: str,
        default_value: bool,
        context: dict[str, object],
    ) -> ResolutionDetails:
        del flag_key, context
        return self._default(default_value)

    def resolve_string_value(
        self,
        flag_key: str,
        default_value: str,
        context: dict[str, object],
    ) -> ResolutionDetails:
        del flag_key, context
        return self._default(default_value)

    def resolve_number_value(
        self,
        flag_key: str,
        default_value: int | float,
        context: dict[str, object],
    ) -> ResolutionDetails:
        del flag_key, context
        return self._default(default_value)

    def resolve_object_value(
        self,
        flag_key: str,
        default_value: dict[str, object],
        context: dict[str, object],
    ) -> ResolutionDetails:
        del flag_key, context
        return self._default(default_value)


class OpenFeatureEvaluationBridge:
    """Typed flag evaluation with OpenFeature-compatible fail-safe defaults.

    Provider errors and type mismatches never escape from evaluation calls. The
    supplied default is returned instead, and the details object records why.
    """

    def __init__(self, provider: FeatureProvider | None = None) -> None:
        self._provider: FeatureProvider = provider or NoOpProvider()

    def get_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        context: dict[str, object] | None = None,
    ) -> FlagEvaluationDetails:
        if type(default_value) is not bool:
            raise TypeError("boolean default value must be bool")
        return self._evaluate(
            flag_key,
            default_value,
            context,
            self._provider.resolve_boolean_value,
            self._is_bool,
        )

    def get_string_details(
        self,
        flag_key: str,
        default_value: str,
        context: dict[str, object] | None = None,
    ) -> FlagEvaluationDetails:
        if not isinstance(default_value, str):
            raise TypeError("string default value must be str")
        return self._evaluate(
            flag_key,
            default_value,
            context,
            self._provider.resolve_string_value,
            self._is_string,
        )

    def get_number_details(
        self,
        flag_key: str,
        default_value: int | float,
        context: dict[str, object] | None = None,
    ) -> FlagEvaluationDetails:
        if not self._is_number(default_value):
            raise TypeError("number default value must be int or float, excluding bool")
        return self._evaluate(
            flag_key,
            default_value,
            context,
            self._provider.resolve_number_value,
            self._is_number,
        )

    def get_object_details(
        self,
        flag_key: str,
        default_value: dict[str, object],
        context: dict[str, object] | None = None,
    ) -> FlagEvaluationDetails:
        if not isinstance(default_value, dict):
            raise TypeError("object default value must be dict")
        return self._evaluate(
            flag_key,
            default_value,
            context,
            self._provider.resolve_object_value,
            self._is_object,
        )

    def get_boolean_value(
        self,
        flag_key: str,
        default_value: bool,
        context: dict[str, object] | None = None,
    ) -> bool:
        return bool(self.get_boolean_details(flag_key, default_value, context).value)

    def get_string_value(
        self,
        flag_key: str,
        default_value: str,
        context: dict[str, object] | None = None,
    ) -> str:
        return str(self.get_string_details(flag_key, default_value, context).value)

    def get_number_value(
        self,
        flag_key: str,
        default_value: int | float,
        context: dict[str, object] | None = None,
    ) -> int | float:
        details = self.get_number_details(flag_key, default_value, context)
        value = details.value
        if not self._is_number(value):
            return default_value
        return value

    def get_object_value(
        self,
        flag_key: str,
        default_value: dict[str, object],
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        details = self.get_object_details(flag_key, default_value, context)
        value = details.value
        if not isinstance(value, dict):
            return default_value
        return dict(value)

    def _evaluate(
        self,
        flag_key: str,
        default_value: object,
        context: dict[str, object] | None,
        resolver: Any,
        validator: Any,
    ) -> FlagEvaluationDetails:
        if not isinstance(flag_key, str) or not flag_key.strip():
            raise ValueError("flag_key must be a non-empty string")
        normalized_context = self._normalize_context(context)
        provider_name = self._provider.metadata.name

        try:
            resolution = resolver(flag_key, default_value, normalized_context)
            if not isinstance(resolution, ResolutionDetails):
                raise TypeError("provider returned invalid resolution details")
            if resolution.error_code:
                return self._fallback(
                    flag_key,
                    default_value,
                    provider_name,
                    normalized_context,
                    error_code=resolution.error_code,
                    reason=resolution.reason or "ERROR",
                )
            if not validator(resolution.value):
                return self._fallback(
                    flag_key,
                    default_value,
                    provider_name,
                    normalized_context,
                    error_code="TYPE_MISMATCH",
                    reason="ERROR",
                )
            return self._details(
                flag_key=flag_key,
                value=resolution.value,
                default_value=default_value,
                provider_name=provider_name,
                reason=resolution.reason or "STATIC",
                variant=resolution.variant,
                error_code=None,
                default_used=resolution.value == default_value,
                context=normalized_context,
            )
        except Exception as exc:  # evaluation must fail safe to the supplied default
            return self._fallback(
                flag_key,
                default_value,
                provider_name,
                normalized_context,
                error_code=self._error_code(exc),
                reason="ERROR",
            )

    def _fallback(
        self,
        flag_key: str,
        default_value: object,
        provider_name: str,
        context: dict[str, object],
        *,
        error_code: str,
        reason: str,
    ) -> FlagEvaluationDetails:
        return self._details(
            flag_key=flag_key,
            value=default_value,
            default_value=default_value,
            provider_name=provider_name,
            reason=reason,
            variant=None,
            error_code=error_code,
            default_used=True,
            context=context,
        )

    @staticmethod
    def _details(
        *,
        flag_key: str,
        value: object,
        default_value: object,
        provider_name: str,
        reason: str,
        variant: str | None,
        error_code: str | None,
        default_used: bool,
        context: dict[str, object],
    ) -> FlagEvaluationDetails:
        payload = {
            "spec_version": OPENFEATURE_SPEC_VERSION,
            "flag_key": flag_key,
            "value": value,
            "default_value": default_value,
            "provider_name": provider_name,
            "reason": reason,
            "variant": variant,
            "error_code": error_code,
            "default_used": default_used,
            "context": context,
            "authority": "CK-NEXUS",
            "permission_granted": False,
            "verification_upgrade_allowed": False,
            "production_mutation_allowed": False,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return FlagEvaluationDetails(
            flag_key=flag_key,
            value=value,
            default_value=default_value,
            provider_name=provider_name,
            reason=reason,
            variant=variant,
            error_code=error_code,
            default_used=default_used,
            evidence_digest=digest,
        )

    @staticmethod
    def _normalize_context(context: dict[str, object] | None) -> dict[str, object]:
        if context is None:
            return {}
        if not isinstance(context, dict):
            raise TypeError("evaluation context must be a dict")
        json.dumps(context, ensure_ascii=False, sort_keys=True)
        return dict(context)

    @staticmethod
    def _is_bool(value: object) -> bool:
        return type(value) is bool

    @staticmethod
    def _is_string(value: object) -> bool:
        return isinstance(value, str)

    @staticmethod
    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and type(value) is not bool

    @staticmethod
    def _is_object(value: object) -> bool:
        return isinstance(value, dict)

    @staticmethod
    def _error_code(exc: Exception) -> str:
        name = type(exc).__name__.upper()
        if "TIMEOUT" in name:
            return "GENERAL"
        if isinstance(exc, (TypeError, ValueError)):
            return "INVALID_CONTEXT"
        return "GENERAL"
