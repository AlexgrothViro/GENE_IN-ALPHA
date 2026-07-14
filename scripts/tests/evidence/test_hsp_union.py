import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from aggregate_hsps import aggregate, load_labels, parse_blast
from common import read_fasta


class HspUnionTests(unittest.TestCase):
    def test_overlapping_hsps_use_union_not_sum(self):
        fixture = Path(__file__).parent / "fixtures"
        rows = aggregate(
            parse_blast(fixture / "overlapping_hits.tsv", "blastn"),
            read_fasta(fixture / "query_sequences.txt"),
            load_labels(str(fixture / "subject_labels.tsv")),
        )
        query_a = next(row for row in rows if row["qseqid"] == "query_a")
        self.assertEqual(query_a["query_covered_bp"], 60)
        self.assertEqual(query_a["reference_covered_bp"], 61)
        self.assertEqual(query_a["hsp_count"], 2)
        self.assertLessEqual(float(query_a["adj_identity"]), 100.0)


if __name__ == "__main__":
    unittest.main()
