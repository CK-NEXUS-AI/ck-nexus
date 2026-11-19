from datetime import UTC, datetime

import pytest

from creator_app.channel_fabric import (
    ChannelIdentityBinding,
    ChannelKind,
    ChannelPolicy,
    authorize_ingress,
    normalize_envelope,
)


def make_envelope(**overrides):
    values = {
        "channel": "telegram",
        "event_id": "evt-1",
        "external_user_id": "user-7",
        "conversation_id": "chat-9",
        "text": "status",
        "received_at": datetime.now(UTC).isoformat(),
    }
    values.update(overrides)
    return normalize_envelope(**values)


def test_bound_identity_is_accepted_as_read_only_ingress():
    envelope = make_envelope()
    policy = ChannelPolicy(
        frozenset({ChannelKind.TELEGRAM}),
        (ChannelIdentityBinding(ChannelKind.TELEGRAM, "user-7", "owner:1"),),
    )
    result = authorize_ingress(envelope, policy)
    assert result.accepted and result.principal_id == "owner:1"
    assert result.reason == "identity_bound_read_only_ingress"


def test_unknown_channel_is_rejected():
    with pytest.raises(ValueError, match="unsupported channel"):
        make_envelope(channel="unknown")


def test_unbound_identity_is_rejected():
    result = authorize_ingress(
        make_envelope(), ChannelPolicy(frozenset({ChannelKind.TELEGRAM}), ())
    )
    assert not result.accepted and result.reason == "identity_unbound_or_ambiguous"


def test_duplicate_identity_binding_is_ambiguous_and_rejected():
    binding = ChannelIdentityBinding(ChannelKind.TELEGRAM, "user-7", "owner:1")
    policy = ChannelPolicy(frozenset({ChannelKind.TELEGRAM}), (binding, binding))
    assert authorize_ingress(make_envelope(), policy).reason == "identity_unbound_or_ambiguous"


def test_disabled_binding_is_rejected():
    binding = ChannelIdentityBinding(ChannelKind.TELEGRAM, "user-7", "owner:1", enabled=False)
    policy = ChannelPolicy(frozenset({ChannelKind.TELEGRAM}), (binding,))
    assert not authorize_ingress(make_envelope(), policy).accepted


def test_timezone_is_required():
    with pytest.raises(ValueError, match="timezone"):
        make_envelope(received_at="2026-11-01T12:00:00")


def test_oversized_message_is_rejected_by_envelope():
    with pytest.raises(ValueError, match="20000"):
        make_envelope(text="x" * 20_001)


def test_event_fingerprint_is_stable_and_excludes_message_text():
    policy = ChannelPolicy(frozenset({ChannelKind.TELEGRAM}), ())
    first, second = make_envelope(text="one"), make_envelope(text="different")
    assert (
        authorize_ingress(first, policy).event_fingerprint
        == authorize_ingress(second, policy).event_fingerprint
    )
