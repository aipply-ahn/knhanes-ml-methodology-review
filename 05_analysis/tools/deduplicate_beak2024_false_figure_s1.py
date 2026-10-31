#!/usr/bin/env python3
"""Remove a second Figure S1 inventory row created from the nearby Table S1 caption."""
import csv, json, shutil
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OLD = "beak2024driven__0016__figure_S1"
NEW = "beak2024driven__0006__figure_S1"
files = [
    "data/ALL_REPORT_VISUAL_OBJECTS.tsv", "data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv",
    "data/CHATGPT_VISION_REVIEW_QUEUE.tsv", "data/FIGURE_PERFORMANCE_CANDIDATES.tsv",
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
]
for rel in files:
    p = R / rel
    if not p.exists():
        continue
    with p.open(encoding="utf-8-sig", newline="") as h:
        rd = csv.DictReader(h, delimiter="\t"); fs = rd.fieldnames or []; rows = list(rd)
    if "object_id" not in fs:
        continue
    with p.open("w", encoding="utf-8-sig", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fs, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(x for x in rows if x.get("object_id") != OLD)

p = R / "data/ALL_REPORT_VISUAL_OBJECTS.jsonl"
rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows if x.get("object_id") != OLD))

p = R / "data/study_json/beak2024driven.json"
d = json.loads(p.read_text()); items = [x for x in d["visual_objects"]["items"] if x.get("object_id") != OLD]
d["visual_objects"]["items"] = items
c = d["visual_objects"]["counts"]
c.update(total=len(items), main_figures=sum(x.get("scope") == "main" and x.get("type") == "figure" for x in items),
         main_tables=sum(x.get("scope") == "main" and x.get("type") == "table" for x in items),
         supplement_figures=sum(x.get("scope") == "supplement" and x.get("type") == "figure" for x in items),
         supplement_tables=sum(x.get("scope") == "supplement" and x.get("type") == "table" for x in items))
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

p = R / "data/STANDARDIZED_STUDY_JSON_INDEX.jsonl"
rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
p.write_text("".join(json.dumps(d if x.get("study_id") == "beak2024driven" else x, ensure_ascii=False) + "\n" for x in rows))

arc = R / "data/visual_object_audit/duplicate_object_aliases"; arc.mkdir(exist_ok=True)
for base in ["vision_annotations", "vision_annotations_before_korean_caption"]:
    src = R / f"data/visual_object_audit/{base}/{OLD}.json"
    if src.exists(): shutil.move(str(src), str(arc / src.name))
with (arc / "ALIASES.tsv").open("a", encoding="utf-8") as h:
    h.write(f"{OLD}\t{NEW}\tDuplicate Figure S1 image was attached to the nearby Table S1 caption; canonical Figure S1 is retained.\n")
