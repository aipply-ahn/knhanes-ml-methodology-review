#!/usr/bin/env python3
"""Build a non-mutating, evidence-linked merge plan for two independent reviews.

Usage: python tools/additional_review_merge_plan.py CYCLE_DIRECTORY BASELINE.xlsx
The plan is a review aid, never authorization to apply a correction automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


def proposals(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload["corrections"]
    if not isinstance(payload, list):
        raise ValueError(f"Expected a corrections list: {path}")
    result = {}
    for item in payload:
        for field in ("study_id", "column", "old_value", "new_value", "evidence", "reason"):
            if field not in item:
                raise ValueError(f"Missing {field} in {path}: {item}")
        key = (item["study_id"], item["column"])
        if key in result:
            raise ValueError(f"Duplicate proposal in {path}: {key}")
        if not item["evidence"] or not item["reason"]:
            raise ValueError(f"Unsupported proposal in {path}: {key}")
        result[key] = item
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cycle", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--effective-a", type=Path, help="Explicit addendum-aware A correction bundle; original frozen review remains unchanged")
    parser.add_argument("--effective-b", type=Path, help="Explicit addendum-aware B correction bundle; original frozen review remains unchanged")
    args = parser.parse_args()
    wb = load_workbook(args.baseline, read_only=True)
    values = list(wb.active.values)
    wb.close()
    headers = values[0]
    if len(set(headers)) != len(headers):
        raise ValueError("Duplicate baseline headers")
    rows = {row[0]: dict(zip(headers, row)) for row in values[1:]}
    if len(rows) != len(values) - 1:
        raise ValueError("Duplicate baseline study IDs")
    path_a = args.effective_a or args.cycle / "reviewer_a/corrections.json"
    path_b = args.effective_b or args.cycle / "reviewer_b/corrections.json"
    a = proposals(path_a)
    b = proposals(path_b)
    issue_reviews = []
    for reviewer in ("reviewer_a", "reviewer_b"):
        path = args.cycle / reviewer / "ambiguities.json"
        items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        issue_reviews.append({(x["study_id"], x["column"]): x for x in items})
    plan = []
    for sid, column in sorted(set(a) | set(b)):
        left, right = a.get((sid, column)), b.get((sid, column))
        cell = rows.get(sid, {})
        status = "agreed" if left and right and left["new_value"] == right["new_value"] else "disputed" if left and right else "single_reviewer"
        if column not in cell:
            status = "invalid_cell"
        elif any(p and (type(p["old_value"]) != type(cell[column]) or p["old_value"] != cell[column]) for p in (left, right)):
            status = "stale_old_value"
        ia, ib = (review.get((sid, column)) for review in issue_reviews)
        if status not in {"invalid_cell", "stale_old_value"} and ia and ib:
            va = left['new_value'] if args.effective_a and left else ia.get("proposed_value", left["new_value"] if left else ia.get("original_value", cell.get(column)))
            vb = right['new_value'] if args.effective_b and right else ib.get("proposed_value", right["new_value"] if right else ib.get("original_value", cell.get(column)))
            if va != vb:
                status = "disputed" if left and right else "disputed_retention"
        plan.append({"study_id": sid, "column": column, "baseline_value": cell.get(column),
                     "status": status, "reviewer_a": left, "reviewer_b": right,
                     "issue_review_a": ia, "issue_review_b": ib})
    comparisons = []
    for sid, column in sorted(set(issue_reviews[0]) | set(issue_reviews[1])):
        ia, ib = (review.get((sid, column)) for review in issue_reviews)
        comparisons.append({"study_id": sid, "column": column, "reviewer_a": ia, "reviewer_b": ib})
    result = {"baseline": str(args.baseline), "baseline_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              "proposal_inputs": {"reviewer_a": str(path_a), "reviewer_b": str(path_b)},
              "addendum_precedence": "Explicit effective correction bundles supersede original ambiguity proposed values for their own corrected cells; original issue readings are retained for audit.",
              "notice": "No changes applied. Evidence and current shared-file state require integrator review.",
              "cells": plan, "issue_comparisons": comparisons}
    (args.cycle / "MERGE_PLAN.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {status: sum(p["status"] == status for p in plan) for status in sorted({p["status"] for p in plan})}
    print(json.dumps({"baseline_sha256": result["baseline_sha256"], "proposal_cells": len(plan), "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
