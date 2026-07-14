import gzip
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "input_validation", ROOT / "scripts" / "lib" / "input_validation.py"
)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class InputValidationTests(unittest.TestCase):
    def test_sample_id_rejects_path_traversal_and_shell_chars(self):
        for value in ("../sample", "a/b", "sample name", "$(touch x)", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validation.validate_sample_id(value)

    def test_paired_fastq_checks_ids_and_lengths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            r1 = tmp / "R1.fastq.gz"
            r2 = tmp / "R2.fastq.gz"
            with gzip.open(r1, "wt") as fh:
                fh.write("@read1/1\nACGT\n+\nIIII\n")
            with gzip.open(r2, "wt") as fh:
                fh.write("@read2/2\nACGT\n+\nIIII\n")
            with self.assertRaises(ValueError):
                validation.validate_fastq(r1, r2)

    def test_fasta_rejects_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contigs.fa"
            path.write_text(">c1\nACGT\n>c1\nACGT\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validation.validate_fasta(path)

    def test_valid_paired_fastq(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            r1 = tmp / "R1.fastq"
            r2 = tmp / "R2.fastq"
            r1.write_text("@read1/1\nACGT\n+\nIIII\n", encoding="utf-8")
            r2.write_text("@read1/2\nTGCA\n+\nIIII\n", encoding="utf-8")
            self.assertEqual(validation.validate_fastq(r1, r2), 1)


if __name__ == "__main__":
    unittest.main()
