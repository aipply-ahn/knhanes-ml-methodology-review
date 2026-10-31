#!/usr/bin/env python3
"""Apply reviewed decisions to a NEW review workbook, preserving its source.

Usage: python tools/additional_review_integrate.py BASELINE.xlsx DECISIONS.json OUTPUT.xlsx
This never changes the submitted workbook, shared overrides, or shared issue ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrate(baseline, decisions, output):
    if output.exists():
        raise ValueError(f"Refusing to overwrite a version: {output}")
    d = json.loads(decisions.read_text(encoding="utf-8"))
    before = sha(baseline)
    if before != d["baseline_sha256"]:
        raise ValueError("Baseline checksum differs from the reviewed decisions")
    wb = load_workbook(baseline)
    ws = wb.active
    headers = {cell.value: cell.column for cell in ws[1]}
    rows = {ws.cell(i, 1).value: i for i in range(2, ws.max_row + 1)}
    if len(headers) != ws.max_column or len(rows) != ws.max_row - 1:
        raise ValueError("Duplicate headers or study IDs")
    # Blue marks changes in this revision, not the union of all past changes.
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if cell.fill.fill_type == "solid" and cell.fill.fgColor.type == "rgb" and cell.fill.fgColor.rgb[-6:] == "DCEBFA":
                cell.fill = PatternFill(fill_type=None)
    seen = set()
    changes = []
    for entry in d.get("corrections", []):
        key = (entry["study_id"], entry["column"])
        if key in seen:
            raise ValueError(f"Duplicate correction: {key}")
        seen.add(key)
        cell = ws.cell(rows[key[0]], headers[key[1]])
        if type(cell.value) != type(entry["old_value"]) or cell.value != entry["old_value"]:
            raise ValueError(f"Stale correction: {key}")
        if not entry["reason"] or not entry["evidence"]:
            raise ValueError(f"Missing evidence or rationale: {key}")
        if cell.value == entry["new_value"]:
            raise ValueError(f"No-op correction: {key}")
        cell.value = entry["new_value"]
        cell.fill = PatternFill("solid", fgColor="DCEBFA")
        previous = str(entry["old_value"])
        if len(previous) > 4000:
            previous = previous[:4000] + "… [complete previous value in the version manifest]"
        note = f"Integrated correction\nValue before this correction: {previous}\n{entry['reason']}\nEvidence: {entry['evidence']}"
        if entry.get("source_provenance"):
            note += "\nOriginal locked source extract (provenance, not a new source-version confirmation):\n" + entry["source_provenance"]
        if len(note) > 30000:
            note = note[:29500] + "\n[Full correction/source extract preserved in this version's manifest.]"
        cell.comment = Comment(note, "integration", width=500, height=220)
        changes.append(entry)
    issue_seen = set()
    for entry in d.get("issues", []):
        key = (entry["study_id"], entry["column"])
        if key in issue_seen:
            raise ValueError(f"Duplicate issue decision: {key}")
        issue_seen.add(key)
        if entry["status"] not in {"resolved", "accepted_source_uncertainty", "unresolved"}:
            raise ValueError(f"Unknown issue status: {key}")
        if not entry["reason"] or not entry["evidence"]:
            raise ValueError(f"Unsupported issue disposition: {key}")
        cell = ws.cell(rows[key[0]], headers[key[1]])
        if entry["status"] == "unresolved":
            cell.fill = PatternFill("solid", fgColor="FFF2A8")
        elif key not in seen:
            cell.fill = PatternFill(fill_type=None)
        suffix = f"\nIssue: {entry['status']}\n{entry['reason']}\nEvidence: {entry['evidence']}"
        prior = cell.comment.text.split("\nIssue:", 1)[0] if cell.comment and cell.comment.author == "integration" else ""
        cell.comment = Comment(prior + suffix, "integration", width=500, height=220)
    for name, explanation in d.get("header_comments", {}).items():
        cell = ws.cell(1, headers[name])
        cell.comment = Comment(explanation, "integration", width=600, height=320)
    renames = d.get("header_renames", {})
    if any(old not in headers or not new for old, new in renames.items()):
        raise ValueError("Header rename must identify an existing column and a nonempty new label")
    final_names = [renames.get(c.value, c.value) for c in ws[1]]
    if len(set(final_names)) != len(final_names):
        raise ValueError("Header rename would produce duplicate columns")
    for old, new in renames.items():
        ws.cell(1, headers[old]).value = new
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    wb.close()
    if sha(baseline) != before:
        raise RuntimeError("Baseline changed concurrently during integration; output requires review")
    manifest = {"integrated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "integrator_sha256": sha(Path(__file__)), "decisions_sha256": sha(decisions),
                "baseline": str(baseline), "baseline_sha256": before, "output": str(output),
                "output_sha256": sha(output), "correction_count": len(changes), "decisions": d}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = integrate(args.baseline, args.decisions, args.output)
    print(json.dumps({k: result[k] for k in ("output", "output_sha256", "correction_count")}, ensure_ascii=False))
