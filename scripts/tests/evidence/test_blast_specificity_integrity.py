import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from aggregate_hsps import aggregate, load_labels, parse_blast
from blast_router import deduplicate_combined_hits, run_router
from build_loci import build_loci
from classify_sample import classify
from competitive_hits import evaluate


def fragment_hit(subject, category, score, qcov=0.9):
    return {
        "qseqid": "q",
        "sseqid": subject,
        "category": category,
        "taxon": subject,
        "task": "blastn",
        "best_bitscore": str(score),
        "query_coverage": str(qcov),
        "low_complexity_status": "ACCEPTABLE",
    }


class BlastSpecificityIntegrityTests(unittest.TestCase):
    def test_dual_profile_dedup_keeps_strongest_exact_coordinate_hit(self):
        weak = "q\ts\t90\t20\t2\t0\t1\t20\t10\t29\t1e-2\t20\t30\t100\n"
        strong = "q\ts\t100\t20\t0\t0\t1\t20\t10\t29\t1e-8\t40\t30\t100\n"
        result = deduplicate_combined_hits([weak, strong]).strip().split("\t")
        self.assertEqual(float(result[11]), 40.0)

    def test_dedup_does_not_collapse_distinct_query_intervals(self):
        first = "q\ts\t95\t20\t1\t0\t1\t20\t10\t29\t1e-5\t30\t40\t100\n"
        second = "q\ts\t95\t20\t1\t0\t21\t40\t10\t29\t1e-5\t30\t40\t100\n"
        self.assertEqual(len(deduplicate_combined_hits([first, second]).splitlines()), 2)

    def test_malformed_coordinates_are_rejected_before_aggregation(self):
        line = "q\ts\t99\t20\t0\t0\t1\t40\t1\t20\t1e-5\t50\t20\t100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.tsv"
            path.write_text(line, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "coordinates exceed"):
                parse_blast(path, "blastn")

    def test_disconnected_reference_hsps_remain_separate_fragments(self):
        common = {
            "qseqid": "q",
            "sseqid": "ref",
            "task": "blastn",
            "pident": 100.0,
            "length": 20,
            "mismatch": 0,
            "gapopen": 0,
            "evalue": 1e-8,
            "bitscore": 40.0,
            "qlen": 100,
            "slen": 1000,
        }
        records = [
            dict(common, qstart=1, qend=20, sstart=1, send=20),
            dict(common, qstart=81, qend=100, sstart=500, send=519),
        ]
        rows = aggregate(records, {"q": "ACGT" * 25}, {})
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["query_covered_bp"] for row in rows], [20, 20])

    def test_locus_query_coverage_is_scoped_per_query(self):
        base = {
            "sseqid": "ref",
            "segment": "u",
            "orientation": "+",
            "task": "blastn",
            "category": "TARGET_VIRUS",
            "slen": "1000",
            "hsp_count": "1",
            "best_bitscore": "50",
            "sum_bitscore": "50",
            "best_evalue": "1e-5",
            "adj_identity": "80",
            "low_complexity_status": "ACCEPTABLE",
            "qlen": "20",
        }
        rows = [
            dict(
                base,
                qseqid="q1",
                reference_intervals="1-20",
                query_intervals="1-20",
                query_covered_bp="20",
                sequence_sha256="a",
            ),
            dict(
                base,
                qseqid="q2",
                reference_intervals="10-29",
                query_intervals="1-20",
                query_covered_bp="20",
                sequence_sha256="b",
            ),
        ]
        locus = build_loci(rows, gap_bp=0)[0]
        self.assertEqual(locus["query_covered_bp"], 40)
        self.assertEqual(locus["max_query_covered_bp"], 20)
        self.assertEqual(locus["query_intervals"], "q1:1-20|q2:1-20")

    def test_candidate_length_uses_aligned_query_span(self):
        locus = {
            "locus_id": "L1",
            "sseqid": "virus",
            "category": "TARGET_VIRUS",
            "query_ids": "q",
            "orientation": "+",
            "task": "blastn",
            "covered_reference_bp": "20",
            "max_query_length": "100",
            "max_query_covered_bp": "20",
            "reference_intervals": "1-20",
        }
        competitive = {
            "qseqid": "q",
            "task": "blastn",
            "specificity_status": "TARGET_SPECIFIC",
        }
        result = classify(
            "synthetic", [locus], [competitive], [], [], "UNCONTROLLED", "shotgun", {}
        )
        gate = next(
            item for item in result["promotion_gates"]
            if item["gate_id"] == "candidate_evidence"
        )
        self.assertEqual(gate["status"], "BLOCKED")

    def test_unlabeled_hit_blocks_target_specificity(self):
        result = evaluate(
            [
                fragment_hit("target", "TARGET_VIRUS", 100),
                fragment_hit("host", "HOST", 80),
                fragment_hit("unknown", "UNLABELED", 99),
            ]
        )[0]
        self.assertEqual(result["specificity_status"], "AMBIGUOUS")
        self.assertIn("UNLABELED_HIT_PRESENT", result["specificity_flags"])

    def test_unverified_external_search_cannot_be_target_specific(self):
        result = evaluate(
            [
                fragment_hit("target", "TARGET_VIRUS", 100),
                fragment_hit("host", "HOST", 80),
            ],
            search_complete=False,
        )[0]
        self.assertNotEqual(result["specificity_status"], "TARGET_SPECIFIC")
        self.assertIn("SEARCH_SPACE_UNVERIFIED", result["specificity_flags"])

    def test_duplicate_subject_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "labels.tsv"
            path.write_text(
                "sseqid\tcategory\nref\tTARGET_VIRUS\nref\tHOST\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_labels(str(path))


@unittest.skipUnless(
    all(shutil.which(name) for name in ("blastn", "blastdbcmd", "makeblastdb")),
    "NCBI BLAST+ tools are not installed",
)
class RealBlastRouterTests(unittest.TestCase):
    def test_report_limit_covers_every_competitive_subject(self):
        config = {
            "blast": {
                "short_max_bp": 29,
                "dual_mode_min_bp": 30,
                "dual_mode_max_bp": 49,
                "explicit_dust": False,
                "soft_masking": True,
            }
        }
        query_sequence = "ACGTCAGTGCATGACCTGACTAGCATCGTACGATGCTAGC"
        subject_sequence = query_sequence + "TGCATCGATCGTACGTAGCTAGCATGCTACGT"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "panel.fa"
            reference.write_text(
                "".join(
                    f">subject_{index:03d}\n{subject_sequence}\n"
                    for index in range(61)
                ),
                encoding="utf-8",
            )
            query = root / "query.fa"
            query.write_text(f">query\n{query_sequence}\n", encoding="utf-8")
            database = root / "panel"
            subprocess.run(
                [
                    shutil.which("makeblastdb"),
                    "-in",
                    str(reference),
                    "-dbtype",
                    "nucl",
                    "-parse_seqids",
                    "-out",
                    str(database),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            short = root / "short.tsv"
            conventional = root / "conventional.tsv"
            provenance = run_router(
                str(query),
                str(database),
                config,
                1,
                short,
                conventional,
                None,
            )
            self.assertEqual(provenance["database_sequence_count"], 61)
            self.assertGreaterEqual(
                provenance["profiles"]["short"]["max_target_seqs"], 61
            )
            self.assertEqual(
                len({line.split("\t")[1] for line in short.read_text().splitlines()}),
                61,
            )
            self.assertEqual(
                len(
                    {
                        line.split("\t")[1]
                        for line in conventional.read_text().splitlines()
                    }
                ),
                61,
            )


if __name__ == "__main__":
    unittest.main()
