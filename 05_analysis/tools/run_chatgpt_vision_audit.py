#!/usr/bin/env python3
"""Run the image-only interpretation stage with ChatGPT vision via Codex CLI.

No OCR library is imported or called.  Each batch attaches study contact sheets to
an ephemeral, read-only ChatGPT/Codex request and requires schema-valid JSON.  The
result is split into immutable object-level annotation files and is merged by
``build_complete_visual_object_audit.py`` on its next run.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "CHATGPT_VISION_REVIEW_QUEUE.tsv"
COVERAGE = ROOT / "data" / "ALL_REPORT_VISUAL_COVERAGE.tsv"
OUT = ROOT / "data" / "visual_object_audit"
ANNOTATIONS = OUT / "vision_annotations"
BATCH_OUT = OUT / "vision_batch_outputs"
SCHEMA = ROOT / "tools" / "chatgpt_vision_annotation.schema.json"


def clean(value: object, limit: int = 700) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def sheet_groups() -> list[tuple[str, str, list[dict]]]:
    queue = list(csv.DictReader(QUEUE.open(encoding="utf-8"), delimiter="\t"))
    coverage = {r["study_key"]: r for r in csv.DictReader(COVERAGE.open(encoding="utf-8"), delimiter="\t")}
    by_study: dict[str, list[dict]] = defaultdict(list)
    for row in queue:
        if row["image_path"]:
            by_study[row["study_key"]].append(row)
    result = []
    for key in sorted(by_study):
        rows = by_study[key]
        sheets = [x for x in coverage.get(key, {}).get("contact_sheets", "").split(";") if x]
        for i in range(0, len(rows), 8):
            sheet_i = i // 8
            pending = []
            for row in rows[i:i + 8]:
                annotation = ROOT / row["annotation_path"]
                done = False
                if annotation.exists():
                    try:
                        done = json.loads(annotation.read_text(encoding="utf-8")).get("status") in {"completed", "uncertain", "unreadable"}
                    except Exception:
                        pass
                if not done:
                    pending.append(row)
            if pending and sheet_i < len(sheets):
                result.append((key, sheets[sheet_i], pending))
    return result


def prompt_for(groups: list[tuple[str, str, list[dict]]]) -> str:
    inventory = []
    for key, sheet, rows in groups:
        inventory.append({
            "study_key": key,
            "attached_contact_sheet": sheet,
            "objects": [{
                "object_id": r["object_id"],
                "type": r["object_type"],
                "label": r["object_label"],
                "source": r["source_scope"],
                "location": r["page_or_sheet"],
                "caption": clean(r["caption"]),
            } for r in rows],
        })
    return """You are the image-reading stage of a systematic-review audit. Inspect every labelled tile in every attached contact sheet. Do not use OCR software, web search, or external sources; use your ChatGPT visual understanding only.

Return exactly one annotation for every object_id in the inventory. For visible_text, transcribe the scientifically meaningful visible labels, headings, legend terms, axes, categories, and values. For a dense table, preserve headers and all legible rows/values; if resolution prevents full transcription, record everything reliably legible and mark uncertain instead of guessing. For interpretation, explain what the object shows, comparisons/trends, best/worst model where visible, and how panels relate. key_values must contain atomic reusable facts such as "CatBoost F1=0.754". State limitations in uncertainty. Set manual_review_reason to an empty string when completed, otherwise state what needs an original-resolution review. Captions supplied below are context, not substitutes for inspecting the image.

Object inventory:
""" + json.dumps(inventory, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheets-per-batch", type=int, default=2)
    parser.add_argument("--max-batches", type=int, default=0, help="0 means all remaining batches")
    parser.add_argument("--workers", type=int, default=1, help="parallel independent ChatGPT vision calls")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    groups = sheet_groups()
    batches = [groups[i:i + args.sheets_per_batch] for i in range(0, len(groups), args.sheets_per_batch)]
    if args.max_batches:
        batches = batches[:args.max_batches]
    ANNOTATIONS.mkdir(parents=True, exist_ok=True)
    BATCH_OUT.mkdir(parents=True, exist_ok=True)
    print(f"remaining contact sheets={len(groups)} batches={len(batches)}")
    def execute(item: tuple[int, list[tuple[str, str, list[dict]]]]) -> str:
        batch_no, batch = item
        ids = [r["object_id"] for _, _, rows in batch for r in rows]
        batch_key = "__".join(f"{key}_{Path(sheet).stem.rsplit('_', 1)[-1]}" for key, sheet, _ in batch)
        output = BATCH_OUT / f"{batch_key}.json"
        command = [
            "codex", "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only",
            "-C", str(ROOT), "--output-schema", str(SCHEMA), "-o", str(output),
        ]
        for _, sheet, _ in batch:
            command.extend(["--image", str(ROOT / sheet)])
        command.append("-")
        if args.dry_run:
            return f"dry-run batch {batch_no}: sheets={len(batch)} objects={len(ids)}"
        proc = subprocess.run(command, cwd=ROOT, text=True, input=prompt_for(batch),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0 or not output.exists():
            return f"FAILED batch {batch_no}/{len(batches)} rc={proc.returncode}: {clean(proc.stdout, 1200)}"
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"FAILED batch {batch_no}: invalid JSON {exc}"
        returned = {a.get("object_id"): a for a in payload.get("annotations", [])}
        missing = [x for x in ids if x not in returned]
        extra = [x for x in returned if x not in ids]
        if missing or extra:
            return f"FAILED batch {batch_no}: missing={missing} extra={extra}"
        for object_id in ids:
            target = ANNOTATIONS / f"{object_id}.json"
            target.write_text(json.dumps(returned[object_id], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f"completed batch {batch_no}/{len(batches)} sheets={len(batch)} objects={len(ids)}"

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
