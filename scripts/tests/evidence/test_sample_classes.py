import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from classify_sample import classify
from summarize_coverage import summarize


class SampleClassTests(unittest.TestCase):
    def test_coverage_metrics_separate_whole_genome_and_covered_positions(self):
        row = summarize({"ref": {1: 3, 2: 3}}, {"ref": 10}, 2, 10, 20)[0]
        self.assertEqual(float(row["breadth_1x"]), 0.2)
        self.assertEqual(float(row["breadth_3x"]), 0.2)
        self.assertEqual(float(row["median_depth_covered"]), 3.0)
        self.assertEqual(float(row["mean_depth_genome"]), 0.6)

    def test_short_fragment_remains_exploratory(self):
        locus = {"query_ids": "q", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "40", "max_query_length": "40"}
        comp = {"qseqid": "q", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"}
        result = classify("synthetic", [locus], [comp], [], [], "UNCONTROLLED", "shotgun", {}, True)
        self.assertEqual(result["evidence_level"], "EXPLORATORY_FRAGMENT")
        self.assertEqual(result["reported_conclusion"], "SHADOW_ONLY")

    def test_uncontrolled_sample_is_capped_at_configured_ceiling(self):
        loci = [
            {"query_ids": "q1", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "80", "max_query_length": "80"},
            {"query_ids": "q2", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "80", "max_query_length": "80"},
        ]
        competitive = [
            {"qseqid": "q1", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"},
            {"qseqid": "q2", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"},
        ]
        support = [{"unique_templates": "3", "distinct_starts": "2", "proper_pair_templates": "3", "support_status": "COVERAGE_AVAILABLE"}]
        coverage = [{"breadth_1x": "0.5", "breadth_3x": "0.4", "median_depth_covered": "5", "max_window_depth_fraction": "0.2"}]
        result = classify("synthetic", loci, competitive, support, coverage, "UNCONTROLLED", "shotgun", {}, True)
        self.assertEqual(result["evidence_level"], "MULTI_LOCUS_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
