from __future__ import annotations

import pytest

from creator_app.credential_broker import (
    CredentialAccessDenied,
    CredentialBroker,
    CredentialId,
)


def broker() -> CredentialBroker:
    return CredentialBroker(
        environment={CredentialId.OPENAI_API_KEY: "secret-openai-key"}
    )


def test_scoped_token_is_opaque_and_redacted() -> None:
    b = broker()
    token = b.issue_scoped_token(
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        scopes=frozenset({"responses.create"}),
    )
    assert "secret-openai-key" not in token.token
    assert "secret-openai-key" not in repr(token)
    assert "<redacted>" in repr(token)


def test_scoped_token_is_consumer_provider_and_scope_bound() -> None:
    b = broker()
    token = b.issue_scoped_token(
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        scopes=frozenset({"responses.create"}),
        max_uses=2,
    )
    with pytest.raises(CredentialAccessDenied):
        b.acquire_scoped(
            token.token,
            CredentialId.OPENAI_API_KEY,
            consumer="provider.openai",
            provider="other",
            required_scopes=frozenset({"responses.create"}),
        )
    with pytest.raises(CredentialAccessDenied):
        b.acquire_scoped(
            token.token,
            CredentialId.OPENAI_API_KEY,
            consumer="provider.openai",
            provider="openai",
            required_scopes=frozenset({"files.read"}),
        )


def test_scoped_token_is_use_limited_and_revocable() -> None:
    b = broker()
    token = b.issue_scoped_token(
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        scopes=frozenset({"responses.create"}),
        max_uses=1,
    )
    lease = b.acquire_scoped(
        token.token,
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        required_scopes=frozenset({"responses.create"}),
    )
    assert lease.reveal(consumer="provider.openai") == "secret-openai-key"
    with pytest.raises(CredentialAccessDenied):
        b.acquire_scoped(
            token.token,
            CredentialId.OPENAI_API_KEY,
            consumer="provider.openai",
            provider="openai",
            required_scopes=frozenset({"responses.create"}),
        )


def test_scoped_token_binds_execution_context() -> None:
    b = broker()
    token = b.issue_scoped_token(
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        scopes=frozenset({"responses.create"}),
        task_id="task-1",
        run_id="run-1",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        risk_class="HIGH",
        network_scope="api.openai.com",
    )
    lease = b.acquire_scoped(
        token.token,
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        required_scopes=frozenset({"responses.create"}),
        task_id="task-1",
        run_id="run-1",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        risk_class="HIGH",
        network_scope="api.openai.com",
    )
    assert lease.reveal(consumer="provider.openai") == "secret-openai-key"


def test_scoped_token_rejects_wrong_execution_context() -> None:
    b = broker()
    token = b.issue_scoped_token(
        CredentialId.OPENAI_API_KEY,
        consumer="provider.openai",
        provider="openai",
        scopes=frozenset({"responses.create"}),
        task_id="task-1",
        tenant_id="tenant-1",
        network_scope="api.openai.com",
        max_uses=2,
    )
    with pytest.raises(CredentialAccessDenied, match="task_id binding mismatch"):
        b.acquire_scoped(
            token.token,
            CredentialId.OPENAI_API_KEY,
            consumer="provider.openai",
            provider="openai",
            required_scopes=frozenset({"responses.create"}),
            task_id="task-other",
            tenant_id="tenant-1",
            network_scope="api.openai.com",
        )
    with pytest.raises(CredentialAccessDenied, match="network_scope binding mismatch"):
        b.acquire_scoped(
            token.token,
            CredentialId.OPENAI_API_KEY,
            consumer="provider.openai",
            provider="openai",
            required_scopes=frozenset({"responses.create"}),
            task_id="task-1",
            tenant_id="tenant-1",
            network_scope="evil.example",
        )
