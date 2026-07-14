import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DbManagerContractTests(unittest.TestCase):
    def test_bowtie2_cache_contract_accepts_small_and_large_indexes(self):
        text = (ROOT / "scripts" / "13_db_manager.sh").read_text(encoding="utf-8")
        self.assertIn("for ext in bt2 bt2l", text)
        self.assertIn('bowtie2_index_complete "${REPO_ROOT}/bowtie2/custom"', text)
        self.assertIn('BUILD_EXT="bt2l"', text)
        self.assertIn('BUILD_EXT="bt2"', text)


if __name__ == "__main__":
    unittest.main()
