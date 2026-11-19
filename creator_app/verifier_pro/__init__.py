"""CK-NEXUS Verifier Pro development-only subject and gap-analysis primitives."""

from .gap_analysis import GapDecision, GapStatus, SubjectGapAnalyzer
from .subject import SubjectComponent, VerificationSubject

__all__ = [
    "GapDecision",
    "GapStatus",
    "SubjectComponent",
    "SubjectGapAnalyzer",
    "VerificationSubject",
]
