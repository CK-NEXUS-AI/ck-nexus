from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StandardStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    CURRENT = "CURRENT"
    DEVELOPMENT = "DEVELOPMENT"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class StandardRecord:
    key: str
    title: str
    version: str
    status: StandardStatus
    note: str


class StandardsBaseline:
    """Small, explicit truth table for standards that influence CK-NEXUS.

    This is not a compliance certificate. It only records the currently known
    publication state so stale references can be detected before design claims are made.
    """

    _RECORDS = {
        "nist_ai_600_1": StandardRecord(
            key="nist_ai_600_1",
            title="NIST AI RMF Generative AI Profile",
            version="NIST.AI.600-1",
            status=StandardStatus.PUBLISHED,
            note="published profile; updated NIST page in 2026 does not make it a new version",
        ),
        "nist_cyber_ai_profile": StandardRecord(
            key="nist_cyber_ai_profile",
            title="NIST Cyber AI Profile",
            version="preliminary/draft workstream",
            status=StandardStatus.DEVELOPMENT,
            note="do not claim final compliance mapping until NIST publishes a final profile",
        ),
        "owasp_agentic_top10_2026": StandardRecord(
            key="owasp_agentic_top10_2026",
            title="OWASP Top 10 for Agentic Applications",
            version="2026",
            status=StandardStatus.CURRENT,
            note="agentic risk baseline for autonomous/multi-step systems",
        ),
        "owasp_llm_top10_2026": StandardRecord(
            key="owasp_llm_top10_2026",
            title="OWASP GenAI LLM Top 10",
            version="2026",
            status=StandardStatus.CURRENT,
            note="latest LLM application risk baseline published August 2026",
        ),
        "microsoft_agent_framework": StandardRecord(
            key="microsoft_agent_framework",
            title="Microsoft Agent Framework",
            version="2026",
            status=StandardStatus.CURRENT,
            note="treat as successor path to AutoGen/Semantic Kernel for frontier comparisons",
        ),
    }

    @classmethod
    def get(cls, key: str) -> StandardRecord:
        if key not in cls._RECORDS:
            raise KeyError(f"unknown standard: {key}")
        return cls._RECORDS[key]

    @classmethod
    def all(cls) -> tuple[StandardRecord, ...]:
        return tuple(cls._RECORDS.values())
