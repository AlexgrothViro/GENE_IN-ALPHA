#!/usr/bin/env python3
import argparse
import hashlib
import ipaddress
import json
import logging
import os
import re
import shlex
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
import zipfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, run
from urllib.parse import parse_qs, urlparse
from logging.handlers import RotatingFileHandler

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "evidence"))
from input_validation import validate_fastq, validate_fasta, validate_sample_id
from evidence_dashboard import EvidenceDashboardService, atomic_json
from run_state import initial_state as initial_evidence_state
DASHBOARD_DIR = REPO_ROOT / "dashboard"
LOG_DIR = REPO_ROOT / "logs"
RUNS_DIR = REPO_ROOT / "results" / "runs"
TARGETS_FILE = REPO_ROOT / "config" / "targets.json"
CONFIG_ENV_PRIMARY = REPO_ROOT / "config" / "picornavirus.env"
CONFIG_ENV_EXAMPLE = REPO_ROOT / "config" / "picornavirus.env.example"
CONFIG_ENV_LEGACY = REPO_ROOT / "config.env"
ENVIRONMENT_YML = REPO_ROOT / "environment.yml"
INSTALL_WSL_SCRIPT = REPO_ROOT / "bundle" / "install_wsl.sh"
EVIDENCE_SERVICE = EvidenceDashboardService(REPO_ROOT)


def initialize_evidence_dashboard_state(action, params):
    run_id = params["run_id"]
    if action == "evidence_pipeline":
        samples = [params["sample"]]
        batch_id = None
        state_action = "evidence_single"
    else:
        manifest = EVIDENCE_SERVICE.manifest(params["manifest_id"])
        samples = [row["sample_id"] for row in manifest["rows"]]
        batch_id = manifest["metadata"].get("batch_id")
        state_action = "evidence_batch"
    state_path = EVIDENCE_SERVICE.evidence_root / "state" / f"{run_id}.json"
    if state_path.exists():
        raise FileExistsError("run_id Evidence V2 já existe")
    atomic_json(state_path, initial_evidence_state(run_id, state_action, samples, batch_id))


def force_evidence_state_terminal(run_id, status, message, failure_type=None, failed_command=None):
    """Close a dashboard-owned V2 state when failure happens before the V2 runner can do it."""
    if not run_id:
        return
    state_path = EVIDENCE_SERVICE.evidence_root / "state" / f"{run_id}.json"
    if not state_path.is_file():
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") in {"done", "done_with_warning", "blocked", "failed", "cancelled"}:
        return
    stage_status = "cancelled" if status == "cancelled" else "failed"
    stage = next((item for item in state.get("stages", []) if item.get("status") == "running"), None)
    stage = stage or next((item for item in state.get("stages", []) if item.get("status") == "pending"), None)
    timestamp = datetime.now().astimezone().isoformat()
    if stage:
        stage.update({"status": stage_status, "started_at": stage.get("started_at") or timestamp, "finished_at": timestamp, "message": message})
    job_metadata = jobs.get(run_id, {})
    failure_type = failure_type or job_metadata.get("failure_type") or ("CANCELLED" if status == "cancelled" else "TOOL_FAILURE")
    failed_command = failed_command or job_metadata.get("command")
    if state.get("official_v1_status") == "running" and state.get("evidence_v2_status") in {"queued", "not_started"}:
        state["official_v1_status"] = "cancelled" if status == "cancelled" else "failed"
    state.update({
        "status": status,
        "evidence_v2_status": status,
        "current_stage": None,
        "finished_at": timestamp,
        "failed_stage": stage.get("id") if stage else state.get("current_stage"),
        "failure_type": failure_type,
        "failure_message": message,
        "failed_command": failed_command,
    })
    atomic_json(state_path, state)


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

MAX_OUTPUT_LINES = 4000
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024
JOB_TTL_SECONDS = 24 * 60 * 60
MAX_JOBS_IN_MEMORY = 100
MAX_RUNNING_JOBS = 4
TMP_UPLOAD_DIR = None  # initialized in main() after LOG_DIR is confirmed
CACHE_BYPASS_CONTENT_TYPES = {"text/html", "application/javascript", "text/css"}

# Pre-compiled regex for bash default-value syntax: : "${KEY:=value}"
_BASH_DEFAULT_RE = re.compile(r'^\s*:\s*"\$\{(\w+):=([^}]*)\}"\s*$')
_BASH_SELF_DEFAULT_RE = re.compile(r'^\$\{(\w+):-([^}]*)\}$')

# Mapping from targets.json long-form keys → short keys used by 13_db_manager.sh
_DB_ALIAS = {
    "teschovirus_a":          "ptv",
    "teschovirus":            "ptv",
    "enterovirus_g":          "evg",
    "sapelovirus_a":          "psv",
    "astrovirus_suino":       "astrovirus_suino",
    "picornaviridae_refseq":  "picornaviridae_refseq",
    "picornaviridae_complete": "picornaviridae_complete",
    "picornaviridae_all":     "picornaviridae_all",
    # short keys pass through unchanged
    "ptv": "ptv",
    "evg": "evg",
    "psv": "psv",
    "svv": "svv",
    "fmdv": "fmdv",
}

# Supported configuration keys for env file
SUPPORTED_ENV_KEYS = [
    "ASSEMBLER", "VELVET_K", "THREADS", "DB", "BLAST_EVALUE",
    "BLAST_MAX_TARGET_SEQS", "SPADES_MEMORY", "SPADES_PARAMS",
    "MIN_CONTIG_LEN", "VELVET_OPTS", "READ_TRKG", "RAW_DIR",
    "BLAST_DB", "HOST_REMOVED_DIR", "HOST_INDEX_PREFIX",
    "HOST_FILTER_ENABLED", "HOST_NAME", "HOST_ACCESSION",
    "BIND_HOST", "PORT", "SAMPLE_NAME", "SAMPLE_ID"
]

jobs = {}
jobs_lock = threading.Lock()
sample_locks = {}
sample_locks_guard = threading.Lock()
db_lock = threading.Lock()


def cleanup_old_jobs():
    """Remove finalizados antigos por TTL ou se o limite MAX_JOBS_IN_MEMORY for excedido."""
    now = time.time()
    ttl_limit = now - JOB_TTL_SECONDS

    with jobs_lock:
        # 1. Limpeza por TTL (24 horas)
        jobs_to_remove = []
        finalized_jobs = []  # lista de (job_id, finished_at ou created_at)

        for jid, job in jobs.items():
            status = job.get("status")
            if status in {"done", "error", "failed", "cancelled"}:
                t = job.get("finished_at") or job.get("created_at") or now
                if t < ttl_limit:
                    jobs_to_remove.append(jid)
                else:
                    finalized_jobs.append((jid, t))

        removed_count = 0
        for jid in jobs_to_remove:
            jobs.pop(jid, None)
            removed_count += 1

        # 2. Limpeza por capacidade máxima (MAX_JOBS_IN_MEMORY = 100)
        if len(jobs) > MAX_JOBS_IN_MEMORY:
            # Ordena do mais antigo para o mais novo
            finalized_jobs.sort(key=lambda x: x[1])
            excess = len(jobs) - MAX_JOBS_IN_MEMORY
            for i in range(min(excess, len(finalized_jobs))):
                jid = finalized_jobs[i][0]
                jobs.pop(jid, None)
                removed_count += 1

        if removed_count > 0:
            logger.info("[cleanup_jobs] Removidos %d jobs antigos finalizados da memória. Total em memória: %d", removed_count, len(jobs))


LOG_DIR.mkdir(parents=True, exist_ok=True)
_log_file = LOG_DIR / "dashboard_errors.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(_log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("dashboard")
logger.info("Dashboard iniciado. Log em: %s", _log_file)


def sanitize_token(text):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", (text or "unknown").strip())
    return value[:80] or "unknown"


def require_sample_id(value):
    try:
        return validate_sample_id(str(value or ""))
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def is_loopback_host(host):
    if host in {"localhost", "ip6-localhost"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def sanitize_for_log(value):
    """Reduce local path exposure in dashboard logs and API job summaries."""
    if value is None:
        return value
    text = str(value)
    if not text:
        return text
    try:
        path = Path(text)
        if path.is_absolute():
            try:
                return str(path.resolve().relative_to(REPO_ROOT.resolve()))
            except (OSError, ValueError):
                return path.name or "[path]"
    except (OSError, ValueError):
        pass
    return text


def params_for_log(params):
    safe = {}
    for key, value in (params or {}).items():
        if isinstance(value, str):
            safe[key] = sanitize_for_log(value)
        else:
            safe[key] = value
    return safe


def command_for_log(cmd):
    return " ".join(sanitize_for_log(part) for part in cmd)


def iso_now(epoch=None):
    dt = datetime.fromtimestamp(epoch or time.time())
    return dt.isoformat(timespec="seconds")


def read_tail(path, lines=30):
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return "(log não encontrado)"

    # Filtra linhas importantes nos últimos 100 linhas
    recent_lines = content[-100:]
    important = []
    for line in recent_lines:
        line_upper = line.upper()
        if any(tok in line_upper for tok in ["[FATAL]", "[AVISO]", "[RECUPERADO]", "[ERROR]", "[WARN]"]):
            important.append(line)

    # Últimas 10 linhas brutas para contexto final
    raw_context = content[-10:]

    # Mescla evitando duplicados
    seen = set()
    result = []
    for line in important:
        if line not in seen:
            result.append(line)
            seen.add(line)
    for line in raw_context:
        if line not in seen:
            result.append(line)
            seen.add(line)

    return "\n".join(result[-lines:])


def list_targets():
    if not TARGETS_FILE.exists():
        return []
    try:
        data = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []

def list_db_profiles():
    try:
        completed = run(
            ["bash", "-lc", "scripts/13_db_manager.sh list --json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return []
        data = json.loads(completed.stdout or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_config_env_path():
    """Return the path to the config env file to use (prefer picornavirus.env over config.env)"""
    if CONFIG_ENV_PRIMARY.exists():
        return CONFIG_ENV_PRIMARY
    elif CONFIG_ENV_LEGACY.exists():
        return CONFIG_ENV_LEGACY
    # If neither exists, we'll create the primary one
    return CONFIG_ENV_PRIMARY


def parse_env_file(filepath):
    """Parse a simple KEY=VALUE env file, ignoring comments and blank lines.

    Handles both standard ``KEY=value`` and bash default-value syntax
    ``': "${KEY:=value}"'``.
    """
    config = {}
    if not filepath.exists():
        return config

    try:
        content = filepath.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and blank lines
            if not line or line.startswith("#"):
                continue
            # Handle bash default syntax: : "${KEY:=value}"
            bash_match = _BASH_DEFAULT_RE.match(line)
            if bash_match:
                key = bash_match.group(1)
                value = bash_match.group(2).strip('"').strip("'")
                config[key] = value
                continue
            # Handle standard key=value format
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                try:
                    parsed_value = shlex.split(value, posix=True)
                    if len(parsed_value) == 1:
                        value = parsed_value[0]
                except ValueError:
                    # Preserve an invalid line for the caller to diagnose.
                    pass
                self_default = _BASH_SELF_DEFAULT_RE.match(value)
                if self_default and self_default.group(1) == key:
                    value = self_default.group(2)
                config[key] = value
    except Exception as e:
        print(f"[WARN] Error parsing env file {filepath}: {e}")

    return config


def load_config_env():
    """Load configuration from picornavirus.env (or config.env as fallback)"""
    env_path = get_config_env_path()
    config = parse_env_file(env_path)

    # Return only supported keys
    result = {}
    for key in SUPPORTED_ENV_KEYS:
        if key in config:
            result[key] = config[key]

    return result


def validate_config_updates(updates):
    if not isinstance(updates, dict):
        raise ValueError("config deve ser um objeto JSON")
    numeric_ranges = {
        "THREADS": (1, 256), "PORT": (1, 65535), "VELVET_K": (15, 127),
        "MIN_CONTIG_LEN": (1, 10_000_000), "BLAST_MAX_TARGET_SEQS": (1, 1000),
        "SPADES_MEMORY": (1, 4096),
    }
    for key, value in updates.items():
        if key not in SUPPORTED_ENV_KEYS:
            raise ValueError(f"Chave nao suportada: {key}")
        if isinstance(value, bool):
            value = str(value).lower()
        if not isinstance(value, (str, int, float)):
            raise ValueError(f"Valor invalido para {key}")
        text = str(value)
        if not text or len(text) > 4096 or "\x00" in text or "\n" in text or "\r" in text:
            raise ValueError(f"Valor invalido para {key}: vazio, grande ou com quebra de linha")
        if key == "ASSEMBLER" and text.lower() not in {"velvet", "spades", "metaspades"}:
            raise ValueError("ASSEMBLER deve ser velvet, spades ou metaspades")
        if key == "BIND_HOST" and not is_loopback_host(text):
            raise ValueError("BIND_HOST deve ser localhost ou um endereco loopback")
        if key in numeric_ranges:
            try:
                number = int(text)
            except ValueError as exc:
                raise ValueError(f"{key} deve ser numerico") from exc
            low, high = numeric_ranges[key]
            if not low <= number <= high:
                raise ValueError(f"{key} fora do intervalo permitido ({low}-{high})")
        if key in {"DB", "SAMPLE_NAME", "SAMPLE_ID"}:
            require_sample_id(text) if key != "DB" else None
            if key == "DB" and not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", text):
                raise ValueError("DB contem caracteres invalidos")
        if key in {"HOST_FILTER_ENABLED", "READ_TRKG"} and text.lower() not in {"true", "false", "0", "1", "yes", "no", "sim", "nao"}:
            raise ValueError(f"{key} deve ser booleano")
    return {key: str(value) for key, value in updates.items()}


def save_config_env(updates):
    """
    Update config/picornavirus.env with new values.
    - Backs up the file first
    - Preserves unknown keys
    - Updates known keys
    - Adds missing known keys at the end
    """
    updates = validate_config_updates(updates)
    env_path = CONFIG_ENV_PRIMARY

    # Create config directory if it doesn't exist
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing file if it exists
    if env_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = env_path.parent / f"{env_path.name}.bak-{timestamp}-{uuid.uuid4().hex[:8]}"
        shutil.copy2(env_path, backup_path)

    # Read existing content or start fresh
    existing_lines = []
    existing_keys = set()

    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            # Track keys we've seen — handle both bash default syntax and KEY=value
            if stripped and not stripped.startswith("#"):
                key = None
                bash_match = _BASH_DEFAULT_RE.match(stripped)
                if bash_match:
                    key = bash_match.group(1)
                elif "=" in stripped:
                    key = stripped.split("=")[0].strip()

                if key:
                    existing_keys.add(key)
                    # Update line if this key is being updated
                    if key in updates:
                        # Rewrite as simple KEY="value" format
                        line = f"{key}={shlex.quote(str(updates[key]))}"

            existing_lines.append(line)

    # Add new keys that weren't in the file
    for key in SUPPORTED_ENV_KEYS:
        if key in updates and key not in existing_keys:
            existing_lines.append(f"{key}={shlex.quote(str(updates[key]))}")

    # Write updated content
    content = "\n".join(existing_lines) + "\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=env_path.parent, prefix=f".{env_path.name}.", suffix=".tmp", delete=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, env_path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def validate_host_index(prefix):
    prefix = (prefix or "").strip()
    if not prefix:
        return {"valid": False, "message": "Informe o prefixo do indice Bowtie2."}
    try:
        completed = run(
            ["bash", "scripts/12_validate_host_index.sh", prefix],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except Exception as exc:
        logger.error("Erro ao validar indice Bowtie2 '%s': %s", sanitize_for_log(prefix), exc)
        return {"valid": False, "message": f"Falha ao validar indice: {exc}"}

    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    return {
        "valid": completed.returncode == 0,
        "message": output or ("Indice valido." if completed.returncode == 0 else "Indice invalido."),
    }


def host_env_from_params(params):
    mode = (params.get("host_filter_mode") or "sus_scrofa").strip().lower()
    default_prefix = str(REPO_ROOT / "ref" / "host" / "sus_scrofa_bt2")

    if mode in {"none", "disabled", "sem_filtro"}:
        return {"HOST_FILTER_ENABLED": "false"}

    if mode in {"sus_scrofa", "default", ""}:
        return {
            "HOST_FILTER_ENABLED": "true",
            "HOST_NAME": "Sus scrofa",
            "HOST_ACCESSION": "GCF_000003025.6",
            "HOST_INDEX_PREFIX": default_prefix,
        }

    if mode == "custom":
        host_name = (params.get("host_name") or "hospedeiro customizado").strip()
        host_index_prefix = (params.get("host_index_prefix") or "").strip()
        validation = validate_host_index(host_index_prefix)
        if not validation["valid"]:
            raise ValueError(f"Indice Bowtie2 customizado invalido: {validation['message']}")
        return {
            "HOST_FILTER_ENABLED": "true",
            "HOST_NAME": host_name,
            "HOST_INDEX_PREFIX": host_index_prefix,
        }

    raise ValueError(f"Modo de filtro de hospedeiro invalido: {mode}")


def get_environment_status():
    """Get status information about environment.yml"""
    status = {
        "has_environment_yml": ENVIRONMENT_YML.exists(),
        "environment_yml_path": str(ENVIRONMENT_YML.relative_to(REPO_ROOT)),
        "environment_yml_mtime": None,
    }

    if ENVIRONMENT_YML.exists():
        mtime = ENVIRONMENT_YML.stat().st_mtime
        status["environment_yml_mtime"] = iso_now(mtime)

    # Try to detect bundle paths if they exist
    bundle_dir = REPO_ROOT / ".bundle"
    if bundle_dir.exists():
        status["micromamba_root"] = str((bundle_dir / "mamba").relative_to(REPO_ROOT)) if (bundle_dir / "mamba").exists() else None
        status["env_dir"] = str((bundle_dir / "env").relative_to(REPO_ROOT)) if (bundle_dir / "env").exists() else None
    else:
        status["micromamba_root"] = None
        status["env_dir"] = None

    # Detect if running on Windows mount
    repo_path = str(REPO_ROOT)
    running_on_windows_mount = repo_path.startswith("/mnt/") and len(repo_path) > 5 and repo_path[5] == "/" and repo_path[4].isalpha()

    status["repo_root"] = repo_path
    status["running_on_windows_mount"] = running_on_windows_mount

    if running_on_windows_mount:
        status["recommendation"] = "O projeto está rodando em um disco do Windows (/mnt/c, etc.). Isso reduz consideravelmente a velocidade de I/O do WSL e pode causar erros de permissão ou cópia de arquivos. Para melhor performance e estabilidade, mova o projeto para dentro do sistema de arquivos nativo do WSL (ex: /home/usuario/Gene-In)."
    else:
        status["recommendation"] = "OK"

    return status


def validate_fastq_name(name):
    return name.endswith(".fastq") or name.endswith(".fastq.gz")


def normalize_sample_from_filename(filename):
    name = filename
    for suffix in ["_R1.fastq.gz", "_R2.fastq.gz", "_R1.fastq", "_R2.fastq"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return ""


def list_samples():
    raw_dir = REPO_ROOT / "data" / "raw"
    if not raw_dir.exists():
        return []
    sample_map = {}
    for item in raw_dir.iterdir():
        if not item.is_file() or not validate_fastq_name(item.name):
            continue
        sample = normalize_sample_from_filename(item.name)
        if not sample:
            continue
        side = "R1" if "_R1." in item.name else "R2"
        sample_map.setdefault(sample, set()).add(side)
    return sorted(sample for sample, sides in sample_map.items() if {"R1", "R2"}.issubset(sides))


def tool_versions():
    tools = {
        "python": ["python3", "--version"],
        "blastn": ["blastn", "-version"],
        "bowtie2": ["bowtie2", "--version"],
        "velveth": ["velveth", "--help"],
        "spades": ["spades.py", "--version"],
        "make": ["make", "--version"],
    }
    versions = {}
    for name, cmd in tools.items():
        try:
            completed = run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
            first = (completed.stdout or completed.stderr or "").splitlines()
            versions[name] = first[0].strip() if first else "available"
        except FileNotFoundError:
            versions[name] = "not found"
    return versions


def clamp_output(lines):
    if len(lines) <= MAX_OUTPUT_LINES:
        return lines
    return lines[-MAX_OUTPUT_LINES:]


def find_blast_path(sample):
    blast_dir = REPO_ROOT / "results" / "blast"
    if not sample or not blast_dir.exists():
        return None
    try:
        sample = require_sample_id(sample)
    except ValueError:
        return None
    preferred = sorted(blast_dir.glob(f"{sample}*_vs_db.tsv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return preferred[0] if preferred else None


def find_hit_contigs_fasta_path(sample):
    try:
        sample = require_sample_id(sample)
    except ValueError:
        return None
    fasta = REPO_ROOT / "results" / "blast" / f"{sample}_hit_contigs.fa"
    return fasta if sample and fasta.exists() else None


def find_report_path(sample):
    try:
        sample = require_sample_id(sample)
    except ValueError:
        return None
    report = REPO_ROOT / "results" / "reports" / f"{sample}_summary.md"
    return report if sample and report.exists() else None


def find_advanced_report_path(sample):
    try:
        sample = require_sample_id(sample)
    except ValueError:
        return None
    report = REPO_ROOT / "results" / "reports" / f"{sample}_advanced_validation.md"
    return report if sample and report.exists() else None


def find_assembly_summary_path(sample):
    try:
        sample = require_sample_id(sample)
    except ValueError:
        return None
    summary = REPO_ROOT / "results" / "assemblies" / sample / "assembly_only_summary.md"
    return summary if sample and summary.exists() else None


def snapshot_run_artifacts(metadata):
    action = metadata.get("action")
    if action not in {"pipeline", "advanced_analysis", "assembly_only"}:
        return metadata
    sample = metadata.get("sample")
    if not sample:
        return metadata

    ts = datetime.fromtimestamp(metadata.get("end_epoch", time.time())).strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"{ts}_{sanitize_token(action)}_{sanitize_token(sample)}_{metadata.get('id', uuid.uuid4().hex)}"

    try:
        run_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning("Falha ao criar diretório de histórico %s: %s", run_dir, e)
        return metadata

    paths = metadata.setdefault("paths", {})

    def safe_copy(src, dst, key):
        try:
            if src and src.exists():
                shutil.copy2(src, dst)
                paths[key] = str(dst.relative_to(REPO_ROOT))
        except Exception as e:
            logger.warning("Falha ao copiar artefato %s para o histórico: %s", src.name if src else 'None', e)

    log_path = Path(paths.get("log", "")) if paths.get("log") else None
    if log_path and not log_path.is_absolute():
        log_path = REPO_ROOT / log_path
    if log_path:
        safe_copy(log_path, run_dir / log_path.name, "run_log")

    if action == "pipeline":
        blast_path = find_blast_path(sample)
        if blast_path:
            safe_copy(blast_path, run_dir / blast_path.name, "run_blast")

        blast_dir = REPO_ROOT / "results" / "blast"
        if blast_dir.exists():
            labeled_path = blast_dir / f"{sample}_labeled_hits.tsv"
            if labeled_path.exists():
                safe_copy(labeled_path, run_dir / labeled_path.name, "run_labeled")

            adj_identity_path = blast_dir / f"{sample}_adj_identity.tsv"
            if adj_identity_path.exists():
                safe_copy(adj_identity_path, run_dir / adj_identity_path.name, "run_adj_identity")

            hit_contigs_fasta_path = find_hit_contigs_fasta_path(sample)
            if hit_contigs_fasta_path:
                safe_copy(hit_contigs_fasta_path, run_dir / hit_contigs_fasta_path.name, "run_hit_contigs_fasta")

        report_path = find_report_path(sample)
        if report_path:
            safe_copy(report_path, run_dir / report_path.name, "run_report")

    elif action == "advanced_analysis":
        report_path = find_advanced_report_path(sample)
        if report_path:
            safe_copy(report_path, run_dir / report_path.name, "run_report")

    elif action == "assembly_only":
        summary_path = find_assembly_summary_path(sample)
        if summary_path:
            safe_copy(summary_path, run_dir / summary_path.name, "run_report")

    metadata["run_dir"] = run_dir.name
    run_json = run_dir / "run.json"
    try:
        run_json.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        paths["run_json"] = str(run_json.relative_to(REPO_ROOT))
    except Exception as e:
        logger.warning("Falha ao escrever run.json em %s: %s", run_json, e)

    return metadata


def parse_pipeline_details(params):
    assembler = (params.get("assembler") or os.environ.get("ASSEMBLER") or "velvet").lower()
    kmer = str(params.get("kmer") or "31")
    sample = params.get("sample")
    threads = str(os.environ.get("THREADS", "4"))
    return sample, assembler, kmer, threads


def build_command(action, params):
    if action in {"import_sample", "pipeline", "advanced_analysis", "assembly_only", "evidence_pipeline"}:
        params = dict(params or {})
        params["sample"] = require_sample_id(params.get("sample"))

    # Restaura a ação de checagem do ambiente
    if action == "check_env":
        return ["make", "test-env"], {}

    # Restaura a ação de geração da amostra demo
    if action == "demo":
        return ["make", "demo"], {}

    # Restaura a ação de reconstrução do ambiente virtual
    if action == "rebuild_env":
        return ["bash", "bundle/install_wsl.sh"], {}

    # Restaura a ação de importação manual de amostras via script
    if action == "import_sample":
        sample = params.get("sample", "")
        r1 = params.get("r1", "")
        r2 = params.get("r2", "")
        cmd = ["bash", "scripts/00_import_sample.sh", "--sample", sample, "--r1", r1, "--r2", r2]
        if params.get("copy"):
            cmd.append("--copy")
        return cmd, {}

    if action == "build_db":
        raw = (params.get("db") or params.get("target") or "").strip()
        db_query = (params.get("db_query") or params.get("query") or "").strip()
        ncbi_db = (params.get("ncbi_db") or "").strip()

        cmd = ["bash", "scripts/13_db_manager.sh", "setup"]
        env = {}

        if db_query:
            # Se tem query customizada, ignora a lista suspensa e força o banco 'custom'
            env["DB"] = "custom"
            env["DB_QUERY"] = db_query
        elif raw:
            env["DB"] = _DB_ALIAS.get(raw.lower(), raw)
        else:
            raise ValueError(
                "Selecione um alvo na lista suspensa OU preencha o campo "
                "'Query customizada'. Ambos não podem estar vazios."
            )

        if ncbi_db:
            env["NCBI_DB"] = ncbi_db

        return cmd, env

    if action == "advanced_analysis":
        sample = params.get("sample")
        if not sample:
            raise ValueError("Campo obrigatório ausente: sample")

        blast_path = find_blast_path(sample)
        if not blast_path or not blast_path.exists():
            raise ValueError(f"Nenhum resultado BLAST prévio encontrado para a amostra '{sample}'. Execute o pipeline principal primeiro.")

        kmer = params.get("kmer") or "31"
        min_pident = params.get("min_pident") or "85.0"
        min_aln_len = params.get("min_aln_len") or "20"
        method = params.get("method") or "auto"

        cmd = [
            "bash", "scripts/21_run_advanced_analysis.sh",
            "--sample", sample,
            "--kmer", str(kmer),
            "--min-pident", str(min_pident),
            "--min-aln-len", str(min_aln_len),
            "--method", method
        ]
        return cmd, {}

    if action == "pipeline":
        sample = params.get("sample")
        if not sample:
            raise ValueError("Campo obrigatório ausente: sample")

        assembler = (params.get("assembler") or "velvet").lower()
        kmer = params.get("kmer") or "31"

        db = (params.get("db") or params.get("target") or "").strip()
        db_query = (params.get("db_query") or params.get("query") or "").strip()

        cmd = ["bash", "scripts/20_run_pipeline.sh", "--sample", sample, "--kmer", str(kmer),
               "--assembler", assembler]
        env = {}
        env.update(host_env_from_params(params))

        # QC toggle do dashboard
        if params.get("skip_qc"):
            cmd.append("--skip-qc")

        if assembler in {"velvet", "spades", "metaspades"}:
            env["ASSEMBLER"] = assembler

        if db_query:
            # Força o pipeline a procurar o banco customizado
            env["DB"] = "custom"
            env["DB_QUERY"] = db_query
        elif db:
            # Translate targets.json long-form keys → short keys known by 13_db_manager.sh
            env["DB"] = _DB_ALIAS.get(db.lower(), db)

        return cmd, env

    if action == "evidence_pipeline":
        sample = params.get("sample")
        assembler = (params.get("assembler") or "spades").lower()
        if assembler not in {"velvet", "spades", "metaspades"}:
            raise ValueError("assembler inválido")
        library_mode = (params.get("library_mode") or "unknown").lower()
        role = (params.get("role") or "sample").lower()
        umi_mode = (params.get("umi_mode") or "none").lower()
        if library_mode not in {"shotgun", "amplicon", "targeted", "unknown"}:
            raise ValueError("library_mode inválido")
        if role not in {"sample", "negative_extraction", "negative_library", "negative_sequencing", "positive"}:
            raise ValueError("role inválido")
        if umi_mode not in {"none", "read_name", "tag"}:
            raise ValueError("umi_mode inválido")
        if umi_mode != "none" and library_mode == "unknown":
            raise ValueError("UMI exige library_mode conhecido")
        if role == "positive" and not str(params.get("expected_target") or "").strip():
            raise ValueError("controle positivo exige expected_target")
        config = str(params.get("config") or "config/evidence_v2.yaml")
        config_path = (REPO_ROOT / config).resolve() if not Path(config).is_absolute() else Path(config).resolve()
        try:
            config_path.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ValueError("config deve estar dentro do projeto") from exc
        if not config_path.is_file():
            raise ValueError("configuração Evidence V2 não encontrada")
        cmd = [
            "bash", "scripts/20_run_pipeline.sh", "--sample", sample,
            "--assembler", assembler, "--evidence-v2", "--evidence-config", str(config_path),
        ]
        env = {
            "EVIDENCE_RUN_ID": str(params.get("run_id") or ""),
            "EVIDENCE_LIBRARY_MODE": library_mode,
            "EVIDENCE_UMI_MODE": umi_mode,
            "EVIDENCE_ROLE": role,
            "EVIDENCE_EXPECTED_TARGET": str(params.get("expected_target") or ""),
        }
        db = str(params.get("db") or params.get("target") or "").strip()
        if db:
            env["DB"] = _DB_ALIAS.get(db.lower(), db)
        return cmd, env

    if action == "evidence_batch":
        manifest_path = EVIDENCE_SERVICE.manifest_export(str(params.get("manifest_id") or ""))
        config = str(params.get("config") or "config/evidence_v2.yaml")
        config_path = (REPO_ROOT / config).resolve() if not Path(config).is_absolute() else Path(config).resolve()
        try:
            config_path.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ValueError("config deve estar dentro do projeto") from exc
        if not config_path.is_file():
            raise ValueError("configuração Evidence V2 não encontrada")
        cmd = [
            "bash", "scripts/23_run_batch.sh", "--batch-manifest", str(manifest_path),
            "--config", str(config_path), "--run-id", str(params.get("run_id") or ""),
        ]
        return cmd, {}

    if action == "assembly_only":
        sample = params.get("sample")
        if not sample:
            raise ValueError("Campo obrigatório ausente: sample")

        assembler = (params.get("assembler") or "velvet").lower()
        kmer = str(params.get("kmer") or "31")
        spades_params = (params.get("spades_params") or "").strip()

        cmd = [
            "bash", "scripts/22_run_assembly_only.sh",
            "--sample", sample,
            "--assembler", assembler,
            "--kmer", kmer,
        ]
        if spades_params:
            cmd.extend(["--spades-params", spades_params])
        return cmd, {}

    raise ValueError("Ação inválida")


def run_job(job_id, action, params):
    env = os.environ.copy()
    try:
        cmd, extra_env = build_command(action, params)
        env.update(extra_env)
    except ValueError as exc:
        logger.error("[job:%s] Comando inválido para ação '%s': %s", job_id, action, exc)
        with jobs_lock:
            jobs[job_id].update({"status": "error", "output": [f"[ERRO] {exc}\n"], "returncode": 1})
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    sample = params.get("sample") or params.get("target") or action
    log_name = f"ux_dashboard_{now}_{sanitize_token(action)}_{sanitize_token(sample)}_{job_id}.log"
    log_path = LOG_DIR / log_name

    start_epoch = time.time()
    pipeline_sample, assembler, kmer, threads = parse_pipeline_details(params)
    logger.info("[job:%s] Iniciando ação='%s' sample='%s' cmd=%s", job_id, action, sample, command_for_log(cmd))

    with jobs_lock:
        jobs[job_id].update({"status": "running", "command": command_for_log(cmd), "log_path": str(log_path.relative_to(REPO_ROOT))})

    try:
        with jobs_lock:
            if jobs.get(job_id, {}).get("status") == "cancelled":
                if action in {"evidence_pipeline", "evidence_batch"}:
                    force_evidence_state_terminal(job_id, "cancelled", "Execução cancelada antes do início; nenhum artefato foi promovido.")
                return
        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(__import__("subprocess"), "CREATE_NEW_PROCESS_GROUP", 0)
        process = Popen(
            cmd, cwd=REPO_ROOT, env=env, stdout=PIPE, stderr=STDOUT,
            text=True, bufsize=1, start_new_session=(os.name != "nt"), creationflags=creation_flags
        )
    except Exception as exc:
        logger.error("[job:%s] Falha ao iniciar processo: %s\n%s", job_id, exc, traceback.format_exc())
        if action in {"evidence_pipeline", "evidence_batch"}:
            with jobs_lock:
                jobs[job_id]["failure_type"] = "DEPENDENCY_MISSING" if isinstance(exc, FileNotFoundError) else "TOOL_FAILURE"
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "failed", "Não foi possível iniciar o processo; verifique o ambiente Linux/WSL.")
        with jobs_lock:
            jobs[job_id].update({"status": "error", "output": [f"[ERRO] Falha ao iniciar processo: {exc}\n"], "returncode": 1})
        return

    # Store process reference so it can be cancelled via /api/job/<id>/cancel
    with jobs_lock:
        jobs[job_id]["process"] = process

    output_lines = []
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            if process.stdout:
                for line in process.stdout:
                    log_file.write(line)
                    log_file.flush()
                    output_lines.append(line)
                    output_lines = clamp_output(output_lines)
                    with jobs_lock:
                        jobs[job_id]["output"] = output_lines
    except Exception as exc:
        logger.error("[job:%s] Erro durante leitura de saída: %s\n%s", job_id, exc, traceback.format_exc())
    returncode = process.wait()
    end_epoch = time.time()

    # Check if job was cancelled while running
    with jobs_lock:
        was_cancelled = jobs[job_id].get("status") == "cancelled"

    if was_cancelled:
        logger.info("[job:%s] Ação '%s' cancelada pelo usuário.", job_id, action)
        with jobs_lock:
            jobs[job_id].update({"returncode": returncode, "finished_at": end_epoch, "output": output_lines,
                                  "tail": "[CANCELADO] A execução foi interrompida pelo usuário."})
        if action in {"evidence_pipeline", "evidence_batch"}:
            force_evidence_state_terminal(job_id, "cancelled", "Execução cancelada; artefatos parciais não foram promovidos.")
        return

    if returncode != 0:
        logger.error("[job:%s] Ação '%s' terminou com código %s. Log: %s", job_id, action, returncode, log_path)
        if action in {"evidence_pipeline", "evidence_batch"}:
            with jobs_lock:
                jobs[job_id]["failure_type"] = classify_evidence_failure(output_lines)
            force_evidence_state_terminal(job_id, "failed", f"Processo encerrou com código {returncode}; consulte o log.")
    else:
        logger.info("[job:%s] Ação '%s' concluída com sucesso em %.1fs", job_id, action, end_epoch - start_epoch)

    report_file = None
    if action == "pipeline":
        rpath = find_report_path(pipeline_sample)
        report_file = str(rpath.relative_to(REPO_ROOT)) if rpath else None
    elif action == "advanced_analysis":
        rpath = find_advanced_report_path(pipeline_sample)
        report_file = str(rpath.relative_to(REPO_ROOT)) if rpath else None
    elif action == "assembly_only":
        rpath = find_assembly_summary_path(pipeline_sample)
        report_file = str(rpath.relative_to(REPO_ROOT)) if rpath else None

    metadata = {
        "id": job_id,
        "action": action,
        "sample": pipeline_sample or params.get("sample"),
        "assembler": assembler if action == "pipeline" else None,
        "requested_assembler": params.get("assembler") if action in {"pipeline", "assembly_only"} else None,
        "used_assembler": assembler if action == "pipeline" else None,
        "input_mode": "CONTIGS" if params.get("contigs") else "READS",
        "failure_type": "NONE" if returncode == 0 else jobs.get(job_id, {}).get("failure_type", "TOOL_FAILURE"),
        "rescue_triggered": None,
        "db_id": params.get("db") or params.get("target") or env.get("DB"),
        "db_query": params.get("db_query") or params.get("query") or env.get("DB_QUERY"),
        "kmer": kmer if action == "pipeline" else params.get("kmer"),
        "threads": threads if action == "pipeline" else params.get("threads"),
        "command": command_for_log(cmd),
        "start": iso_now(start_epoch),
        "end": iso_now(end_epoch),
        "start_epoch": start_epoch,
        "end_epoch": end_epoch,
        "exit_code": returncode,
        "params": params,
        "versions": tool_versions() if action == "pipeline" else {},
        "paths": {
            "log": str(log_path.relative_to(REPO_ROOT)),
            "report": report_file,
            "blast": str(find_blast_path(pipeline_sample).relative_to(REPO_ROOT)) if (action == "pipeline" and find_blast_path(pipeline_sample)) else None,
        },
    }
    metadata = snapshot_run_artifacts(metadata)

    with jobs_lock:
        jobs[job_id].update(
            {
                "returncode": returncode,
                "status": "done" if returncode == 0 else "error",
                "output": output_lines,
                "finished_at": end_epoch,
                "run": metadata,
                "tail": read_tail(log_path, lines=30) if returncode != 0 else "",
            }
        )


# SPAdes/Velvet intermediate subdirectory names that are safe to delete
_HEAVY_ASSEMBLER_SUBDIR_NAMES = frozenset({
    "tmp", "corrected", "misc", "before_rr",
    "intermediate_contigs", "pipeline_state", "assembly_graph_with_scaffolds",
})
_HEAVY_ASSEMBLER_SUBDIRS = re.compile(
    r'^K\d+$'  # SPAdes per-kmer work dirs: K21, K33, K55, K77, K99, K127 …
    r'|^(' + '|'.join(re.escape(n) for n in sorted(_HEAVY_ASSEMBLER_SUBDIR_NAMES)) + r')$'
)
# Large Velvet intermediate files (not contigs.fa) that can be deleted
_VELVET_HEAVY_FILES = frozenset({"Sequences", "Roadmaps", "Graph2", "LastGraph", "PreGraph"})


def cleanup_temp_files():
    """Remove heavy intermediate files from assembler output directories.

    Preserves:
    - Any contigs.fa / contigs.fasta file
    - results/blast/, results/reports/, results/runs/ (never touched)
    """
    assemblies_dir = REPO_ROOT / "data" / "assemblies"
    removed = []
    errors = []
    freed_bytes = 0

    if not assemblies_dir.exists():
        return {"removed": removed, "errors": errors, "freed_bytes": freed_bytes, "success": True}

    for asm_dir in assemblies_dir.iterdir():
        if not asm_dir.is_dir() or asm_dir.name.startswith("."):
            continue
        # Remove heavy SPAdes intermediate subdirectories (K21/, tmp/, corrected/, etc.)
        for child in asm_dir.iterdir():
            if child.is_dir() and _HEAVY_ASSEMBLER_SUBDIRS.match(child.name):
                try:
                    size = sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
                    shutil.rmtree(child)
                    freed_bytes += size
                    removed.append(str(child.relative_to(REPO_ROOT)))
                    logger.info("[cleanup] Removido: %s (%.1f MB)", child.relative_to(REPO_ROOT), size / 1048576)
                except Exception as exc:
                    errors.append(f"{child.relative_to(REPO_ROOT)}: {exc}")
                    logger.warning("[cleanup] Erro ao remover %s: %s", child, exc)
            elif child.is_file() and child.name in _VELVET_HEAVY_FILES:
                try:
                    size = child.stat().st_size
                    child.unlink()
                    freed_bytes += size
                    removed.append(str(child.relative_to(REPO_ROOT)))
                    logger.info("[cleanup] Removido arquivo Velvet: %s (%.1f MB)", child.relative_to(REPO_ROOT), size / 1048576)
                except Exception as exc:
                    errors.append(f"{child.relative_to(REPO_ROOT)}: {exc}")
                    logger.warning("[cleanup] Erro ao remover arquivo %s: %s", child, exc)

    return {"removed": removed, "errors": errors, "freed_bytes": freed_bytes, "success": True}


def list_run_history():
    runs = []
    for run_json in RUNS_DIR.glob("*/run.json"):
        try:
            data = json.loads(run_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        data["run_dir"] = run_json.parent.name
        runs.append(data)
    evidence_states = REPO_ROOT / "results" / "evidence" / "state"
    for state_path in evidence_states.glob("*.json") if evidence_states.is_dir() else []:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        status = state.get("status", "failed")
        runs.append({
            "id": state.get("run_id"), "run_id": state.get("run_id"),
            "action": state.get("action"), "sample": ", ".join(state.get("sample_ids") or []),
            "batch_id": state.get("batch_id"), "start": state.get("started_at") or state.get("created_at"),
            "end": state.get("finished_at"), "end_epoch": 0,
            "exit_code": 0 if status in {"done", "done_with_warning"} else 1,
            "status": status, "shadow_mode": True, "evidence_v2": True,
            "official_v1_status": state.get("official_v1_status", "not_started"),
            "evidence_v2_status": state.get("evidence_v2_status", status),
            "failure_type": state.get("failure_type"),
            "failed_stage": state.get("failed_stage"),
            "failure_message": state.get("failure_message"),
            "complete": (REPO_ROOT / "results" / "evidence" / "runs" / str(state.get("run_id")) / "SUCCESS.json").is_file(),
        })
    runs.sort(key=lambda item: item.get("end_epoch", 0), reverse=True)
    return runs


def resolve_history_file(run_dir, file_type):
    if not isinstance(run_dir, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", run_dir):
        return None
    run_path = RUNS_DIR / run_dir
    run_json = run_path / "run.json"
    if not run_json.exists():
        return None
    data = json.loads(run_json.read_text(encoding="utf-8"))
    key_map = {
        "report": "run_report",
        "log": "run_log",
        "blast": "run_blast",
        "labeled": "run_labeled",
        "adj_identity": "run_adj_identity",
        "hit_contigs_fasta": "run_hit_contigs_fasta",
    }
    relpath = data.get("paths", {}).get(key_map.get(file_type, ""))
    if not relpath:
        return None
    target = REPO_ROOT / relpath
    if not target.exists():
        return None
    # Security: ensure the resolved target is inside run_path (prevents path traversal)
    try:
        target.resolve().relative_to(run_path.resolve())
    except ValueError:
        logger.warning("Path traversal attempt blocked: target=%s run_path=%s", target, run_path)
        return None
    return target


def json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def request_content_length(handler):
    raw = handler.headers.get("Content-Length", "0")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Content-Length invalido") from exc
    if value < 0:
        raise ValueError("Content-Length invalido")
    return value


def text_response(handler, status, text):
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_file(handler, filepath, content_type):
    if not filepath.exists():
        logger.warning("Arquivo estático não encontrado: %s", filepath)
        handler.send_error(HTTPStatus.NOT_FOUND, "Arquivo não encontrado")
        return
    try:
        body = filepath.read_bytes()
    except OSError as exc:
        logger.error("Erro ao ler arquivo estático %s: %s", filepath, exc)
        handler.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Erro ao ler arquivo")
        return
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    if content_type.split(";")[0].strip() in CACHE_BYPASS_CONTENT_TYPES:
        handler.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        handler.send_header("Pragma", "no-cache")
        handler.send_header("Expires", "0")
    handler.end_headers()
    handler.wfile.write(body)


def import_uploaded_files(sample, r1_name, r1_data, r2_name, r2_data, replace=False):
    sample = require_sample_id(sample)
    if not validate_fastq_name(r1_name) or not validate_fastq_name(r2_name):
        raise ValueError("Extensão inválida (use .fastq ou .fastq.gz)")
    if not r1_data:
        raise ValueError("arquivo vazio: R1")
    if not r2_data:
        raise ValueError("arquivo vazio: R2")

    raw_dir = REPO_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_r1 = raw_dir / f"{sample}_R1.fastq.gz"
    out_r2 = raw_dir / f"{sample}_R2.fastq.gz"

    if not replace and (out_r1.exists() or out_r2.exists()):
        raise FileExistsError(f"Amostra '{sample}' ja existe; confirme substituicao explicitamente")

    import gzip

    replaced = []
    try:
        with tempfile.TemporaryDirectory(dir=raw_dir, prefix=f".{sample}.upload-") as temp_dir:
            temp_dir = Path(temp_dir)
            tmp_r1 = temp_dir / "R1.fastq.gz"
            tmp_r2 = temp_dir / "R2.fastq.gz"
            if r1_name.lower().endswith(".gz"):
                tmp_r1.write_bytes(r1_data)
            else:
                with gzip.open(tmp_r1, "wb") as fh:
                    fh.write(r1_data)
            if r2_name.lower().endswith(".gz"):
                tmp_r2.write_bytes(r2_data)
            else:
                with gzip.open(tmp_r2, "wb") as fh:
                    fh.write(r2_data)
            validate_fastq(tmp_r1, tmp_r2)
            os.replace(tmp_r1, out_r1)
            replaced.append(out_r1)
            os.replace(tmp_r2, out_r2)
            replaced.append(out_r2)
    except Exception:
        for path in replaced:
            path.unlink(missing_ok=True)
        raise


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# Transactional replacement used by the current upload route. The legacy
# helper above is retained only as source-compatible fallback code; all calls
# resolve to this definition after module loading.
def import_uploaded_files(sample, r1_name, r1_data, r2_name, r2_data, replace=False):
    sample = require_sample_id(sample)
    if not validate_fastq_name(r1_name) or not validate_fastq_name(r2_name):
        raise ValueError("Extensao invalida (use .fastq ou .fastq.gz)")
    if not r1_data or not r2_data:
        raise ValueError("R1 e R2 nao podem ser vazios")
    if len(r1_data) > MAX_UPLOAD_BYTES or len(r2_data) > MAX_UPLOAD_BYTES:
        raise ValueError("FASTQ excede o limite de upload")

    raw_dir = REPO_ROOT / "data" / "raw"
    incoming_dir = REPO_ROOT / "data" / "incoming"
    raw_dir.mkdir(parents=True, exist_ok=True)
    incoming_dir.mkdir(parents=True, exist_ok=True)
    out_r1 = raw_dir / f"{sample}_R1.fastq.gz"
    out_r2 = raw_dir / f"{sample}_R2.fastq.gz"
    if not replace and (out_r1.exists() or out_r2.exists()):
        raise FileExistsError(f"Amostra '{sample}' ja existe; confirme substituicao explicitamente")

    import gzip

    with tempfile.TemporaryDirectory(dir=incoming_dir, prefix=f".{sample}.upload-") as temp_name:
        temp_dir = Path(temp_name)
        tmp_r1 = temp_dir / "R1.fastq.gz"
        tmp_r2 = temp_dir / "R2.fastq.gz"
        if r1_name.lower().endswith(".gz"):
            tmp_r1.write_bytes(r1_data)
        else:
            with gzip.open(tmp_r1, "wb") as handle:
                handle.write(r1_data)
        if r2_name.lower().endswith(".gz"):
            tmp_r2.write_bytes(r2_data)
        else:
            with gzip.open(tmp_r2, "wb") as handle:
                handle.write(r2_data)
        count = validate_fastq(tmp_r1, tmp_r2)
        metadata = {
            "sample_id": sample,
            "read_count_pairs": count,
            "r1_name": Path(r1_name).name,
            "r2_name": Path(r2_name).name,
            "r1_sha256": _sha256_bytes(r1_data),
            "r2_sha256": _sha256_bytes(r2_data),
            "imported_at": datetime.now().astimezone().isoformat(),
            "source_scope": "operational_only",
        }
        metadata_path = incoming_dir / f"{sample}.json"
        backups = []
        promoted = []
        try:
            for target in (out_r1, out_r2):
                if target.exists():
                    backup = temp_dir / f"backup-{target.name}"
                    os.replace(target, backup)
                    backups.append((backup, target))
            for source, target in ((tmp_r1, out_r1), (tmp_r2, out_r2)):
                os.replace(source, target)
                promoted.append(target)
            atomic_json(metadata_path, metadata)
            for backup, _ in backups:
                backup.unlink(missing_ok=True)
        except Exception:
            for target in promoted:
                target.unlink(missing_ok=True)
            for backup, target in reversed(backups):
                if backup.exists():
                    os.replace(backup, target)
            raise


def import_zip_sample(sample, zip_bytes):
    if not zip_bytes:
        raise ValueError("arquivo vazio")

    tmp_dir = LOG_DIR / "uploads_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_zip = tmp_dir / f"tmp_upload_{uuid.uuid4().hex}.zip"
    temp_zip.write_bytes(zip_bytes)

    try:
        with zipfile.ZipFile(temp_zip) as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            expanded_size = sum(info.file_size for info in infos)
            if len(zip_bytes) > MAX_UPLOAD_BYTES:
                raise ValueError("arquivo ZIP excede o limite comprimido permitido")
            if expanded_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES or any(info.file_size > MAX_UPLOAD_BYTES for info in infos):
                raise ValueError("arquivo ZIP excede o limite descompactado permitido")
            if any(info.compress_size and info.file_size / info.compress_size > 1000 for info in infos):
                raise ValueError("arquivo ZIP possui razao de compressao incompatível com upload seguro")
            names = [info.filename for info in infos]
            fastqs = [n for n in names if validate_fastq_name(n.lower())]
            r1_candidates = [n for n in fastqs if "r1" in n.lower()]
            r2_candidates = [n for n in fastqs if "r2" in n.lower()]
            if len(r1_candidates) != 1:
                raise ValueError("R1 não encontrado no .zip")
            if len(r2_candidates) != 1:
                raise ValueError("R2 não encontrado no .zip")

            r1_name = r1_candidates[0]
            r2_name = r2_candidates[0]
            import_uploaded_files(sample, Path(r1_name).name, zf.read(r1_name), Path(r2_name).name, zf.read(r2_name))
    finally:
        temp_zip.unlink(missing_ok=True)


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self._do_GET_inner()
        except FileNotFoundError as exc:
            json_response(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            json_response(self, HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except Exception as exc:
            logger.error("Exceção não tratada em do_GET path=%s: %s\n%s", getattr(self, "path", "?"), exc, traceback.format_exc())
            try:
                json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Erro interno do servidor"})
            except Exception:
                pass

    def _do_GET_inner(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/":
            return serve_file(self, DASHBOARD_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/api/dbs":
            return json_response(self, HTTPStatus.OK, {"dbs": list_db_profiles()})
        if parsed.path == "/styles.css":
            return serve_file(self, DASHBOARD_DIR / "styles.css", "text/css; charset=utf-8")
        if parsed.path == "/app.js":
            return serve_file(self, DASHBOARD_DIR / "app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/hero-bg.png":
            return serve_file(self, DASHBOARD_DIR / "hero-bg.png", "image/png")
        if parsed.path == "/gene-in-logo.png":
            return serve_file(self, DASHBOARD_DIR / "gene-in-logo.png", "image/png")
        if parsed.path == "/favicon.ico":
            # Return empty 204 to suppress constant 404 warnings from browsers
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path == "/api/samples":
            return json_response(self, HTTPStatus.OK, {"samples": list_samples()})
        if parsed.path == "/api/targets":
            return json_response(self, HTTPStatus.OK, {"targets": list_targets()})
        if parsed.path == "/api/history":
            return json_response(self, HTTPStatus.OK, {"runs": list_run_history()})
        if parsed.path == "/api/evidence/config":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.config())
        if parsed.path == "/api/evidence/dependencies":
            dependencies = EVIDENCE_SERVICE.dependencies()
            return json_response(self, HTTPStatus.OK if dependencies.get("valid") else HTTPStatus.SERVICE_UNAVAILABLE, dependencies)
        if parsed.path == "/api/evidence/manifests":
            return json_response(self, HTTPStatus.OK, {"manifests": EVIDENCE_SERVICE.list_manifests()})
        if parsed.path == "/api/evidence/manifest":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.manifest((query.get("id") or [""])[0]))
        if parsed.path == "/api/evidence/manifest/export":
            target = EVIDENCE_SERVICE.manifest_export((query.get("id") or [""])[0])
            return serve_file(self, target, "text/tab-separated-values; charset=utf-8")
        if parsed.path == "/api/evidence/run":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.state((query.get("id") or [""])[0]))
        if parsed.path == "/api/evidence/result":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.result((query.get("run") or [""])[0]))
        if parsed.path == "/api/evidence/artifact":
            target = EVIDENCE_SERVICE.artifact(
                (query.get("run") or [""])[0], (query.get("type") or [""])[0]
            )
            if target.suffix == ".json":
                ctype = "application/json; charset=utf-8"
            elif target.suffix in {".bam", ".bai"}:
                ctype = "application/octet-stream"
            else:
                ctype = "text/plain; charset=utf-8"
            return serve_file(self, target, ctype)
        if parsed.path == "/api/config/env":
            try:
                config = load_config_env()
                return json_response(self, HTTPStatus.OK, {"config": config})
            except ValueError as exc:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc), "success": False})
            except Exception as exc:
                logger.error("Erro ao carregar configuração: %s\n%s", exc, traceback.format_exc())
                return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Erro ao carregar configuração: {exc}"})
        if parsed.path == "/api/config/environment":
            try:
                status = get_environment_status()
                return json_response(self, HTTPStatus.OK, status)
            except Exception as exc:
                logger.error("Erro ao obter status do ambiente: %s\n%s", exc, traceback.format_exc())
                return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Erro ao obter status do ambiente: {exc}"})
        if parsed.path == "/api/history/file":
            query = parse_qs(parsed.query)
            target = resolve_history_file((query.get("run") or [""])[0], (query.get("type") or [""])[0])
            if not target:
                logger.warning("Arquivo de histórico não encontrado: run=%s type=%s", (query.get("run") or [""])[0], (query.get("type") or [""])[0])
                return self.send_error(HTTPStatus.NOT_FOUND, "Arquivo do histórico não encontrado")
            ctype = "text/markdown; charset=utf-8" if target.suffix == ".md" else "text/plain; charset=utf-8"
            return serve_file(self, target, ctype)
        if parsed.path.startswith("/api/job/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            cleanup_old_jobs()
            with jobs_lock:
                job = jobs.get(job_id)
            if not job:
                logger.warning("Job não encontrado: %s", job_id)
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Job não encontrado"})
            return json_response(self, HTTPStatus.OK, {"id": job_id, "status": job.get("status"), "output": "".join(job.get("output", [])), "returncode": job.get("returncode"), "command": job.get("command"), "log_path": job.get("log_path"), "run": job.get("run"), "tail": job.get("tail", "")})
        logger.warning("Rota GET não encontrada: %s", self.path)
        return self.send_error(HTTPStatus.NOT_FOUND, "Rota inválida")


    def do_POST(self):
        try:
            self._do_POST_inner()
        except FileExistsError as exc:
            json_response(self, HTTPStatus.CONFLICT, {"error": str(exc)})
        except FileNotFoundError as exc:
            json_response(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            json_response(self, HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except Exception as exc:
            logger.error("Exceção não tratada em do_POST path=%s: %s\n%s", getattr(self, "path", "?"), exc, traceback.format_exc())
            try:
                json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Erro interno do servidor"})
            except Exception:
                pass

    def _do_POST_inner(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/import-upload":
            return self.handle_upload_import()

        try:
            content_length = request_content_length(self)
        except ValueError as exc:
            return text_response(self, HTTPStatus.BAD_REQUEST, str(exc))
        if content_length > MAX_UPLOAD_BYTES:
            logger.warning("Upload recusado por tamanho em POST: %s bytes (limite %s bytes)", content_length, MAX_UPLOAD_BYTES)
            return text_response(self, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Upload muito grande. Limite atual: 500 MB. Use arquivos menores ou importe os FASTQs manualmente para data/raw/.")
        if content_length <= 0:
            return text_response(self, HTTPStatus.BAD_REQUEST, "Body vazio")
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning("JSON inválido recebido em POST %s", parsed.path)
            return text_response(self, HTTPStatus.BAD_REQUEST, "JSON inválido")

        if parsed.path == "/api/evidence/config/validate":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.validate_config_text(payload.get("content", "")))
        if parsed.path == "/api/evidence/manifests/validate":
            result = EVIDENCE_SERVICE.validate_manifest(payload.get("rows"), validate_files=True)
            return json_response(self, HTTPStatus.OK if result["valid"] else HTTPStatus.BAD_REQUEST, result)
        if parsed.path == "/api/evidence/manifests/save":
            result = EVIDENCE_SERVICE.save_manifest(payload.get("rows"), payload.get("manifest_id"))
            return json_response(self, HTTPStatus.OK if result["valid"] else HTTPStatus.BAD_REQUEST, result)
        if parsed.path == "/api/evidence/manifests/import":
            return json_response(self, HTTPStatus.OK, EVIDENCE_SERVICE.import_manifest(payload.get("content", "")))
        if parsed.path == "/api/evidence/run":
            mode = str(payload.get("mode") or "individual").lower()
            params = payload.get("params") or {}
            if mode == "individual":
                return self.start_job("evidence_pipeline", params)
            if mode == "batch":
                return self.start_job("evidence_batch", params)
            return json_response(self, HTTPStatus.BAD_REQUEST, {"error": "mode deve ser individual ou batch"})

        if parsed.path == "/api/host-index/validate":
            result = validate_host_index(payload.get("prefix", ""))
            status = HTTPStatus.OK if result["valid"] else HTTPStatus.BAD_REQUEST
            return json_response(self, status, result)

        if parsed.path == "/api/config/env":
            prevalidated_updates = payload.get("config", {})
            try:
                validate_config_updates(prevalidated_updates)
            except ValueError as exc:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc), "success": False})
            try:
                updates = payload.get("config", {})
                if not isinstance(updates, dict):
                    return json_response(self, HTTPStatus.BAD_REQUEST, {"error": "config deve ser um objeto JSON", "success": False})
                # Validate that only supported keys are being updated
                for key in updates:
                    if key not in SUPPORTED_ENV_KEYS:
                        logger.warning("Chave de configuração não suportada: %s", key)
                        return json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Chave não suportada: {key}", "success": False})

                save_config_env(updates)
                logger.info("Configuração salva: %s", list(updates.keys()))
                return json_response(self, HTTPStatus.OK, {"success": True, "message": "Configuração atualizada com sucesso"})
            except Exception as exc:
                logger.error("Erro ao salvar configuração: %s\n%s", exc, traceback.format_exc())
                return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Erro ao salvar configuração: {exc}", "success": False})

        if parsed.path == "/api/config/environment/rebuild":
            # Trigger bundle/install_wsl.sh as a background job
            if not INSTALL_WSL_SCRIPT.exists():
                logger.error("Script não encontrado: %s", INSTALL_WSL_SCRIPT)
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Script bundle/install_wsl.sh não encontrado", "success": False})

            return self.start_job("rebuild_env", {})

        if parsed.path == "/api/history/rerun":
            raw_run_dir = payload.get("run_dir")
            if not isinstance(raw_run_dir, str):
                logger.warning("rerun: run_dir inválido (tipo): %r", type(raw_run_dir))
                return text_response(self, HTTPStatus.BAD_REQUEST, "run_dir inválido")
            run_dir = raw_run_dir.strip()
            if not run_dir:
                logger.warning("rerun: run_dir vazio")
                return text_response(self, HTTPStatus.BAD_REQUEST, "run_dir obrigatório")
            run_json = RUNS_DIR / run_dir / "run.json"
            try:
                run_json.resolve().relative_to(RUNS_DIR.resolve())
            except ValueError:
                return text_response(self, HTTPStatus.BAD_REQUEST, "run_dir invalido")
            if not run_json.exists():
                logger.warning("rerun: run.json não encontrado para run_dir='%s'", run_dir)
                return text_response(self, HTTPStatus.NOT_FOUND, "run.json não encontrado")
            try:
                data = json.loads(run_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("rerun: erro ao ler run.json '%s': %s", run_json, exc)
                return text_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, f"Erro ao ler run.json: {exc}")
            logger.info("rerun: relançando run_dir='%s' action='%s'", run_dir, data.get("action"))
            return self.start_job(data.get("action", "pipeline"), data.get("params") or {})

        if parsed.path == "/api/cleanup":
            try:
                result = cleanup_temp_files()
                if result.get("errors"):
                    logger.warning("[cleanup] Erros durante limpeza: %s", result["errors"])
                return json_response(self, HTTPStatus.OK, result)
            except Exception as exc:
                logger.error("Erro durante limpeza: %s\n%s", exc, traceback.format_exc())
                return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Erro durante limpeza: {exc}", "success": False})

        # Cancel a running job: POST /api/job/<id>/cancel
        if parsed.path.startswith("/api/job/") and parsed.path.endswith("/cancel"):
            parts = parsed.path.split("/")
            # path looks like /api/job/<job_id>/cancel → parts = ['', 'api', 'job', '<id>', 'cancel']
            job_id = parts[3] if len(parts) >= 5 else ""
            with jobs_lock:
                job = jobs.get(job_id)
            if not job:
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Job não encontrado"})
            status = job.get("status")
            if status not in ("running", "queued"):
                return json_response(self, HTTPStatus.OK, {"ok": False, "message": f"Job não está em execução (status={status})"})
            process = job.get("process")
            with jobs_lock:
                jobs[job_id]["status"] = "cancelled"
            if process is not None:
                import signal as _signal
                try:
                    if os.name != "nt":
                        os.killpg(os.getpgid(process.pid), _signal.SIGTERM)
                    else:
                        process.send_signal(getattr(_signal, "CTRL_BREAK_EVENT", _signal.SIGTERM))
                    logger.info("[job:%s] SIGTERM enviado para cancelamento.", job_id)
                except Exception:
                    pass
                # Give it 3 s to die gracefully, then SIGKILL
                def _force_kill(p, jid):
                    import time as _time
                    import signal as _signal
                    _time.sleep(3)
                    try:
                        if os.name != "nt":
                            os.killpg(os.getpgid(p.pid), _signal.SIGKILL)
                        else:
                            p.kill()
                        logger.info("[job:%s] SIGKILL enviado (processo não encerrou com SIGTERM).", jid)
                    except Exception:
                        pass
                threading.Thread(target=_force_kill, args=(process, job_id), daemon=True).start()
            logger.info("[job:%s] Cancelamento solicitado pelo usuário.", job_id)
            return json_response(self, HTTPStatus.OK, {"ok": True, "message": "Cancelamento solicitado"})

        if parsed.path != "/api/run":
            logger.warning("Rota POST não encontrada: %s", parsed.path)
            return self.send_error(HTTPStatus.NOT_FOUND, "Rota inválida")
        return self.start_job(payload.get("action"), payload.get("params") or {})

    def handle_upload_import(self):
        """Handle multipart/form-data upload without the deprecated `cgi` module."""
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return text_response(self, HTTPStatus.BAD_REQUEST, "Content-Type deve ser multipart/form-data")

        # Extract boundary from Content-Type header
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part[len("boundary="):].strip('"')
                break
        if not boundary:
            return text_response(self, HTTPStatus.BAD_REQUEST, "Boundary ausente no Content-Type")

        try:
            content_length = request_content_length(self)
        except ValueError as exc:
            return text_response(self, HTTPStatus.BAD_REQUEST, str(exc))
        if content_length > MAX_UPLOAD_BYTES:
            logger.warning("Upload recusado por tamanho em handle_upload_import: %s bytes (limite %s bytes)", content_length, MAX_UPLOAD_BYTES)
            return text_response(self, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Upload muito grande. Limite atual: 500 MB. Use arquivos menores ou importe os FASTQs manualmente para data/raw/.")
        if content_length <= 0:
            return text_response(self, HTTPStatus.BAD_REQUEST, "Body vazio")
        raw_body = self.rfile.read(content_length)

        # Parse multipart fields using email.parser (stdlib, not deprecated)
        import email
        import email.parser
        import email.policy

        msg_text = f"Content-Type: {content_type}\r\n\r\n".encode() + raw_body
        msg = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(msg_text)

        fields = {}
        for part in msg.get_payload():
            if not hasattr(part, 'get_payload'):
                continue
            cd = part.get("Content-Disposition", "")
            name = None
            filename = None
            for item in cd.split(";"):
                item = item.strip()
                if item.startswith('name="'):
                    name = item[6:-1]
                elif item.startswith('filename="'):
                    filename = item[10:-1]
            if name:
                payload = part.get_payload(decode=True)
                fields[name] = {"data": payload, "filename": filename}

        sample = (fields.get("sample", {}).get("data") or b"").decode("utf-8", errors="replace").strip()
        if not sample:
            return text_response(self, HTTPStatus.BAD_REQUEST, "Campo obrigatório: sample")

        try:
            zip_field = fields.get("zipfile")
            r1_field = fields.get("r1file")
            r2_field = fields.get("r2file")

            if zip_field and zip_field.get("filename") and zip_field.get("data"):
                import_zip_sample(sample, zip_field["data"])
            elif (r1_field and r1_field.get("filename") and r1_field.get("data")
                  and r2_field and r2_field.get("filename") and r2_field.get("data")):
                import_uploaded_files(
                    sample,
                    r1_field["filename"], r1_field["data"],
                    r2_field["filename"], r2_field["data"]
                )
            else:
                return text_response(self, HTTPStatus.BAD_REQUEST, "Envie R1/R2 ou arquivo .zip")
        except FileExistsError as exc:
            logger.warning("Amostra duplicada no upload '%s': %s", sample, exc)
            return text_response(self, HTTPStatus.CONFLICT, str(exc))
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            logger.warning("Erro no upload de amostra '%s': %s", sample, exc)
            return text_response(self, HTTPStatus.BAD_REQUEST, str(exc))
        logger.info("Upload importado com sucesso: sample='%s'", sample)
        return json_response(self, HTTPStatus.OK, {
            "message": f"Amostra importada: {sample}",
            "sample_id": sample,
            "r1": f"data/raw/{sample}_R1.fastq.gz",
            "r2": f"data/raw/{sample}_R2.fastq.gz",
            "source_scope": "operational_only",
        })

    def start_job(self, action, params):
        cleanup_old_jobs()
        if action not in {"check_env", "demo", "import_sample", "build_db", "pipeline", "rebuild_env", "advanced_analysis", "assembly_only", "evidence_pipeline", "evidence_batch"}:
            logger.warning("Tentativa de ação inválida: '%s'", action)
            return text_response(self, HTTPStatus.BAD_REQUEST, "Ação inválida")
        params = params or {}
        if not isinstance(params, dict):
            return text_response(self, HTTPStatus.BAD_REQUEST, "params deve ser um objeto JSON")
        sample = None
        if action in {"import_sample", "pipeline", "advanced_analysis", "assembly_only", "evidence_pipeline"}:
            try:
                sample = require_sample_id(params.get("sample"))
            except ValueError as exc:
                return text_response(self, HTTPStatus.BAD_REQUEST, str(exc))
            params = dict(params)
            params["sample"] = sample

        job_id = uuid.uuid4().hex
        params = dict(params)
        if action in {"evidence_pipeline", "evidence_batch"}:
            params["run_id"] = job_id
            # Validate the complete contract before a job becomes visible as queued.
            build_command(action, params)
            config_value = str(params.get("config") or "config/evidence_v2.yaml")
            config_path = Path(config_value)
            config_path = config_path if config_path.is_absolute() else REPO_ROOT / config_path
            config_path = config_path.resolve()
            try:
                config_path.relative_to(REPO_ROOT.resolve())
            except ValueError as exc:
                raise ValueError("config Evidence V2 deve estar dentro do projeto") from exc
            if not config_path.is_file():
                raise ValueError("configuração Evidence V2 não encontrada")
            EVIDENCE_SERVICE.validate_config_text(config_path.read_text(encoding="utf-8"))
        with jobs_lock:
            running = sum(1 for item in jobs.values() if item.get("status") in {"queued", "running"})
            if running >= MAX_RUNNING_JOBS:
                return json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"error": "Limite de jobs simultaneos atingido"})
            if sample and any(
                item.get("sample") == sample and item.get("status") in {"queued", "running"}
                for item in jobs.values()
            ):
                return json_response(self, HTTPStatus.CONFLICT, {"error": f"A amostra '{sample}' ja possui um job em execucao"})
            if action in {"build_db", "rebuild_env"} and any(
                item.get("action") in {"build_db", "rebuild_env"} and item.get("status") in {"queued", "running"}
                for item in jobs.values()
            ):
                return json_response(self, HTTPStatus.CONFLICT, {"error": "Ja existe uma operacao de ambiente/banco em execucao"})
            if action == "evidence_batch" and any(
                item.get("action") == "evidence_batch"
                and item.get("manifest_id") == params.get("manifest_id")
                and item.get("status") in {"queued", "running"}
                for item in jobs.values()
            ):
                return json_response(self, HTTPStatus.CONFLICT, {"error": "Este manifesto ja possui uma execucao Evidence V2 em andamento"})
            jobs[job_id] = {
                "status": "queued", "created_at": time.time(), "action": action,
                "sample": sample, "manifest_id": params.get("manifest_id"),
                "output": [], "returncode": None,
            }
        if action in {"evidence_pipeline", "evidence_batch"}:
            try:
                initialize_evidence_dashboard_state(action, params)
            except Exception:
                with jobs_lock:
                    jobs.pop(job_id, None)
                raise
        logger.info("Job enfileirado: id=%s action='%s' params=%s", job_id, action, params_for_log(params))
        threading.Thread(target=run_job, args=(job_id, action, params), daemon=True).start()
        return json_response(self, HTTPStatus.OK, {"job_id": job_id})

    def log_message(self, format, *args):
        msg = format % args
        parts = msg.split('"')
        status_code = None
        if len(parts) >= 3:
            after_quote = parts[2].strip().split()
            if after_quote and after_quote[0].isdigit():
                status_code = int(after_quote[0])
        if status_code is not None and status_code >= 500:
            logger.error("HTTP %s %s", self.address_string(), msg)
        elif status_code is not None and status_code >= 400:
            logger.warning("HTTP %s %s", self.address_string(), msg)
        else:
            logger.debug("HTTP %s %s", self.address_string(), msg)

    def send_error(self, code, message=None, explain=None):
        logger.error("Erro HTTP %s: %s | path=%s | client=%s", code, message, getattr(self, "path", "?"), self.address_string())
        super().send_error(code, message, explain)


def _ensure_config_env():
    """Bootstrap config/picornavirus.env from the bundled example if it doesn't exist yet."""
    if not CONFIG_ENV_PRIMARY.exists():
        if CONFIG_ENV_EXAMPLE.exists():
            CONFIG_ENV_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(CONFIG_ENV_EXAMPLE, CONFIG_ENV_PRIMARY)
            logger.info(
                "config/picornavirus.env criado a partir do exemplo: %s", CONFIG_ENV_EXAMPLE.name
            )
        else:
            logger.warning(
                "config/picornavirus.env não encontrado e nenhum .example disponível; "
                "usando config.env como fallback."
            )


def main():
    config_defaults = parse_env_file(get_config_env_path())
    default_host = os.environ.get("BIND_HOST") or config_defaults.get("BIND_HOST") or "127.0.0.1"
    try:
        default_port = int(os.environ.get("PORT") or config_defaults.get("PORT") or "8000")
    except ValueError:
        default_port = 8000

    parser = argparse.ArgumentParser(description="Painel local do Gene-In")
    parser.add_argument("--host", default=default_host,
                        help="Endereço de escuta. Padrão vem de BIND_HOST no config. "
                             "Somente localhost e endereços loopback são aceitos.")
    parser.add_argument("--port", default=default_port, type=int)
    args = parser.parse_args()

    if not is_loopback_host(args.host):
        print("[ERRO] O dashboard aceita somente enderecos loopback (127.0.0.1/localhost).")
        print("       A exposicao na rede exige uma modalidade autenticada futura.")
        raise SystemExit(2)
    if not 1 <= args.port <= 65535:
        print("[ERRO] A porta deve estar entre 1 e 65535.")
        raise SystemExit(2)

    _ensure_config_env()

    ThreadingHTTPServer.allow_reuse_address = True
    try:
        server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    except OSError as exc:
        if getattr(exc, "errno", None) in {98, 10048}:
            logger.error("Porta %s indisponivel em %s: %s", args.port, args.host, exc)
            print(f"[ERRO] A porta {args.port} ja esta em uso.")
            print("Feche o dashboard aberto anteriormente ou inicie em outra porta:")
            print(f"  python3 scripts/ux_dashboard.py --host {args.host} --port {args.port + 1}")
            raise SystemExit(1) from exc
        raise
    print("Painel ativo em:")
    print(f"  http://localhost:{args.port}")
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"  http://{args.host}:{args.port}  ← exposto na rede")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando painel...")


if __name__ == "__main__":
    main()
