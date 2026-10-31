#!/usr/bin/env python3
"""Normalize the single legacy `supplementary` scope label to `supplement`.

This is a deterministic vocabulary repair.  It changes no object identity, text,
interpretation, image, or numeric value.
"""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TARGET="kim2024gender__0002__table_S1"

def fix_tsv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f,delimiter="\t"); fields=rd.fieldnames; rows=list(rd)
    changed=0
    for r in rows:
        if r.get("object_id")==TARGET and r.get("source_scope")=="supplementary":
            r["source_scope"]="supplement"; changed+=1
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=fields,delimiter="\t",lineterminator="\n"); wr.writeheader(); wr.writerows(rows)
    return changed

def fix_jsonl(path):
    rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]; changed=0
    for r in rows:
        if r.get("object_id")==TARGET and r.get("source_scope")=="supplementary":
            r["source_scope"]="supplement"; changed+=1
    path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
    return changed

def fix_study(path):
    d=json.loads(path.read_text()); changed=0
    for r in d["visual_objects"]["items"]:
        if r.get("object_id")==TARGET and r.get("scope")=="supplementary":
            r["scope"]="supplement"; changed+=1
    d["visual_objects"]["counts"]["supplement_tables"]=sum(
        x.get("scope")=="supplement" and x.get("type")=="table" for x in d["visual_objects"]["items"])
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
    return changed

def main():
    changes={
        "tsv":fix_tsv(DATA/"ALL_REPORT_VISUAL_OBJECTS.tsv"),
        "jsonl":fix_jsonl(DATA/"ALL_REPORT_VISUAL_OBJECTS.jsonl"),
        "study_json":fix_study(DATA/"study_json/kim2024gender.json"),
    }
    print(changes)

if __name__=="__main__": main()
