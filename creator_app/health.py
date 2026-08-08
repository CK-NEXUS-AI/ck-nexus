from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class HealthState(StrEnum):
    """Aggregate state exposed by the reliability layer."""

    LIVE = "live"
    READY = "ready"
    DEGRADED = "degraded"


class DependencyState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class HealthCause(StrEnum):
    PROCESS_NOT_LIVE = "PROCESS_NOT_LIVE"
    REQUIRED_DEPENDENCY_DEGRADED = "REQUIRED_DEPENDENCY_DEGRADED"
    REQUIRED_DEPENDENCY_UNAVAILABLE = "REQUIRED_DEPENDENCY_UNAVAILABLE"
    REQUIRED_DEPENDENCY_UNKNOWN = "REQUIRED_DEPENDENCY_UNKNOWN"
    REQUIRED_DEPENDENCY_DISABLED = "REQUIRED_DEPENDENCY_DISABLED"
    OPTIONAL_DEPENDENCY_DEGRADED = "OPTIONAL_DEPENDENCY_DEGRADED"
    OPTIONAL_DEPENDENCY_UNAVAILABLE = "OPTIONAL_DEPENDENCY_UNAVAILABLE"
    OPTIONAL_DEPENDENCY_UNKNOWN = "OPTIONAL_DEPENDENCY_UNKNOWN"


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    name: str
    state: DependencyState
    required: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("dependency name must not be empty")


@dataclass(frozen=True, slots=True)
class HealthReport:
    state: HealthState
    live: bool
    ready: bool
    degraded: bool
    dependencies: tuple[DependencyStatus, ...]
    causes: tuple[HealthCause, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a stable, secret-free structure suitable for health endpoints."""
        return {
            "state": self.state.value,
            "live": self.live,
            "ready": self.ready,
            "degraded": self.degraded,
            "causes": [cause.value for cause in self.causes],
            "dependencies": [
                {
                    "name": dependency.name,
                    "state": dependency.state.value,
                    "required": dependency.required,
                }
                for dependency in self.dependencies
            ],
        }


def evaluate_health(
    dependencies: Iterable[DependencyStatus] = (),
    *,
    process_live: bool = True,
) -> HealthReport:
    """Aggregate dependency observations without performing privileged recovery.

    Required dependency failures block readiness. Optional failures make the service
    degraded but do not block readiness. A disabled optional integration is expected
    and therefore does not degrade the service.
    """

    observed = tuple(dependencies)
    causes: list[HealthCause] = []

    if not process_live:
        causes.append(HealthCause.PROCESS_NOT_LIVE)

    for dependency in observed:
        if dependency.state is DependencyState.HEALTHY:
            continue
        if dependency.state is DependencyState.DISABLED and not dependency.required:
            continue

        if dependency.required:
            cause_by_state = {
                DependencyState.DEGRADED: HealthCause.REQUIRED_DEPENDENCY_DEGRADED,
                DependencyState.UNAVAILABLE: HealthCause.REQUIRED_DEPENDENCY_UNAVAILABLE,
                DependencyState.UNKNOWN: HealthCause.REQUIRED_DEPENDENCY_UNKNOWN,
                DependencyState.DISABLED: HealthCause.REQUIRED_DEPENDENCY_DISABLED,
            }
        else:
            cause_by_state = {
                DependencyState.DEGRADED: HealthCause.OPTIONAL_DEPENDENCY_DEGRADED,
                DependencyState.UNAVAILABLE: HealthCause.OPTIONAL_DEPENDENCY_UNAVAILABLE,
                DependencyState.UNKNOWN: HealthCause.OPTIONAL_DEPENDENCY_UNKNOWN,
            }
        cause = cause_by_state.get(dependency.state)
        if cause is not None:
            causes.append(cause)

    required_ready = all(
        dependency.state is DependencyState.HEALTHY
        for dependency in observed
        if dependency.required
    )
    ready = process_live and required_ready
    degraded = bool(causes)

    if degraded:
        state = HealthState.DEGRADED
    elif ready and observed:
        state = HealthState.READY
    else:
        state = HealthState.LIVE

    return HealthReport(
        state=state,
        live=process_live,
        ready=ready,
        degraded=degraded,
        dependencies=observed,
        causes=tuple(causes),
    )
