"""Shared readers for the canonical per-study JSON source layer."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical_records() -> list[dict]:
    paths = sorted((ROOT / "data/study_json").glob("*.json"))
    if not paths:
        raise RuntimeError("Canonical study JSON is missing; run tools/build_integrated_study_audit.py")
    rows = [json.load(open(path, encoding="utf-8")) for path in paths]
    if len(rows) != 222 or len({r["study_id"] for r in rows}) != 222:
        raise RuntimeError(f"Canonical study JSON failed 222-record uniqueness check: {len(rows)}")
    return rows


def included_extractions() -> list[dict]:
    """Compatibility view used by established analyses.

    Values come from the losslessly retained legacy snapshot inside canonical
    JSON, never by reopening ``data/extraction/<key>.json``.
    """
    if os.environ.get("KNHANES_CANONICAL_BOOTSTRAP") == "1":
        refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json", encoding="utf-8"))}
        rows = [json.load(open(path, encoding="utf-8")) for path in sorted((ROOT / "data/extraction").glob("*.json"))]
        return [r for r in rows if refs.get(r["key"], {}).get("verdict") == "INCLUDE" and r.get("source") == "full_text"]
    return [r["legacy_extraction_snapshot"] for r in canonical_records()]


def included_extraction_index() -> dict[str, dict]:
    return {r["key"]: r for r in included_extractions()}


def appendix15_rows() -> list[dict]:
    rows = [r["appendix15_fields"] for r in canonical_records()]
    return sorted(rows, key=lambda x: int(x["record_no"]))
