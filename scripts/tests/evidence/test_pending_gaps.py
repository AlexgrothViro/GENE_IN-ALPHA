import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from common import write_json_atomic
from environment_lock import validate as validate_environment_lock
from evidence_dashboard import EvidenceDashboardService
import index_cache
from run_state import initial_state
from runtime_preflight import run as runtime_preflight

spec = importlib.util.spec_from_file_location("gene_in_ux_dashboard", ROOT / "scripts" / "ux_dashboard.py")
ux_dashboard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ux_dashboard)


class PendingGapRegressionTests(unittest.TestCase):
    def test_lockfile_hash_mismatch_blocks_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lockfile = root / "conda-linux-64.lock"
            lockfile.write_text("@EXPLICIT\nhttps://example.invalid/pkg.conda#0123456789abcdef\n", encoding="utf-8")
            manifest = root / "environment_lock.json"
            manifest.write_text(json.dumps({
                "schema_version": "1.0", "lockfile": lockfile.name,
                "sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            lockfile.write_text("@EXPLICIT\nhttps://example.invalid/changed.conda#0123456789abcdef\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "LOCKFILE_HASH_MISMATCH"):
                validate_environment_lock(lockfile, manifest)
            report, errors = runtime_preflight(
                ROOT / "config" / "evidence_v2.yaml", "none", "none", False, [], lockfile, manifest,
            )
            self.assertTrue(errors)
            self.assertTrue(any("LOCKFILE_HASH_MISMATCH" in error for error in errors))

    def test_index_reuse_blocked_on_content_change_same_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "panel.fa"
            reference.write_text(">ref\nAAAA\n", encoding="utf-8")
            timestamp = reference.stat().st_mtime_ns
            identity = {"makeblastdb": {"command": "makeblastdb", "executable": "/tool", "version": "1", "sha256": "a"}}
            with patch.object(index_cache, "builder_identity", side_effect=lambda name: identity[name]):
                manifest = index_cache.fingerprint(reference, ["makeblastdb"])
                reference.write_text(">ref\nTTTT\n", encoding="utf-8")
                os.utime(reference, ns=(timestamp, timestamp))
                self.assertFalse(index_cache.matches(manifest, reference, ["makeblastdb"]))
            manager = (ROOT / "scripts" / "13_db_manager.sh").read_text(encoding="utf-8")
            self.assertNotIn('-ot "$REF_FASTA"', manager)
            self.assertIn("index_cache.py", manager)

    def test_no_output_path_bypasses_legacy_incompatibility_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = EvidenceDashboardService(root)
            run_id = "run-public"
            state_path = root / "results/evidence/state" / f"{run_id}.json"
            state = initial_state(run_id, "evidence_single", ["sample-a"], None)
            state["status"] = "done"
            state["pipeline_version"] = "2.0.0-alpha.1"
            write_json_atomic(state_path, state)
            run_dir = root / "results/evidence/runs" / run_id
            run_dir.mkdir(parents=True)
            (run_dir / "SUCCESS.json").write_text('{"status":"done"}\n', encoding="utf-8")
            (run_dir / "sample_evidence.json").write_text(json.dumps({"sample_id": "sample-a", "evidence_class": "STRONG"}), encoding="utf-8")
            legacy_report = root / "results/reports/sample-a_summary.md"
            legacy_report.parent.mkdir(parents=True, exist_ok=True)
            legacy_report.write_text("LEGACY_STRONG_RAW_REPORT", encoding="utf-8")
            result = service.result(run_id)
            self.assertFalse(result["valid_alpha2"])
            self.assertEqual(result["compatibility"]["status"], "LEGACY_INCOMPATIBLE")
            self.assertEqual(result["compatibility"]["analysis_outcome"], "NOT_EVALUABLE")
            self.assertIn("reexecute", result["compatibility"]["message"])
            self.assertIsNone(result["evidence_v2"])
            self.assertNotEqual(result.get("evidence_level"), "E1")
            self.assertTrue(result["artifacts_preserved"])
            with self.assertRaisesRegex(ValueError, "canonical result endpoint"):
                service.artifact(run_id, "sample_evidence")

    def test_dashboard_reports_cancellation_group_kill_failure_as_failed_not_success(self):
        class BrokenProcess:
            pid = 1

            def send_signal(self, _signal):
                raise OSError("simulated signal failure")

        with patch.object(ux_dashboard.os, "name", "nt"):
            ok, error = ux_dashboard.terminate_process_group(BrokenProcess(), 1)
        self.assertFalse(ok)
        self.assertIn("could not signal", error)
        job_id = "cancel-failure-test"
        with ux_dashboard.jobs_lock:
            ux_dashboard.jobs[job_id] = {"status": "cancelling", "action": "pipeline"}
        try:
            ux_dashboard.mark_cancellation_failure(job_id, "pipeline", "simulated")
            self.assertEqual(ux_dashboard.jobs[job_id]["status"], "failed")
            self.assertEqual(ux_dashboard.jobs[job_id]["failure_type"], "CANCELLATION_FAILED")
        finally:
            with ux_dashboard.jobs_lock:
                ux_dashboard.jobs.pop(job_id, None)

    def test_dashboard_no_legacy_cache_bypasses_shadow_mode(self):
        class Handler:
            def __init__(self):
                self.headers = {}

            def send_response(self, status):
                self.status = status

            def send_header(self, key, value):
                self.headers[key] = value

            def end_headers(self):
                pass

            class Stream:
                @staticmethod
                def write(_data):
                    return None

            wfile = Stream()

        handler = Handler()
        ux_dashboard.json_response(handler, 200, {"run_id": "new"})
        self.assertEqual(handler.headers["Cache-Control"], "no-cache, no-store, must-revalidate")
        self.assertEqual(handler.headers["Pragma"], "no-cache")
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn('cache: "no-store"', app)


if __name__ == "__main__":
    unittest.main()
