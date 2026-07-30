import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tests"))
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from environment_lock import validate as validate_lock
from verify_locked_runtime import package_record_from_url, verify


def write_lock_fixture(root: Path, version: str = "1.2.3", build: str = "py311_0"):
    lockfile = root / "conda-linux-64.lock"
    lockfile.write_text(
        "@EXPLICIT\n"
        f"https://example.invalid/noarch/synthetic-tool-{version}-{build}.conda#"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )
    manifest = root / "environment_lock.json"
    manifest.write_text(
        json.dumps({
            "schema_version": "1.0",
            "lockfile": lockfile.name,
            "sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest(),
            "package_entries": 1,
        }),
        encoding="utf-8",
    )
    return lockfile, manifest


def write_conda_record(prefix: Path, version: str = "1.2.3", build: str = "py311_0"):
    metadata = prefix / "conda-meta"
    metadata.mkdir(parents=True)
    (metadata / f"synthetic-tool-{version}-{build}.json").write_text(
        json.dumps({"name": "synthetic-tool", "version": version, "build": build}),
        encoding="utf-8",
    )


class ReproducibilityContractTests(unittest.TestCase):
    def test_package_filename_parser_preserves_hyphenated_name(self):
        self.assertEqual(
            package_record_from_url(
                "https://example.invalid/noarch/synthetic-tool-1.2.3-py311_0.conda"
            ),
            ("synthetic-tool", "1.2.3", "py311_0"),
        )

    def test_exact_active_environment_is_lock_qualified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lockfile, manifest = write_lock_fixture(root)
            prefix = root / "env"
            write_conda_record(prefix)
            report = verify(lockfile, manifest, prefix, prefix / "bin" / "python")
            self.assertEqual(report["status"], "LOCK_QUALIFIED")
            self.assertEqual(report["package_entries"], 1)

    def test_version_or_build_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lockfile, manifest = write_lock_fixture(root)
            prefix = root / "env"
            write_conda_record(prefix, version="1.2.4")
            with self.assertRaisesRegex(ValueError, "ACTIVE_ENVIRONMENT_LOCK_MISMATCH"):
                verify(lockfile, manifest, prefix, prefix / "bin" / "python")

    def test_python_outside_active_environment_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lockfile, manifest = write_lock_fixture(root)
            prefix = root / "env"
            write_conda_record(prefix)
            with self.assertRaisesRegex(ValueError, "ACTIVE_PYTHON_OUTSIDE_LOCKED_ENV"):
                verify(lockfile, manifest, prefix, root / "other" / "python")

    def test_manifest_entry_count_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lockfile, manifest = write_lock_fixture(root)
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["package_entries"] = 2
            manifest.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "LOCKFILE_ENTRY_COUNT_MISMATCH"):
                validate_lock(lockfile, manifest)

    def test_make_targets_keep_engineering_operational_and_reproducible_separate(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "tests" / "run_test_suite.sh").read_text(encoding="utf-8")
        tiers = (ROOT / "docs" / "quality" / "testing-tiers.md").read_text(encoding="utf-8")
        self.assertIn("test: test-engineering", makefile)
        self.assertIn("test-operational:", makefile)
        self.assertIn("test-reproducible:", makefile)
        self.assertIn("não constitui validação científica", runner)
        for label in ("Engenharia", "Operacional", "Reprodutibilidade", "Validação científica"):
            self.assertIn(label, tiers)


if __name__ == "__main__":
    unittest.main()
