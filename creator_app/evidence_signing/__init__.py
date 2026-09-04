"""CK-NEXUS evidence signing and chain-of-custody primitives."""

from .bundle import (
    REQUIRED_EVIDENCE_FILES,
    EvidenceBundleError,
    append_chain_event,
    build_evidence_bundle,
    record_system_signature,
    verify_evidence_bundle,
)
from .openssl_ed25519 import sign_and_verify_ed25519

__all__ = [
    "REQUIRED_EVIDENCE_FILES",
    "EvidenceBundleError",
    "append_chain_event",
    "build_evidence_bundle",
    "record_system_signature",
    "sign_and_verify_ed25519",
    "verify_evidence_bundle",
]
