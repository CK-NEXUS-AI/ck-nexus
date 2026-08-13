from __future__ import annotations

import re

from creator_app.connector_fabric.models import RiskClass

_DESTRUCTIVE = re.compile(
    r"(^|[._-])(delete|destroy|drop|purge|erase|wipe|revoke|terminate|remove)([._-]|$)",
    re.IGNORECASE,
)
_WRITE = re.compile(
    r"(^|[._-])(create|update|write|send|post|put|patch|execute|run|commit|push|merge|deploy|approve|invite|upload|set)([._-]|$)",
    re.IGNORECASE,
)
_READISH = re.compile(
    r"(^|[._-])(get|list|read|search|find|query|status|inspect|describe|fetch|lookup|health)([._-]|$)",
    re.IGNORECASE,
)


def classify_mcp_tool(name: str, annotations: dict) -> RiskClass:
    if annotations.get("destructiveHint") is True or _DESTRUCTIVE.search(name):
        return RiskClass.DESTRUCTIVE
    if _WRITE.search(name):
        return RiskClass.WRITE
    # Per MCP guidance, annotations from an untrusted server are only advisory. We use
    # readOnlyHint only together with a conservative read-oriented name.
    if annotations.get("readOnlyHint") is True and _READISH.search(name):
        return RiskClass.READ_ONLY
    return RiskClass.UNKNOWN


def classify_openapi_operation(method: str, operation_id: str) -> RiskClass:
    method = method.upper()
    if method in {"GET", "HEAD", "OPTIONS"}:
        return RiskClass.READ_ONLY
    if method == "DELETE" or _DESTRUCTIVE.search(operation_id):
        return RiskClass.DESTRUCTIVE
    return RiskClass.WRITE
