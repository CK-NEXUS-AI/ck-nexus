from __future__ import annotations


def resolve_name(*, requested: str, extension: str, occupied: set[str]) -> str:
    """Resolve command/skill names deterministically without shadowing.

    User/project names keep precedence. Extension-provided names fall back to
    a namespaced form so capability discovery remains explicit and auditable.
    """

    if requested not in occupied:
        return requested
    candidate = f"{extension}.{requested}"
    index = 2
    while candidate in occupied:
        candidate = f"{extension}.{requested}.{index}"
        index += 1
    return candidate
