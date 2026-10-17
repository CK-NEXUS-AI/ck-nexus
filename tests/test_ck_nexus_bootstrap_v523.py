import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scripts import ck_nexus_bootstrap_v523 as bootstrap


class EvidenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir, self.run_fd = bootstrap.SecurePathManager.create_run_dir(
            self.tmp.name, "run_test"
        )
        self.store = bootstrap.EvidenceStore(self.run_dir, self.run_fd)

    def tearDown(self):
        os.close(self.run_fd)
        self.tmp.cleanup()

    def test_write_chain_and_reconcile(self):
        meta = self.store.write_artifact("terminal.log", b"hello evidence")
        self.store.append_lineage(
            "terminal.log",
            {
                "exit_code": 0,
                "truncated": False,
                "original_size_bytes": 14,
                "stored_size_bytes": 14,
                "output_sha256": meta["sha256"],
                "timed_out": False,
            },
        )
        self.assertTrue(self.store.reconcile()["chain_intact"])

    def test_artifact_tampering_fails_closed(self):
        meta = self.store.write_artifact("terminal.log", b"original")
        self.store.append_lineage(
            "terminal.log",
            {
                "exit_code": 0,
                "truncated": False,
                "original_size_bytes": 8,
                "stored_size_bytes": 8,
                "output_sha256": meta["sha256"],
                "timed_out": False,
            },
        )
        fd = os.open("terminal.log", os.O_WRONLY | os.O_TRUNC, dir_fd=self.run_fd)
        try:
            os.write(fd, b"tampered")
        finally:
            os.close(fd)
        with self.assertRaises(bootstrap.EvidenceError):
            self.store.reconcile()

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            self.store.write_artifact("../escape", b"x")
        with self.assertRaises(ValueError):
            self.store.append_lineage("..", {"exit_code": 0, "truncated": False})

    def test_reserved_metadata_rejected(self):
        self.store.write_artifact("terminal.log", b"x")
        with self.assertRaises(ValueError):
            self.store.append_lineage(
                "terminal.log", {"idx": 99, "exit_code": 0, "truncated": False}
            )

    def test_short_writes_are_retried(self):
        real_write = os.write
        calls = {"n": 0}

        def short_write(fd, data):
            calls["n"] += 1
            return real_write(fd, data[:3])

        with patch.object(bootstrap.os, "write", side_effect=short_write):
            meta = self.store.write_artifact("terminal.log", b"0123456789")
            self.store.append_lineage(
                "terminal.log",
                {
                    "exit_code": 0,
                    "truncated": False,
                    "original_size_bytes": 10,
                    "stored_size_bytes": 10,
                    "output_sha256": meta["sha256"],
                    "timed_out": False,
                },
            )
        self.assertGreater(calls["n"], 2)
        self.assertTrue(self.store.reconcile()["chain_intact"])


class ExecutionContractTests(unittest.TestCase):
    def test_unapproved_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            result = bootstrap.execute("rm -rf /", base)
            self.assertEqual(result["status"], "POLICY_REJECTED")
            self.assertEqual(result["exit_code"], 126)

    @patch("scripts.ck_nexus_bootstrap_v523.subprocess.run")
    def test_pass_requires_artifact_and_reconciliation(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        with tempfile.TemporaryDirectory() as base:
            result = bootstrap.execute("bootstrap-tests", base)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["terminal_recorded"])
        self.assertTrue(result["reconciliation"]["chain_intact"])
        self.assertTrue(mock_run.call_args.kwargs["shell"] is False)

    @patch("scripts.ck_nexus_bootstrap_v523.subprocess.run")
    def test_timeout_is_recorded_as_failure(self, mock_run):
        mock_run.side_effect = __import__("subprocess").TimeoutExpired(
            ["pytest"], 1, output=b"partial", stderr=b"timeout"
        )
        with tempfile.TemporaryDirectory() as base:
            result = bootstrap.execute("bootstrap-tests", base, timeout=1)
        self.assertEqual(result["status"], "TEST_FAILURE")
        self.assertEqual(result["exit_code"], 124)
        self.assertTrue(result["terminal_recorded"])
        self.assertTrue(result["reconciliation"]["chain_intact"])


if __name__ == "__main__":
    unittest.main()
