"""Memory tier placement policy."""

from __future__ import annotations

from .models import ResourceSnapshot


TIERS = ("HOT", "WARM", "COOL", "COLD")


def choose_memory_tier(resource: ResourceSnapshot, item_size_bytes: int) -> str:
    available = resource.available_ram_bytes
    if available is None:
        return "COOL"
    if item_size_bytes <= 0:
        return "HOT"
    pressure = resource.memory_psi_avg10 or 0.0
    ratio = item_size_bytes / max(available, 1)
    if pressure >= 20.0 or ratio >= 0.50:
        return "COLD"
    if pressure >= 5.0 or ratio >= 0.20:
        return "COOL"
    if ratio >= 0.05:
        return "WARM"
    return "HOT"
