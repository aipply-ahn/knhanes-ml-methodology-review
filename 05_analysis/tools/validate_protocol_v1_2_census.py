#!/usr/bin/env python3
"""Validate the adjudicated protocol-v1.2 census and linked dynamic units."""
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"data/protocol_v1_2"
expected=set(json.loads((ROOT/"KNHANES_ML_study_audit_template_v1.2.json").read_text())["protocol_items"])
files=sorted((BASE/"final").glob("KHM*_final.json")); errors=[]; stats=Counter(); tasks=Counter()

def included(d):
    return d.get("corpus_status",{}).get("include",d["protocol_items"]["ELG04"][0]["value"]=="Y")

if len(files)!=222: errors.append(f"final file count {len(files)} != 222")
if len(list((BASE/"P2_blinded").glob("KHM*_P2.json")))!=222: errors.append("P2 blinded packet count != 222")
if len(list((BASE/"final_consensus").glob("KHM*_CON.json")))!=222: errors.append("consensus packet count != 222")

kept=[]
for p in files:
    d=json.loads(p.read_text()); sid=d["study_id"]
    if d.get("adjudication",{}).get("status")!="COMPLETE": errors.append(f"{sid}: adjudication not COMPLETE")
    got=set(d.get("protocol_items",{}))
    if got!=expected: errors.append(f"{sid}: item ID mismatch")
    evid={x["evidence_id"] for x in d.get("evidence_registry",[])}
    unit_ids={sid}
    for vals in d.get("units",{}).values():
        for u in vals: unit_ids.update(v for k,v in u.items() if k.endswith("_id") and isinstance(v,str))
    unit_ids.update(x.get("supplement_id") for x in d.get("source_package",{}).get("supplement_files",[]) if x.get("supplement_id"))
    unit_ids.update(x["object_id"] for x in d.get("visual_objects",[]))
    for iid,rows in d.get("protocol_items",{}).items():
        if not rows: errors.append(f"{sid}/{iid}: empty repeat array")
        for j,r in enumerate(rows):
            if r.get("status")!="COMPLETE" or r.get("value") is None: errors.append(f"{sid}/{iid}[{j}]: incomplete")
            if set(r.get("evidence_ids",[]))-evid: errors.append(f"{sid}/{iid}[{j}]: missing evidence")
            if r.get("unit_id") and r["unit_id"] not in unit_ids: errors.append(f"{sid}/{iid}[{j}]: unknown unit")
    for group in ("performance_metrics","best_model_selections","visual_objects"):
        for j,x in enumerate(d.get(group,[])):
            if set(x.get("evidence_ids",[]))-evid: errors.append(f"{sid}/{group}[{j}]: missing evidence")
            if x.get("status")!="COMPLETE": errors.append(f"{sid}/{group}[{j}]: incomplete")
    if included(d):
        kept.append(d); tasks[d["protocol_items"]["TSK01"][0]["value"]]+=1
        stats["visual_objects"]+=len(d.get("visual_objects",[]))
        if d["protocol_items"]["TSK01"][0]["value"] in {"CLS","CONT"}:
            stats["developments"]+=len(d.get("units",{}).get("developments",[]))
            stats["evaluations"]+=len(d.get("units",{}).get("evaluations",[]))
        stats["performance_metrics"]+=len(d.get("performance_metrics",[]))
        stats["best_model_selections"]+=len(d.get("best_model_selections",[]))
        stats["evidence_records"]+=len(evid)

expected_tasks={"CLS":196,"CONT":12,"OTHER":12}
expected_stats={"visual_objects":3386,"developments":308,"evaluations":401,"performance_metrics":6128,"best_model_selections":308,"evidence_records":13517}
if dict(tasks)!=expected_tasks: errors.append(f"task denominators {dict(tasks)}")
for k,v in expected_stats.items():
    if stats[k]!=v: errors.append(f"{k} {stats[k]} != {v}")
ahn=next(d for d in kept if d["canonical_key"]=="ahn2025discovering")
if not any(str(x.get("metric")).upper()=="F1" and x.get("estimate")==0.754 for x in ahn["performance_metrics"]): errors.append("Ahn F1=0.754 absent")
if any(x.get("interpretation_method")=="OCR_ENGINE" for p in files for x in json.loads(p.read_text()).get("visual_objects",[])): errors.append("OCR engine provenance found")

report={"schema":"protocol_v1_2_census_validation","date":date.today().isoformat(),"status":"PASS" if not errors else "FAIL",
        "review_packets":len(files),"included_studies":len(kept),"protocol_items_per_study":len(expected),
        "task_denominators":dict(tasks),"included_dynamic_units":dict(stats),
        "P2_files":len(list((BASE/"P2_blinded").glob("KHM*_P2.json"))),
        "consensus_files":len(list((BASE/"final_consensus").glob("KHM*_CON.json"))),
        "adjudication_state":"COMPLETE","checks":{"item_and_link_integrity":not any("item ID" in e or "missing evidence" in e or "unknown unit" in e for e in errors),
        "fixed_denominators":dict(tasks)==expected_tasks,"dynamic_totals":all(stats[k]==v for k,v in expected_stats.items()),
        "ahn_best_score_propagated":not any("Ahn" in e for e in errors),"no_ocr_engine":not any("OCR" in e for e in errors)},"errors":errors}
(BASE/"VALIDATION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(bool(errors))
