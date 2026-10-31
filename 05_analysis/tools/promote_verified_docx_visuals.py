#!/usr/bin/env python3
"""Promote directly matched native DOCX figures; preserve prior crops."""
from __future__ import annotations

import csv
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
HISTORY = ROOT / "data/visual_object_audit/recrop_history"
LOG = ROOT / "data/visual_object_audit/promoted_docx_native_log.tsv"
BASE = ROOT / "data/visual_object_audit/docx_native_candidates"

MATCHES = {
    "beak2024driven__0010__figure_S5": ["beak2024driven/image6.png"],
    "beak2024driven__0016__figure_S1": ["beak2024driven/image1.png"],
    "beak2024driven__0029__figure_S8": ["beak2024driven/image9.png"],
    "beak2024driven__0030__figure_S9": ["beak2024driven/image10.png"],
    "costa2026integrated__0023__figure_S4": ["costa2026integrated/image4.jpg"],
    "lee2024machine__0012__figure_S2": ["lee2024machine/image2.png"],
}

# Figure S2 is stored as two separate native panels in document order.
MULTIPANEL = {
    "beak2024driven__0007__figure_media2": ["beak2024driven/image2.png", "beak2024driven/image3.png"],
}


def read_ledger():
    with LEDGER.open(encoding="utf-8-sig", newline="") as f:
        return {r["object_id"]: r for r in csv.DictReader(f, delimiter="\t")}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(paths, dst):
    ims = [Image.open(BASE / p).convert("RGB") for p in paths]
    width = max(im.width for im in ims)
    gap = 24
    canvas = Image.new("RGB", (width, sum(im.height for im in ims) + gap*(len(ims)-1)), "white")
    y = 0
    for im in ims:
        canvas.paste(im, ((width-im.width)//2, y)); y += im.height + gap
    canvas.save(dst)


def main():
    ledger = read_ledger(); HISTORY.mkdir(parents=True, exist_ok=True)
    records = []
    for oid, rels in {**MATCHES, **MULTIPANEL}.items():
        dst = ROOT / ledger[oid]["image_path"]
        backup = HISTORY / f"{oid}__pre_docx_native_repair.png"
        if not backup.exists(): shutil.copy2(dst, backup)
        before = digest(dst)
        tmp = dst.with_suffix(".docx-native.tmp.png")
        if oid in MULTIPANEL:
            compose(rels, tmp)
            method = "native_ooxml_multipanel_stitch"
        else:
            with Image.open(BASE / rels[0]) as im:
                im.convert("RGB").save(tmp)
            method = "native_ooxml_media"
        tmp.replace(dst)
        records.append({
            "promoted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "object_id": oid, "method": method,
            "native_sources": ";".join(str((BASE/p).relative_to(ROOT)) for p in rels),
            "output_path": ledger[oid]["image_path"], "before_sha256": before,
            "after_sha256": digest(dst), "backup_path": str(backup.relative_to(ROOT)),
            "visual_verification": "completed_direct_image_review",
        })
    with LOG.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    print({"promoted_docx": len(records), "log": str(LOG.relative_to(ROOT))})


if __name__ == "__main__":
    main()
