from __future__ import annotations

from .catalog import KnowledgeCatalog
from .control_fabric_snapshot import universal_control_catalog
from .infrastructure_control_snapshot import infrastructure_control_catalog
from .research_snapshot import initial_catalog
from .standards_snapshot import standards_catalog

_SUPERSEDED_IDS = frozenset(
    {
        "control.protocol.mcp",
        "control.protocol.a2a",
        "infra.observability.opentelemetry",
    }
)


def current_knowledge_catalog() -> KnowledgeCatalog:
    """Return the reconciled current knowledge view used for new decisions.

    Historical snapshots remain available for audit, but entries superseded by a newer
    exact-version standard are excluded from this decision view.
    """

    current = KnowledgeCatalog()
    catalogs = (
        initial_catalog(),
        universal_control_catalog(),
        infrastructure_control_catalog(),
        standards_catalog(),
    )
    for catalog in catalogs:
        for item in catalog.all():
            if item.item_id in _SUPERSEDED_IDS:
                continue
            current.add(item)
    return current


def superseded_item_ids() -> frozenset[str]:
    return _SUPERSEDED_IDS
