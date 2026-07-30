import unittest
from pathlib import Path
from unittest import mock

import scripts.ux_dashboard as dashboard


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "dashboard" / "index.html"
GUIDED_JS = REPO_ROOT / "dashboard" / "js" / "guided.js"
WIZARD_JS = REPO_ROOT / "dashboard" / "js" / "wizard.js"


class DashboardGuidedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.guided = GUIDED_JS.read_text(encoding="utf-8")
        cls.wizard = WIZARD_JS.read_text(encoding="utf-8")

    def test_reference_layout_contract_is_present(self):
        for element_id in (
            "context-bar",
            "next-action",
            "ctx-env",
            "ctx-db",
            "ctx-sample",
            "ctx-job",
            "history-search",
        ):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_wizard_uses_the_reference_five_phase_model(self):
        for label in ("Ambiente", "Banco viral", "Amostra", "Executar", "Acompanhar"):
            self.assertIn(f'label: "{label}"', self.wizard)
        self.assertEqual(self.wizard.count("label:"), 5)

    def test_review_and_gate_reuse_the_canonical_pipeline_form(self):
        self.assertIn('document.getElementById("pipeline-form")', self.guided)
        self.assertIn('#pipeline-form button[type="submit"]', self.guided)
        self.assertNotIn('fetch("/api/run"', self.guided)

    def test_scientific_language_remains_conservative(self):
        self.assertIn("evidência computacional", self.guided)
        self.assertIn("20–49 pb permanecem exploratórios", self.guided)
        self.assertIn("não constituem diagnóstico", self.guided)

    def test_preflight_reports_assembler_capability(self):
        with mock.patch("scripts.ux_dashboard.shutil.which", return_value=None):
            result = dashboard.get_preflight_status()
        self.assertFalse(result["ok"])
        self.assertFalse(result["assembler_available"])
        self.assertIn("nenhum montador", result["summary"])

    def test_environment_status_exposes_environment_file_contract(self):
        result = dashboard.get_environment_status()
        self.assertTrue(result["has_environment_yml"])
        self.assertTrue(result["environment_yml_path"].endswith("environment.yml"))
        self.assertTrue(result["environment_yml_mtime"])

    def test_module_allowlist_is_explicit(self):
        self.assertIn("guided.js", dashboard.JAVASCRIPT_MODULES)
        self.assertNotIn("../guided.js", dashboard.JAVASCRIPT_MODULES)

    def test_primary_workflow_controls_have_accessible_labels(self):
        for control_id in (
            "db-target", "db-query", "db-taxid",
            "upload-sample", "upload-r1-file", "upload-r2-file", "upload-zip-file",
            "import-sample", "import-r1", "import-r2",
            "assembly-only-sample-select", "assembly-only-assembler",
            "pipeline-assembler", "pipeline-kmer", "host-filter-mode",
            "advanced-sample-select", "advanced-min-pident", "advanced-min-aln-len",
        ):
            self.assertIn(f'for="{control_id}"', self.html, control_id)
            self.assertIn(f'id="{control_id}"', self.html, control_id)
        self.assertIn(
            'role="group" aria-labelledby="pipeline-sample-label"',
            self.html,
        )

    def test_complementary_analysis_exposes_real_artifact_contract(self):
        advanced_script = (REPO_ROOT / "scripts" / "21_run_advanced_analysis.sh").read_text(encoding="utf-8")
        jobs = (REPO_ROOT / "scripts" / "dashboard" / "jobs.py").read_text(encoding="utf-8")
        self.assertIn(r"\`${PHYLOGENY_GATE}\`", advanced_script)
        for artifact in (
            "advanced_alignment.fa", "advanced_tree.nwk", "advanced_gate.json",
            "advanced_hits.fa", "advanced_refs.fa", "advanced_summary.tsv",
        ):
            self.assertIn(artifact, jobs)
        self.assertIn('type=advanced_report', (REPO_ROOT / "dashboard" / "app.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
