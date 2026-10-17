import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_relative_evidence_base_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            bootstrap.SecurePathManager.create_run_dir("relative-evidence", "run_test")

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

    def test_pass_requires_artifact_and_reconciliation(self):
        command = (sys.executable, "-c", "print('ok')")
        with (
            patch.dict(bootstrap.PROFILES, {"bootstrap-tests": command}),
            tempfile.TemporaryDirectory() as base,
        ):
            result = bootstrap.execute("bootstrap-tests", base)
            run_dir = next(Path(base).iterdir())
            log = (run_dir / "terminal.log").read_bytes()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["terminal_recorded"])
        self.assertTrue(result["reconciliation"]["chain_intact"])
        self.assertIn(b"ok", log)

    def test_output_is_bounded_during_capture(self):
        command = (
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'x' * 2200000)",
        )
        with (
            patch.dict(bootstrap.PROFILES, {"bootstrap-tests": command}),
            tempfile.TemporaryDirectory() as base,
        ):
            result = bootstrap.execute("bootstrap-tests", base)
            run_dir = next(Path(base).iterdir())
            log = (run_dir / "terminal.log").read_bytes()
            chain = json.loads((run_dir / "chain.json").read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(log), 1048576)
        self.assertTrue(chain[0]["truncated"])
        self.assertEqual(chain[0]["original_size_bytes"], 2200000)

    def test_binary_output_is_preserved(self):
        command = (
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes([255, 0, 128]))",
        )
        with (
            patch.dict(bootstrap.PROFILES, {"bootstrap-tests": command}),
            tempfile.TemporaryDirectory() as base,
        ):
            result = bootstrap.execute("bootstrap-tests", base)
            run_dir = next(Path(base).iterdir())
            log = (run_dir / "terminal.log").read_bytes()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(log, bytes([255, 0, 128]))

    def test_timeout_is_recorded_as_failure(self):
        command = (sys.executable, "-c", "import time; time.sleep(5)")
        with (
            patch.dict(bootstrap.PROFILES, {"bootstrap-tests": command}),
            tempfile.TemporaryDirectory() as base,
        ):
            result = bootstrap.execute("bootstrap-tests", base, timeout=0.1)
            run_dir = next(Path(base).iterdir())
            log = (run_dir / "terminal.log").read_bytes()
        self.assertEqual(result["status"], "TEST_FAILURE")
        self.assertEqual(result["exit_code"], 124)
        self.assertTrue(result["terminal_recorded"])
        self.assertTrue(result["reconciliation"]["chain_intact"])
        self.assertIn(b"[PROCESS TIMEOUT]", log)

    def test_timeout_returns_when_escaped_descendant_holds_pipe(self):
        command = (
            sys.executable,
            "-c",
            "import os, subprocess, sys, time; "
            "p=subprocess.Popen([sys.executable, '-c', "
            "'import os,time; os.setsid(); time.sleep(30)'], "
            "stdout=sys.stdout, stderr=sys.stderr); "
            "print(p.pid, flush=True); time.sleep(30)",
        )
        started = time.monotonic()
        descendant_pid = None
        try:
            output, code, timed_out, truncated, total = bootstrap._run_bounded(
                command, os.getcwd(), timeout=0.2, limit=4096
            )
            elapsed = time.monotonic() - started
            descendant_pid = int(output.strip().splitlines()[0])
            self.assertTrue(timed_out)
            self.assertEqual(code, 124)
            self.assertLess(elapsed, 2.5, f"timeout path took {elapsed:.2f}s")
            self.assertGreater(descendant_pid, 1)
            self.assertGreaterEqual(total, len(output))
        finally:
            # The test intentionally creates a descendant that escapes the
            # process group; clean it up explicitly so the test leaves no child.
            if descendant_pid is not None:
                try:
                    os.kill(descendant_pid, 9)
                except ProcessLookupError:
                    pass

    def test_timeout_bounds_continuous_output_flood(self):
        command = (
            sys.executable,
            "-c",
            "import os; chunk=b'z'*65536; "
            "exec('while True: os.write(1, chunk)')",
        )
        started = time.monotonic()
        output, code, timed_out, truncated, total = bootstrap._run_bounded(
            command, os.getcwd(), timeout=0.2, limit=8192
        )
        elapsed = time.monotonic() - started
        self.assertTrue(timed_out)
        self.assertEqual(code, 124)
        self.assertEqual(len(output), 8192)
        self.assertTrue(truncated)
        self.assertGreater(total, len(output))
        self.assertLess(elapsed, 2.5, f"output flood took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
