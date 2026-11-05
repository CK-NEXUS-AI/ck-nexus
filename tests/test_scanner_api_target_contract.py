from pathlib import Path


def test_scanner_api_requires_exact_canonical_target_string() -> None:
    source = Path("ops/vps/services/cknexus_scanner_api.py").read_text(encoding="utf-8")
    assert 'target = d.get("target")' in source
    assert 'target != str(R)' in source
    assert 'Path(d.get("target", "")).resolve()' not in source
