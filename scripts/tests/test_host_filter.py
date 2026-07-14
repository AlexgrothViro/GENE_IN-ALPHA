import gzip
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEST_TMP_ROOT = ROOT / "tmp" / "tests"


def find_bash() -> str | None:
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Git/bin/bash.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None
    return shutil.which("bash")


def bash_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return str(resolved)
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[1]
    return f"/{drive}{tail}"


def workspace_tempdir() -> tempfile.TemporaryDirectory:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)


def repo_relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


@unittest.skipUnless(find_bash(), "bash nao encontrado")
class HostFilterTests(unittest.TestCase):
    def setUp(self):
        self.bash = find_bash()

    def test_index_requires_all_six_components(self):
        with workspace_tempdir() as tmp:
            prefix = Path(tmp) / "host"
            library = bash_path(ROOT / "scripts/lib/host_filter.sh")
            env = {**os.environ, "PREFIX": bash_path(prefix), "LIBRARY": library}
            command = 'source "$LIBRARY"; resolve_bt2_index "$PREFIX"'

            for component in ("1", "2"):
                Path(f"{prefix}.{component}.bt2").write_text("partial\n", encoding="utf-8")
            partial = subprocess.run(
                [self.bash, "-c", command], env=env, capture_output=True, text=True
            )
            self.assertNotEqual(partial.returncode, 0)
            self.assertEqual(partial.stdout.strip(), "none")

            for component in ("3", "4", "rev.1", "rev.2"):
                Path(f"{prefix}.{component}.bt2").write_text("complete\n", encoding="utf-8")
            complete = subprocess.run(
                [self.bash, "-c", command], env=env, capture_output=True, text=True
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            self.assertEqual(complete.stdout.strip(), "small")

    def test_main_pipeline_uses_shared_index_validation(self):
        pipeline = (ROOT / "scripts/20_run_pipeline.sh").read_text(encoding="utf-8")
        self.assertIn('source "${SCRIPT_DIR}/lib/host_filter.sh"', pipeline)
        self.assertIn('resolve_bt2_index "$HOST_INDEX_PREFIX"', pipeline)
        self.assertNotIn('[[ -s "${HOST_INDEX_PREFIX}.1.bt2"', pipeline)

    def test_invalid_staged_pair_preserves_previous_outputs(self):
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            reads = tmp / "reads"
            output = tmp / "filtered"
            reads.mkdir()
            output.mkdir()
            r1 = reads / "sample_R1.fastq.gz"
            r2 = reads / "sample_R2.fastq.gz"
            r1.write_bytes(b"not-a-gzip")
            with gzip.open(r2, "wt", encoding="utf-8") as handle:
                handle.write("@read/2\nTGCA\n+\nIIII\n")

            final_r1 = output / "sample_R1.host_removed.fastq.gz"
            final_r2 = output / "sample_R2.host_removed.fastq.gz"
            with gzip.open(final_r1, "wt", encoding="utf-8") as handle:
                handle.write("@previous/1\nAAAA\n+\nIIII\n")
            with gzip.open(final_r2, "wt", encoding="utf-8") as handle:
                handle.write("@previous/2\nTTTT\n+\nIIII\n")

            env = {
                **os.environ,
                "HOST_FILTER_ENABLED": "false",
                "HOST_REMOVED_DIR": repo_relative_path(output),
                "SAMPLE_R1": repo_relative_path(r1),
                "SAMPLE_R2": repo_relative_path(r2),
            }
            result = subprocess.run(
                [self.bash, bash_path(ROOT / "scripts/03_filter_host.sh"), "sample"],
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("corrompidos", result.stderr)
            with gzip.open(final_r1, "rt", encoding="utf-8") as handle:
                self.assertIn("@previous/1", handle.read())
            with gzip.open(final_r2, "rt", encoding="utf-8") as handle:
                self.assertIn("@previous/2", handle.read())
            self.assertEqual(list(output.glob(".sample.host-filter.*")), [])

    def test_disabled_filter_promotes_valid_pair_and_cleans_staging(self):
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            reads = tmp / "reads"
            output = tmp / "filtered"
            reads.mkdir()
            output.mkdir()
            r1 = reads / "sample_R1.fastq"
            r2 = reads / "sample_R2.fastq"
            r1.write_text("@new/1\nACGT\n+\nIIII\n", encoding="utf-8")
            r2.write_text("@new/2\nTGCA\n+\nIIII\n", encoding="utf-8")

            env = {
                **os.environ,
                "HOST_FILTER_ENABLED": "false",
                "HOST_REMOVED_DIR": repo_relative_path(output),
                "SAMPLE_R1": repo_relative_path(r1),
                "SAMPLE_R2": repo_relative_path(r2),
            }
            result = subprocess.run(
                [self.bash, bash_path(ROOT / "scripts/03_filter_host.sh"), "sample"],
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with gzip.open(output / "sample_R1.host_removed.fastq.gz", "rt", encoding="utf-8") as handle:
                self.assertIn("@new/1", handle.read())
            with gzip.open(output / "sample_R2.host_removed.fastq.gz", "rt", encoding="utf-8") as handle:
                self.assertIn("@new/2", handle.read())
            self.assertEqual(list(output.glob(".sample.host-filter.*")), [])


if __name__ == "__main__":
    unittest.main()
