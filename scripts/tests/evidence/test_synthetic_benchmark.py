import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))

from generate_synthetic_matrix import generate


class SyntheticBenchmarkTests(unittest.TestCase):
    def test_matrix_has_required_boundaries_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            first, second = Path(left), Path(right)
            summary = generate(first); generate(second)
            self.assertEqual(summary["sequences"], 48)
            self.assertEqual((first / "short_fragment_matrix.fasta").read_bytes(), (second / "short_fragment_matrix.fasta").read_bytes())
            table = (first / "short_fragment_matrix.tsv").read_text(encoding="utf-8")
            for length in (20, 29, 30, 49, 50, 79, 80, 200):
                self.assertIn(f"_{length}bp", table)
            self.assertIn("\tdual\tEXPLORATORY_FRAGMENT", table)


if __name__ == "__main__":
    unittest.main()
