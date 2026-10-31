#!/usr/bin/env python3
"""Parse the integrated v1.3 protocol Markdown into a compact core-item spec for blinded P2 review.

    python tools/p2_item_spec.py

Reads only KNHANES_ML_study_audit_protocol.md (no P1/final data) and writes
data/protocol_v1_2/P2_work/ITEM_SPEC.json and ITEM_SPEC.tsv.
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "KNHANES_ML_study_audit_protocol.md"
OUT = ROOT / "data/protocol_v1_2/P2_work"
COLS = ["no", "id", "subsection", "item_role", "primary_unit", "required_related_ids", "nature",
        "applicability", "question", "format", "allowed", "evidence", "rule", "json_key",
        "output", "official_item_id", "required_components"]


def codes(allowed):
    """'CLS=...; CONT=...' or 'Y; N; UNC; NA' -> ['CLS','CONT'] / ['Y','N','UNC','NA']."""
    if not allowed or "=" in allowed and "/" in allowed.split("=")[0]:
        return []
    out = []
    for part in allowed.split(";"):
        c = part.strip().split("=")[0].strip()
        if re.fullmatch(r"[A-Z0-9_]+", c):
            out.append(c)
    return out


def main():
    items, section = {}, None
    for line in MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### ([A-V])\. (.+)", line)
        if m:
            section = f"{m.group(1)}. {m.group(2)}"
            continue
        if not re.match(r"^\| \d+ \| `", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != len(COLS):
            raise SystemExit(f"column mismatch: {line[:80]}")
        r = dict(zip(COLS, cells))
        r["id"] = r["id"].strip("`"); r["json_key"] = r["json_key"].strip("`")
        r["section"] = section
        r["codes"] = codes(r["allowed"]) if r["format"] in ("Single choice", "Multiple choice", "Multiple choice (복수)") else []
        items[r["id"]] = r
    if len(items) != 382:
        raise SystemExit(f"parsed {len(items)} items, expected 382")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ITEM_SPEC.json").write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n")
    keep = ["id", "section", "item_role", "nature", "primary_unit", "required_related_ids", "applicability",
            "question", "format", "allowed", "rule", "json_key", "official_item_id", "required_components"]
    with open(OUT / "ITEM_SPEC.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keep, delimiter="\t", extrasaction="ignore")
        w.writeheader(); w.writerows(items.values())
    roles = {}
    for r in items.values():
        roles[r["item_role"]] = roles.get(r["item_role"], 0) + 1
    print({"items": len(items), "roles": roles})


if __name__ == "__main__":
    main()
