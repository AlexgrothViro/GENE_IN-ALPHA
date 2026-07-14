import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ux_dashboard", ROOT / "scripts" / "ux_dashboard.py")
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


class DashboardSecurityTests(unittest.TestCase):
    def test_only_loopback_hosts_are_allowed(self):
        self.assertTrue(dashboard.is_loopback_host("127.0.0.1"))
        self.assertTrue(dashboard.is_loopback_host("localhost"))
        self.assertFalse(dashboard.is_loopback_host("0.0.0.0"))
        self.assertFalse(dashboard.is_loopback_host("192.168.1.10"))

    def test_config_values_are_shell_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "picornavirus.env"
            original = dashboard.CONFIG_ENV_PRIMARY
            dashboard.CONFIG_ENV_PRIMARY = target
            try:
                dashboard.save_config_env({"SPADES_PARAMS": "$(touch should_not_run)"})
                content = target.read_text(encoding="utf-8")
                self.assertIn("'$(touch should_not_run)'", content)
            finally:
                dashboard.CONFIG_ENV_PRIMARY = original

        with self.assertRaises(ValueError):
            dashboard.validate_config_updates({"BIND_HOST": "0.0.0.0"})

    def test_upload_rejects_traversal_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = dashboard.REPO_ROOT
            dashboard.REPO_ROOT = Path(tmp)
            r1 = b"@read/1\nACGT\n+\nIIII\n"
            r2 = b"@read/2\nTGCA\n+\nIIII\n"
            try:
                with self.assertRaises(ValueError):
                    dashboard.import_uploaded_files("../escape", "r1.fastq", r1, "r2.fastq", r2)
                dashboard.import_uploaded_files("safe", "r1.fastq", r1, "r2.fastq", r2)
                with self.assertRaises(FileExistsError):
                    dashboard.import_uploaded_files("safe", "r1.fastq", r1, "r2.fastq", r2)
            finally:
                dashboard.REPO_ROOT = original


if __name__ == "__main__":
    unittest.main()
