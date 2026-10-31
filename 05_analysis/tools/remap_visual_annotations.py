#!/usr/bin/env python3
"""Snapshot/restore ChatGPT annotations across mechanical object-ID shifts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.tsv"
ANN = ROOT / "data" / "visual_object_audit" / "vision_annotations"
SNAPSHOT = ROOT / "data" / "visual_object_audit" / "annotation_signature_snapshot.jsonl"


def signature(row: dict) -> str:
    return "\x1f".join([
        row.get("study_key", ""), row.get("source_path", ""), row.get("object_type", ""),
        row.get("object_label", ""), row.get("page_or_sheet", ""),
    ])


def indexed_rows() -> list[tuple[dict, str]]:
    rows = list(csv.DictReader(LEDGER.open(encoding="utf-8"), delimiter="\t"))
    seen: dict[str, int] = defaultdict(int)
    result = []
    for row in rows:
        base = signature(row)
        seen[base] += 1
        result.append((row, f"{base}\x1foccurrence={seen[base]}"))
    return result


def snapshot() -> None:
    saved = 0
    with SNAPSHOT.open("w", encoding="utf-8") as f:
        for row, sig in indexed_rows():
            path = ANN / f"{row['object_id']}.json"
            if not path.exists():
                continue
            payload = {"signature": sig, "old_object_id": row["object_id"],
                       "annotation": json.loads(path.read_text(encoding="utf-8"))}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            saved += 1
    print(f"snapshot annotations={saved} -> {SNAPSHOT}")


def restore() -> None:
    source = {}
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        source[item["signature"]] = item["annotation"]
    ANN.mkdir(parents=True, exist_ok=True)
    restored = 0
    for row, sig in indexed_rows():
        if sig not in source:
            continue
        annotation = dict(source[sig])
        annotation["object_id"] = row["object_id"]
        (ANN / f"{row['object_id']}.json").write_text(
            json.dumps(annotation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        restored += 1
    print(f"restored annotations={restored}; unmatched new vision objects require ChatGPT review")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "restore"])
    args = parser.parse_args()
    snapshot() if args.action == "snapshot" else restore()


if __name__ == "__main__":
    main()
