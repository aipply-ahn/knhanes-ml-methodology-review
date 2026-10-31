#!/usr/bin/env python3
"""Merge object-level ChatGPT vision JSON into the reusable audit datasets."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
OBJECTS = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.tsv"
OBJECTS_JSONL = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.jsonl"
OBJECTS_XLSX = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.xlsx"
COVERAGE = ROOT / "data" / "ALL_REPORT_VISUAL_COVERAGE.tsv"
QUEUE = ROOT / "data" / "CHATGPT_VISION_REVIEW_QUEUE.tsv"
MANUAL = ROOT / "data" / "CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv"
REPORT = ROOT / "data" / "ALL_REPORT_VISUAL_AUDIT.md"
ANN = ROOT / "data" / "visual_object_audit" / "vision_annotations"


VISION_FIELDS = [
    "chatgpt_vision_status", "chatgpt_review_stage", "chatgpt_visible_text",
    "chatgpt_interpretation", "chatgpt_key_values", "chatgpt_uncertainty",
    "manual_review_reason",
]


def read_tsv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def merge() -> tuple[list[dict], list[str]]:
    rows = read_tsv(OBJECTS)
    fields = list(rows[0])
    for field in VISION_FIELDS:
        if field not in fields:
            fields.append(field)
    missing = []
    for row in rows:
        if row.get("vision_required") != "Y":
            if not row.get("chatgpt_vision_status"):
                row["chatgpt_vision_status"] = "not_required_native_table"
            continue
        path = ANN / f"{row['object_id']}.json"
        if not path.exists():
            missing.append(row["object_id"])
            row["chatgpt_vision_status"] = "pending"
            continue
        annotation = json.loads(path.read_text(encoding="utf-8"))
        row.update({
            "chatgpt_vision_status": annotation.get("status", "uncertain"),
            "chatgpt_review_stage": annotation.get("review_stage", "first_pass"),
            "chatgpt_visible_text": annotation.get("visible_text", ""),
            "chatgpt_interpretation": annotation.get("interpretation", ""),
            "chatgpt_key_values": json.dumps(annotation.get("key_values", []), ensure_ascii=False),
            "chatgpt_uncertainty": annotation.get("uncertainty", ""),
            "manual_review_reason": annotation.get("manual_review_reason", ""),
        })
    write_tsv(OBJECTS, rows, fields)
    with OBJECTS_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows, missing


def write_xlsx(rows: list[dict]) -> None:
    fields = list(rows[0])
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Visual objects"
    ws.append(fields)
    illegal = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
    for row in rows:
        ws.append([illegal.sub("", str(row.get(field, ""))) for field in fields])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    compact = {"study_key": 25, "source_scope": 12, "object_id": 43, "object_type": 12,
               "object_label": 24, "object_number": 15, "page_or_sheet": 18,
               "chatgpt_vision_status": 20, "chatgpt_review_stage": 24}
    long_fields = {"caption", "nearby_context", "native_text", "native_interpretation",
                   "chatgpt_visible_text", "chatgpt_interpretation", "chatgpt_key_values",
                   "chatgpt_uncertainty", "manual_review_reason", "source_path"}
    for idx, field in enumerate(fields, 1):
        ws.column_dimensions[get_column_letter(idx)].width = compact.get(field, 55 if field in long_fields else 18)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(OBJECTS_XLSX)


def update_coverage(rows: list[dict]) -> list[dict]:
    coverage = read_tsv(COVERAGE)
    by_study: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_study[row["study_key"]].append(row)
    new_fields = ["chatgpt_completed", "chatgpt_uncertain", "chatgpt_unreadable", "original_resolution_retried"]
    fields = list(coverage[0])
    for field in new_fields:
        if field not in fields:
            fields.append(field)
    for item in coverage:
        visual = [r for r in by_study[item["study_key"]] if r["vision_required"] == "Y"]
        counts = Counter(r["chatgpt_vision_status"] for r in visual)
        item["chatgpt_vision_pending"] = str(counts["pending"])
        item["chatgpt_completed"] = str(counts["completed"])
        item["chatgpt_uncertain"] = str(counts["uncertain"])
        item["chatgpt_unreadable"] = str(counts["unreadable"])
        item["original_resolution_retried"] = str(sum(r.get("chatgpt_review_stage") == "original_resolution_retry" for r in visual))
        if int(item["processing_errors"]) or int(item["unmatched_caption_labels"]) or counts["pending"]:
            item["audit_status"] = "needs_follow_up"
        elif counts["uncertain"] or counts["unreadable"]:
            item["audit_status"] = "complete_with_flagged_visual_uncertainty"
        else:
            item["audit_status"] = "complete"
    write_tsv(COVERAGE, coverage, fields)
    return coverage


def update_queues(rows: list[dict]) -> list[dict]:
    queue = read_tsv(QUEUE)
    index = {r["object_id"]: r for r in rows}
    qfields = list(queue[0])
    for field in VISION_FIELDS:
        if field not in qfields:
            qfields.append(field)
    for item in queue:
        source = index[item["object_id"]]
        for field in VISION_FIELDS:
            item[field] = source.get(field, "")
    write_tsv(QUEUE, queue, qfields)
    manual = [{
        "study_key": r["study_key"], "object_id": r["object_id"], "object_type": r["object_type"],
        "object_label": r["object_label"], "source_path": r["source_path"],
        "page_or_sheet": r["page_or_sheet"], "image_path": r["image_path"],
        "status": r["chatgpt_vision_status"], "review_stage": r.get("chatgpt_review_stage", ""),
        "visible_text": r["chatgpt_visible_text"], "interpretation": r["chatgpt_interpretation"],
        "uncertainty": r["chatgpt_uncertainty"], "manual_review_reason": r["manual_review_reason"],
    } for r in rows if r["chatgpt_vision_status"] in {"uncertain", "unreadable"}]
    write_tsv(MANUAL, manual)
    return manual


def report(rows: list[dict], coverage: list[dict], manual: list[dict], missing: list[str]) -> None:
    scope_type = Counter((r["source_scope"], r["object_type"]) for r in rows)
    status = Counter(r["chatgpt_vision_status"] for r in rows if r["vision_required"] == "Y")
    stage = Counter(r.get("chatgpt_review_stage") or "not_applicable" for r in rows if r["vision_required"] == "Y")
    audit = Counter(r["audit_status"] for r in coverage)
    lines = [
        "# Complete figure/table audit of included reports", "",
        "All figure/table objects in the available main reports and archived supplements were mechanically inventoried. Native text and table cells were retained. Image-specific transcription and interpretation were produced with ChatGPT vision only; no OCR-engine output was used.", "",
        f"- Included studies: {len(coverage)}",
        f"- Visual/table objects: {len(rows)}",
        f"- Main figures/tables: {scope_type[('main','figure')]}/{scope_type[('main','table')]}",
        f"- Supplement figures/tables: {scope_type[('supplement','figure')]}/{scope_type[('supplement','table')]}",
        f"- Objects requiring ChatGPT vision: {sum(status.values())}",
        f"- Vision status: completed {status['completed']}; uncertain {status['uncertain']}; unreadable {status['unreadable']}; pending {status['pending']}",
        f"- Original-resolution second review: {stage['original_resolution_retry']}",
        f"- Missing annotations: {len(missing)}",
        f"- Unmatched caption labels: {sum(int(r['unmatched_caption_labels']) for r in coverage)}",
        f"- Processing errors: {sum(int(r['processing_errors']) for r in coverage)}", "",
        "`uncertain` and `unreadable` are not silently imputed. Their first-pass interpretation, original-resolution retry, exact source location, and manual-review reason remain in `CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv`.", "",
        "## Study-level audit status", "",
    ]
    lines += [f"- {key}: {value}" for key, value in sorted(audit.items())]
    lines += ["", "## Reusable files", "",
              "- `ALL_REPORT_VISUAL_OBJECTS.tsv`: complete tabular object ledger",
              "- `ALL_REPORT_VISUAL_OBJECTS.jsonl`: lossless JSON-lines copy",
              "- `ALL_REPORT_VISUAL_OBJECTS.xlsx`: filterable workbook",
              "- `ALL_REPORT_VISUAL_COVERAGE.tsv`: study-level completeness ledger",
              "- `CHATGPT_VISION_REVIEW_QUEUE.tsv`: complete vision ledger with status",
              "- `CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv`: only flagged original-resolution follow-up objects",
              "- `visual_object_audit/objects/`: rendered images and exact native tables",
              "- `visual_object_audit/vision_annotations/`: one ChatGPT annotation JSON per image object", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows, missing = merge()
    if missing:
        raise SystemExit(f"Missing ChatGPT annotations for {len(missing)} objects; first={missing[:10]}")
    coverage = update_coverage(rows)
    manual = update_queues(rows)
    write_xlsx(rows)
    report(rows, coverage, manual, missing)
    print("objects", len(rows))
    print("vision", dict(Counter(r["chatgpt_vision_status"] for r in rows if r["vision_required"] == "Y")))
    print("manual_review", len(manual))
    print("study_status", dict(Counter(r["audit_status"] for r in coverage)))


if __name__ == "__main__":
    main()
