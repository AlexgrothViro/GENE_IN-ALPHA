import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from runtime_preflight import command_info, run


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

    def test_non_utf8_tool_version_output_is_replaced_not_raised(self):
        with (
            patch("runtime_preflight.shutil.which", return_value=sys.executable),
            patch(
                "runtime_preflight.subprocess.run",
                return_value=SimpleNamespace(stdout="tool 1.0 \ufffd\n", stderr=""),
            ) as mocked_run,
        ):
            info = command_info("synthetic-tool")
        self.assertEqual(info["version"], "tool 1.0 \ufffd")
        self.assertEqual(mocked_run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(mocked_run.call_args.kwargs["errors"], "replace")
        self.assertEqual(mocked_run.call_args.kwargs["timeout"], 15)

    def test_blast_uses_its_read_only_version_flag(self):
        with (
            patch("runtime_preflight.shutil.which", return_value=sys.executable),
            patch(
                "runtime_preflight.subprocess.run",
                return_value=SimpleNamespace(stdout="blastn: 2.17.0+\n", stderr=""),
            ) as mocked_run,
        ):
            info = command_info("blastn")
        self.assertEqual(info["version"], "blastn: 2.17.0+")
        self.assertEqual(mocked_run.call_args.args[0], [sys.executable, "-version"])

    def test_velvet_is_hashed_without_potentially_mutating_version_probe(self):
        with (
            patch("runtime_preflight.shutil.which", return_value=sys.executable),
            patch("runtime_preflight.subprocess.run") as mocked_run,
        ):
            info = command_info("velvetg")
        self.assertIsNone(info["version"])
        self.assertIsNotNone(info["sha256"])
        mocked_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
