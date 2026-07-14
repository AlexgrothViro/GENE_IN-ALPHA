import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from run_state import initial_state, set_failure, set_stage


class RunStateTests(unittest.TestCase):
    def test_terminal_stage_cannot_regress_to_failed(self):
        state = initial_state("run-safe", "evidence_single", ["sample"], None)
        set_stage(state, "quality_control", "done", "QC concluído")
        set_stage(state, "quality_control", "running", "handoff repetido")
        self.assertEqual(state["stages"][1]["status"], "done")
        with self.assertRaises(ValueError):
            set_stage(state, "quality_control", "failed", "não deve regredir")

    def test_failure_metadata_is_typed_and_keeps_official_status_separate(self):
        state = initial_state("run-safe", "evidence_single", ["sample"], None)
        state["official_v1_status"] = "done"
        set_failure(state, "DEPENDENCY_MISSING", "input_validation", "PyYAML ausente", "python3 runtime_preflight.py")
        self.assertEqual(state["official_v1_status"], "done")
        self.assertEqual(state["failure_type"], "DEPENDENCY_MISSING")
        self.assertEqual(state["failed_stage"], "input_validation")
        self.assertEqual(state["failed_command"], "python3 runtime_preflight.py")

    def test_official_pipeline_and_v2_statuses_do_not_get_mixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps(initial_state("run-safe", "evidence_single", ["sample"], None)), encoding="utf-8")
            runner = [sys.executable, str(ROOT / "scripts/evidence/run_state.py"), "--state", str(state_path)]
            subprocess.run(runner + ["status", "--value", "running", "--official-v1-status", "running", "--evidence-v2-status", "queued"], check=True)
            subprocess.run(runner + ["stage", "--id", "quality_control", "--status", "running"], check=True)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["official_v1_status"], "running")
            self.assertEqual(state["evidence_v2_status"], "queued")
            subprocess.run(runner + ["status", "--value", "running", "--official-v1-status", "done", "--evidence-v2-status", "running"], check=True)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["official_v1_status"], "done")
            self.assertEqual(state["evidence_v2_status"], "running")


if __name__ == "__main__":
    unittest.main()
