#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OID = "dashdondov2026assessing__0012__figure_4"
STAMP = "2026-09-14T04:05:00+09:00"
UNCERTAINTY = "The supplied article-in-press PDF contains the complete Figure 4 caption and discussion, but the Figure 4 artwork is absent between the caption and the following page."
FOLLOWUP = "Recover the separate Figure 4 artwork from the publisher production package, final version, or author-supplied source."

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
            x["remaining_uncertainty"] = UNCERTAINTY
        if "required_followup" in x:
            x["required_followup"] = FOLLOWUP
    with p.open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

ap = ROOT / f"data/visual_object_audit/vision_annotations/{OID}.json"
d = json.loads(ap.read_text())
d.update({
    "status": "source_recovery_required",
    "uncertainty": UNCERTAINTY,
    "manual_review_reason": "The production PDF omits the actual artwork; this is not a crop-resolution failure.",
})
ap.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
