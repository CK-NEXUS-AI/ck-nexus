"""Tests สำหรับ Autoscale ทั้งหมด — Pool + Health + Provision + Orchestrator."""

from __future__ import annotations

import tempfile

import pytest

from creator_app.credentials.autoscale.auto_provisioner import AutoProvisioner
from creator_app.credentials.autoscale.free_provider_registry import FreeProviderRegistry
from creator_app.credentials.autoscale.key_health_monitor import KeyHealthMonitor
from creator_app.credentials.autoscale.multi_key_pool import KeyStatus, MultiKeyPool


@pytest.fixture
def vault():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ═══ MultiKeyPool ═══

class TestMultiKeyPool:
    def test_add_and_get(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("postman", "PMAK-testkey1234567890abcdef")
        entry = pool.get_key("postman")
        assert entry is not None
        assert entry.provider == "postman"
        assert entry.status == KeyStatus.ACTIVE

    def test_get_key_value(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("groq", "gsk_testkey1234567890abcdef")
        result = pool.get_key_value("groq")
        assert result is not None
        key, entry = result
        assert key == "gsk_testkey1234567890abcdef"

    def test_failover(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        vid1 = pool.add_key("openai", "sk-key1_testkey1234567890ab")
        vid2 = pool.add_key("openai", "sk-key2_testkey1234567890cd")

        # ตัวแรกพัง
        pool.mark_dead(vid1)
        pool.mark_dead(vid1)
        pool.mark_dead(vid1)

        # ยังได้ตัวที่สอง
        entry = pool.get_key("openai")
        assert entry is not None
        assert entry.vault_id == vid2

    def test_mark_success(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        vid = pool.add_key("test", "testkey1234567890abcdef")
        pool.mark_success(vid)
        entry = pool.get_key("test")
        assert entry.success_rate > 0.5

    def test_list_keys(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("a", "key_aaa")
        pool.add_key("b", "key_bbb")
        entries = pool.list_keys()
        assert len(entries) == 2

    def test_status(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("x", "key_xxx")
        pool.add_key("y", "key_yyy")
        status = pool.status()
        assert status["total"] == 2
        assert status["active"] == 2

    def test_failover_chain(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("test", "key1")
        pool.add_key("test", "key2")
        chain = pool.get_failover_chain("test")
        assert len(chain) == 2


# ═══ KeyHealthMonitor ═══

class TestKeyHealthMonitor:
    def test_check_healthy(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        vid = pool.add_key("test", "key123")
        monitor = KeyHealthMonitor(pool)
        entry = pool.get_key("test")
        result = monitor.check_key(entry)
        assert result.healthy

    def test_check_low_success_rate(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        vid = pool.add_key("test", "key123")
        entry = pool.get_key("test")
        entry.success_rate = 0.2
        monitor = KeyHealthMonitor(pool)
        result = monitor.check_key(entry)
        assert not result.healthy
        assert "Low success rate" in result.error

    def test_full_check(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        pool.add_key("prov_a", "key1")
        pool.add_key("prov_b", "key2")
        monitor = KeyHealthMonitor(pool)
        report = monitor.full_check()
        assert "prov_a" in report
        assert "prov_b" in report

    def test_recommendation(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        monitor = KeyHealthMonitor(pool)
        rec = monitor.get_recommendation("nonexistent")
        assert "CRITICAL" in rec


# ═══ AutoProvisioner ═══

class TestAutoProvisioner:
    def test_ingest_key(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        prov = AutoProvisioner(pool=pool)
        result = prov.ingest_key("postman", "PMAK-testkey1234567890abcdef")
        assert result.success
        assert result.vault_id.startswith("v-postman-")

    def test_provision_manual(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        prov = AutoProvisioner(pool=pool)
        result = prov.provision("unknown_provider")
        assert not result.success
        assert "instructions" in dir(result)

    def test_status(self, vault):
        pool = MultiKeyPool(vault_dir=vault)
        prov = AutoProvisioner(pool=pool)
        status = prov.get_status()
        assert "auto_provisionable" in status


# ═══ FreeProviderRegistry ═══

class TestFreeProviderRegistry:
    def test_by_category(self):
        reg = FreeProviderRegistry()
        llm = reg.by_category("llm")
        assert len(llm) >= 5

    def test_search(self):
        reg = FreeProviderRegistry()
        results = reg.search("groq")
        assert len(results) >= 1

    def test_categories(self):
        reg = FreeProviderRegistry()
        cats = reg.categories()
        assert "llm" in cats
        assert "email" in cats

    def test_setup_guide(self):
        reg = FreeProviderRegistry()
        guide = reg.setup_guide("llm")
        assert "Setup Guide" in guide
        assert "Groq" in guide

    def test_summary(self):
        reg = FreeProviderRegistry()
        s = reg.summary()
        assert s["total"] >= 15
        assert "llm" in s["by_category"]

    def test_full_guide(self):
        reg = FreeProviderRegistry()
        guide = reg.full_setup_guide()
        assert "FREE API KEY SETUP GUIDE" in guide


# ═══ AutoScaleOrchestrator ═══

class TestAutoScaleOrchestrator:
    def test_ingest_and_get(self, vault):
        from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
        orch = AutoScaleOrchestrator(vault_dir=vault)
        orch.ingest("postman", "PMAK-testkey1234567890abcdef")
        result = orch.get_key("postman")
        assert result is not None
        key, entry = result
        assert key == "PMAK-testkey1234567890abcdef"

    def test_report(self, vault):
        from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
        orch = AutoScaleOrchestrator(vault_dir=vault)
        orch.ingest("test", "testkey1234567890abcdef")
        report = orch.report()
        assert "AUTO-SCALE" in report
        assert "test" in report

    def test_health_check(self, vault):
        from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
        orch = AutoScaleOrchestrator(vault_dir=vault)
        orch.ingest("test", "key123")
        health = orch.health_check()
        assert "test" in health

    def test_mark_dead_and_failover(self, vault):
        from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
        orch = AutoScaleOrchestrator(vault_dir=vault)
        vid1 = orch.ingest("test", "key_aaa")
        vid2 = orch.ingest("test", "key_bbb")
        orch.mark_dead(vid1)
        orch.mark_dead(vid1)
        orch.mark_dead(vid1)
        result = orch.get_key("test")
        assert result is not None
        _, entry = result
        assert entry.vault_id == vid2
