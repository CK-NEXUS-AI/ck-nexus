"""Compatibility helpers backed by the declarative R10 registry."""
from __future__ import annotations

from .registry import PatternRegistry


def initial_patterns():
    return PatternRegistry.from_file().all()
