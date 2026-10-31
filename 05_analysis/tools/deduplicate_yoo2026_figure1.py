#!/usr/bin/env python3
"""Collapse the prose-derived Fig 1A pseudo-object into canonical multipanel Fig 1."""
from __future__ import annotations
import csv, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD="yoo2026merwacs__0002__figure_1A"
NEW="yoo2026merwacs__0003__figure_1"

def filter_tsv(rel: str):
    p=ROOT/rel
    if not p.exists(): return
    with p.open(encoding="utf-8-sig",newline="") as h:
        rd=csv.DictReader(h,delimiter="\t"); fields=rd.fieldnames or []; rows=list(rd)
    if "object_id" not in fields: return
    rows=[r for r in rows if r.get("object_id") != OLD]
    with p.open("w",encoding="utf-8-sig",newline="") as h:
        w=csv.DictWriter(h,fieldnames=fields,delimiter="\t",lineterminator="\n",extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def clean_study(d):
    vis=d.get("visual_objects",{})
    vis["items"]=[x for x in vis.get("items",[]) if x.get("object_id") != OLD]
    c=vis.get("counts",{})
    c["total"]=len(vis["items"])
    c["main_figures"]=sum(x.get("scope")=="main" and x.get("type")=="figure" for x in vis["items"])
    c["main_tables"]=sum(x.get("scope")=="main" and x.get("type")=="table" for x in vis["items"])
    c["supplement_figures"]=sum(x.get("scope")=="supplement" and x.get("type")=="figure" for x in vis["items"])
    c["supplement_tables"]=sum(x.get("scope")=="supplement" and x.get("type")=="table" for x in vis["items"])
    return d

study=ROOT/"data/study_json/yoo2026merwacs.json"
d=clean_study(json.loads(study.read_text()))
study.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")

for rel in [
    "data/ALL_REPORT_VISUAL_OBJECTS.tsv","data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv",
    "data/CHATGPT_VISION_REVIEW_QUEUE.tsv","data/FIGURE_PERFORMANCE_CANDIDATES.tsv",
    "data/visual_manual_review/contact_sheets/index.tsv",
    "data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv",
    "data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv",
    "data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv",
    "data/visual_manual_review/manual_review_manifest.tsv",
    "data/visual_manual_review/potential_multipanel_manifest.tsv",
    "data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv",
    "data/visual_object_audit/recrop_candidates/candidate_manifest.tsv",
    "data/visual_object_audit/vector_recrop_candidates/vector_candidate_manifest.tsv",
    "data/visual_object_audit/visual_crop_reaudit.tsv",
]: filter_tsv(rel)

p=ROOT/"data/ALL_REPORT_VISUAL_OBJECTS.jsonl"
rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows if x.get("object_id") != OLD))

p=ROOT/"data/STANDARDIZED_STUDY_JSON_INDEX.jsonl"
rows=[]
for line in p.read_text().splitlines():
    if not line.strip(): continue
    x=json.loads(line)
    rows.append(d if x.get("study_id")=="yoo2026merwacs" else x)
p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))

archive=ROOT/"data/visual_object_audit/duplicate_object_aliases"
archive.mkdir(parents=True,exist_ok=True)
for rel in [
    f"data/visual_object_audit/vision_annotations/{OLD}.json",
    f"data/visual_object_audit/vision_annotations_before_korean_caption/{OLD}.json",
]:
    src=ROOT/rel
    if src.exists(): shutil.move(str(src),str(archive/src.name))

alias=archive/"ALIASES.tsv"
alias.write_text("duplicate_object_id\tcanonical_object_id\treason\n"+
                 f"{OLD}\t{NEW}\tFig 1A prose mention was incorrectly inventoried as a separate object; canonical Fig 1 preserves panels A and B together.\n")
