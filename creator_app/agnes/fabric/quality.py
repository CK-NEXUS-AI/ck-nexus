"""Adaptive quality selection driven by resource evidence."""

from .models import ResourceSnapshot, RuntimeDecision

PROFILES = ("ECO", "BALANCED", "QUALITY", "STUDIO", "SOVEREIGN")


def select_runtime_decision(
    resource: ResourceSnapshot,
    *,
    sovereign: bool = False,
    requested_quality: str = "AUTO",
) -> RuntimeDecision:
    reasons: list[str] = []
    if sovereign:
        return RuntimeDecision("SOVEREIGN", "COOL", 1, ("SOVEREIGN_POLICY",))

    missing = []
    if resource.memory_psi_avg10 is None:
        missing.append("MISSING_MEMORY_PSI")
    if resource.available_ram_bytes is None:
        missing.append("MISSING_AVAILABLE_RAM")
    if resource.thermal_celsius is None:
        missing.append("MISSING_THERMAL")
    if missing:
        return RuntimeDecision("ECO", "COLD", 1, tuple(missing))

    pressure = resource.memory_psi_avg10
    thermal = resource.thermal_celsius
    available = resource.available_ram_bytes

    if pressure >= 20.0:
        reasons.append("HIGH_MEMORY_PSI")
    if thermal >= 70.0:
        reasons.append("HIGH_THERMAL")
    if available < 1_500_000_000:
        reasons.append("LOW_AVAILABLE_RAM")

    if reasons:
        return RuntimeDecision("ECO", "COOL", 1, tuple(reasons))

    if requested_quality in PROFILES and requested_quality != "SOVEREIGN":
        concurrency = 1 if requested_quality == "STUDIO" else 2
        tier = "WARM" if requested_quality in {"QUALITY", "STUDIO"} else "HOT"
        return RuntimeDecision(requested_quality, tier, concurrency, ("EXPLICIT_REQUEST",))

    if available >= 8_000_000_000 and pressure < 1.0:
        return RuntimeDecision("QUALITY", "WARM", 3, ("RESOURCE_HEADROOM",))
    return RuntimeDecision("BALANCED", "HOT", 2, ("DEFAULT_AUTO",))
