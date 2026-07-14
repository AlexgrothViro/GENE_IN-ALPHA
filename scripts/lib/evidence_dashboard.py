from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from input_validation import validate_fastq, validate_sample_id
from common import validate_evidence_config


ROLES = {"sample", "negative_extraction", "negative_library", "negative_sequencing", "positive"}
LIBRARY_MODES = {"shotgun", "amplicon", "targeted", "unknown"}
UMI_MODES = {"none", "read_name", "tag"}
MANIFEST_FIELDS = ["batch_id", "sample_id", "role", "library_mode", "umi_mode", "r1", "r2", "expected_target"]
ARTIFACTS = {
    "fragment_evidence": "fragment_evidence.tsv",
    "locus_evidence": "locus_evidence.tsv",
    "competitive_hits": "competitive_hits.tsv",
    "read_support": "read_support.tsv",
    "coverage": "coverage.tsv",
    "sample_evidence": "sample_evidence.json",
    "provenance": "provenance.json",
    "runtime_preflight": "runtime_preflight.json",
    "read_support_bam": "read_support.bam",
    "read_support_bai": "read_support.bam.bai",
    "report": "evidence_report.md",
    "state": "run_state.json",
    "success": "SUCCESS.json",
    "batch_evidence": "batch_evidence.json",
    "control_status": "control_status.tsv",
    "batch_report": "batch_report.md",
}
STATUS_EXPLANATIONS = {
    "UNCONTROLLED": "A análise não possui controles associados; a força interpretativa permanece limitada.",
    "CONTROL_NOT_DETECTED": "O sinal avaliado não foi observado nos controles associados.",
    "CONTROL_BELOW_SAMPLE": "O controle apresentou sinal inferior ao da amostra segundo a regra provisória.",
    "CONTROL_ASSOCIATED_SIGNAL": "Também existe sinal relacionado no controle; requer revisão e não confirma contaminação.",
    "CONTROL_EQUAL_OR_HIGHER": "O controle apresentou suporte igual ou superior ao da amostra.",
    "CONTROL_NOT_APPLICABLE": "Esta linha representa um controle; a comparação amostra/controle não se aplica a ela.",
    "TARGET_CONTROL_FAILURE": "O controle positivo do alvo não atingiu o mínimo operacional; a interpretação desse alvo está bloqueada.",
    "BATCH_GLOBAL_FAILURE": "Múltiplos controles positivos falharam; o lote está bloqueado globalmente.",
    "TARGET_SPECIFIC": "O melhor alinhamento alvo superou os competidores segundo os parâmetros provisórios.",
    "AMBIGUOUS": "O alvo não foi separado de forma suficiente dos competidores.",
    "NON_TARGET_BEST": "Um competidor não alvo apresentou o melhor alinhamento.",
    "NOT_EVALUATED": "A especificidade competitiva não pôde ser avaliada.",
    "EXPLORATORY_FRAGMENT": "Fragmento curto retido somente para revisão exploratória.",
    "LOCUS_CANDIDATE": "Existe um locus candidato com suporte computacional rastreável.",
    "MULTI_LOCUS_CANDIDATE": "Existem loci candidatos independentes segundo regras provisórias.",
    "GENOME_SUPPORTED": "A cobertura atende aos critérios operacionais provisórios; não representa confirmação diagnóstica.",
    "INCONCLUSIVE": "As evidências disponíveis não permitem promoção operacional.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_json(path: Path, value: object) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class EvidenceDashboardService:
    def __init__(self, repo_root: Path):
        self.root = repo_root.resolve()
        self.config_path = self.root / "config" / "evidence_v2.yaml"
        self.config_example = self.root / "config" / "evidence_v2.yaml.example"
        self.manifest_dir = self.root / "data" / "manifests"
        self.evidence_root = self.root / "results" / "evidence"

    def _safe_id(self, value: str, label: str = "id") -> str:
        value = (value or "").strip()
        if not value or len(value) > 128 or not all(ch.isalnum() or ch in "._-" for ch in value):
            raise ValueError(f"{label} inválido")
        return value

    def _inside_root_file(self, value: str) -> Path:
        path = Path(value)
        path = path if path.is_absolute() else self.root / path
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("arquivos do manifesto devem estar dentro do projeto") from exc
        if not resolved.is_file():
            raise ValueError(f"arquivo inexistente: {resolved}")
        return resolved

    def config(self) -> dict:
        path = self.config_path if self.config_path.is_file() else self.config_example
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML não está disponível no ambiente do dashboard") from exc
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = yaml.safe_load(handle)
            value = validate_evidence_config(value)
        except Exception as exc:
            raise ValueError(f"configuração Evidence V2 inválida: {exc}") from exc
        return {
            "config": value,
            "schema_version": value["schema_version"],
            "pipeline_version": "2.0.0-alpha.1",
            "shadow_mode": True,
            "calibration_status": "EM_CALIBRACAO",
            "source": str(path.relative_to(self.root)),
        }

    def dependencies(self) -> dict:
        try:
            from runtime_preflight import run
            report, errors = run(self.config_path, "spades", "none", False, [])
        except Exception as exc:
            report, errors = {"valid": False, "python": {"executable": "unknown"}}, [str(exc)]
        report["valid"] = not errors
        report["errors"] = errors
        return report

    def validate_config_text(self, content: str) -> dict:
        if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > 1024 * 1024:
            raise ValueError("conteúdo YAML ausente ou muito grande")
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML não está disponível no ambiente do dashboard") from exc
        try:
            value = yaml.safe_load(content)
            value = validate_evidence_config(value)
        except Exception as exc:
            raise ValueError(f"configuração Evidence V2 inválida: {exc}") from exc
        return {"valid": True, "config": value, "shadow_mode": True}

    def validate_manifest(self, rows: list[dict], validate_files: bool = True) -> dict:
        if not isinstance(rows, list) or not rows:
            raise ValueError("o lote precisa conter pelo menos uma amostra")
        normalized = []
        errors = []
        warnings = []
        ids = set()
        paths = set()
        has_sample = False
        has_control = False
        batch_ids = set()
        for index, raw in enumerate(rows, 1):
            row_errors = []
            row = {field: str((raw or {}).get(field, "")).strip() for field in MANIFEST_FIELDS}
            try:
                row["sample_id"] = validate_sample_id(row["sample_id"])
            except ValueError as exc:
                row_errors.append(str(exc))
            if not row["batch_id"]:
                row_errors.append("batch_id obrigatório")
            else:
                batch_ids.add(row["batch_id"])
            if row["role"] not in ROLES: row_errors.append("role inválido")
            if row["library_mode"] not in LIBRARY_MODES: row_errors.append("library_mode inválido")
            if row["umi_mode"] not in UMI_MODES: row_errors.append("umi_mode inválido")
            if row["umi_mode"] != "none" and row["library_mode"] == "unknown":
                row_errors.append("UMI exige library_mode conhecido")
            if row["role"] == "positive" and not row["expected_target"]:
                row_errors.append("controle positivo exige expected_target")
            has_sample = has_sample or row["role"] == "sample"
            has_control = has_control or row["role"] != "sample"
            if row["sample_id"] in ids: row_errors.append("sample_id duplicado")
            ids.add(row["sample_id"])
            try:
                r1 = self._inside_root_file(row["r1"])
                r2 = self._inside_root_file(row["r2"])
                for path in (r1, r2):
                    key = str(path).lower()
                    if key in paths: row_errors.append("arquivo reutilizado em outra amostra")
                    paths.add(key)
                row["r1"] = str(r1.relative_to(self.root))
                row["r2"] = str(r2.relative_to(self.root))
                if validate_files and not row_errors:
                    validate_fastq(r1, r2)
            except (OSError, ValueError) as exc:
                row_errors.append(str(exc))
            if row_errors:
                errors.append({"row": index, "sample_id": row["sample_id"], "errors": row_errors})
            normalized.append(row)
        if len(batch_ids) > 1:
            errors.append({"row": 0, "sample_id": "", "errors": ["um manifesto deve conter somente um batch_id"]})
        if not has_sample:
            errors.append({"row": 0, "sample_id": "", "errors": ["lote sem amostra analítica"]})
        if not has_control:
            warnings.append("Lote sem controles; resultados serão marcados como UNCONTROLLED.")
        return {"valid": not errors, "rows": normalized, "errors": errors, "warnings": warnings}

    def _manifest_tsv(self, rows: list[dict]) -> str:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, delimiter="\t", fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in MANIFEST_FIELDS} for row in rows)
        return output.getvalue()

    def save_manifest(self, rows: list[dict], manifest_id: str | None = None) -> dict:
        result = self.validate_manifest(rows, validate_files=True)
        if not result["valid"]:
            return result
        manifest_id = self._safe_id(manifest_id or uuid.uuid4().hex, "manifest_id")
        tsv_path = self.manifest_dir / f"{manifest_id}.tsv"
        json_path = self.manifest_dir / f"{manifest_id}.json"
        if tsv_path.exists() or json_path.exists():
            raise FileExistsError("manifest_id já existe")
        tsv = self._manifest_tsv(result["rows"])
        metadata = {
            "manifest_id": manifest_id,
            "schema_version": "2.0-alpha",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "sha256": hashlib.sha256(tsv.encode("utf-8")).hexdigest(),
            "row_count": len(result["rows"]),
            "batch_id": result["rows"][0]["batch_id"],
            "validation_status": "VALID",
            "warnings": result["warnings"],
        }
        atomic_text(tsv_path, tsv)
        try:
            atomic_json(json_path, metadata)
        except Exception:
            tsv_path.unlink(missing_ok=True)
            raise
        return {**result, "manifest_id": manifest_id, "metadata": metadata}

    def import_manifest(self, content: str) -> dict:
        if not isinstance(content, str) or len(content.encode("utf-8")) > 5 * 1024 * 1024:
            raise ValueError("manifesto ausente ou muito grande")
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        if reader.fieldnames != MANIFEST_FIELDS:
            raise ValueError("cabeçalho do manifesto incompatível")
        return self.save_manifest(list(reader))

    def list_manifests(self) -> list[dict]:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        result = []
        for path in sorted(self.manifest_dir.glob("*.json"), reverse=True):
            try:
                result.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return result

    def manifest(self, manifest_id: str) -> dict:
        manifest_id = self._safe_id(manifest_id, "manifest_id")
        tsv_path = self.manifest_dir / f"{manifest_id}.tsv"
        metadata_path = self.manifest_dir / f"{manifest_id}.json"
        if not tsv_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("manifesto não encontrado")
        with tsv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        return {"manifest_id": manifest_id, "rows": rows, "metadata": json.loads(metadata_path.read_text(encoding="utf-8"))}

    def manifest_export(self, manifest_id: str) -> Path:
        manifest_id = self._safe_id(manifest_id, "manifest_id")
        path = self.manifest_dir / f"{manifest_id}.tsv"
        if not path.is_file():
            raise FileNotFoundError("manifesto não encontrado")
        return path

    def state(self, run_id: str) -> dict:
        run_id = self._safe_id(run_id, "run_id")
        path = self.evidence_root / "state" / f"{run_id}.json"
        if not path.is_file():
            raise FileNotFoundError("execução Evidence V2 não encontrada")
        return json.loads(path.read_text(encoding="utf-8"))

    def result(self, run_id: str) -> dict:
        state = self.state(run_id)
        run_dir = self.evidence_root / "runs" / run_id
        success = run_dir / "SUCCESS.json"
        if not success.is_file():
            return {"state": state, "complete": False, "official_v1": None, "evidence_v2": None}
        if state.get("action") == "evidence_batch":
            evidence = json.loads((run_dir / "batch_evidence.json").read_text(encoding="utf-8"))
            return {
                "state": state, "complete": True, "official_v1": None,
                "evidence_v2": evidence, "explanations": STATUS_EXPLANATIONS,
                "artifacts": [name for name, filename in ARTIFACTS.items() if (run_dir / filename).is_file()],
            }
        evidence = json.loads((run_dir / "sample_evidence.json").read_text(encoding="utf-8"))
        sample = evidence.get("sample_id", "")
        official_path = self.root / "results" / "reports" / f"{sample}_summary.md"
        return {
            "state": state,
            "complete": True,
            "official_v1": official_path.read_text(encoding="utf-8", errors="replace") if official_path.is_file() else None,
            "evidence_v2": evidence,
            "explanations": STATUS_EXPLANATIONS,
            "artifacts": [name for name, filename in ARTIFACTS.items() if (run_dir / filename).is_file()],
        }

    def artifact(self, run_id: str, artifact_type: str) -> Path:
        run_id = self._safe_id(run_id, "run_id")
        if artifact_type not in ARTIFACTS:
            raise ValueError("tipo de artefato inválido")
        run_dir = self.evidence_root / "runs" / run_id
        if not (run_dir / "SUCCESS.json").is_file():
            raise FileNotFoundError("execução incompleta ou inválida")
        path = (run_dir / ARTIFACTS[artifact_type]).resolve()
        path.relative_to(run_dir.resolve())
        if not path.is_file():
            raise FileNotFoundError("artefato não encontrado")
        return path
