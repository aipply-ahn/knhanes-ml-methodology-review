#!/usr/bin/env python3
"""Promote only vector candidates visibly confirmed as complete figures."""
from __future__ import annotations

import csv, hashlib, shutil
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"data/ALL_REPORT_VISUAL_OBJECTS.tsv"
INDEX=ROOT/"data/visual_object_audit/vector_recrop_candidates/vector_candidate_manifest.tsv"
HISTORY=ROOT/"data/visual_object_audit/recrop_history"
LOG=ROOT/"data/visual_object_audit/promoted_vector_recrop_log.tsv"

APPROVED={
"chang2023classification__0001__figure_1","chang2023classification__0004__figure_4",
"chang2023classification__0006__figure_5","choi2014screening__0001__figure_1",
"choi2023comparisons__0001__figure_1","choi2024application__0008__figure_5",
"choi2024explainable__0004__figure_1","dashdondov2026assessing__0011__figure_3",
"hunag2023predicting__0006__figure_2","hunag2023predicting__0007__figure_3",
"hwang2021retracted__0001__figure_1","hwang2021retracted__0005__figure_4",
"khongorzul2022comparison__0004__figure_4","kim2017neural__0001__figure_1",
"kim2017neural__0008__figure_7","kim2017neural__0010__figure_5",
"kim2021deep__0005__figure_4","kim2021deep__0011__figure_6",
"kim2023usefulness__0001__figure_1","kim2025machinec__0001__figure_1",
"kim2025machinec__0002__figure_2","oh2020prediction__0002__figure_2",
"park2022prediction__0004__figure_3","seok2023machine__0012__figure_4",
"seok2023sarcopenia__0018__figure_5","song2017development__0002__figure_2",
"wu2026development__0004__figure_2","wu2026development__0006__figure_4",
"yang2013coronary__0001__figure_1","yang2013coronary__0003__figure_2",
}

def read(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f,delimiter="\t"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ledger={r["object_id"]:r for r in read(LEDGER)}; rows=read(INDEX); HISTORY.mkdir(parents=True,exist_ok=True); log=[]
 for r in rows:
  oid=r["object_id"]
  if oid not in APPROVED:
   r["verification"]="direct_review_rejected_or_manual_crop_required";continue
  src=ROOT/r["candidate_path"];dst=ROOT/ledger[oid]["image_path"]
  bak=HISTORY/f"{oid}__pre_verified_vector_repair.png"
  if not bak.exists():shutil.copy2(dst,bak)
  before=sha(dst);tmp=dst.with_suffix(".vector-recrop.tmp.png");shutil.copy2(src,tmp);tmp.replace(dst)
  r["verification"]="completed_direct_review_promoted"
  log.append({"promoted_at":datetime.now().astimezone().isoformat(timespec="seconds"),"object_id":oid,
   "method":"verified_vector_geometry_450dpi","source_pdf":r["source_pdf"],"pdf_page":r["pdf_page"],
   "clip_points":r["clip_points"],"output_path":ledger[oid]["image_path"],"before_sha256":before,
   "after_sha256":sha(dst),"backup_path":str(bak.relative_to(ROOT)),"visual_verification":"completed_direct_image_review"})
 with INDEX.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(rows)
 with LOG.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(log[0]),delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(log)
 print({"promoted_vector":len(log),"rejected_or_manual":len(rows)-len(log),"log":str(LOG.relative_to(ROOT))})

if __name__=="__main__":main()
