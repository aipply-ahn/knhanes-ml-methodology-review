#!/usr/bin/env python3
"""Remove two DOCX prose mentions incorrectly inventoried as duplicate figures."""
from __future__ import annotations
import csv,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALIASES={
 "lee2024lifestyle__0011__figure_2":"lee2024lifestyle__0002__figure_2",
 "lee2024lifestyle__0013__figure_1":"lee2024lifestyle__0001__figure_1",
}

def tsv(rel):
 p=ROOT/rel
 if not p.exists():return
 with p.open(encoding="utf-8-sig",newline="") as h:rd=csv.DictReader(h,delimiter="\t");fs=rd.fieldnames or [];rows=list(rd)
 if "object_id" not in fs:return
 rows=[x for x in rows if x.get("object_id") not in ALIASES]
 with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=fs,delimiter="\t",lineterminator="\n",extrasaction="ignore");w.writeheader();w.writerows(rows)

active=["data/ALL_REPORT_VISUAL_OBJECTS.tsv","data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv","data/CHATGPT_VISION_REVIEW_QUEUE.tsv","data/FIGURE_PERFORMANCE_CANDIDATES.tsv","data/visual_manual_review/contact_sheets/index.tsv","data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv","data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv","data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv","data/visual_manual_review/manual_review_manifest.tsv","data/visual_manual_review/potential_multipanel_manifest.tsv","data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv","data/visual_object_audit/recrop_candidates/candidate_manifest.tsv","data/visual_object_audit/vector_recrop_candidates/vector_candidate_manifest.tsv","data/visual_object_audit/visual_crop_reaudit.tsv"]
for x in active:tsv(x)

p=ROOT/"data/ALL_REPORT_VISUAL_OBJECTS.jsonl";rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()];p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows if x.get("object_id") not in ALIASES))
p=ROOT/"data/study_json/lee2024lifestyle.json";d=json.loads(p.read_text());items=[x for x in d["visual_objects"]["items"] if x.get("object_id") not in ALIASES];d["visual_objects"]["items"]=items;c=d["visual_objects"]["counts"];c.update(total=len(items),main_figures=sum(x.get("scope")=="main" and x.get("type")=="figure" for x in items),main_tables=sum(x.get("scope")=="main" and x.get("type")=="table" for x in items),supplement_figures=sum(x.get("scope")=="supplement" and x.get("type")=="figure" for x in items),supplement_tables=sum(x.get("scope")=="supplement" and x.get("type")=="table" for x in items));p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
p=ROOT/"data/STANDARDIZED_STUDY_JSON_INDEX.jsonl";rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()];p.write_text("".join(json.dumps(d if x.get("study_id")=="lee2024lifestyle" else x,ensure_ascii=False)+"\n" for x in rows))
arc=ROOT/"data/visual_object_audit/duplicate_object_aliases";arc.mkdir(exist_ok=True)
for old in ALIASES:
 for base in ["vision_annotations","vision_annotations_before_korean_caption"]:
  src=ROOT/f"data/visual_object_audit/{base}/{old}.json"
  if src.exists():shutil.move(str(src),str(arc/src.name))
with (arc/"ALIASES.tsv").open("a",encoding="utf-8") as h:
 for old,new in ALIASES.items():h.write(f"{old}\t{new}\tDOCX contains only a prose mention; canonical main-PDF figure already exists.\n")
