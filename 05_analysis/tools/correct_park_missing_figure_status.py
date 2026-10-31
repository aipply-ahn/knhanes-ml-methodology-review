#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OID = "park2024predicting__0002__figure_1"
STAMP = "2026-09-14T03:35:00+09:00"

for rel in (
    "data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv",
    "data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv",
    "data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv",
    "data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv",
):
    p = ROOT / rel
    with p.open(encoding="utf-8-sig", newline="") as h:
        rd = csv.DictReader(h, delimiter="\t")
        fields = rd.fieldnames or []
        rows = list(rd)
    for x in rows:
        if x.get("object_id") != OID:
            continue
        if "refreshed_at" in x:
            x["refreshed_at"] = STAMP
        if "crop_recovery_status" in x:
            x["crop_recovery_status"] = "source_locator_required"
        if "scientific_interpretation_status" in x:
            x["scientific_interpretation_status"] = "SOURCE_RECOVERY_REQUIRED"
        if "remaining_uncertainty" in x:
            x["remaining_uncertainty"] = "The official PDF and recovered official submission DOCX contain the Figure 1 legend but no Figure 1 artwork."
        if "required_followup" in x:
            x["required_followup"] = "Recover the separate Figure 1 submission artwork from an author- or submission-system-accessible source."
    with p.open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

ap = ROOT / f"data/visual_object_audit/vision_annotations/{OID}.json"
d = json.loads(ap.read_text())
d.update({
    "status": "source_recovery_required",
    "uncertainty": "Official PDF and official submission DOCX omit the actual Figure 1 artwork.",
    "manual_review_reason": "Separate submission artwork is not publicly exposed; this is not a crop-resolution failure.",
})
ap.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
