"""Policy-first ingress contracts for multi-channel CK-NEXUS control."""

from .contracts import (
    ChannelEnvelope,
    ChannelIdentityBinding,
    ChannelKind,
    ChannelPolicy,
    IngressDecision,
    authorize_ingress,
    normalize_envelope,
)

__all__ = [
    "ChannelKind",
    "ChannelEnvelope",
    "ChannelIdentityBinding",
    "ChannelPolicy",
    "IngressDecision",
    "authorize_ingress",
    "normalize_envelope",
]
