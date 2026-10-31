#!/usr/bin/env python3
"""Check two independent, explicit approvals for the exact current review bytes."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


def check(workbook, signoffs):
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    errors, identities = [], []
    if len(signoffs) != 2:
        errors.append("Exactly two independent signoffs are required")
    for path in signoffs:
        if not path.exists():
            errors.append(f"Missing signoff: {path}")
            continue
        s = json.loads(path.read_text(encoding="utf-8"))
        who = s.get("reviewer_id")
        if not who:
            errors.append(f"Missing reviewer identity: {path}")
        identities.append(who)
        if s.get("input_sha256") != digest:
            errors.append(f"Signoff refers to different workbook bytes: {path}")
        if s.get("verdict") != "NO_ISSUES":
            errors.append(f"Reviewer has not approved: {path}")
        if s.get("required_scope_complete") is not True:
            errors.append(f"Required scope is incomplete: {path}")
        for field in ("unresolved_errors", "unverified_required_items"):
            if s.get(field) != []:
                errors.append(f"{field} is nonempty or unspecified: {path}")
        if not s.get("scope"):
            errors.append(f"Review scope is unspecified: {path}")
        try:
            if datetime.fromisoformat(s["completed_at"]).tzinfo is None:
                raise ValueError("Review time lacks timezone")
        except (KeyError, ValueError, TypeError):
            errors.append(f"Invalid completion time: {path}")
    if len(set(identities)) != len(identities):
        errors.append("Reviewer identities are not distinct")
    wb = load_workbook(workbook)
    pending = [f"{ws.title}!{c.coordinate}" for ws in wb for row in ws for c in row
               if c.comment and "Issue: unresolved" in c.comment.text]
    wb.close()
    if pending:
        errors.append(f"Workbook still contains {len(pending)} unresolved issue annotations")
    return {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "approved": not errors, "workbook": str(workbook), "workbook_sha256": digest,
            "reviewers": identities, "unresolved_annotations": pending, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("signoffs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.workbook, args.signoffs)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["approved"] else 1)
