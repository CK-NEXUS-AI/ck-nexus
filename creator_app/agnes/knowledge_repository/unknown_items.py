from __future__ import annotations

from dataclasses import replace

from .models import KnowledgeItem, KnowledgeSource, KnowledgeStatus


def collect_unknown(
    *,
    item_id: str,
    name: str,
    category: str,
    summary: str,
    usage: str,
    source: KnowledgeSource,
    relevance: tuple[str, ...] = (),
    observations: tuple[str, ...] = (),
    capabilities: tuple[str, ...] = (),
) -> KnowledgeItem:
    if not item_id.strip() or not name.strip() or not source.url.strip():
        raise ValueError("unknown items require id, name, and source url")
    return KnowledgeItem(
        item_id=item_id,
        name=name,
        category=category,
        summary=summary,
        usage=usage,
        status=KnowledgeStatus.PENDING_REVIEW,
        sources=(source,),
        relevance=relevance,
        observations=observations,
        capabilities=capabilities,
    )


def transition_status(item: KnowledgeItem, status: KnowledgeStatus) -> KnowledgeItem:
    allowed = {
        KnowledgeStatus.PENDING_REVIEW: {
            KnowledgeStatus.STUDYING,
            KnowledgeStatus.REJECTED,
        },
        KnowledgeStatus.STUDYING: {
            KnowledgeStatus.UNDERSTOOD,
            KnowledgeStatus.REJECTED,
        },
        KnowledgeStatus.UNDERSTOOD: {
            KnowledgeStatus.ADOPTABLE,
            KnowledgeStatus.REJECTED,
        },
        KnowledgeStatus.ADOPTABLE: {
            KnowledgeStatus.ADOPTED,
            KnowledgeStatus.REJECTED,
        },
        KnowledgeStatus.ADOPTED: set(),
        KnowledgeStatus.REJECTED: set(),
    }
    if status not in allowed[item.status]:
        raise ValueError(f"invalid knowledge status transition: {item.status} -> {status}")
    return replace(item, status=status)
