import gzip
import os
import random
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

    def test_disabled_filter_preserves_previous_valid_host_filtered_outputs(self):
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            reads = tmp / "reads"
            output = tmp / "filtered"
            reads.mkdir()
            output.mkdir()
            r1 = reads / "sample_R1.fastq.gz"
            r2 = reads / "sample_R2.fastq.gz"
            with gzip.open(r1, "wt", encoding="utf-8") as handle:
                handle.write("@new/1\nACGT\n+\nIIII\n")
            with gzip.open(r2, "wt", encoding="utf-8") as handle:
                handle.write("@new/2\nTGCA\n+\nIIII\n")

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

            self.assertEqual(result.returncode, 0, result.stderr)
            with gzip.open(final_r1, "rt", encoding="utf-8") as handle:
                self.assertIn("@previous/1", handle.read())
            with gzip.open(final_r2, "rt", encoding="utf-8") as handle:
                self.assertIn("@previous/2", handle.read())
            self.assertEqual(list(output.glob(".sample.host-filter.*")), [])

    def test_disabled_filter_does_not_create_misleading_host_removed_outputs(self):
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
            self.assertFalse((output / "sample_R1.host_removed.fastq.gz").exists())
            self.assertFalse((output / "sample_R2.host_removed.fastq.gz").exists())
            self.assertEqual(list(output.glob(".sample.host-filter.*")), [])

    def test_enabled_filter_requires_explicit_host_identity(self):
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            r1 = tmp / "sample_R1.fastq"
            r2 = tmp / "sample_R2.fastq"
            r1.write_text("@new/1\nACGT\n+\nIIII\n", encoding="utf-8")
            r2.write_text("@new/2\nTGCA\n+\nIIII\n", encoding="utf-8")
            env = {
                **os.environ,
                "PIPELINE_CONFIG_LOADED": "1",
                "HOST_FILTER_ENABLED": "true",
                "HOST_NAME": "",
                "HOST_INDEX_PREFIX": "",
                "HOST_REMOVED_DIR": repo_relative_path(tmp / "filtered"),
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
            self.assertIn("HOST_NAME", result.stderr)

    def test_pair_filter_keeps_only_templates_with_both_mates_unmapped(self):
        script = (ROOT / "scripts/03_filter_host.sh").read_text(encoding="utf-8")
        self.assertIn("samtools view -b -f 12 -F 256", script)
        self.assertNotIn("--un-conc-gz", script)
        self.assertIn('-U "$SINGLE"', script)
        self.assertIn("--un-gz", script)
        self.assertIn("Use SAMPLE_SINGLE ou SAMPLE_R1/SAMPLE_R2, mas não ambos.", script)

    def test_qc_validates_single_end_fastq_and_fastp_report_before_promotion(self):
        script = (ROOT / "scripts/02_qc_fastp.sh").read_text(encoding="utf-8")
        self.assertIn('RAW_SINGLE="${SAMPLE_SINGLE:-${SINGLE:-}}"', script)
        self.assertIn("Entradas pareadas explícitas exigem SAMPLE_R1/R1 e SAMPLE_R2/R2.", script)
        self.assertIn('fastp-json "$WORK_DIR/fastp.json"', script)
        self.assertIn("promote_qc_outputs", script)
        self.assertNotIn("--dedup", script)

    def test_evidence_provenance_hashes_qc_and_host_index_artifacts(self):
        runner = (ROOT / "scripts/22_run_evidence_v2.sh").read_text(encoding="utf-8")
        writer = (ROOT / "scripts/evidence/write_provenance.py").read_text(encoding="utf-8")
        self.assertIn("fastp_report=$QC_REPORT", runner)
        self.assertIn("host_filter_log=$HOST_FILTER_LOG", runner)
        self.assertIn("HOST_INDEX_ARTIFACTS", runner)
        self.assertIn("host_index_${component//./_}", runner)
        self.assertIn('HOST_FILTER_READ_POLICY="both_mates_unmapped"', runner)
        self.assertIn("qc_qualified_quality_phred=$QC_MIN_QUALITY", runner)
        self.assertIn('"fastp"', writer)
        self.assertIn('"bowtie2-inspect"', writer)

    def test_real_fastp_accepts_synthetic_single_end_input(self):
        if not shutil.which("fastp"):
            self.skipTest("fastp real nao encontrado")
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            reads = tmp / "single.fastq.gz"
            cleaned = tmp / "cleaned"
            reports = tmp / "reports"
            with gzip.open(reads, "wt", encoding="utf-8") as handle:
                handle.write("@read1\n" + "ACGT" * 20 + "\n+\n" + "I" * 80 + "\n")
                handle.write("@read2\n" + "TGCA" * 20 + "\n+\n" + "I" * 80 + "\n")
            env = {
                **os.environ,
                "PIPELINE_CONFIG_LOADED": "1",
                "SAMPLE_SINGLE": repo_relative_path(reads),
                "QC_OUT_DIR": repo_relative_path(cleaned),
                "QC_REPORT_DIR": repo_relative_path(reports),
                "QC_MIN_LEN": "50",
                "QC_MIN_QUAL": "20",
            }
            result = subprocess.run(
                [self.bash, bash_path(ROOT / "scripts/02_qc_fastp.sh"), "sample", "1"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with gzip.open(cleaned / "sample.clean.fastq.gz", "rt", encoding="utf-8") as handle:
                output = handle.read()
            self.assertIn("@read1", output)
            self.assertTrue((reports / "sample_fastp.json").is_file())
            self.assertTrue((reports / "sample_fastp.html").is_file())

    def test_real_host_filter_drops_entire_pair_if_one_mate_maps_host(self):
        required = ("bowtie2", "bowtie2-build", "bowtie2-inspect", "samtools")
        if any(not shutil.which(command) for command in required):
            self.skipTest("Bowtie2/samtools reais nao encontrados")
        with workspace_tempdir() as tmp:
            tmp = Path(tmp)
            rng = random.Random(20260729)
            host_sequence = "".join(rng.choice("ACGT") for _ in range(500))
            host_fasta = tmp / "host.fa"
            host_fasta.write_text(">synthetic_host\n" + host_sequence + "\n", encoding="utf-8")
            index_prefix = tmp / "synthetic_host"
            build = subprocess.run(
                ["bowtie2-build", str(host_fasta), str(index_prefix)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)

            r1 = tmp / "sample_R1.fastq.gz"
            r2 = tmp / "sample_R2.fastq.gz"
            quality = "I" * 75
            with gzip.open(r1, "wt", encoding="utf-8") as handle:
                handle.write(f"@mixed/1\n{host_sequence[100:175]}\n+\n{quality}\n")
                handle.write(f"@nonhost/1\n{'N' * 75}\n+\n{quality}\n")
            with gzip.open(r2, "wt", encoding="utf-8") as handle:
                handle.write(f"@mixed/2\n{'N' * 75}\n+\n{quality}\n")
                handle.write(f"@nonhost/2\n{'N' * 75}\n+\n{quality}\n")

            output = tmp / "filtered"
            env = {
                **os.environ,
                "PIPELINE_CONFIG_LOADED": "1",
                "HOST_FILTER_ENABLED": "true",
                "HOST_NAME": "synthetic_host",
                "HOST_INDEX_PREFIX": repo_relative_path(index_prefix),
                "HOST_MIN_ALIGNMENT_RATE": "0",
                "HOST_REMOVED_DIR": repo_relative_path(output),
                "SAMPLE_R1": repo_relative_path(r1),
                "SAMPLE_R2": repo_relative_path(r2),
                "THREADS": "1",
            }
            result = subprocess.run(
                [self.bash, bash_path(ROOT / "scripts/03_filter_host.sh"), "sample"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with gzip.open(
                output / "sample_R1.host_removed.fastq.gz", "rt", encoding="utf-8"
            ) as handle:
                output_r1 = handle.read()
            with gzip.open(
                output / "sample_R2.host_removed.fastq.gz", "rt", encoding="utf-8"
            ) as handle:
                output_r2 = handle.read()
            self.assertIn("@nonhost", output_r1)
            self.assertIn("@nonhost", output_r2)
            self.assertNotIn("@mixed", output_r1)
            self.assertNotIn("@mixed", output_r2)

    def test_pipeline_never_silently_falls_back_when_qc_or_host_filter_fails(self):
        pipeline = (ROOT / "scripts/20_run_pipeline.sh").read_text(encoding="utf-8")
        self.assertNotIn("fastp não gerou reads limpos válidos; usando reads originais", pipeline)
        self.assertNotIn("fastp não encontrado — etapa de QC ignorada", pipeline)
        self.assertNotIn("03_filter_host.sh não gerou reads válidos; usando reads da etapa anterior", pipeline)
        self.assertIn("fastp não encontrado; instale a dependência ou use --skip-qc explicitamente", pipeline)
        self.assertIn('CLEANED_SINGLE="${QC_OUT_DIR}/${SAMPLE_NAME}.clean.fastq.gz"', pipeline)
        self.assertIn('"$INPUT_MODE" == "READS"', pipeline)


if __name__ == "__main__":
    unittest.main()
