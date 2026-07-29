import sys
import json
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from run_state import (
    adopt_reserved_state, initial_state, initialize_runner_state, reserve_state,
    set_failure, set_stage,
)


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

    def test_dashboard_reservation_is_adopted_only_with_matching_identity_and_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state/run-safe.json"
            staging = root / ".staging/run-safe"
            final = root / "runs/run-safe"
            token = "reservation-token-0123456789abcdef"
            reserve_state(state_path, "run-safe", "evidence_single", ["sample-a"], None, token)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "running"
            state["official_v1_status"] = "done"
            state["evidence_v2_status"] = "running"
            set_stage(state, "input_validation", "done", None)
            set_stage(state, "quality_control", "done", None)
            set_stage(state, "assembly", "done", None)
            set_stage(state, "initial_blast", "done", None)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            adopted = adopt_reserved_state(
                state_path, run_id="run-safe", action="evidence_single", samples=["sample-a"],
                batch_id=None, reservation_token=token, staging=staging, final=final,
            )
            self.assertEqual(adopted["reservation"]["status"], "claimed")
            with self.assertRaises(FileExistsError):
                adopt_reserved_state(
                    state_path, run_id="run-safe", action="evidence_single", samples=["sample-a"],
                    batch_id=None, reservation_token=token, staging=staging, final=final,
                )

    def test_two_concurrent_adopters_cannot_claim_the_same_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state/run-safe.json"
            staging = root / ".staging/run-safe"
            final = root / "runs/run-safe"
            token = "reservation-token-0123456789abcdef"
            reserve_state(state_path, "run-safe", "evidence_single", ["sample-a"], None, token)

            def attempt():
                return adopt_reserved_state(
                    state_path, run_id="run-safe", action="evidence_single", samples=["sample-a"],
                    batch_id=None, reservation_token=token, staging=staging, final=final,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(attempt) for _ in range(2)]
            successes = sum(future.exception() is None for future in futures)
            self.assertEqual(successes, 1)

    def test_existing_successful_run_and_previous_state_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "state/run-safe.json"
            final = root / "runs/run-safe"
            final.mkdir(parents=True)
            (final / "SUCCESS.json").write_text('{"status":"done"}\n', encoding="utf-8")
            token = "reservation-token-0123456789abcdef"
            reserve_state(state_path, "run-safe", "evidence_single", ["sample-a"], None, token)
            original = state_path.read_bytes()
            with self.assertRaises(FileExistsError):
                adopt_reserved_state(
                    state_path, run_id="run-safe", action="evidence_single", samples=["sample-a"],
                    batch_id=None, reservation_token=token, staging=root / ".staging/run-safe", final=final,
                )
            with self.assertRaises(FileExistsError):
                initialize_runner_state(state_path, "run-safe", "evidence_single", ["sample-a"], None)
            self.assertEqual(state_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
