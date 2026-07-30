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

    def test_evidence_receives_database_and_input_provenance(self):
        pipeline = (ROOT / "scripts" / "20_run_pipeline.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "22_run_evidence_v2.sh").read_text(encoding="utf-8")
        self.assertIn('DATABASE_MANIFEST="${BLAST_DB}.db-manifest.json"', pipeline)
        self.assertIn('--database-manifest "$DATABASE_MANIFEST"', pipeline)
        self.assertIn('--artifact "database_generation_manifest=$DATABASE_MANIFEST"', runner)
        self.assertIn('--artifact "input_r1=$R1"', runner)
        self.assertIn('--artifact "input_single=$SINGLE"', runner)

    def test_ncbi_download_is_retrying_and_fail_closed(self):
        common = (ROOT / "scripts" / "lib" / "common.sh").read_text(encoding="utf-8")
        manager = (ROOT / "scripts" / "13_db_manager.sh").read_text(encoding="utf-8")
        self.assertIn("fetch_ncbi_fasta()", common)
        self.assertIn("EDIRECT_RETRIES", common)
        self.assertIn("grep -q '^>'", common)
        self.assertIn('fetch_ncbi_fasta "$REF_TMP"', manager)
        self.assertIn('input_validation.py" fasta "$REF_TMP', manager)

    def test_all_runtime_preflights_accept_blast_v5_aliases(self):
        common = (ROOT / "scripts" / "lib" / "common.sh").read_text(encoding="utf-8")
        pipeline = (ROOT / "scripts" / "20_run_pipeline.sh").read_text(encoding="utf-8")
        legacy_blast = (ROOT / "scripts" / "02_run_blast.sh").read_text(encoding="utf-8")
        environment = (ROOT / "scripts" / "00_check_env.sh").read_text(encoding="utf-8")

        self.assertIn("validate_blast_database()", common)
        self.assertIn('blastdbcmd -db "$database" -info', common)
        self.assertIn('validate_blast_database "$BLAST_DB"', pipeline)
        self.assertIn('check_blast_database "$DB"', legacy_blast)
        self.assertIn('validate_blast_database "$DIAG_BLAST_DB"', environment)
        self.assertNotIn('${BLAST_DB}.nhr', pipeline)
        self.assertNotIn('${DB}.nhr', legacy_blast)


if __name__ == "__main__":
    unittest.main()
