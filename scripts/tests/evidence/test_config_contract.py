import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from common import validate_evidence_config


BASE = {
    "schema_version": "2.0-alpha",
    "blast": {"short_max_bp": 29, "dual_mode_min_bp": 30, "dual_mode_max_bp": 49, "explicit_dust": True, "soft_masking": True},
    "locus": {"gap_bp": 100, "minimum_candidate_bp": 50},
    "support": {"minimum_unique_templates": 3, "minimum_distinct_starts_shotgun": 2, "minimum_mapq": 10, "minimum_base_quality": 20, "require_proper_pair_shotgun": True},
    "specificity": {"minimum_delta_bitscore": 10, "maximum_qcov_difference_pp": 5},
    "sample_evidence": {"multi_locus_minimum": 2, "multi_locus_total_bp": 150, "genome_breadth_1x": .2, "median_covered_depth": 3, "concentration_window_bp": 100},
    "controls": {"provisional_sample_to_negative_ratio": 10, "uncontrolled_maximum": "MULTI_LOCUS_CANDIDATE"},
    "phylogeny": {"minimum_aligned_bp": 200, "minimum_informative_sites": 20, "minimum_references": 4, "maximum_n_fraction": .05, "maximum_gap_fraction": .5},
}


class ConfigContractTests(unittest.TestCase):
    def test_complete_config_is_valid(self):
        self.assertEqual(validate_evidence_config(copy.deepcopy(BASE))["schema_version"], "2.0-alpha")

    def test_mapq_and_boolean_types_are_strict(self):
        value = copy.deepcopy(BASE); value["support"]["minimum_mapq"] = 61
        with self.assertRaises(ValueError): validate_evidence_config(value)
        value = copy.deepcopy(BASE); value["blast"]["explicit_dust"] = "yes"
        with self.assertRaises(ValueError): validate_evidence_config(value)

    def test_unknown_or_missing_keys_are_rejected(self):
        value = copy.deepcopy(BASE); value["support"]["silent_override"] = 1
        with self.assertRaises(ValueError): validate_evidence_config(value)
        value = copy.deepcopy(BASE); del value["phylogeny"]["minimum_references"]
        with self.assertRaises(ValueError): validate_evidence_config(value)


if __name__ == "__main__":
    unittest.main()
