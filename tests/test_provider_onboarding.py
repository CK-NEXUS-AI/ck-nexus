from dataclasses import dataclass

import pytest

from creator_app.provider_onboarding import (
    AuthMechanism, ProviderDescriptor, ProviderLifecycle, ProviderOnboardingRegistry, default_provider_catalog,
)
from creator_app.provider_router import ProviderCapabilities, ProviderKind


@dataclass
class FakeAdapter:
    name: str = "gemini"
    kind: ProviderKind = ProviderKind.CLOUD
    capabilities: ProviderCapabilities = ProviderCapabilities(features=frozenset({"text", "vision"}))
    available: bool = True
    def is_available(self): return self.available
    async def invoke(self, prompt: str): return "ok"


def registry():
    return ProviderOnboardingRegistry(default_provider_catalog())


def test_default_catalog_is_fail_closed():
    r=registry()
    assert len(r.all()) >= 6
    assert r.eligible_ids() == ()
    assert all(x.state is ProviderLifecycle.CONFIG_REQUIRED for x in r.all())


def test_authorize_verify_enable_sequence():
    r=registry()
    assert r.authorize("gemini", evidence_ref="auth:1").state is ProviderLifecycle.AUTHORIZED
    assert r.verify("gemini", evidence_ref="verify:1").state is ProviderLifecycle.VERIFIED
    assert r.enable("gemini", evidence_ref="enable:1").state is ProviderLifecycle.ENABLED
    assert r.eligible_ids(required_capabilities=("text",)) == ("gemini",)


def test_cannot_skip_verification():
    r=registry()
    with pytest.raises(RuntimeError): r.enable("gemini", evidence_ref="bad")


def test_quarantine_removes_eligibility():
    r=registry(); r.authorize("gemini", evidence_ref="a"); r.verify("gemini", evidence_ref="v")
    assert "gemini" in r.eligible_ids()
    r.quarantine("gemini", reason="schema drift", evidence_ref="q")
    assert "gemini" not in r.eligible_ids()


def test_bind_adapter_requires_verified_provider():
    r=registry()
    with pytest.raises(PermissionError): r.bind_adapter("gemini", FakeAdapter())
    r.authorize("gemini", evidence_ref="a"); r.verify("gemini", evidence_ref="v")
    assert r.bind_adapter("gemini", FakeAdapter()).name == "gemini"


def test_bind_adapter_rejects_identity_mismatch():
    r=registry(); r.authorize("gemini", evidence_ref="a"); r.verify("gemini", evidence_ref="v")
    with pytest.raises(ValueError): r.bind_adapter("gemini", FakeAdapter(name="other"))


def test_authenticated_descriptor_requires_broker_id():
    with pytest.raises(ValueError):
        ProviderDescriptor("x", "X", ProviderKind.CLOUD, AuthMechanism.API_KEY, frozenset({"text"}))


def test_evidence_is_append_only_metadata():
    r=registry(); r.authorize("gemini", evidence_ref="a"); r.verify("gemini", evidence_ref="v")
    item=r.get("gemini")
    assert item.evidence_refs == ("a", "v")
    assert not hasattr(item, "api_key")
