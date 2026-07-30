import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from classify_sample import classify
from evidence_contract import validate_document
from export_evidence import render
from summarize_coverage import summarize


class SampleClassTests(unittest.TestCase):
    def test_coverage_metrics_separate_whole_genome_and_covered_positions(self):
        loci = [{"sseqid": "ref", "category": "TARGET_VIRUS", "locus_id": "L1", "orientation": "+", "query_ids": "q", "reference_intervals": "1-10"}]
        row = summarize({"ref": {1: 3, 2: 3}}, {"ref": 10}, loci, 2, 10, 20)[0]
        self.assertEqual(float(row["breadth_1x"]), 0.2)
        self.assertEqual(float(row["breadth_3x"]), 0.2)
        self.assertEqual(float(row["median_depth_covered"]), 3.0)
        self.assertEqual(float(row["mean_depth_locus"]), 0.6)

    def test_short_fragment_remains_exploratory(self):
        locus = {"locus_id": "L1", "sseqid": "virus", "query_ids": "q", "orientation": "+", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "40", "max_query_length": "40"}
        comp = {"qseqid": "q", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"}
        result = classify("synthetic", [locus], [comp], [], [], "UNCONTROLLED", "shotgun", {}, True)
        self.assertEqual(result["evidence_level"], "E1")
        self.assertEqual(result["analysis_outcome"], "EVIDENCE_RECOVERED")
        self.assertEqual(result["reported_conclusion"], "SHADOW_ONLY")
        self.assertEqual(result["candidates"][0]["candidate_class"], "EXPLORATORY_FRAGMENT")
        self.assertEqual(result["candidates"][0]["promotion_status"], "BLOCKED")
        self.assertIn(
            "BELOW_MINIMUM_CANDIDATE_BP",
            result["candidates"][0]["blocking_reasons"],
        )
        self.assertEqual(result["metrics"]["promotion_eligible_candidate_count"], 0)
        self.assertEqual(
            next(
                gate for gate in result["promotion_gates"]
                if gate["gate_id"] == "candidate_evidence"
            )["status"],
            "BLOCKED",
        )
        report = render(result)
        self.assertIn("classe `EXPLORATORY_FRAGMENT`", report)
        self.assertIn("promoção `BLOCKED`", report)

    def test_uncontrolled_sample_is_capped_at_configured_ceiling(self):
        loci = [
            {"locus_id": "L1", "sseqid": "virus", "query_ids": "q1", "orientation": "+", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "80", "max_query_length": "80"},
            {"locus_id": "L2", "sseqid": "virus", "query_ids": "q2", "orientation": "-", "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "80", "max_query_length": "80"},
        ]
        competitive = [
            {"qseqid": "q1", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"},
            {"qseqid": "q2", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"},
        ]
        support = [{"reference_id": "virus", "category": "TARGET_VIRUS", "locus_id": "L1", "unique_templates": "3", "distinct_starts": "2", "proper_pair_templates": "3", "support_status": "SUPPORT_AVAILABLE"}]
        coverage = [{"reference_id": "virus", "category": "TARGET_VIRUS", "locus_id": "L1", "breadth_1x": "0.5", "breadth_3x": "0.4", "median_depth_covered": "5", "max_window_depth_fraction": "0.2"}]
        result = classify("synthetic", loci, competitive, support, coverage, "UNCONTROLLED", "shotgun", {}, True)
        self.assertEqual(result["evidence_level"], "E1")
        self.assertEqual(next(g for g in result["promotion_gates"] if g["gate_id"] == "alpha_shadow_ceiling")["status"], "BLOCKED")

    def test_candidate_orientation_is_required_and_both_strands_are_representable(self):
        candidates = []
        for index, orientation in enumerate(("+", "-"), 1):
            locus = {
                "locus_id": f"L{index}", "sseqid": "virus", "query_ids": f"q{index}",
                "orientation": orientation, "task": "blastn", "category": "TARGET_VIRUS",
                "covered_reference_bp": "40", "max_query_length": "40",
            }
            competitive = {
                "qseqid": f"q{index}", "task": "blastn", "specificity_status": "TARGET_SPECIFIC",
            }
            result = classify(
                "synthetic", [locus], [competitive], [], [], "UNCONTROLLED", "shotgun", {}, True,
            )
            candidates.append(result["candidates"][0])
        self.assertEqual([candidate["orientation"] for candidate in candidates], ["+", "-"])

        document = classify(
            "synthetic",
            [{
                "locus_id": "L3", "sseqid": "virus", "query_ids": "q3", "orientation": "+",
                "task": "blastn", "category": "TARGET_VIRUS", "covered_reference_bp": "40",
                "max_query_length": "40",
            }],
            [{"qseqid": "q3", "task": "blastn", "specificity_status": "TARGET_SPECIFIC"}],
            [], [], "UNCONTROLLED", "shotgun", {}, True,
        )
        document["candidates"][0].pop("orientation")
        with self.assertRaisesRegex(ValueError, "candidate missing fields: orientation"):
            validate_document(document)


if __name__ == "__main__":
    unittest.main()
