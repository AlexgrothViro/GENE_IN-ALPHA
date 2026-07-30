import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

import sys

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from analysis_profiles import load_profiles, resolve_profile
from activation_policy import conclusion_for, load_activation_policy
from assembly_consensus import combine, locus_concordance


class ActivationPolicyTests(unittest.TestCase):
    def test_active_policy_is_e1_only_and_non_diagnostic(self):
        policy = load_activation_policy(ROOT / "config" / "evidence_activation.json")
        self.assertFalse(policy["shadow_mode"])
        self.assertEqual(policy["evidence_ceiling"], "E1")
        self.assertFalse(policy["invariants"]["diagnostic_language_allowed"])
        self.assertEqual(
            conclusion_for(policy, "EVIDENCE_RECOVERED"),
            "E1_COMPUTATIONAL_EVIDENCE",
        )


class AnalysisProfileTests(unittest.TestCase):
    def test_profiles_are_typed_and_consensus_requires_two_assemblers(self):
        config = load_profiles(ROOT / "config" / "analysis_profiles.json")
        profile_id, profile = resolve_profile(config, "assembly-consensus")
        self.assertEqual(profile_id, "assembly-consensus")
        self.assertEqual(profile["assembly"]["strategy"], "consensus")
        self.assertEqual(profile["assembly"]["minimum_successful_assemblers"], 2)
        self.assertEqual(profile["evidence_ceiling"], "E1")
        self.assertTrue(all(
            plugin["evidence_authority"].endswith(("_ONLY",))
            for plugin in config["plugins"]
        ))

    def test_plugin_cannot_claim_promotion_authority(self):
        config = json.loads(
            (ROOT / "config" / "analysis_profiles.json").read_text(encoding="utf-8")
        )
        config["plugins"][0]["evidence_authority"] = "PROMOTE_TO_E2"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "promotion authority"):
                load_profiles(path)


class AssemblyConsensusTests(unittest.TestCase):
    def test_exact_and_locus_concordance_are_observational(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            velvet = root / "velvet.fa"
            spades = root / "spades.fa"
            metaspades = root / "metaspades.fa"
            shared = "ACGT" * 75
            velvet.write_text(f">v1\n{shared}\n>v2\n{'A' * 240}\n", encoding="utf-8")
            spades.write_text(f">s1\n{shared}\n>s2\n{'C' * 250}\n", encoding="utf-8")
            metaspades.write_text(f">m1\n{shared}\n", encoding="utf-8")
            out_fasta = root / "combined.fa"
            manifest_path = root / "manifest.json"
            manifest = combine(
                {"velvet": velvet, "spades": spades, "metaspades": metaspades},
                {"velvet": "SUCCESS", "spades": "SUCCESS", "metaspades": "SUCCESS"},
                out_fasta,
                manifest_path,
                2,
                "assembly-consensus",
            )
            self.assertTrue(manifest["consensus_requirement_met"])
            self.assertEqual(manifest["multi_assembler_exact_sequence_count"], 1)
            shared_query = next(
                item["query_id"] for item in manifest["sequences"] if item["support_count"] == 3
            )
            loci = root / "loci.tsv"
            loci.write_text(
                "sseqid\tcategory\tlocus_id\tquery_ids\n"
                f"virus\tTARGET_VIRUS\tL1\t{shared_query}\n",
                encoding="utf-8",
            )
            result = locus_concordance(
                loci,
                manifest_path,
                root / "concordance.tsv",
                root / "concordance.json",
            )
            self.assertEqual(result["multi_assembler_locus_count"], 1)
            self.assertEqual(result["evidence_authority"], "CORROBORATION_ONLY")


if __name__ == "__main__":
    unittest.main()
