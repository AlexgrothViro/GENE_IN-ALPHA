import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from evaluate_controls import evaluate


class ControlTests(unittest.TestCase):
    def test_tenfold_ratio_is_state_not_contamination_verdict(self):
        manifest = [
            {"batch_id": "b", "sample_id": "s", "role": "sample", "library_mode": "shotgun", "umi_mode": "none", "r1": "a", "r2": "b", "expected_target": "virus"},
            {"batch_id": "b", "sample_id": "n", "role": "negative_library", "library_mode": "shotgun", "umi_mode": "none", "r1": "c", "r2": "d", "expected_target": "virus"},
        ]
        metrics = [
            {"batch_id": "b", "sample_id": "s", "target": "virus", "rpm_post_qc": "100", "rpm_nonhost": "NA", "sequence_hashes": "x"},
            {"batch_id": "b", "sample_id": "n", "target": "virus", "rpm_post_qc": "5", "rpm_nonhost": "NA", "sequence_hashes": "y"},
        ]
        row = evaluate(manifest, metrics, 10)[0]
        self.assertEqual(row["control_status"], "CONTROL_BELOW_SAMPLE")
        self.assertNotIn("CONTAMINATION", row["control_status"])

    def test_failed_positive_is_target_failure_and_control_is_not_applicable(self):
        manifest = [
            {"batch_id": "b", "sample_id": "s", "role": "sample", "library_mode": "shotgun", "umi_mode": "none", "r1": "a", "r2": "b", "expected_target": "virus"},
            {"batch_id": "b", "sample_id": "p", "role": "positive", "library_mode": "shotgun", "umi_mode": "none", "r1": "c", "r2": "d", "expected_target": "virus"},
        ]
        metrics = [
            {"batch_id": "b", "sample_id": "s", "target": "virus", "rpm_post_qc": "100", "rpm_nonhost": "NA", "sequence_hashes": "x", "evidence_level": "LOCUS_CANDIDATE"},
            {"batch_id": "b", "sample_id": "p", "target": "virus", "expected_target": "virus", "rpm_post_qc": "0", "rpm_nonhost": "NA", "sequence_hashes": "", "evidence_level": "INCONCLUSIVE"},
        ]
        rows = evaluate(manifest, metrics, 10)
        by_sample = {row["sample_id"]: row for row in rows}
        self.assertEqual(by_sample["s"]["control_status"], "TARGET_CONTROL_FAILURE")
        self.assertEqual(by_sample["p"]["control_status"], "CONTROL_NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
