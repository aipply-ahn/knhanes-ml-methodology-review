#!/usr/bin/env python3
"""Build a browsable, non-destructive bundle for uncertain/unreadable visual objects."""
from __future__ import annotations

import csv
import html
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
OUT = ROOT / "data/visual_manual_review"
PANEL_RE = re.compile(r"\([A-Za-z]\)|\bpanels?\b|\b(?:fig(?:ure)?|table)\s*\w+\s*[A-D](?:\b|[,:])", re.I)


def read_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def materialise(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    shutil.copy2(src, dst)


def main() -> None:
    rows = [r for r in read_rows() if r.get("chatgpt_vision_status") in {"uncertain", "unreadable"}]
    # Remove only legacy top-level review copies created by the previous bundle
    # layout; canonical images and nested type folders are never targeted.
    for status in ("uncertain", "unreadable"):
        status_dir = OUT / status
        if status_dir.exists():
            for old in status_dir.iterdir():
                if old.is_file() or old.is_symlink():
                    old.unlink()
    manifest_rows = []
    cards = []
    for r in rows:
        status = r["chatgpt_vision_status"]
        src = ROOT / r["image_path"]
        suffix = src.suffix.lower() or ".png"
        safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in r["object_id"])
        rel = Path(status) / r["object_type"] / f"{safe_id}{suffix}"
        if src.exists():
            materialise(src, OUT / rel)
        item = {
            "review_status": status,
            "study_key": r["study_key"],
            "object_id": r["object_id"],
            "object_type": r["object_type"],
            "source_scope": r["source_scope"],
            "object_label": r["object_label"],
            "page_or_sheet": r["page_or_sheet"],
            "caption": r["caption"],
            "current_visible_text": r["chatgpt_visible_text"],
            "current_interpretation": r["chatgpt_interpretation"],
            "uncertainty": r["chatgpt_uncertainty"],
            "manual_review_reason": r["manual_review_reason"],
            "potential_multipanel": "Y" if PANEL_RE.search(" ".join((r["object_label"], r["caption"]))) else "N",
            "review_image": rel.as_posix() if src.exists() else "MISSING",
            "original_image": r["image_path"],
            "source_file": r["source_path"],
            "source_sha256": r["source_sha256"],
            "reviewer_decision": "",
            "reviewer_transcription": "",
            "reviewer_notes": "",
        }
        manifest_rows.append(item)
        cards.append(
            f'<article class="{status}"><h2>{html.escape(r["study_key"])} — {html.escape(r["object_label"])}</h2>'
            f'<p><b>{html.escape(status.upper())}</b> · {html.escape(r["object_type"])} · page/sheet {html.escape(r["page_or_sheet"])}</p>'
            f'<a href="{html.escape(rel.as_posix())}"><img loading="lazy" src="{html.escape(rel.as_posix())}"></a>'
            f'<p><b>Caption:</b> {html.escape(r["caption"])}</p>'
            f'<p><b>Why review:</b> {html.escape(r["manual_review_reason"] or r["chatgpt_uncertainty"])}</p>'
            f'<p><b>Original source:</b> <code>{html.escape(r["source_path"])}</code></p></article>'
        )

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "manual_review_manifest.tsv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(manifest_rows)
    panel_rows = [r for r in manifest_rows if r["potential_multipanel"] == "Y"]
    with (OUT / "potential_multipanel_manifest.tsv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(panel_rows)
    counts = Counter((r["review_status"], r["object_type"]) for r in manifest_rows)
    readme = f"""# Visual manual-review bundle

This folder contains independent review copies from the complete visual-object ledger.
The canonical source images remain at the paths recorded in the manifest. Record review
decisions in `manual_review_manifest.tsv` and merge them through an adjudication step.

- Unreadable: {sum(k[0] == 'unreadable' and v for k, v in counts.items())} ({counts[('unreadable','figure')]} figures; {counts[('unreadable','table')]} tables)
- Uncertain: {sum(k[0] == 'uncertain' and v for k, v in counts.items())} ({counts[('uncertain','figure')]} figures; {counts[('uncertain','table')]} tables)
- Total manual-review queue: {len(manifest_rows)}
- Potential multi-panel containers in this queue (caption/label screen): {len(panel_rows)}

The current audit image is one rendered file per numbered figure/table container. Multi-panel
figures were interpreted jointly within that container; panels were not consistently cropped
to separate files. Protocol v1.1 requires a panel manifest and separate panel crops whenever
an individual panel contains distinct evidence or cannot be reliably reviewed at container scale.

Open `index.html` for a thumbnail catalogue. The TSV gives the original report path, page,
caption, current interpretation, uncertainty, and blank columns for the human decision.
Unreadable and uncertain copies are further separated into `figure` and `table` subfolders.
`potential_multipanel_manifest.tsv` is a conservative caption/label screen and still requires
visual confirmation; it must not be treated as the final panel count.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    page = """<!doctype html><meta charset="utf-8"><title>KNHANES visual manual review</title>
<style>body{font-family:sans-serif;max-width:1500px;margin:auto}article{border:2px solid #bbb;margin:1rem;padding:1rem}article.unreadable{border-color:#b2182b}article.uncertain{border-color:#ef8a62}img{max-width:100%;max-height:850px;background:#eee}code{overflow-wrap:anywhere}</style>
<h1>KNHANES visual manual-review queue</h1><p>Red: unreadable; orange: uncertain. Click an image for full resolution.</p>""" + "\n".join(cards)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(dict(Counter(r["review_status"] for r in manifest_rows)))


if __name__ == "__main__":
    main()
