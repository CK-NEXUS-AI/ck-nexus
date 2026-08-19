"""Governed development-assistant discovery and execution contracts for CK-NEXUS.

The package catalogs approved open-source/free-entry developer assistants,
selects among locally installed tools, and builds fail-closed execution plans.
It never grants those assistants CK-NEXUS authority or executes them directly.
"""

from .evidence import ExecutionEvidence, digest_bytes
from .execution import (
    DevExecutionContract,
    ExecutionPolicy,
    ExecutionRequest,
    IsolationMode,
    NetworkMode,
)
from .orchestrator import DevAssistantFabric
from .registry import ASSISTANTS, AssistantSpec, AssistantStatus

__all__ = [
    "ASSISTANTS",
    "AssistantSpec",
    "AssistantStatus",
    "DevAssistantFabric",
    "DevExecutionContract",
    "ExecutionEvidence",
    "ExecutionPolicy",
    "ExecutionRequest",
    "IsolationMode",
    "NetworkMode",
    "digest_bytes",
]
