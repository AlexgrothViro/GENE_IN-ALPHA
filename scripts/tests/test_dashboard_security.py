import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_pipeline_requires_explicit_database_selection(self):
        with self.assertRaisesRegex(ValueError, "explicitamente"):
            dashboard.build_command("pipeline", {"sample": "safe", "assembler": "spades"})
        command, environment = dashboard.build_command(
            "pipeline", {"sample": "safe", "assembler": "spades", "db": "ptv"}
        )
        self.assertIn("scripts/20_run_pipeline.sh", command)
        self.assertEqual(environment["DB"], "ptv")
        self.assertEqual(environment["HOST_FILTER_ENABLED"], "false")

    def test_auxiliary_dashboard_actions_have_executable_commands(self):
        check_command, _ = dashboard.build_command("check_env", {})
        demo_command, _ = dashboard.build_command("demo", {})
        db_command, _ = dashboard.build_command("build_db", {"db": "ptv"})
        assembly_command, _ = dashboard.build_command(
            "assembly_only", {"sample": "safe", "assembler": "spades"}
        )
        self.assertEqual(check_command, ["bash", "scripts/00_check_env.sh"])
        self.assertEqual(demo_command, ["make", "demo"])
        self.assertIn("make", db_command)
        self.assertIn("scripts/22_run_assembly_only.sh", assembly_command)

    def test_evidence_requires_database_and_defaults_to_no_host_filter(self):
        with self.assertRaisesRegex(ValueError, "explicitamente"):
            dashboard.build_command(
                "evidence_pipeline",
                {"sample": "safe", "assembler": "spades"},
            )
        command, environment = dashboard.build_command(
            "evidence_pipeline",
            {"sample": "safe", "assembler": "spades", "db": "ptv"},
        )
        self.assertIn("scripts/20_run_pipeline.sh", command)
        self.assertEqual(environment["DB"], "ptv")
        self.assertEqual(environment["HOST_FILTER_ENABLED"], "false")

    def test_evidence_batch_requires_database_and_accepts_explicit_host_filter(self):
        with patch.object(
            dashboard.EVIDENCE_SERVICE,
            "manifest_export",
            return_value=ROOT / "manifest.tsv",
        ), patch.object(
            dashboard,
            "validate_host_index",
            return_value={"valid": True, "message": "fixture"},
        ):
            with self.assertRaisesRegex(ValueError, "explicitamente"):
                dashboard.build_command("evidence_batch", {"manifest_id": "batch-safe"})
            command, environment = dashboard.build_command(
                "evidence_batch",
                {
                    "manifest_id": "batch-safe",
                    "target": "ptv",
                    "host_filter_mode": "custom",
                    "host_name": "Bos taurus",
                    "host_index_prefix": "ref/host/bos_taurus_bt2",
                },
            )
        self.assertIn("scripts/23_run_batch.sh", command)
        self.assertEqual(environment["DB"], "ptv")
        self.assertEqual(environment["HOST_FILTER_ENABLED"], "true")
        self.assertEqual(environment["HOST_NAME"], "Bos taurus")
        self.assertEqual(environment["HOST_INDEX_PREFIX"], "ref/host/bos_taurus_bt2")

    def test_dashboard_contract_has_no_silent_host_or_scientific_authority_label(self):
        html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "dashboard/app.js").read_text(encoding="utf-8")
        self.assertIn('id="evidence-target" name="target" class="field__input" required', html)
        self.assertIn('id="evidence-batch-target" class="field__input" required', html)
        self.assertLess(
            html.index('<option value="none">Sem filtro de hospedeiro</option>'),
            html.index('<option value="sus_scrofa">Sus scrofa (opt-in)</option>'),
        )
        self.assertNotIn("Configuração padrão", javascript)
        self.assertNotIn("Validação Científica", html)
        self.assertNotIn("Validação Científica", javascript)
        self.assertIn("Conclusão reportada pelo artefato canônico", javascript)

        self.assertIn("Tipo de falha: ${state.failure_type}.", javascript)
        self.assertIn("Etapa: ${state.failed_stage}.", javascript)

    def test_evidence_history_uses_canonical_state_once_and_sorts_by_timestamp(self):
        class InspectionService:
            @staticmethod
            def inspect_run(_run_id):
                return {
                    "status": "INCOMPLETE", "valid_alpha2": False,
                    "complete": False, "message": "incompleto",
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs_dir = root / "results/runs"
            legacy = runs_dir / "legacy"
            evidence_snapshot = runs_dir / "evidence-snapshot"
            legacy.mkdir(parents=True)
            evidence_snapshot.mkdir()
            (legacy / "run.json").write_text(json.dumps({
                "action": "pipeline", "sample": "legacy",
                "end_epoch": 10, "start": "2026-01-01T00:00:00+00:00",
            }), encoding="utf-8")
            (evidence_snapshot / "run.json").write_text(json.dumps({
                "action": "evidence_pipeline", "sample": "sample-a",
                "end_epoch": 20,
            }), encoding="utf-8")
            state_dir = root / "results/evidence/state"
            state_dir.mkdir(parents=True)
            (state_dir / "run-v2.json").write_text(json.dumps({
                "run_id": "run-v2", "action": "evidence_single",
                "sample_ids": ["sample-a"], "status": "failed",
                "evidence_v2_status": "failed", "official_v1_status": "done",
                "created_at": "2026-01-02T00:00:00+00:00",
                "finished_at": "2026-01-02T01:00:00+00:00",
                "failure_message": "falha sintética",
            }), encoding="utf-8")
            with (
                patch.object(dashboard, "REPO_ROOT", root),
                patch.object(dashboard, "RUNS_DIR", runs_dir),
                patch.object(dashboard, "EVIDENCE_SERVICE", InspectionService()),
            ):
                history = dashboard.list_run_history()
            self.assertEqual(len(history), 2)
            self.assertTrue(history[0]["evidence_v2"])
            self.assertEqual(history[0]["run_id"], "run-v2")
            self.assertEqual(history[1]["sample"], "legacy")


if __name__ == "__main__":
    unittest.main()
