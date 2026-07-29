#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator


def validate_evidence_config(data: object) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != "2.0-alpha":
        raise ValueError("evidence config must be a mapping with schema_version: 2.0-alpha")
    allowed = {"schema_version", "blast", "locus", "support", "specificity", "sample_evidence", "controls", "phylogeny"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown evidence config sections: {', '.join(sorted(unknown))}")
    expected_keys = {
        "blast": {"short_max_bp", "dual_mode_min_bp", "dual_mode_max_bp", "explicit_dust", "soft_masking"},
        "locus": {"gap_bp", "minimum_candidate_bp"},
        "support": {"minimum_unique_templates", "minimum_distinct_starts_shotgun", "minimum_mapq", "minimum_base_quality", "require_proper_pair_shotgun"},
        "specificity": {"minimum_delta_bitscore", "maximum_qcov_difference_pp"},
        "sample_evidence": {"multi_locus_minimum", "multi_locus_total_bp", "genome_breadth_1x", "median_covered_depth", "concentration_window_bp"},
        "controls": {"provisional_sample_to_negative_ratio", "uncontrolled_maximum"},
        "phylogeny": {"minimum_aligned_bp", "minimum_informative_sites", "minimum_references", "maximum_n_fraction", "maximum_gap_fraction"},
    }
    for section, keys in expected_keys.items():
        if section not in data:
            raise ValueError(f"missing evidence config section: {section}")
        value = data[section]
        if not isinstance(value, dict):
            raise ValueError(f"config section {section} must be a mapping")
        extra, missing = set(value) - keys, keys - set(value)
        if extra:
            raise ValueError(f"unknown keys in {section}: {', '.join(sorted(extra))}")
        if missing:
            raise ValueError(f"missing keys in {section}: {', '.join(sorted(missing))}")

    def number(section: str, key: str, minimum: float, maximum: float | None = None) -> float:
        value = data[section][key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{section}.{key} must be numeric")
        value = float(value)
        if value < minimum or (maximum is not None and value > maximum):
            raise ValueError(f"{section}.{key} is outside the allowed range")
        return value

    for section, key in (("blast", "explicit_dust"), ("blast", "soft_masking"), ("support", "require_proper_pair_shotgun")):
        if not isinstance(data[section][key], bool):
            raise ValueError(f"{section}.{key} must be boolean")
    short = number("blast", "short_max_bp", 1, 29)
    dual_min = number("blast", "dual_mode_min_bp", 2, 49)
    dual_max = number("blast", "dual_mode_max_bp", 2, 49)
    if not (short < dual_min <= dual_max):
        raise ValueError("BLAST length boundaries are inconsistent")
    for section, key, low, high in (
        ("locus", "gap_bp", 0, 100000), ("locus", "minimum_candidate_bp", 20, 1000000),
        ("support", "minimum_unique_templates", 1, 1000000), ("support", "minimum_distinct_starts_shotgun", 1, 1000000),
        ("support", "minimum_mapq", 0, 60), ("support", "minimum_base_quality", 0, 93),
        ("specificity", "minimum_delta_bitscore", 0, 1000000), ("specificity", "maximum_qcov_difference_pp", 0, 100),
        ("sample_evidence", "multi_locus_minimum", 1, 1000), ("sample_evidence", "multi_locus_total_bp", 1, 100000000),
        ("sample_evidence", "genome_breadth_1x", 0, 1), ("sample_evidence", "median_covered_depth", 0, 1000000),
        ("sample_evidence", "concentration_window_bp", 1, 1000000),
        ("controls", "provisional_sample_to_negative_ratio", 0.000001, 1000000),
        ("phylogeny", "minimum_aligned_bp", 1, 100000000), ("phylogeny", "minimum_informative_sites", 0, 100000000),
        ("phylogeny", "minimum_references", 1, 100000), ("phylogeny", "maximum_n_fraction", 0, 1),
        ("phylogeny", "maximum_gap_fraction", 0, 1),
    ):
        number(section, key, low, high)
    if data["controls"]["uncontrolled_maximum"] not in {"INCONCLUSIVE", "EXPLORATORY_FRAGMENT", "LOCUS_CANDIDATE", "MULTI_LOCUS_CANDIDATE"}:
        raise ValueError("controls.uncontrolled_maximum is invalid")
    return data


def load_yaml_config(path: str | Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required for evidence_v2.yaml; install pyyaml in the Gene-In environment"
        ) from exc
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return validate_evidence_config(data)


def read_tsv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV has no header: {path}")
        return list(reader)


def _atomic_target(path: Path) -> tuple[Path, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    return Path(tmp_name), os.fdopen(fd, "w", encoding="utf-8", newline="")


def fsync_directory(path: str | Path) -> None:
    """Durably persist directory metadata where the platform supports it."""
    directory = Path(path)
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _flush_and_sync(handle: object) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def write_tsv_atomic(path: str | Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    target = Path(path)
    tmp, handle = _atomic_target(target)
    try:
        with handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({name: row.get(name, "") for name in fieldnames})
            _flush_and_sync(handle)
        os.replace(tmp, target)
        fsync_directory(target.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_json_atomic(path: str | Path, value: object) -> None:
    target = Path(path)
    tmp, handle = _atomic_target(target)
    try:
        with handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            _flush_and_sync(handle)
        os.replace(tmp, target)
        fsync_directory(target.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_text_atomic(path: str | Path, value: str) -> None:
    target = Path(path)
    tmp, handle = _atomic_target(target)
    try:
        with handle:
            handle.write(value)
            _flush_and_sync(handle)
        os.replace(tmp, target)
        fsync_directory(target.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_fasta(path: str | Path) -> dict[str, str]:
    sequences: dict[str, str] = {}
    current: str | None = None
    with Path(path).open("r", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                current = line[1:].split()[0]
                if not current or current in sequences:
                    raise ValueError(f"invalid or duplicate FASTA identifier: {current!r}")
                sequences[current] = ""
            elif current is None:
                raise ValueError("FASTA sequence found before first header")
            else:
                sequences[current] += line.upper()
    return sequences


def merge_intervals(intervals: Iterable[tuple[int, int]], gap: int = 0) -> list[tuple[int, int]]:
    normalized = sorted((min(a, b), max(a, b)) for a, b in intervals)
    merged: list[list[int]] = []
    for start, end in normalized:
        if not merged or start > merged[-1][1] + gap + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def interval_size(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start + 1 for start, end in merge_intervals(intervals))


def format_intervals(intervals: Iterable[tuple[int, int]]) -> str:
    return ";".join(f"{a}-{b}" for a, b in merge_intervals(intervals))


def parse_intervals(value: str) -> list[tuple[int, int]]:
    result = []
    for item in filter(None, value.split(";")):
        left, right = item.split("-", 1)
        result.append((int(left), int(right)))
    return result


def sequence_metrics(sequence: str) -> dict[str, float]:
    seq = sequence.upper()
    if not seq:
        return {"entropy": 0.0, "n_fraction": 0.0, "max_homopolymer_fraction": 0.0}
    counts = Counter(base for base in seq if base in "ACGT")
    valid = sum(counts.values())
    entropy = 0.0
    if valid:
        entropy = -sum((count / valid) * math.log2(count / valid) for count in counts.values())
    longest = 1
    run = 1
    for previous, current in zip(seq, seq[1:]):
        run = run + 1 if current == previous else 1
        longest = max(longest, run)
    return {
        "entropy": entropy,
        "n_fraction": seq.count("N") / len(seq),
        "max_homopolymer_fraction": longest / len(seq),
    }


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(directory: str | Path, *, exclude: set[str] | None = None) -> dict:
    root = Path(directory)
    excluded = {"SUCCESS.json", "artifact_manifest.json"} if exclude is None else exclude
    files = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded or path.name.startswith(".") or path.name.endswith(".tmp"):
            continue
        files[relative] = {"size": path.stat().st_size, "sha256": sha256_file(path)}
    return {"schema_version": "1.0", "files": files}


def validate_artifact_manifest(
    directory: str | Path, manifest: dict, *, exclude: set[str] | None = None
) -> list[str]:
    root = Path(directory)
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        return ["artifact manifest schema is invalid"]
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, dict) or not files:
        return ["artifact manifest is empty or invalid"]
    excluded = {"SUCCESS.json", "artifact_manifest.json"} if exclude is None else exclude
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix() not in excluded
        and not path.name.startswith(".")
        and not path.name.endswith(".tmp")
    }
    declared_files = set(files)
    for relative in sorted(actual_files - declared_files):
        errors.append(f"artifact is missing from manifest: {relative}")
    for relative in sorted(declared_files - actual_files):
        errors.append(f"manifest declares an unexpected artifact: {relative}")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, dict):
            errors.append(f"invalid artifact manifest entry: {relative!r}")
            continue
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            errors.append(f"artifact escapes run directory: {relative}")
            continue
        if not path.is_file():
            errors.append(f"manifest artifact is missing: {relative}")
            continue
        if path.stat().st_size != expected.get("size"):
            errors.append(f"artifact size mismatch: {relative}")
        if sha256_file(path) != expected.get("sha256"):
            errors.append(f"artifact hash mismatch: {relative}")
    return errors


def as_int(value: str | int | float | None, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: str | int | float | None, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
