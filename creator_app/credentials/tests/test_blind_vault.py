"""Tests สำหรับ Blind Vault."""

from __future__ import annotations

import tempfile

import pytest

from creator_app.credentials.blind_vault import BlindVault, scan_and_store


@pytest.fixture
def tmp_vault():
    """สร้าง vault ชั่วคราวสำหรับทดสอบ."""
    with tempfile.TemporaryDirectory() as d:
        vault = BlindVault(vault_dir=d)
        yield vault


class TestBlindVault:
    def test_store_and_retrieve(self, tmp_vault):
        vid = tmp_vault.store("postman", "PMAK-test1234567890abcdef")
        assert vid.startswith("v-postman-")
        key = tmp_vault.retrieve(vid)
        assert key == "PMAK-test1234567890abcdef"

    def test_vault_id_hidden(self, tmp_vault):
        vid = tmp_vault.store("openai", "sk-test1234567890abcdef")
        entries = tmp_vault.list_entries()
        assert len(entries) == 1
        assert entries[0]["vault_id"] == vid
        assert "sk-" not in str(entries)
        assert "test1234" not in str(entries)

    def test_verify(self, tmp_vault):
        vid = tmp_vault.store("groq", "gsk_test1234567890abcdef")
        assert tmp_vault.verify(vid, "gsk_test1234567890abcdef")
        assert not tmp_vault.verify(vid, "wrong-key")

    def test_list_by_provider(self, tmp_vault):
        tmp_vault.store("postman", "key1")
        tmp_vault.store("openai", "key2")
        tmp_vault.store("postman", "key3")
        postman = tmp_vault.list_entries(provider="postman")
        assert len(postman) == 2

    def test_delete(self, tmp_vault):
        vid = tmp_vault.store("test", "key123")
        assert tmp_vault.delete(vid)
        with pytest.raises(KeyError):
            tmp_vault.retrieve(vid)

    def test_delete_nonexistent(self, tmp_vault):
        assert not tmp_vault.delete("v-nonexistent-xxxx")

    def test_status(self, tmp_vault):
        tmp_vault.store("a", "key1")
        tmp_vault.store("b", "key2")
        status = tmp_vault.status()
        assert status["total_keys"] == 2
        assert "a" in status["providers"]

    def test_encrypt_decrypt(self, tmp_vault):
        original = "super-secret-key-12345"
        encrypted = tmp_vault._encrypt(original)
        assert encrypted != original
        decrypted = tmp_vault._decrypt(encrypted)
        assert decrypted == original


class TestScanAndStore:
    def test_scan_postman_key(self, tmp_vault):
        text = "Here is my key: PMAK-abc123def456ghi789jkl0"
        results = scan_and_store(text, tmp_vault)
        assert len(results) == 1
        assert results[0]["provider"] == "postman"
        assert results[0]["status"] == "stored"

    def test_scan_openai_key(self, tmp_vault):
        text = "api_key=sk-proj1234567890abcdef1234567890ab"
        results = scan_and_store(text, tmp_vault)
        assert len(results) >= 1

    def test_scan_no_key(self, tmp_vault):
        text = "This is just plain text with no keys"
        results = scan_and_store(text, tmp_vault)
        assert len(results) == 0

    def test_scan_dedup(self, tmp_vault):
        key = "PMAK-abc123def456ghi789jkl0"
        scan_and_store(key, tmp_vault)
        results = scan_and_store(key, tmp_vault)
        assert results[0]["status"] == "already_stored"

    def test_scan_multiple_providers(self, tmp_vault):
        text = (
            "postman: PMAK-abc123def456ghi789jkl0\n"
            "groq: gsk_abc123def456ghi789jkl0mnop"
        )
        results = scan_and_store(text, tmp_vault)
        providers = {r["provider"] for r in results}
        assert "postman" in providers
        assert "groq" in providers
