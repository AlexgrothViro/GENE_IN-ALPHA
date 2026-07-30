"""
Gene-In Dashboard Jobs & Execution Management Module
Gerenciador de jobs em segundo plano, monitoramento de processos, cancelamento e histórico.
"""

import json
import logging
import os
import secrets
import shlex
import shutil
import signal
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, run

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "evidence"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from input_validation import validate_fastq, validate_fasta, validate_run_id, validate_sample_id
from evidence_dashboard import EvidenceDashboardService, atomic_json
from run_state import mutate_state_file, reserve_state as reserve_evidence_state
from analysis_profiles import load_profiles, resolve_profile
from dashboard.config import (
    LOG_DIR, RUNS_DIR, REPO_ROOT, iso_now, _DB_ALIAS, host_env_from_params,
    load_config_env, validate_config_updates, save_config_env,
    get_repo_root, get_runs_dir,
)

EVIDENCE_SERVICE = EvidenceDashboardService(REPO_ROOT)

def get_evidence_service():
    if "ux_dashboard" in sys.modules and hasattr(sys.modules["ux_dashboard"], "EVIDENCE_SERVICE"):
        return sys.modules["ux_dashboard"].EVIDENCE_SERVICE
    return EVIDENCE_SERVICE

jobs = {}
jobs_lock = threading.Lock()

MAX_OUTPUT_LINES = 4000
JOB_TTL_SECONDS = 24 * 60 * 60
MAX_JOBS_IN_MEMORY = 100
MAX_RUNNING_JOBS = 4


def initialize_evidence_dashboard_state(action, params):
    run_id = validate_run_id(params["run_id"])
    service = get_evidence_service()
    if action == "evidence_pipeline":
        samples = [params["sample"]]
        batch_id = None
        state_action = "evidence_single"
    else:
        manifest = service.manifest(params["manifest_id"])
        samples = [row["sample_id"] for row in manifest["rows"]]
        batch_id = manifest["metadata"].get("batch_id")
        state_action = "evidence_batch"
    state_path = service.evidence_root / "state" / f"{run_id}.json"
    reservation_token = secrets.token_urlsafe(32)
    reserve_evidence_state(
        state_path, run_id, state_action, samples, batch_id, reservation_token,
    )
    params["reservation_token"] = reservation_token


def force_evidence_state_terminal(run_id, status, message, failure_type=None, failed_command=None):
    """Close a dashboard-owned V2 state when failure happens before the V2 runner can do it."""
    if not run_id:
        return
    service = get_evidence_service()
    state_path = service.evidence_root / "state" / f"{run_id}.json"
    if not state_path.is_file():
        return
    job_metadata = jobs.get(run_id, {})
    failure_type = failure_type or job_metadata.get("failure_type") or ("CANCELLED" if status == "cancelled" else "TOOL_FAILURE")
    failed_command = failed_command or job_metadata.get("command")

    def terminalize(state):
        if state.get("status") in {"done", "done_with_warning", "blocked", "failed", "cancelled"}:
            return
        stage_status = "cancelled" if status == "cancelled" else "failed"
        stage = next((item for item in state.get("stages", []) if item.get("status") == "running"), None)
        stage = stage or next((item for item in state.get("stages", []) if item.get("status") == "pending"), None)
        timestamp = datetime.now().astimezone().isoformat()
        previous_stage = state.get("current_stage")
        if stage:
            stage.update({
                "status": stage_status,
                "started_at": stage.get("started_at") or timestamp,
                "finished_at": timestamp,
                "message": message,
            })
        if state.get("official_v1_status") == "running" and state.get("evidence_v2_status") in {"queued", "not_started"}:
            state["official_v1_status"] = "cancelled" if status == "cancelled" else "failed"
        state.update({
            "status": status,
            "evidence_v2_status": status,
            "execution_status": status,
            "analysis_outcome": "NOT_EVALUABLE",
            "evidence_level": "NOT_EVALUABLE",
            "current_stage": None,
            "finished_at": timestamp,
            "failed_stage": stage.get("id") if stage else previous_stage,
            "failure_type": failure_type,
            "failure_message": message,
            "failed_command": failed_command,
        })

    mutate_state_file(state_path, terminalize)


def terminate_process_group(process, signal_value) -> tuple[bool, str | None]:
    """Signal the complete job group and report failure instead of swallowing it."""
    try:
        if os.name != "nt":
            os.killpg(os.getpgid(process.pid), signal_value)
        elif getattr(signal, "SIGKILL", None) is not None and signal_value == signal.SIGKILL:
            process.kill()
        else:
            process.send_signal(signal_value)
    except (OSError, ProcessLookupError, ValueError) as exc:
        return False, f"could not signal process group: {exc}"
    return True, None


def mark_cancellation_failure(job_id, action, message) -> None:
    """Make an unverified cancellation a terminal failure, never a success."""
    with jobs_lock:
        jobs[job_id].update({"status": "failed", "failure_type": "CANCELLATION_FAILED"})
    if action in {"evidence_pipeline", "evidence_batch"}:
        force_evidence_state_terminal(job_id, "failed", message, "CANCELLATION_FAILED")


def classify_evidence_failure(output):
    """Map early process failures to stable machine-readable categories."""
    text = "\n".join(output or []).lower()
    if "modulenotfounderror" in text and ("yaml" in text or "pyyaml" in text):
        return "DEPENDENCY_MISSING"
    if "pyyaml" in text and ("ausente" in text or "indispon" in text or "missing" in text):
        return "DEPENDENCY_MISSING"
    if "config" in text and any(token in text for token in ("invalid", "inval", "schema", "yaml")):
        return "CONFIG_INVALID"
    if any(token in text for token in ("fastq", "fasta", "entrada", "arquivo inexistente", "not found")):
        return "INPUT_INVALID"
    if any(token in text for token in ("artefato", "success.json", "quickcheck", "artifact")):
        return "ARTIFACT_INVALID"
    return "TOOL_FAILURE"


def evidence_status_summary(run_id):
    if not run_id:
        return {}
    service = get_evidence_service()
    state_path = service.evidence_root / "state" / f"{run_id}.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, json.JSONDecodeError):
        return {}
    v2_status = state.get("evidence_v2_status", state.get("status", "not_started"))
    official_status = state.get("official_v1_status", "not_started")
    warning = None
    if official_status == "done" and v2_status not in {"done", "done_with_warning"}:
        warning = "A versão oficial 1.1 foi concluída, mas a Evidence V2 experimental não foi concluída; resultado V2 NOT_EVALUABLE."
    return {
        "official_v1_status": official_status,
        "evidence_v2_status": v2_status,
        "experimental_warning": warning,
        "experimental_analysis_outcome": state.get("analysis_outcome") or ("NOT_EVALUABLE" if warning else None),
    }


def cleanup_old_jobs():
    """Remove expired jobs from in-memory tracking dictionary."""
    with jobs_lock:
        now = time.time()
        to_remove = []
        for job_id, info in jobs.items():
            if info["status"] in {"done", "failed", "cancelled"}:
                finished_at = info.get("finished_at")
                if finished_at:
                    try:
                        dt = datetime.fromisoformat(finished_at)
                        if (now - dt.timestamp()) > JOB_TTL_SECONDS:
                            to_remove.append(job_id)
                    except ValueError:
                        pass
        for job_id in to_remove:
            del jobs[job_id]

        if len(jobs) > MAX_JOBS_IN_MEMORY:
            finished = [
                (jid, j) for jid, j in jobs.items()
                if j["status"] in {"done", "failed", "cancelled"}
            ]
            finished.sort(key=lambda x: x[1].get("finished_at", ""))
            excess = len(jobs) - MAX_JOBS_IN_MEMORY
            for jid, _ in finished[:excess]:
                del jobs[jid]


def read_tail(path, lines=30):
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            return [line.rstrip("\r\n") for line in all_lines[-lines:]]
    except Exception:
        return []


def clamp_output(lines):
    if len(lines) <= MAX_OUTPUT_LINES:
        return lines
    half = MAX_OUTPUT_LINES // 2
    truncated_count = len(lines) - MAX_OUTPUT_LINES
    marker = f"[... {truncated_count} linhas omissoas pelo dashboard ...]"
    return lines[:half] + [marker] + lines[-half:]


def find_blast_path(sample):
    repo_root = get_repo_root()
    candidate = repo_root / "results" / "blast" / f"{sample}_labeled_hits.tsv"
    if candidate.exists():
        return candidate
    candidate_unlabeled = repo_root / "results" / "blast" / f"{sample}_hits.tsv"
    if candidate_unlabeled.exists():
        return candidate_unlabeled
    return None


def find_hit_contigs_fasta_path(sample):
    repo_root = get_repo_root()
    candidate = repo_root / "results" / "blast" / f"{sample}_hit_contigs.fasta"
    if candidate.exists():
        return candidate
    return None


def find_report_path(sample):
    repo_root = get_repo_root()
    candidate = repo_root / "results" / "reports" / f"{sample}_report.md"
    if candidate.exists():
        return candidate
    return None


def find_advanced_report_path(sample):
    repo_root = get_repo_root()
    candidate = repo_root / "results" / "reports" / f"{sample}_advanced_report.md"
    if candidate.exists():
        return candidate
    return None


def find_assembly_summary_path(sample):
    repo_root = get_repo_root()
    candidate = repo_root / "results" / "assembly" / sample / "assembly_summary.json"
    if candidate.exists():
        return candidate
    return None


def snapshot_run_artifacts(metadata):
    sample = metadata.get("sample")
    run_id = metadata.get("run_id") or metadata.get("id")
    if not run_id:
        return None

    run_dir = get_runs_dir() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meta_file = run_dir / "metadata.json"
    atomic_json(meta_file, metadata)

    copied = []
    if sample:
        targets = [
            (find_blast_path(sample), "labeled_hits.tsv"),
            (find_hit_contigs_fasta_path(sample), "hit_contigs.fasta"),
            (find_report_path(sample), "report.md"),
            (find_advanced_report_path(sample), "advanced_report.md"),
            (find_assembly_summary_path(sample), "assembly_summary.json"),
        ]
        for src, dest_name in targets:
            if src and src.exists():
                dest = run_dir / dest_name
                try:
                    shutil.copy2(src, dest)
                    copied.append(dest_name)
                except OSError as exc:
                    print(f"[WARN] Falha ao copiar artefato {src} -> {dest}: {exc}")

    manifest_file = run_dir / "manifest.json"
    manifest_data = {
        "run_id": run_id,
        "sample": sample,
        "created_at": iso_now(),
        "artifacts": copied,
    }
    atomic_json(manifest_file, manifest_data)
    return str(run_dir)


def parse_pipeline_details(params):
    raw = (params.get("pipeline_details") or "").strip()
    if not raw:
        return {}

    parsed = {}
    try:
        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            return {
                str(k).strip(): str(v).strip()
                for k, v in decoded.items()
                if str(k).strip() and str(v).strip()
            }
    except json.JSONDecodeError:
        pass

    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        if "=" in token:
            k, v = token.split("=", 1)
        elif ":" in token:
            k, v = token.split(":", 1)
        else:
            continue
        k = k.strip()
        v = v.strip()
        if k and v:
            parsed[k] = v

    return parsed


def build_command(action, params):
    cmd = []
    env = {}

    db = (params.get("db") or params.get("target") or "").strip().lower()
    if action in {"pipeline", "evidence_pipeline", "evidence_batch"}:
        if not db:
            raise ValueError("A seleção do banco de referência é obrigatória e deve ser feita explicitamente.")
        alias_db = _DB_ALIAS.get(db, db)
        env["DB"] = alias_db

        host_mode = params.get("host_filter_mode", "none")
        if host_mode != "none":
            env["HOST_FILTER_ENABLED"] = "true"
            if "host_name" in params:
                env["HOST_NAME"] = params["host_name"]
            if "host_index_prefix" in params:
                env["HOST_INDEX_PREFIX"] = params["host_index_prefix"]
        else:
            env["HOST_FILTER_ENABLED"] = "false"

    if action == "sample_add":
        sample = validate_sample_id(params["sample"])
        r1 = validate_fastq(params["r1"])
        r2 = validate_fastq(params.get("r2", "")) if params.get("r2") else ""
        cmd = ["make", "sample-add", f"ID={sample}", f"R1={r1}"]
        if r2:
            cmd.append(f"R2={r2}")

    elif action == "pipeline":
        sample = validate_sample_id(params["sample"])
        assembler = (params.get("assembler") or "spades").strip().lower()
        if assembler not in {"velvet", "spades", "metaspades"}:
            raise ValueError("assembler invalido")
        alias_db = _DB_ALIAS.get(db, db)
        cmd = ["scripts/20_run_pipeline.sh", f"SAMPLE={sample}", f"ASSEMBLER={assembler}", f"DB={alias_db}"]

    elif action == "report":
        sample = validate_sample_id(params["sample"])
        cmd = ["make", "report", f"SAMPLE={sample}"]

    elif action == "evidence_pipeline":
        sample = validate_sample_id(params["sample"])
        run_id = validate_run_id(params.get("run_id") or "dashboard-run-00000000")
        assembler = (params.get("assembler") or "spades").strip().lower()
        if assembler not in {"velvet", "spades", "metaspades"}:
            raise ValueError("assembler invalido")
        alias_db = _DB_ALIAS.get(db, db)
        profile = (params.get("profile") or "default").strip()
        token = params.get("reservation_token", "")
        cmd = [
            "scripts/20_run_pipeline.sh",
            f"--sample={sample}",
            f"--run-id={run_id}",
            f"--assembler={assembler}",
            f"--db={alias_db}",
            f"--profile={profile}",
        ]
        if token:
            cmd.append(f"--reservation-token={token}")
            env["EVIDENCE_RESERVATION_TOKEN"] = token

    elif action == "evidence_batch":
        manifest_id = validate_sample_id(params["manifest_id"])
        run_id = validate_run_id(params.get("run_id") or "dashboard-run-00000000")
        token = params.get("reservation_token", "")
        cmd = [
            "scripts/23_run_batch.sh",
            f"--manifest={manifest_id}",
            f"--run-id={run_id}",
        ]
        if token:
            cmd.append(f"--reservation-token={token}")
            env["EVIDENCE_RESERVATION_TOKEN"] = token

    elif action == "db_build":
        db_name = (params.get("db") or "").strip().lower()
        alias_db = _DB_ALIAS.get(db_name, db_name)

        target_file = get_repo_root() / "config" / "targets.json"
        known_targets = set()
        if target_file.exists():
            try:
                targets_data = json.loads(target_file.read_text(encoding="utf-8"))
                known_targets = {t["id"] for t in targets_data if "id" in t}
            except Exception:
                pass

        if alias_db not in known_targets and alias_db not in {"ptv", "evg", "psv", "astrovirus_suino", "picornaviridae_refseq", "picornaviridae_complete", "picornaviridae_all"}:
            raise ValueError(f"Banco nao reconhecido em targets.json: '{db_name}'.")

        cmd = ["make", "db", f"DB={alias_db}"]

    else:
        raise ValueError(f"Acao desconhecida: {action}")

    return cmd, env


def run_job(job_id, action, params):
    output_buf = []

    with jobs_lock:
        job_info = jobs[job_id]
        if job_info.get("status") in {"cancelling", "cancelled"}:
            job_info.update({
                "status": "cancelled",
                "finished_at": iso_now(),
                "failure_type": "CANCELLED",
            })
            return
        job_info["status"] = "running"
        job_info["started_at"] = iso_now()

    env = dict(os.environ)

    try:
        env.update(host_env_from_params(params))
    except ValueError as exc:
        with jobs_lock:
            jobs[job_id].update({
                "status": "failed",
                "output": [f"[ERRO] Parametros de hospedeiro invalidos: {exc}"],
                "finished_at": iso_now(),
                "failure_type": "INPUT_INVALID",
                "failure_message": str(exc),
            })
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "failed", str(exc), "INPUT_INVALID")
        return

    if action in {"pipeline", "evidence_pipeline", "evidence_batch"}:
        p_details = parse_pipeline_details(params)
        for k, v in p_details.items():
            env[k] = str(v)

    try:
        cmd, extra_env = build_command(action, params)
        env.update(extra_env)
    except (ValueError, KeyError) as e:
        with jobs_lock:
            jobs[job_id].update({
                "status": "failed",
                "output": [f"[ERRO] Parametros invalidos: {e}"],
                "finished_at": iso_now(),
                "failure_type": "INPUT_INVALID",
                "failure_message": str(e),
            })
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "failed", str(e), "INPUT_INVALID")
        return

    log_file = LOG_DIR / f"ux_{job_id}.log"
    with jobs_lock:
        jobs[job_id]["command"] = " ".join(cmd)
        jobs[job_id]["log_file"] = str(log_file)

    try:
        popener = Popen(
            cmd,
            cwd=get_repo_root(),
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            bufsize=1,
            env=env,
            start_new_session=(os.name != "nt"),
        )
    except Exception as exc:
        msg = f"[ERRO] Falha ao iniciar processo: {exc}"
        with jobs_lock:
            jobs[job_id].update({
                "status": "failed",
                "output": [msg],
                "finished_at": iso_now(),
                "failure_type": "TOOL_FAILURE",
                "failure_message": str(exc),
            })
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "failed", str(exc), "TOOL_FAILURE", " ".join(cmd))
        return

    with jobs_lock:
        jobs[job_id]["process"] = popener

    try:
        with open(log_file, "w", encoding="utf-8") as lf:
            for line in popener.stdout:
                line_clean = line.rstrip("\r\n")
                lf.write(line)
                lf.flush()
                output_buf.append(line_clean)

                with jobs_lock:
                    jobs[job_id]["output"] = clamp_output(list(output_buf))
                    if jobs[job_id].get("cancel_requested"):
                        signaled, err_msg = terminate_process_group(popener, getattr(signal, "SIGTERM", signal.SIGINT))
                        if not signaled:
                            jobs[job_id]["output"].append(f"[WARN] {err_msg}")
                            terminate_process_group(popener, getattr(signal, "SIGKILL", signal.SIGINT))

        popener.wait()
        rc = popener.returncode

        with jobs_lock:
            jobs[job_id]["process"] = None
            jobs[job_id]["finished_at"] = iso_now()
            jobs[job_id]["exit_code"] = rc

            if jobs[job_id].get("cancel_requested"):
                if rc == 0:
                    jobs[job_id].update({"status": "failed", "failure_type": "CANCELLATION_FAILED"})
                    if action in {"evidence_pipeline", "evidence_batch"}:
                        force_evidence_state_terminal(
                            job_id, "failed",
                            "O processo concluiu normalmente apesar do pedido de cancelamento",
                            "CANCELLATION_FAILED", " ".join(cmd),
                        )
                else:
                    jobs[job_id].update({"status": "cancelled", "failure_type": "CANCELLED"})
                    if action in {"evidence_pipeline", "evidence_batch"}:
                        force_evidence_state_terminal(
                            job_id, "cancelled", "Execucao cancelada pelo usuario",
                            "CANCELLED", " ".join(cmd),
                        )
            elif rc == 0:
                jobs[job_id]["status"] = "done"
                if action in {"pipeline", "evidence_pipeline"}:
                    sample = params.get("sample", "")
                    snapshot_run_artifacts({
                        "id": job_id,
                        "run_id": job_id,
                        "sample": sample,
                        "action": action,
                        "params": params,
                        "finished_at": jobs[job_id]["finished_at"],
                        "command": " ".join(cmd),
                        "status": "done",
                    })
            else:
                failure_type = classify_evidence_failure(output_buf)
                jobs[job_id].update({
                    "status": "failed",
                    "failure_type": failure_type,
                    "failure_message": f"Processo encerrou com codigo de erro {rc}",
                })
                if action in {"evidence_pipeline", "evidence_batch"}:
                    force_evidence_state_terminal(
                        job_id, "failed",
                        f"Processo encerrou com codigo de erro {rc}",
                        failure_type, " ".join(cmd),
                    )

    except Exception as exc:
        logging.exception(f"Exceção não tratada na execução do job {job_id}")
        with jobs_lock:
            jobs[job_id]["process"] = None
            jobs[job_id].update({
                "status": "failed",
                "output": clamp_output(list(output_buf) + [f"[ERRO EXCECAO] {exc}"]),
                "finished_at": iso_now(),
                "failure_type": "TOOL_FAILURE",
                "failure_message": str(exc),
            })
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "failed", str(exc), "TOOL_FAILURE", " ".join(cmd))


def _history_epoch(value):
    """Convert an ISO timestamp to a sortable epoch without failing history."""
    if not value:
        return 0
    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except (TypeError, ValueError, OverflowError):
        return 0


def list_run_history():
    runs = []
    seen_ids = set()
    # History is called through the compatibility facade, which temporarily
    # redirects this module's service/root for isolated callers and tests.
    service = EVIDENCE_SERVICE
    repo_root = get_repo_root()
    runs_dir = get_runs_dir()
    evidence_root = getattr(service, "evidence_root", None) or (repo_root / "results" / "evidence")
    state_dir = evidence_root / "state"
    if state_dir.exists():
        for state_file in state_dir.glob("*.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            run_id = state.get("run_id")
            if not run_id:
                continue
            seen_ids.add(run_id)
            status = state.get("status", "failed")
            try:
                inspection = service.inspect_run(str(run_id))
            except (AttributeError, FileNotFoundError, ValueError):
                inspection = {
                    "status": "INCOMPLETE", "valid_alpha2": False, "complete": False,
                    "message": "Execução Evidence V2 incompleta.",
                }
            evidence_v2_status = state.get("evidence_v2_status", status)
            finished_at = state.get("finished_at")
            if inspection["valid_alpha2"]:
                display_status = evidence_v2_status
            elif inspection["status"] == "INCOMPLETE":
                display_status = evidence_v2_status
            else:
                display_status = inspection["status"].lower()
            official_v1_status = state.get("official_v1_status", "not_started")
            experimental_warning = None
            if official_v1_status == "done" and evidence_v2_status not in {"done", "done_with_warning"}:
                experimental_warning = "A versão oficial 1.1 concluiu, mas a Evidence V2 experimental ficou NOT_EVALUABLE."
            runs.append({
                "id": run_id, "run_id": run_id,
                "action": state.get("action"), "sample": ", ".join(state.get("sample_ids") or []),
                "batch_id": state.get("batch_id"), "start": state.get("started_at") or state.get("created_at"),
                "end": finished_at, "end_epoch": _history_epoch(finished_at),
                "exit_code": 0 if inspection["valid_alpha2"] and status in {"done", "done_with_warning"} else 1,
                "status": display_status, "shadow_mode": True, "evidence_v2": True,
                "valid_alpha2": inspection["valid_alpha2"],
                "compatibility_status": inspection["status"],
                "compatibility_message": inspection["message"],
                "job_status": "done" if official_v1_status == "done" else official_v1_status,
                "official_v1_status": official_v1_status,
                "evidence_v2_status": evidence_v2_status,
                "experimental_warning": experimental_warning,
                "failure_type": state.get("failure_type"),
                "failed_stage": state.get("failed_stage"),
                "failure_message": state.get("failure_message"),
                "complete": inspection["complete"],
            })

    if runs_dir.exists():
        for item in runs_dir.iterdir():
            if not item.is_dir() or item.name in seen_ids or item.name.startswith("evidence"):
                continue
            run_json = item / "run.json"
            meta_file = item / "metadata.json"
            if run_json.exists():
                try:
                    data = json.loads(run_json.read_text(encoding="utf-8"))
                    if data.get("action", "").startswith("evidence"):
                        continue
                    runs.append({
                        "id": item.name, "run_id": item.name,
                        "action": data.get("action"), "sample": data.get("sample"),
                        "start": data.get("start"), "end": data.get("end"),
                        "end_epoch": data.get("end_epoch", 0),
                        "status": "done",
                    })
                except Exception:
                    pass
            elif meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    if meta.get("action", "").startswith("evidence"):
                        continue
                    runs.append({
                        "id": item.name, "run_id": item.name,
                        "action": meta.get("action"), "sample": meta.get("sample"),
                        "start": meta.get("created_at"), "end": meta.get("finished_at"),
                        "end_epoch": 0,
                        "status": meta.get("status", "done"),
                    })
                except Exception:
                    pass

    runs.sort(key=lambda item: item.get("end_epoch", 0), reverse=True)
    return runs


def resolve_history_file(run_dir, file_type):
    targets = {
        "report": "report.md",
        "advanced_report": "advanced_report.md",
        "blast_tsv": "labeled_hits.tsv",
        "hit_contigs": "hit_contigs.fasta",
        "assembly_summary": "assembly_summary.json",
        "sample_evidence": "sample_evidence.json",
    }
    filename = targets.get(file_type)
    if not filename:
        return None
    candidate = run_dir / filename
    return candidate if candidate.is_file() else None
