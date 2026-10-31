#!/usr/bin/env python3
"""Retry uncertain/unreadable visual objects using original-resolution images.

For unreadable PDF objects, the complete source page is added beside the original
crop.  Interpretation still comes exclusively from ChatGPT vision; no OCR engine
is used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
OBJECTS = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.tsv"
ANN = ROOT / "data" / "visual_object_audit" / "vision_annotations"
BATCH = ROOT / "data" / "visual_object_audit" / "vision_retry_outputs"
PAGES = ROOT / "data" / "visual_object_audit" / "full_page_retry"
SCHEMA = ROOT / "tools" / "chatgpt_vision_annotation.schema.json"


def clean(value: object, limit: int = 900) -> str:
    return " ".join(str(value or "").split())[:limit]


def open_pdf_source(source: str) -> fitz.Document | None:
    if "::" in source:
        archive, member = source.split("::", 1)
        archive_path = ROOT / archive
        if archive_path.suffix.lower() != ".zip" or not archive_path.exists():
            return None
        try:
            with zipfile.ZipFile(archive_path) as z:
                data = z.read(member)
            return fitz.open(stream=data, filetype="pdf")
        except Exception:
            return None
    path = ROOT / source
    if path.exists() and path.suffix.lower() == ".pdf":
        try:
            return fitz.open(path)
        except Exception:
            return None
    return None


def full_page(row: dict) -> Path | None:
    try:
        page_no = int(row["page_or_sheet"])
    except Exception:
        return None
    target = PAGES / f"{row['object_id']}__full_page.png"
    if target.exists():
        return target
    doc = open_pdf_source(row["source_path"])
    if doc is None or not (1 <= page_no <= len(doc)):
        if doc is not None:
            doc.close()
        return None
    PAGES.mkdir(parents=True, exist_ok=True)
    page = doc[page_no - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(190 / 72, 190 / 72), alpha=False, colorspace=fitz.csRGB)
    pix.save(target)
    doc.close()
    return target


def inventory() -> list[dict]:
    rows = list(csv.DictReader(OBJECTS.open(encoding="utf-8"), delimiter="\t"))
    result = []
    for row in rows:
        path = ANN / f"{row['object_id']}.json"
        if not path.exists() or not row["image_path"]:
            continue
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if prior.get("review_stage") == "original_resolution_retry":
            continue
        if prior.get("status") not in {"uncertain", "unreadable"}:
            continue
        attachments = [ROOT / row["image_path"]]
        if prior.get("status") == "unreadable" and row["source_format"] == ".pdf":
            page = full_page(row)
            if page:
                attachments.append(page)
        result.append({"row": row, "prior": prior, "attachments": attachments})
    return result


def prompt_for(items: list[dict]) -> str:
    data = []
    for item in items:
        row, prior = item["row"], item["prior"]
        data.append({
            "object_id": row["object_id"],
            "type": row["object_type"], "label": row["object_label"],
            "caption": clean(row["caption"]), "nearby_context": clean(row["nearby_context"]),
            "prior_status": prior.get("status"),
            "prior_visible_text": clean(prior.get("visible_text"), 1400),
            "prior_interpretation": clean(prior.get("interpretation"), 1000),
            "attached_files": [p.name for p in item["attachments"]],
        })
    return """Re-review every listed scientific figure/table using the attached ORIGINAL-RESOLUTION object images. Some unreadable PDF objects also have a second image named __full_page showing the source page. Use ChatGPT visual understanding only: do not invoke OCR software, web search, or external sources.

Return exactly one schema-valid annotation per object_id. Improve or replace the prior reading. Transcribe meaningful headings, axes, legends, category/model names, and reliably legible values. Dense tables should preserve headers and all legible rows. Interpret comparisons, trends, panel relationships, best/worst model, and uncertainty. Never guess clipped or illegible values. Use status=completed only if the scientifically material content is recoverable; otherwise retain uncertain or unreadable and state the precise limitation and manual-review need.

Inventory:
""" + json.dumps(data, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects-per-batch", type=int, default=5)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    items = inventory()
    batches = [items[i:i + args.objects_per_batch] for i in range(0, len(items), args.objects_per_batch)]
    if args.max_batches:
        batches = batches[:args.max_batches]
    BATCH.mkdir(parents=True, exist_ok=True)
    print(f"flagged objects={len(items)} retry batches={len(batches)}")

    def execute(pair: tuple[int, list[dict]]) -> str:
        number, batch = pair
        ids = [x["row"]["object_id"] for x in batch]
        batch_digest = hashlib.sha1("\n".join(ids).encode()).hexdigest()[:16]
        output = BATCH / f"retry_{number:04d}_{batch_digest}.json"
        command = ["codex", "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only",
                   "-C", str(ROOT), "--output-schema", str(SCHEMA), "-o", str(output)]
        for item in batch:
            for image in item["attachments"]:
                command.extend(["--image", str(image)])
        command.append("-")
        if args.dry_run:
            return f"dry-run {number}: objects={len(ids)} images={sum(len(x['attachments']) for x in batch)}"
        proc = subprocess.run(command, cwd=ROOT, text=True, input=prompt_for(batch),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0 or not output.exists():
            return f"FAILED retry {number}/{len(batches)} rc={proc.returncode}: {clean(proc.stdout, 1000)}"
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"FAILED retry {number}: invalid JSON {exc}"
        returned = {x.get("object_id"): x for x in payload.get("annotations", [])}
        if set(returned) != set(ids):
            return f"FAILED retry {number}: missing={sorted(set(ids)-set(returned))} extra={sorted(set(returned)-set(ids))}"
        for object_id, annotation in returned.items():
            annotation["review_stage"] = "original_resolution_retry"
            (ANN / f"{object_id}.json").write_text(
                json.dumps(annotation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        return f"completed retry {number}/{len(batches)} objects={len(ids)}"

    indexed = list(enumerate(batches, 1))
    if args.workers <= 1:
        for item in indexed:
            print(execute(item), flush=True)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(execute, item) for item in indexed]
            for future in as_completed(futures):
                print(future.result(), flush=True)


if __name__ == "__main__":
    main()
