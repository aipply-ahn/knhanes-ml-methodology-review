#!/usr/bin/env python3
"""Mark one source-resolution-limited figure for explicit user review."""
import csv, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]; OID="byeon2016factors__0001__figure_1"
reason="Publisher-provided raster is too low-resolution to read individual network-node labels after direct ChatGPT image reread; topology and the surrounding-text interpretation remain readable."
for rel in ["data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv","data/ALL_REPORT_VISUAL_OBJECTS.tsv","data/CHATGPT_VISION_REVIEW_QUEUE.tsv","data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv"]:
 p=R/rel
 if not p.exists(): continue
 with p.open(encoding="utf-8-sig",newline="") as h: rd=csv.DictReader(h,delimiter="\t"); fs=rd.fieldnames or []; rows=list(rd)
 for x in rows:
  if x.get("object_id")==OID:
   if "scientific_interpretation_status" in fs: x["scientific_interpretation_status"]="MANUAL_REVIEW_REQUIRED_SOURCE_RESOLUTION"
   if "decode_status" in fs: x["decode_status"]="PARTIALLY_DECODED_SOURCE_RESOLUTION_LIMIT"
   if "remaining_uncertainty" in fs: x["remaining_uncertainty"]=reason
   if "required_followup" in fs: x["required_followup"]="User may inspect the isolated source image; no higher-resolution publisher object is available locally."
   if "manual_review_reason" in fs: x["manual_review_reason"]=reason
 with p.open("w",encoding="utf-8-sig",newline="") as h: w=csv.DictWriter(h,fieldnames=fs,delimiter="\t",lineterminator="\n",extrasaction="ignore");w.writeheader();w.writerows(rows)
p=R/"data/ALL_REPORT_VISUAL_OBJECTS.jsonl"; rows=[]
for line in p.read_text().splitlines():
 if not line.strip(): continue
 x=json.loads(line)
 if x.get("object_id")==OID: x.update(chatgpt_vision_status="manual_review_required_source_resolution",chatgpt_uncertainty=reason,manual_review_reason=reason)
 rows.append(x)
p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
p=R/f"data/visual_object_audit/vision_annotations/{OID}.json"; d=json.loads(p.read_text()) if p.exists() else {"object_id":OID};d.update(status="manual_review_required_source_resolution",uncertainty=reason,manual_review_reason=reason);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
p=R/"data/study_json/byeon2016factors.json";d=json.loads(p.read_text())
for x in d["visual_objects"]["items"]:
 if x.get("object_id")==OID: x.update(vision_status="manual_review_required_source_resolution",uncertainty=reason,manual_review_reason=reason)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
p=R/"data/STANDARDIZED_STUDY_JSON_INDEX.jsonl";out=[]
for line in p.read_text().splitlines():
 if line.strip():
  x=json.loads(line);out.append(d if x.get("study_id")=="byeon2016factors" else x)
p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in out))
