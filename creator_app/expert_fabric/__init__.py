"""Governed domain-expertise routing for AGNES.

Expert Fabric recommends existing agents and capabilities. It never grants
permissions, executes tools, or upgrades verification state.
"""

from .models import ExpertProfile, ExpertRoute, RiskClass
from .registry import ExpertRegistry, default_registry
from .router import ExpertRouter

__all__ = [
    "ExpertProfile",
    "ExpertRegistry",
    "ExpertRoute",
    "ExpertRouter",
    "RiskClass",
    "default_registry",
]
