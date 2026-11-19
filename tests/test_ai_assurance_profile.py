import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ai_assurance import validate


class AssuranceProfileTests(unittest.TestCase):
    def test_canonical_profile_valid(self):
        self.assertEqual(validate("config/ai_assurance_controls.json"), [])

    def test_verified_without_evidence_fails(self):
        data = json.loads(Path("config/ai_assurance_controls.json").read_text())
        data["controls"][0]["state"] = "VERIFIED"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps(data))
            errors = validate(str(p))
        self.assertTrue(any("evidence required" in e for e in errors))
        self.assertTrue(any("independent verification required" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
