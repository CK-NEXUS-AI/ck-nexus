"""CK-NEXUS untrusted-content defense."""

from .guard import GuardResult, inspect_untrusted_content

__all__ = ["GuardResult", "inspect_untrusted_content"]
