import hashlib
import json
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from services import cknexus_scanner_api as scanner


class ScannerApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "test"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "fixture"], check=True)
        self.token = self.base / "token"
        self.token.write_text("test-token\n", encoding="utf-8")
        self.evidence = self.base / "evidence"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), scanner.create_handler(self.repo, self.token, self.evidence)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def post(self, payload, token="test-token"):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = Request(
            self.url + "/api/scan",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_auth_fails_closed(self):
        self.assertEqual(self.post({"target": str(self.repo)}, token=None)[0], 401)
        self.assertEqual(self.post({"target": str(self.repo)}, token="bad-\u00ff")[0], 401)

    def test_target_and_scanner_allowlist(self):
        status, _ = self.post(
            {"target": {"path": str(self.repo)}, "scanners": ["trivy"]}
        )
        self.assertEqual(status, 400)
        status, payload = self.post({"target": str(self.repo), "scanners": ["trivy", "custom"]})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "no_allowed_scanners")

    def test_dirty_checkout_fails_closed(self):
        (self.repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        status, payload = self.post({"target": str(self.repo), "scanners": ["trivy"]})
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"], "source_not_clean")

    def test_evidence_hash_and_source_identity(self):
        with patch.object(scanner, "_run_scanner", return_value={"exit_code": 0, "findings": 0}):
            status, response = self.post({"target": str(self.repo), "scanners": ["semgrep"]})
        self.assertEqual(status, 200)
        self.assertEqual(response["status"], "EXECUTED_NOT_VERIFIED")
        artifact = self.evidence / (response["scan_id"] + ".json")
        actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
        self.assertEqual(actual_hash, response["artifact_sha256"])
        stored = json.loads(artifact.read_bytes())
        expected_sha = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        self.assertEqual(stored["source_sha"], expected_sha)
        self.assertNotIn("artifact_sha256", stored)


if __name__ == "__main__":
    unittest.main()
