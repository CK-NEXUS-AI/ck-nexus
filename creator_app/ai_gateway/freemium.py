"""Governed zero-cost-first routing for CK-NEXUS development assistants.

This module extends the provider-agnostic gateway with deterministic freemium
selection. It does not fetch credentials, call provider APIs, or grant execution
authority. Runtime adapters remain responsible for transport and credential leases.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from .contracts import DataClass, GatewayRequest, ModelCapability


class FreemiumMode(StrEnum):
    ECONOMY = "economy"
    BALANCED = "balanced"
    QUALITY = "quality"
    PRIVATE = "private"
    REALTIME = "realtime"
    COUNCIL = "council"
    OFFLINE = "offline"


class LifecycleState(StrEnum):
    DISCOVERED = "DISCOVERED"
    CONNECTED = "CONNECTED"
    EXECUTED_UNVERIFIED = "EXECUTED_UNVERIFIED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True, slots=True)
class FreemiumLane:
    provider_id: str
    model_id: str
    capabilities: frozenset[ModelCapability]
    allowed_data_classes: frozenset[DataClass]
    lifecycle: LifecycleState = LifecycleState.DISCOVERED
    healthy: bool = True
    zero_cost: bool = True
    local: bool = False
    quality_score: int = 50
    latency_score: int = 50
    reliability_score: int = 50
    quota_remaining_ratio: float = 1.0
    paid_tool_risk: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise ValueError("provider_id and model_id must not be empty")
        for name, value in (
            ("quality_score", self.quality_score),
            ("latency_score", self.latency_score),
            ("reliability_score", self.reliability_score),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if not 0.0 <= self.quota_remaining_ratio <= 1.0:
            raise ValueError("quota_remaining_ratio must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class FreemiumDecision:
    primary: FreemiumLane
    verifier: FreemiumLane | None
    mode: FreemiumMode
    evidence: dict[str, object]


class NoFreemiumRoute(RuntimeError):
    """Raised when no lane satisfies capability, privacy, cost and lifecycle policy."""


class FreemiumIntelligenceMesh:
    """Deterministic zero-cost-first model selection with optional provider diversity."""

    def __init__(self, lanes: tuple[FreemiumLane, ...]) -> None:
        self._lanes = lanes

    @staticmethod
    def _eligible(lane: FreemiumLane, request: GatewayRequest, mode: FreemiumMode) -> bool:
        if not lane.healthy or lane.quota_remaining_ratio <= 0:
            return False
        if not request.required_capabilities.issubset(lane.capabilities):
            return False
        if request.data_class not in lane.allowed_data_classes:
            return False
        if request.allowed_providers and lane.provider_id not in request.allowed_providers:
            return False
        if lane.provider_id in request.denied_providers:
            return False
        if mode in {FreemiumMode.PRIVATE, FreemiumMode.OFFLINE} and not lane.local:
            return False
        if lane.paid_tool_risk and request.max_cost_tier == 0:
            return False
        if not lane.zero_cost and request.max_cost_tier == 0:
            return False
        if lane.lifecycle == LifecycleState.DISCOVERED:
            return False
        return True

    @staticmethod
    def _score(lane: FreemiumLane, mode: FreemiumMode) -> tuple[float, str, str]:
        weights = {
            FreemiumMode.ECONOMY: (15, 20, 15, 45, 5),
            FreemiumMode.BALANCED: (30, 25, 20, 20, 5),
            FreemiumMode.QUALITY: (45, 15, 25, 10, 5),
            FreemiumMode.PRIVATE: (20, 15, 20, 5, 40),
            FreemiumMode.REALTIME: (20, 45, 15, 15, 5),
            FreemiumMode.COUNCIL: (40, 15, 25, 15, 5),
            FreemiumMode.OFFLINE: (20, 10, 20, 5, 45),
        }[mode]
        quality_w, latency_w, reliability_w, quota_w, local_w = weights
        score = (
            lane.quality_score * quality_w
            + lane.latency_score * latency_w
            + lane.reliability_score * reliability_w
            + lane.quota_remaining_ratio * 100 * quota_w
            + (100 if lane.local else 0) * local_w
        ) / 100
        if lane.zero_cost:
            score += 10
        if lane.lifecycle == LifecycleState.VERIFIED:
            score += 8
        elif lane.lifecycle == LifecycleState.EXECUTED_UNVERIFIED:
            score += 3
        return (-score, lane.provider_id, lane.model_id)

    def route(self, request: GatewayRequest, mode: FreemiumMode) -> FreemiumDecision:
        eligible = [lane for lane in self._lanes if self._eligible(lane, request, mode)]
        if not eligible:
            raise NoFreemiumRoute("no freemium lane satisfies capability, privacy, quota and lifecycle policy")
        eligible.sort(key=lambda lane: self._score(lane, mode))
        primary = eligible[0]

        verifier: FreemiumLane | None = None
        if mode in {FreemiumMode.QUALITY, FreemiumMode.COUNCIL}:
            verifier = next(
                (lane for lane in eligible[1:] if lane.provider_id != primary.provider_id),
                None,
            )

        payload = {
            "mode": mode.value,
            "primary": {"provider_id": primary.provider_id, "model_id": primary.model_id},
            "verifier": (
                {"provider_id": verifier.provider_id, "model_id": verifier.model_id}
                if verifier
                else None
            ),
            "candidate_count": len(eligible),
            "required_capabilities": sorted(item.value for item in request.required_capabilities),
            "data_class": request.data_class.value,
            "zero_cost_first": True,
            "cross_provider_verifier_required": mode in {FreemiumMode.QUALITY, FreemiumMode.COUNCIL},
            "cross_provider_verifier_available": verifier is not None,
            "authority": "CK-NEXUS",
            "credential_material_in_route": False,
            "production_mutation": False,
            "production_ready": False,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return FreemiumDecision(
            primary=primary,
            verifier=verifier,
            mode=mode,
            evidence={**payload, "route_digest": digest},
        )
