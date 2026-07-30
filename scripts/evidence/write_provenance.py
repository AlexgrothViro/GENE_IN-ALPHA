#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

try:
    from .common import sha256_file, write_json_atomic
except ImportError:
    from common import sha256_file, write_json_atomic


def version(command: str) -> str:
    executable = shutil.which(command)
    if not executable:
        return "UNAVAILABLE"
    for args in ([command, "--version"], [command, "-version"]):
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            line = (result.stdout or result.stderr).splitlines()
            if line:
                return line[0].strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return "UNKNOWN"


def tool_record(command: str) -> dict[str, str]:
    executable = shutil.which(command)
    return {
        "version": version(command),
        "executable": str(Path(executable).resolve()) if executable else "UNAVAILABLE",
        "sha256": sha256_file(executable) if executable and Path(executable).is_file() else "UNAVAILABLE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Write reproducible evidence-v2 provenance")
    parser.add_argument("--out", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--value", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--artifact", action="append", default=[], metavar="KEY=PATH")
    args = parser.parse_args()
    values = {}
    for item in args.value:
        if "=" not in item:
            parser.error("--value must use KEY=VALUE")
        key, value = item.split("=", 1)
        values[key] = value
    artifacts = {}
    for item in args.artifact:
        if "=" not in item:
            parser.error("--artifact must use KEY=PATH")
        key, value = item.split("=", 1)
        path = Path(value)
        if not path.is_file():
            parser.error(f"artifact does not exist: {path}")
        artifacts[key] = {
            "path": str(path.resolve()), "size": path.stat().st_size, "sha256": sha256_file(path),
        }
    write_json_atomic(args.out, {
        "schema_version": "2.0", "pipeline_version": "2.0.0-alpha.2",
        "platform": platform.platform(), "config_path": str(Path(args.config).resolve()),
        "config_sha256": sha256_file(args.config), "parameters": values, "artifacts": artifacts,
        "tools": {name: tool_record(name) for name in (
            "python3", "fastp", "blastn", "makeblastdb", "bowtie2", "bowtie2-inspect", "samtools", "spades.py",
            "metaspades.py", "umi_tools", "mafft", "iqtree2", "iqtree",
        )},
    })


if __name__ == "__main__":
    main()
