import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from common import write_json_atomic
from classify_sample import classify
from evidence_dashboard import EvidenceDashboardService
from run_state import initial_state


def fastq(path: Path, mate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"@template/" + str(mate) + "\nACGT\n+\nIIII\n", encoding="utf-8")


class ManifestServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        fastq(self.root / "data/raw/a_R1.fastq", 1)
        fastq(self.root / "data/raw/a_R2.fastq", 2)
        self.service = EvidenceDashboardService(self.root)
        self.row = {
            "batch_id": "batch-a", "sample_id": "sample-a", "role": "sample",
            "library_mode": "shotgun", "umi_mode": "none",
            "r1": "data/raw/a_R1.fastq", "r2": "data/raw/a_R2.fastq", "expected_target": "",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_manifest_is_validated_and_promoted_as_tsv_json_pair(self):
        result = self.service.save_manifest([self.row], "manifest-a")
        self.assertTrue(result["valid"])
        self.assertIn("UNCONTROLLED", result["warnings"][0])
        self.assertTrue((self.root / "data/manifests/manifest-a.tsv").is_file())
        self.assertTrue((self.root / "data/manifests/manifest-a.json").is_file())

    def test_duplicate_sample_and_path_are_rejected(self):
        duplicate = dict(self.row)
        result = self.service.validate_manifest([self.row, duplicate])
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicado" in error for item in result["errors"] for error in item["errors"]))

    def test_incomplete_run_cannot_export_artifact(self):
        state = self.root / "results/evidence/state/run-safe.json"
        write_json_atomic(state, initial_state("run-safe", "evidence_single", ["sample-a"], None))
        with self.assertRaises((FileNotFoundError, ValueError)):
            self.service.artifact("run-safe", "sample_evidence")


class TransactionTests(unittest.TestCase):
    def make_staging(self, root: Path) -> Path:
        staging = root / ".staging/run-safe"
        staging.mkdir(parents=True)
        headers = {
            "fragment_evidence.tsv": "qseqid\tsseqid\ttask\tquery_covered_bp\treference_covered_bp\tadj_identity\n",
            "locus_evidence.tsv": "locus_id\tsseqid\tsegment\torientation\tcovered_reference_bp\tquery_ids\n",
            "competitive_hits.tsv": "qseqid\ttask\ttarget_bitscore\tcompetitor_bitscore\tdelta_bitscore\tspecificity_status\n",
            "read_support.tsv": "sample_id\treference_id\tcategory\tlocus_id\tquery_ids\tunique_templates\tdistinct_starts\tsupport_status\n",
            "coverage.tsv": "reference_id\tcategory\tlocus_id\tquery_ids\tbreadth_1x\tbreadth_3x\tmean_depth_locus\tmedian_depth_covered\n",
        }
        for name, header in headers.items():
            (staging / name).write_text(header, encoding="utf-8")
        (staging / "sample_evidence.json").write_text(
            json.dumps(classify(
                "sample-a", [], [], [], [], "UNCONTROLLED", "unknown", {}, run_id="run-safe",
            )) + "\n",
            encoding="utf-8",
        )
        (staging / "runtime_preflight.json").write_text('{"valid": true}\n', encoding="utf-8")
        (staging / "provenance.json").write_text("{}\n", encoding="utf-8")
        (staging / "evidence_report.md").write_text("# experimental\n", encoding="utf-8")
        return staging

    def test_success_marker_exists_only_after_atomic_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.make_staging(root)
            state = root / "state/run-safe.json"
            write_json_atomic(state, initial_state("run-safe", "evidence_single", ["sample-a"], None))
            final = root / "runs/run-safe"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/finalize_run.py"),
                "--state", str(state), "--staging", str(staging), "--final", str(final),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(staging.exists())
            self.assertTrue((final / "SUCCESS.json").is_file())
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["status"], "done")

    def test_partial_file_prevents_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.make_staging(root)
            (staging / ".interrupted.tmp").write_text("partial", encoding="utf-8")
            state = root / "state/run-safe.json"
            write_json_atomic(state, initial_state("run-safe", "evidence_single", ["sample-a"], None))
            final = root / "runs/run-safe"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/finalize_run.py"),
                "--state", str(state), "--staging", str(staging), "--final", str(final),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(final.exists())
            self.assertFalse((staging / "SUCCESS.json").exists())

    def test_existing_run_is_preserved_when_replacement_cannot_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.make_staging(root)
            final = root / "runs/run-safe"
            final.mkdir(parents=True)
            (final / "SUCCESS.json").write_text('{"status":"done"}\n', encoding="utf-8")
            (final / "old-result.txt").write_text("previous\n", encoding="utf-8")
            state = root / "state/run-safe.json"
            write_json_atomic(state, initial_state("run-safe", "evidence_single", ["sample-a"], None))
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/finalize_run.py"),
                "--state", str(state), "--staging", str(staging), "--final", str(final),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((final / "old-result.txt").read_text(encoding="utf-8"), "previous\n")
            self.assertFalse((staging / "SUCCESS.json").exists())

    def test_success_marker_is_removed_if_directory_promotion_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.make_staging(root)
            state = root / "state/run-safe.json"
            write_json_atomic(state, initial_state("run-safe", "evidence_single", ["sample-a"], None))
            blocked_parent = root / "blocked-parent"
            blocked_parent.write_text("not a directory\n", encoding="utf-8")
            final = blocked_parent / "run-safe"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/evidence/finalize_run.py"),
                "--state", str(state), "--staging", str(staging), "--final", str(final),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(staging.is_dir())
            self.assertFalse((staging / "SUCCESS.json").exists())


if __name__ == "__main__":
    unittest.main()
