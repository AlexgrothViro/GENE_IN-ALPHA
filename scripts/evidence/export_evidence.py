#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def render(data: dict) -> str:
    metrics = data.get("metrics", {})
    return f"""# Gene-In 2.0 evidence report — {data['sample_id']}

> **SHADOW MODE:** this report does not modify or replace the Gene-In 1.1 conclusion.

## Independent evidence dimensions

| Dimension | Status |
|---|---|
| Evidence level | `{data['evidence_level']}` |
| Specificity | `{data['specificity_status']}` |
| Coverage | `{data['coverage_status']}` |
| Controls | `{data['control_status']}` |

## Aggregated metrics

- Qualifying loci: {metrics.get('qualifying_loci', 0)}
- Nonredundant reference bases: {metrics.get('total_nonredundant_reference_bp', 0)}
- Unique templates: {metrics.get('unique_templates', 0)}
- Distinct starts: {metrics.get('distinct_starts', 0)}
- Breadth 1×: {metrics.get('breadth_1x', 0):.6f}
- Breadth 3×: {metrics.get('breadth_3x', 0):.6f}
- Median depth on covered positions: {metrics.get('median_depth_covered', 0):.3f}
- Maximum-window depth fraction: {metrics.get('max_window_depth_fraction', 0):.6f}

## Interpretation policy

- Fragments between 20 and 49 bp remain exploratory.
- Operational thresholds are provisional until the benchmark is completed.
- No diagnostic or biological confirmation is produced by this report.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a shadow-mode evidence report")
    parser.add_argument("--json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with open(args.json, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(render(data))
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    main()
