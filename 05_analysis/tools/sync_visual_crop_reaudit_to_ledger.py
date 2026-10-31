#!/usr/bin/env python3
"""Sync recrop dimensions and disposition fields to the central visual ledger."""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
REAUDIT = ROOT / "data/visual_object_audit/visual_crop_reaudit.tsv"

REPAIRED_PREFIXES = ("repaired_",)


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    rows = read(LEDGER)
    audit = {r["object_id"]: r for r in read(REAUDIT)}
    added = ["crop_reaudit_status", "crop_reaudit_method", "crop_reaudit_at", "crop_reaudit_ocr_engine_used"]
    fields = list(rows[0]) + [x for x in added if x not in rows[0]]
    dimension_updates = 0
    for r in rows:
        a = audit.get(r["object_id"])
        if not a:
            for key in added: r.setdefault(key, "")
            continue
        r["crop_reaudit_status"] = a["disposition"]
        r["crop_reaudit_method"] = a["recovery_candidate_method"] or a["disposition_reason"]
        r["crop_reaudit_at"] = a["reviewed_at"]
        r["crop_reaudit_ocr_engine_used"] = a["ocr_engine_used"]
        if a["disposition"].startswith(REPAIRED_PREFIXES):
            image = ROOT / r["image_path"]
            with Image.open(image) as im:
                r["image_width_px"], r["image_height_px"] = str(im.width), str(im.height)
            r["extraction_confidence"] = "high"
            r["chatgpt_review_stage"] = "recrop_verified_pending_scientific_reinterpretation"
            dimension_updates += 1
    with LEDGER.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print({"ledger_rows": len(rows), "flagged_synced": len(audit), "dimension_updates": dimension_updates})


if __name__ == "__main__":
    main()
