#!/usr/bin/env python3
"""Validate the runtime used by Evidence V2.

This check intentionally runs with the same ``python3`` that will execute the
pipeline. It prevents a stale bundle environment from failing halfway through
an otherwise successful 1.1 run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from .common import load_yaml_config
except ImportError:
    from common import load_yaml_config


def command_info(name: str) -> dict:
    path = shutil.which(name)
    result = {"available": bool(path), "path": path, "version": None, "sha256": None}
    if not path:
        return result
    try:
        version = subprocess.run(
            [path, "--version"], capture_output=True, text=True, check=False
        )
        result["version"] = (version.stdout or version.stderr).splitlines()[0][:300]
    except OSError:
        result["version"] = None
    try:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        result["sha256"] = digest.hexdigest()
    except (OSError, PermissionError):
        result["sha256"] = None
    return result


def run(config: Path, assembler: str, umi_mode: str, require_phylogeny: bool,
        required_commands: list[str]) -> tuple[dict, list[str]]:
    errors: list[str] = []
    report = {
        "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        "pyyaml": {"available": False, "version": None},
        "config": str(config),
        "commands": {},
    }
    try:
        import yaml  # type: ignore
        report["pyyaml"] = {"available": True, "version": getattr(yaml, "__version__", "unknown")}
        report["config_schema"] = load_yaml_config(config).get("schema_version")
    except (ImportError, ModuleNotFoundError):
        errors.append(
            "PyYAML ausente no Python efetivo; atualize o ambiente Gene-In com environment.yml"
        )
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"configuração Evidence V2 inválida: {exc}")
    except Exception as exc:
        errors.append(f"config Evidence V2 inválida: {exc}")

    selected = list(required_commands)
    if assembler == "velvet":
        selected.extend(["velveth", "velvetg"])
    elif assembler == "spades":
        selected.append("spades.py")
    elif assembler == "metaspades":
        selected.append("metaspades.py")
    if umi_mode != "none":
        selected.append("umi_tools")
    if require_phylogeny:
        selected.extend(["iqtree2" if shutil.which("iqtree2") else "iqtree"])
    # PyYAML parser exceptions are not all ValueError subclasses; keep the
    # preflight report machine-readable for malformed YAML as well.
    for name in dict.fromkeys(selected):
        info = command_info(name)
        report["commands"][name] = info
        if not info["available"]:
            errors.append(f"dependência ausente: {name}")
    return report, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight do runtime Evidence V2")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--assembler", choices=["none", "velvet", "spades", "metaspades"], default="spades")
    parser.add_argument("--umi-mode", choices=["none", "read_name", "tag"], default="none")
    parser.add_argument("--require-phylogeny", action="store_true")
    parser.add_argument("--require-command", action="append", default=[])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report, errors = run(args.config, args.assembler, args.umi_mode, args.require_phylogeny, args.require_command)
    report["valid"] = not errors
    report["errors"] = errors
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"[FATAL] {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
