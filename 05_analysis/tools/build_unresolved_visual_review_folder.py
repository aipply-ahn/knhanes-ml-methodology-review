#!/usr/bin/env python3
"""Collect every unresolved post-recrop object for human review."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
REAUDIT = ROOT / "data/visual_object_audit/visual_crop_reaudit.tsv"
OUT = ROOT / "data/visual_manual_review/unresolved_after_recrop"
INDEX = OUT / "UNRESOLVED_VISUALS.tsv"

UNRESOLVED = {
    "manual_recrop_required_vector",
    "source_locator_required",
    "non_pdf_source_manual_review_required",
    "manual_source_review_required",
    "table_source_page_recovered_locator_uncertain",
}


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def copy_if(path_text, dst_dir, prefix):
    if not path_text: return ""
    src = ROOT / path_text
    if not src.exists(): return ""
    dst = dst_dir / f"{prefix}__{src.name}"
    shutil.copy2(src, dst)
    return str(dst.relative_to(ROOT))


def main():
    ledger = {r["object_id"]: r for r in read(LEDGER)}
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for a in read(REAUDIT):
        if a["disposition"] not in UNRESOLVED: continue
        oid = a["object_id"]
        folder = OUT / a["disposition"] / a["study_key"] / oid
        folder.mkdir(parents=True, exist_ok=True)
        current = copy_if(ledger[oid]["image_path"], folder, "current")
        candidate = copy_if(a["recovery_candidate_path"], folder, "candidate")
        vector_candidate = copy_if(a.get("vector_candidate_path", ""), folder, "vector_candidate")
        table_page = copy_if(a["table_recovery_page_path"], folder, "source_page")
        records.append({**a, "review_current_copy": current,
                        "review_candidate_copy": candidate,
                        "review_vector_candidate_copy": vector_candidate,
                        "review_source_page_copy": table_page})
    with INDEX.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    print({"unresolved": len(records), "output": str(OUT.relative_to(ROOT)),
           "manifest": str(INDEX.relative_to(ROOT))})


if __name__ == "__main__":
    main()
