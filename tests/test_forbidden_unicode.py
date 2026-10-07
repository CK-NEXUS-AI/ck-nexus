from pathlib import Path

from scripts.check_forbidden_unicode import _scan


def test_forbidden_unicode_checker_accepts_plain_code(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text("value = 'plain text'\n", encoding="utf-8")
    assert _scan(path) == []


def test_forbidden_unicode_checker_rejects_symbol_other(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text("value = '\u2605'\n", encoding="utf-8")
    findings = _scan(path)
    assert findings
    assert findings[0][2] == "U+2605"
