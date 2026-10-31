#!/usr/bin/env python3
"""Re-render verified failed visual crops directly from PDF vector pages."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
HISTORY = ROOT / "data/visual_object_audit/recrop_history"
LOG = ROOT / "data/visual_object_audit/manual_recrop_log.tsv"

# Coordinates are PDF points (72 points/inch), established by direct inspection
# of the complete source page. page is one-based for human-facing consistency.
REPAIRS = {
    "ahn2025machine__0001__figure_1": {
        "pdf": "references/pdf/ahn2025machine.pdf", "page": 3,
        "clip": [145, 72, 452, 322], "dpi": 500,
        "reason": "Previous crop retained only the right exclusion boxes; recover the entire participant-flow diagram and caption.",
    },
    "anon2025improving__0003__figure_2": {
        "pdf": "references/pdf/anon2025improving.pdf", "page": 4,
        "clip": [55, 92, 262, 255], "dpi": 500,
        "reason": "Previous crop began at the caption and omitted the experimental-setup diagram.",
    },
    "anon2026partial__0002__figure_1": {
        "pdf": "references/pdf/anon2026partial.pdf", "page": 10,
        "clip": [132, 232, 352, 463], "dpi": 500,
        "reason": "Previous crop removed the upper and left portions of the correlation heatmap.",
    },
    "anon2026partial__0005__figure_4": {
        "pdf": "references/pdf/anon2026partial.pdf", "page": 12,
        "clip": [80, 96, 408, 372], "dpi": 500,
        "reason": "Previous crop omitted two of the four partial-dependence panels.",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ledger_index():
    with LEDGER.open(encoding="utf-8-sig", newline="") as f:
        return {r["object_id"]: r for r in csv.DictReader(f, delimiter="\t")}


def main():
    index = ledger_index()
    HISTORY.mkdir(parents=True, exist_ok=True)
    records = []
    for object_id, spec in REPAIRS.items():
        row = index[object_id]
        dst = ROOT / row["image_path"]
        pdf = ROOT / spec["pdf"]
        before_sha = sha256(dst)
        backup = HISTORY / f"{object_id}__pre_manual_repair.png"
        if not backup.exists():
            shutil.copy2(dst, backup)
        doc = fitz.open(pdf)
        page = doc[spec["page"] - 1]
        clip = fitz.Rect(*spec["clip"])
        if not page.rect.contains(clip):
            raise ValueError(f"Clip outside page for {object_id}: {clip} vs {page.rect}")
        pix = page.get_pixmap(dpi=spec["dpi"], clip=clip, alpha=False)
        tmp = dst.with_suffix(".manual-recrop.tmp.png")
        pix.save(tmp)
        doc.close()
        tmp.replace(dst)
        records.append({
            "repaired_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "object_id": object_id, "source_pdf": spec["pdf"], "pdf_page": spec["page"],
            "clip_points": json.dumps(spec["clip"]), "render_dpi": spec["dpi"],
            "output_path": row["image_path"], "before_sha256": before_sha,
            "after_sha256": sha256(dst), "backup_path": str(backup.relative_to(ROOT)),
            "reason": spec["reason"], "visual_verification": "completed_direct_image_review",
        })
    with LOG.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    print(json.dumps({"repaired": len(records), "log": str(LOG.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
