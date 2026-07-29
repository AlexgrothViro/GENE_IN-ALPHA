import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from runtime_preflight import run


class RuntimePreflightTests(unittest.TestCase):
    def test_effective_python_and_missing_command_are_reported(self):
        report, errors = run(ROOT / "config" / "evidence_v2.yaml", "spades", "none", False,
                             ["__gene_in_missing_tool__"], ROOT / "conda-linux-64.lock",
                             ROOT / "config" / "environment_lock.json")
        self.assertEqual(report["python"]["executable"], sys.executable)
        self.assertIn("__gene_in_missing_tool__", report["commands"])
        self.assertTrue(any("__gene_in_missing_tool__" in error for error in errors))

    def test_preflight_report_has_machine_readable_valid_flag(self):
        report, errors = run(ROOT / "config" / "evidence_v2.yaml", "spades", "none", False, [],
                             ROOT / "conda-linux-64.lock", ROOT / "config" / "environment_lock.json")
        self.assertEqual(not errors, report.get("valid", not errors))


if __name__ == "__main__":
    unittest.main()
