#!/usr/bin/env python3
"""Create an object-level disposition ledger for every flagged visual."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"
CANDIDATES = ROOT / "data/visual_object_audit/recrop_candidates/candidate_manifest.tsv"
TABLES = ROOT / "data/visual_object_audit/table_recovery_pages/table_recovery_manifest.tsv"
DOCX_LOG = ROOT / "data/visual_object_audit/promoted_docx_native_log.tsv"
VECTOR = ROOT / "data/visual_object_audit/vector_recrop_candidates/vector_candidate_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/visual_crop_reaudit.tsv"

MANUAL_REPAIRS = {
    "ahn2025machine__0001__figure_1",
    "anon2025improving__0003__figure_2",
    "anon2026partial__0002__figure_1",
    "anon2026partial__0005__figure_4",
}


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    flagged = read_tsv(MANUAL)
    cand = {r["object_id"]: r for r in read_tsv(CANDIDATES)}
    tables = {r["object_id"]: r for r in read_tsv(TABLES)} if TABLES.exists() else {}
    docx_done = {r["object_id"] for r in read_tsv(DOCX_LOG)} if DOCX_LOG.exists() else set()
    vectors = {r["object_id"]: r for r in read_tsv(VECTOR)} if VECTOR.exists() else {}
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    out = []
    for r in flagged:
        oid = r["object_id"]
        c = cand.get(oid)
        t = tables.get(oid)
        v = vectors.get(oid)
        fmt = Path(r["source_file"]).suffix.lower().lstrip(".") or "unknown"
        if oid in MANUAL_REPAIRS:
            disposition, reason = "repaired_manual_500dpi", "direct source-page crop verified complete"
        elif c and c["verification"] == "completed_direct_review_promoted":
            disposition, reason = "repaired_verified_geometry_400dpi", "complete embedded figure promoted after direct review"
        elif oid in docx_done:
            disposition, reason = "repaired_native_docx_media", "native OOXML media matched to caption after direct review"
        elif v and v["verification"] == "completed_direct_review_promoted":
            disposition, reason = "repaired_verified_vector_450dpi", "vector geometry candidate promoted after direct image review"
        elif c and c["verification"] == "direct_review_rejected_incomplete_split_artwork":
            disposition, reason = "manual_recrop_required_split_artwork", "automatic candidate omitted part of a multi-block figure"
        elif c and c["method"] == "vector_safe_region":
            disposition, reason = "manual_recrop_required_vector", "vector artwork cannot be safely bounded by embedded-image geometry"
        elif c and c["method"] == "caption_not_found_full_page":
            disposition, reason = "source_locator_required", "caption not found in available PDF; full-page recovery retained"
        elif t and t["caption_found"] == "Y":
            disposition, reason = "table_source_page_recovered_350dpi", "caption-located full-width source page retained without clipping"
        elif t:
            disposition, reason = "table_source_page_recovered_locator_uncertain", "full-width ledger page retained; caption was not located"
        elif fmt != "pdf":
            disposition, reason = "non_pdf_source_manual_review_required", f"source format {fmt} requires format-specific recovery"
        else:
            disposition, reason = "manual_source_review_required", "no safe automatic recovery path"
        out.append({
            "reviewed_at": stamp,
            "object_id": oid,
            "study_key": r["study_key"],
            "object_type": r["object_type"],
            "object_label": r["object_label"],
            "source_file": r["source_file"],
            "source_format": fmt,
            "initial_vision_status": r.get("chatgpt_vision_status", ""),
            "initial_manual_review_reason": r.get("manual_review_reason", ""),
            "contact_sheet_direct_review": "completed_chatgpt_image_model",
            "recovery_candidate_method": c["method"] if c else "not_generated",
            "recovery_candidate_path": c["candidate_path"] if c else "",
            "vector_candidate_path": v["candidate_path"] if v else "",
            "table_recovery_page_path": t["page_image_path"] if t else "",
            "candidate_verification": c["verification"] if c else "",
            "disposition": disposition,
            "disposition_reason": reason,
            "ocr_engine_used": "N",
        })
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(out)
    print({"objects": len(out), "dispositions": dict(Counter(r["disposition"] for r in out)),
           "output": str(OUT.relative_to(ROOT))})


if __name__ == "__main__":
    main()
