#!/usr/bin/env python3
"""Refresh the human-readable visual-review bundle after crop recovery.

No OCR engine is used. Existing ChatGPT image-model transcriptions and
interpretations are retained verbatim, while crop-recovery and scientific
reinterpretation states are represented separately.
"""
from __future__ import annotations

import csv
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/visual_manual_review"
MANIFEST = BASE / "manual_review_manifest.tsv"
REAUDIT = ROOT / "data/visual_object_audit/visual_crop_reaudit.tsv"
OUT = BASE / "latest_after_recrop"

RECOVERED = {
    "repaired_manual_500dpi",
    "repaired_verified_geometry_400dpi",
    "repaired_verified_vector_450dpi",
    "repaired_native_docx_media",
    "table_source_page_recovered_350dpi",
}


def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def choose_latest(a: dict, original: str) -> tuple[str, str]:
    disposition = a["disposition"]
    if disposition.startswith("table_source_page_recovered") and a.get("table_recovery_page_path"):
        return a["table_recovery_page_path"], "full_source_page"
    if disposition in RECOVERED:
        return original, "recovered_canonical_crop"
    for field, kind in (("vector_candidate_path", "vector_candidate"), ("recovery_candidate_path", "recovery_candidate"), ("table_recovery_page_path", "source_page")):
        if a.get(field):
            return a[field], kind
    return original, "current_crop"


def main():
    rows = read(MANIFEST); audit = {r["object_id"]: r for r in read(REAUDIT)}
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "decoded_recovered").mkdir(parents=True)
    (OUT / "unresolved").mkdir(parents=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    latest = []
    for r in rows:
        a = audit[r["object_id"]]
        recovered = a["disposition"] in RECOVERED
        source_rel, source_kind = choose_latest(a, r["original_image"])
        source = ROOT / source_rel
        bucket = "decoded_recovered" if recovered else "unresolved"
        target = OUT / bucket / r["object_type"] / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, target)
            latest_image = str(target.relative_to(ROOT))
        else:
            latest_image = source_rel
        reread_complete = r.get("reviewer_decision") == "complete_after_repaired_crop_chatgpt_image_reread"
        if reread_complete:
            decode_status = "COMPLETE_AFTER_RECROP_CHATGPT_IMAGE_REREAD"
            scientific_status = "COMPLETE"
        elif recovered:
            decode_status = "DECODED_TEXT_AVAILABLE_RECOVERED_IMAGE"
            scientific_status = "REINTERPRETATION_REQUIRED_FOR_NEWLY_EXPOSED_CONTENT" if (r["uncertainty"] or r["manual_review_reason"]) else "EXISTING_INTERPRETATION_RETAINED"
        else:
            decode_status = "PARTIAL_DECODE_RETAINED_SOURCE_UNRESOLVED"
            scientific_status = "SOURCE_RECOVERY_REQUIRED"
        latest.append({
            "refreshed_at": stamp, "study_key": r["study_key"], "object_id": r["object_id"], "object_type": r["object_type"],
            "object_label": r["object_label"], "source_scope": r["source_scope"], "page_or_sheet": r["page_or_sheet"],
            "caption": r["caption"], "decode_status": decode_status, "crop_recovery_status": a["disposition"],
            "scientific_interpretation_status": scientific_status, "chatgpt_image_transcription": r["current_visible_text"],
            "chatgpt_image_interpretation": r["current_interpretation"], "remaining_uncertainty": r["uncertainty"],
            "required_followup": r["manual_review_reason"], "latest_review_image": latest_image, "latest_image_kind": source_kind,
            "canonical_image": r["original_image"], "source_file": r["source_file"], "ocr_engine_used": "N",
        })
    fields = list(latest[0])
    with (OUT / "LATEST_VISUAL_REVIEW.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(latest)
    for bucket in ("decoded_recovered", "unresolved"):
        subset = [r for r in latest if ("decoded_recovered" if r["crop_recovery_status"] in RECOVERED else "unresolved") == bucket]
        with (OUT / f"{bucket.upper()}_INDEX.tsv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(subset)
    counts = Counter(r["decode_status"] for r in latest)
    readme = f"""# Latest visual manual-review bundle after recrop

Updated: {stamp}

- Total originally flagged objects: {len(latest)}
- Recovered high-resolution crop/source-page: {sum(r['crop_recovery_status'] in RECOVERED for r in latest)}
- Completed direct post-recrop ChatGPT image reread: {sum(r['scientific_interpretation_status'] == 'COMPLETE' for r in latest)}
- Source/crop still unresolved: {sum(r['crop_recovery_status'] not in RECOVERED for r in latest)}
- OCR engines used: 0

`LATEST_VISUAL_REVIEW.tsv` is the current object-level index. The transcription and interpretation columns preserve the existing ChatGPT image-model reading. `crop_recovery_status` describes image recovery only. `scientific_interpretation_status` explicitly identifies objects whose newly exposed rows, panels, or labels still need a fresh scientific reread; recovery alone is never treated as completed reinterpretation.

Files are separated into `decoded_recovered/` and `unresolved/`. The latter remains the user-facing manual-review queue.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print({"objects": len(latest), "recovered_with_decode": sum(r["crop_recovery_status"] in RECOVERED for r in latest),
           "unresolved": sum(r["crop_recovery_status"] not in RECOVERED for r in latest), "decode_status": dict(counts), "ocr_engine_used": False})


if __name__ == "__main__":
    main()
