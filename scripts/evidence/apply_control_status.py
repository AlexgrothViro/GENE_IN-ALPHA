#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

try:
    from .common import read_tsv, write_json_atomic
    from .export_evidence import render
except ImportError:
    from common import read_tsv, write_json_atomic
    from export_evidence import render


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply independent control status to shadow JSON reports")
    parser.add_argument("--statuses", required=True)
    parser.add_argument("--evidence-root", required=True)
    args = parser.parse_args()
    root = Path(args.evidence_root)
    for status in read_tsv(args.statuses):
        directory = root / "samples" / status["sample_id"] if (root / "samples").is_dir() else root / status["sample_id"]
        json_path = directory / "sample_evidence.json"
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data["control_status"] = status["control_status"]
        data.setdefault("control_metrics", {}).update(status)
        write_json_atomic(json_path, data)
        report = directory / "evidence_report.md"
        fd, tmp = tempfile.mkstemp(prefix=f".{report.name}.", suffix=".tmp", dir=report.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(render(data))
            os.replace(tmp, report)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


if __name__ == "__main__":
    main()
