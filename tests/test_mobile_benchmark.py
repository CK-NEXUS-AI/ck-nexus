from pathlib import Path

from scripts.mobile_benchmark import _read_meminfo, _rss_kib, _sha256


def test_sha256_is_deterministic(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("ck-nexus\n", encoding="utf-8")
    assert _sha256(artifact) == _sha256(artifact)
    assert len(_sha256(artifact)) == 64


def test_rss_is_non_negative() -> None:
    assert _rss_kib() >= 0


def test_meminfo_is_mapping() -> None:
    result = _read_meminfo()
    assert isinstance(result, dict)
    assert all(isinstance(value, int) for value in result.values())
