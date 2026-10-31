#!/usr/bin/env python3
"""Prompt 106: add the 32 criterion-A studies to data/input_counts.tsv (initial candidate predictor counts).
Value = protocol item PRD02 (first/initial candidate input count) from each FINAL record when it is an integer;
blank otherwise (same convention as the existing rows). Existing rows are kept byte-for-byte."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/input_counts.tsv"
adds = list(csv.DictReader(open(ROOT / "data/protocol_v1_2/criterion_a_additions.tsv"), delimiter="\t"))
text = P.read_text(encoding="utf-8-sig")
have = {line.split("\t")[0] for line in text.splitlines()[1:]}
rows = []
for a in adds:
    if a["canonical_key"] in have:
        continue
    d = json.loads((ROOT / f"data/protocol_v1_2/final/{a['study_id']}_final.json").read_text())
    v = [r.get("value") for r in d["protocol_items"].get("PRD02", [])]
    n = next((int(x) for x in v if isinstance(x, int) or (isinstance(x, str) and x.isdigit())), None)
    label = next((str(r.get("value")) for r in d["protocol_items"].get("PRD03", []) if r.get("value") not in (None, "NR", "NA")), "")
    rows.append("\t".join([a["canonical_key"], a["year"], "" if n is None else str(n), label.replace("\t", " ")[:200], "PRD02 (criterion-A single review, prompt 106)"]))
eol = "\r\n" if "\r\n" in text else "\n"
body = text.rstrip("\r\n") + eol + eol.join(rows) + eol
P.write_text("\ufeff" + body if not body.startswith("\ufeff") else body, encoding="utf-8")
print(len(rows), "rows;", sum(1 for r in rows if r.split("\t")[2]), "with a count")
