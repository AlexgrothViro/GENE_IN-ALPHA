import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(Path(__file__).parent))

from classify_sample import classify
from common import write_json_atomic
from evidence_contract import adapt_legacy_document, promote_for_public_output
from evidence_dashboard import EvidenceDashboardService
from generate_alpha2_fixture import generate_fixture
from run_state import initial_state
from summarize_coverage import FIELDS as COVERAGE_FIELDS
from summarize_read_support import FIELDS as READ_SUPPORT_FIELDS
from validate_run_artifacts import REQUIRED_HEADERS, validate


def write_core_alpha2_artifacts(directory: Path, run_id: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, required in REQUIRED_HEADERS.items():
        directory.joinpath(name).write_text("\t".join(sorted(required)) + "\n", encoding="utf-8")
    evidence = classify(
        "sample-a", [], [], [], [], "UNCONTROLLED", "unknown", {}, run_id=run_id,
    )
    write_json_atomic(directory / "sample_evidence.json", evidence)
    write_json_atomic(directory / "runtime_preflight.json", {"valid": True})
    write_json_atomic(directory / "provenance.json", {"run_id": run_id})
    directory.joinpath("evidence_report.md").write_text("# Alpha.2 shadow fixture\n", encoding="utf-8")


def write_legacy_run(root: Path, run_id: str = "legacy-run") -> tuple[EvidenceDashboardService, Path]:
    service = EvidenceDashboardService(root)
    state = initial_state(run_id, "evidence_single", ["sample-a"], None)
    state.update({"status": "done", "pipeline_version": "2.0.0-alpha.1"})
    write_json_atomic(root / "results/evidence/state" / f"{run_id}.json", state)
    run_dir = root / "results/evidence/runs" / run_id
    run_dir.mkdir(parents=True)
    run_dir.joinpath("SUCCESS.json").write_text(
        json.dumps({"run_id": run_id, "pipeline_version": "2.0.0-alpha.1", "status": "done"}) + "\n",
        encoding="utf-8",
    )
    run_dir.joinpath("sample_evidence.json").write_text(
        json.dumps({"sample_id": "sample-a", "evidence_class": "STRONG"}) + "\n",
        encoding="utf-8",
    )
    return service, run_dir


class LegacyAlpha2CompatibilityTests(unittest.TestCase):
    def test_current_tsv_producers_include_every_required_alpha2_column(self):
        self.assertTrue(REQUIRED_HEADERS["coverage.tsv"].issubset(COVERAGE_FIELDS))
        self.assertTrue(REQUIRED_HEADERS["read_support.tsv"].issubset(READ_SUPPORT_FIELDS))
        runner = (ROOT / "scripts/22_run_evidence_v2.sh").read_text(encoding="utf-8")
        for field in REQUIRED_HEADERS["coverage.tsv"] | REQUIRED_HEADERS["read_support.tsv"]:
            self.assertIn(field, runner)

    def test_checked_in_complete_alpha2_fixture_passes_cli_validator(self):
        fixture = ROOT / "scripts/tests/evidence/fixtures/alpha2_complete"
        self.assertEqual(validate(fixture), [])
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts/evidence/validate_run_artifacts.py"),
            "--dir", str(fixture),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checked_in_complete_alpha2_fixture_is_canonically_reproducible(self):
        fixture = ROOT / "scripts/tests/evidence/fixtures/alpha2_complete"
        with tempfile.TemporaryDirectory(dir=ROOT / "scripts/tests/evidence") as tmp:
            regenerated = Path(tmp) / "alpha2_complete"
            generate_fixture(regenerated)
            expected = {path.name: path.read_bytes() for path in fixture.iterdir() if path.is_file()}
            actual = {path.name: path.read_bytes() for path in regenerated.iterdir() if path.is_file()}
        self.assertEqual(actual, expected)

    def test_incomplete_legacy_run_is_rejected_by_strict_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            for name, required in REQUIRED_HEADERS.items():
                legacy = sorted(required - {"category", "locus_id", "query_ids", "reference_id", "mean_depth_locus"})
                run_dir.joinpath(name).write_text("\t".join(legacy or ["legacy"]) + "\n", encoding="utf-8")
            run_dir.joinpath("sample_evidence.json").write_text(
                '{"sample_id":"sample-a","evidence_class":"STRONG"}\n', encoding="utf-8",
            )
            run_dir.joinpath("runtime_preflight.json").write_text('{"valid":true}\n', encoding="utf-8")
            run_dir.joinpath("provenance.json").write_text('{}\n', encoding="utf-8")
            run_dir.joinpath("evidence_report.md").write_text("# legacy\n", encoding="utf-8")
            run_dir.joinpath("SUCCESS.json").write_text('{"pipeline_version":"2.0.0-alpha.1"}\n', encoding="utf-8")
            errors = validate(run_dir)
        joined = "\n".join(errors)
        self.assertIn("missing required TSV columns", joined)
        self.assertIn("evidence document missing fields", joined)
        self.assertIn("artifact_manifest.json", joined)

    def test_dashboard_returns_not_evaluable_for_legacy_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, _ = write_legacy_run(Path(tmp))
            result = service.result("legacy-run")
        self.assertFalse(result["valid_alpha2"])
        self.assertEqual(result["compatibility"]["status"], "LEGACY_INCOMPATIBLE")
        self.assertEqual(result["compatibility"]["analysis_outcome"], "NOT_EVALUABLE")
        self.assertIn("reexecute", result["compatibility"]["message"])
        self.assertIsNone(result["evidence_v2"])

    def test_legacy_cannot_be_promoted_without_explicit_traceable_adaptation(self):
        legacy = {"sample_id": "sample-a", "run_id": "legacy-run", "evidence_class": "STRONG"}
        with self.assertRaises(ValueError):
            promote_for_public_output(legacy)
        with self.assertRaisesRegex(ValueError, "explicit adaptation_id"):
            adapt_legacy_document(legacy)
        adapted = adapt_legacy_document(legacy, adaptation_id="review-2026-07-17")
        trace = adapted["provenance"]["legacy_adaptation"]
        self.assertEqual(adapted["evidence_level"], "NOT_EVALUABLE")
        self.assertEqual(adapted["analysis_outcome"], "NOT_EVALUABLE")
        self.assertEqual(trace["mode"], "EXPLICIT")
        self.assertEqual(trace["adaptation_id"], "review-2026-07-17")
        self.assertEqual(len(trace["source_sha256"]), 64)

    def test_new_complete_alpha2_run_passes_validator_and_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "alpha2-run"
            staging = root / "results/evidence/.staging" / run_id
            final = root / "results/evidence/runs" / run_id
            state_path = root / "results/evidence/state" / f"{run_id}.json"
            write_core_alpha2_artifacts(staging, run_id)
            write_json_atomic(state_path, initial_state(run_id, "evidence_single", ["sample-a"], None))
            promoted = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/finalize_run.py"),
                "--state", str(state_path), "--staging", str(staging), "--final", str(final),
            ], capture_output=True, text=True)
            self.assertEqual(promoted.returncode, 0, promoted.stderr)
            validation = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/validate_run_artifacts.py"),
                "--dir", str(final),
            ], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            self.assertEqual(validate(final), [])
            result = EvidenceDashboardService(root).result(run_id)
            self.assertTrue(result["valid_alpha2"])
            self.assertTrue(result["evidence_v2"]["shadow_mode"])
            self.assertIn(result["evidence_v2"]["evidence_level"], {"E1", "NOT_EVALUABLE"})
            for name in ("coverage.tsv", "read_support.tsv"):
                header = final.joinpath(name).read_text(encoding="utf-8").splitlines()[0].split("\t")
                self.assertTrue(REQUIRED_HEADERS[name].issubset(header))

    def test_legacy_inspection_preserves_every_original_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            service, run_dir = write_legacy_run(Path(tmp), "preserved-run")
            before = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
            service.state("preserved-run")
            service.result("preserved-run")
            after = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
