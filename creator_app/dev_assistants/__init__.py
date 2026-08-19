"""Governed development-assistant discovery for CK-NEXUS.

The package catalogs approved open-source/free-entry developer assistants and
selects among locally installed tools. It never grants those assistants CK-NEXUS
authority and does not install or execute third-party software by itself.
"""

from .orchestrator import DevAssistantFabric
from .registry import ASSISTANTS, AssistantSpec, AssistantStatus

__all__ = ["ASSISTANTS", "AssistantSpec", "AssistantStatus", "DevAssistantFabric"]
