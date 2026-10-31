#!/usr/bin/env python3
"""Promote directly reviewed, complete PDF figure candidates.

Only embedded-image-geometry candidates are eligible. Known split-image or
manually repaired objects are excluded. Existing canonical crops are retained
in recrop_history before replacement. No OCR is used.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
CANDIDATES = ROOT / "data/visual_object_audit/recrop_candidates/candidate_manifest.tsv"
HISTORY = ROOT / "data/visual_object_audit/recrop_history"
LOG = ROOT / "data/visual_object_audit/promoted_recrop_log.tsv"

MANUAL_REPAIRS = {
    "ahn2025machine__0001__figure_1",
    "anon2025improving__0003__figure_2",
    "anon2026partial__0002__figure_1",
    "anon2026partial__0005__figure_4",
}

# Direct review showed that the PDF stores this artwork in separate blocks and
# the geometry candidate does not contain the complete multi-panel figure.
DIRECT_REVIEW_REJECTS = {
    "beak2024driven__0007__figure_4": "split image blocks; candidate omits a panel",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_tsv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    ledger = {r["object_id"]: r for r in read_tsv(LEDGER)}
    rows = read_tsv(CANDIDATES)
    HISTORY.mkdir(parents=True, exist_ok=True)
    records = []
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    for row in rows:
        oid = row["object_id"]
        if row["method"] != "embedded_image_geometry":
            row["verification"] = "direct_review_completed_manual_recrop_needed"
            continue
        if oid in MANUAL_REPAIRS:
            row["verification"] = "direct_review_completed_manual_500dpi_preferred"
            continue
        if oid in DIRECT_REVIEW_REJECTS:
            row["verification"] = "direct_review_rejected_incomplete_split_artwork"
            continue
        if oid not in ledger:
            row["verification"] = "not_promoted_missing_ledger_object"
            continue

        src = ROOT / row["candidate_path"]
        dst = ROOT / ledger[oid]["image_path"]
        if not src.exists() or not dst.exists():
            row["verification"] = "not_promoted_missing_file"
            continue
        before = sha256(dst)
        backup = HISTORY / f"{oid}__pre_verified_geometry_repair.png"
        if not backup.exists():
            shutil.copy2(dst, backup)
        tmp = dst.with_suffix(".verified-recrop.tmp.png")
        shutil.copy2(src, tmp)
        tmp.replace(dst)
        after = sha256(dst)
        row["verification"] = "completed_direct_review_promoted"
        records.append({
            "promoted_at": now,
            "object_id": oid,
            "method": row["method"],
            "source_pdf": row["source_pdf"],
            "pdf_page": row["located_pdf_page"],
            "clip_points": row["clip_points"],
            "render_dpi": row["dpi"],
            "output_path": ledger[oid]["image_path"],
            "before_sha256": before,
            "after_sha256": after,
            "backup_path": str(backup.relative_to(ROOT)),
            "visual_verification": "completed_direct_image_review",
        })

    fields = list(rows[0])
    with CANDIDATES.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    if records:
        with LOG.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
            w.writeheader(); w.writerows(records)
    print({"promoted": len(records), "candidate_manifest": str(CANDIDATES.relative_to(ROOT)),
           "log": str(LOG.relative_to(ROOT))})


if __name__ == "__main__":
    main()
