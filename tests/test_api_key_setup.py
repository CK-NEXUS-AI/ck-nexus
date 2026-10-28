import os
import stat

import pytest

from scripts.api_key_setup import configure, is_api_command


def test_api_command_exact_trimmed_case_insensitive():
    for value in ("Api", " api ", "API", "\tApI\n"):
        assert is_api_command(value)
    for value in ("api now", "my Api", "", "apis", None):
        assert not is_api_command(value)


def test_openai_admin_key_written_private(tmp_path, monkeypatch):
    target = tmp_path / "admin-key"
    monkeypatch.setattr(
        "scripts.api_key_setup.PROVIDERS", {"3": ("OpenAI Admin API", target, None, None)}
    )
    result = configure("3", "sk-admin-test-secret")
    assert "PASS" in result
    assert target.read_text() == "sk-admin-test-secret"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert target.stat().st_uid == os.getuid()


def test_reject_wrong_admin_key(tmp_path, monkeypatch):
    target = tmp_path / "admin-key"
    monkeypatch.setattr(
        "scripts.api_key_setup.PROVIDERS", {"3": ("OpenAI Admin API", target, None, None)}
    )
    with pytest.raises(ValueError):
        configure("3", "sk-test-wrong-prefix")
    assert not target.exists()


def test_env_write_preserves_other_values_and_permissions(tmp_path, monkeypatch):
    target = tmp_path / "qwen.env"
    target.write_text("DASHSCOPE_API_KEY=old-secret\nQWEN_MODEL=qwen-test\n")
    target.chmod(0o600)
    monkeypatch.setattr(
        "scripts.api_key_setup.PROVIDERS",
        {"1": ("Qwen", target, "DASHSCOPE_API_KEY", "fake.service")},
    )
    result = configure("1", "new-secret")
    content = target.read_text()
    assert "PASS" in result
    assert content.count("DASHSCOPE_API_KEY=") == 1
    assert "DASHSCOPE_API_KEY=new-secret" in content
    assert "QWEN_MODEL=qwen-test" in content
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    backups = list(tmp_path.glob("qwen.env.backup-*"))
    assert len(backups) == 1
    assert "old-secret" in backups[0].read_text()
    assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600


@pytest.mark.parametrize("key", ["", "has\nnewline", "has\rreturn", "has\x00null"])
def test_reject_empty_or_control_chars(key):
    with pytest.raises(ValueError):
        configure("3", key)


def test_blocked_provider_cannot_write(tmp_path, monkeypatch):
    target = tmp_path / "blocked"
    monkeypatch.setattr("scripts.api_key_setup.PROVIDERS", {"3": ("Admin", target, None, None)})
    with pytest.raises(ValueError):
        configure("5", "any-secret")
    assert not target.exists()
