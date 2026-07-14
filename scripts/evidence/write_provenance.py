#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
from pathlib import Path

try:
    from .common import write_json_atomic
except ImportError:
    from common import write_json_atomic


def version(command: str) -> str:
    executable = shutil.which(command)
    if not executable:
        return "UNAVAILABLE"
    for args in ([command, "--version"], [command, "-version"]):
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
            line = (result.stdout or result.stderr).splitlines()
            if line:
                return line[0].strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write reproducible evidence-v2 provenance")
    parser.add_argument("--out", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--value", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    config_bytes = Path(args.config).read_bytes()
    values = {}
    for item in args.value:
        if "=" not in item:
            parser.error("--value must use KEY=VALUE")
        key, value = item.split("=", 1)
        values[key] = value
    write_json_atomic(args.out, {
        "schema_version": "2.0-alpha", "pipeline_version": "2.0.0-alpha.1",
        "platform": platform.platform(), "config_path": str(Path(args.config).resolve()),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(), "parameters": values,
        "tools": {name: version(name) for name in ("python3", "blastn", "makeblastdb", "bowtie2", "samtools", "iqtree2", "iqtree")},
    })


if __name__ == "__main__":
    main()
