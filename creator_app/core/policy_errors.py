from __future__ import annotations


class PolicyViolation(PermissionError):
    """A governed action violated an explicit CK-NEXUS policy contract."""


class BudgetExceeded(ValueError):
    """A governed dispatch would exceed a declared budget or concurrency ceiling."""
