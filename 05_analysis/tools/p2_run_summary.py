#!/usr/bin/env python3
"""Summarise the blinded P2 run for the final report (reads P2 data only).

    python tools/p2_run_summary.py

Reads P2_work/answers/*.json, P2_work/P2_VALIDATION.json (if present), P2_work/rereview_log/*.json,
P2_work/CONSISTENCY_SWEEP.json and P2_work/CONVENTION_RECODE_LOG.json. Writes P2_work/P2_RUN_SUMMARY.json.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/protocol_v1_2/P2_work"


def rows(a, iid):
    r = a.get("items", {}).get(iid) or []
    return [r] if isinstance(r, dict) else r


def first(a, iid):
    r = rows(a, iid)
    return r[0].get("value") if r else None


def main():
    answers = sorted((WORK / "answers").glob("KHM*.json"))
    s = {"studies": len(answers)}
    unit_totals = Counter()
    dist = defaultdict(Counter)
    overall = defaultdict(Counter)
    adm09 = []
    n_evidence = n_metrics = n_visual = n_conflicts = 0
    for f in answers:
        a = json.loads(f.read_text())
        sid = a["study_id"]
        for k, v in (a.get("units") or {}).items():
            unit_totals[k] += len(v)
        n_evidence += len(a.get("evidence_registry") or [])
        n_metrics += len(a.get("performance_metrics") or [])
        n_visual += len(a.get("visual_objects") or [])
        n_conflicts += len(a.get("conflicting_evidence") or [])
        for iid in ("TSK01", "TSK06", "ELG02", "ELG04", "SUR12", "SUR14", "ADM07"):
            v = first(a, iid)
            dist[iid][json.dumps(v, ensure_ascii=False) if isinstance(v, list) else str(v)] += 1
        for iid in a.get("items", {}):
            if iid.endswith("_OVERALL"):
                for r in rows(a, iid):
                    overall[iid][str(r.get("value"))] += 1
        if (a.get("system_metadata") or {}).get("ADM09") == "Y":
            adm09.append(sid)
    s["unit_totals"] = dict(unit_totals)
    s["evidence_records"] = n_evidence
    s["performance_metrics"] = n_metrics
    s["visual_objects"] = n_visual
    s["conflicting_evidence_entries"] = n_conflicts
    s["distributions"] = {k: dict(v) for k, v in dist.items()}
    s["probast_overall"] = {k: dict(v) for k, v in overall.items()}
    s["adm09_Y"] = {"n": len(adm09), "studies": adm09}

    val = WORK / "P2_VALIDATION.json"
    if val.exists():
        v = json.loads(val.read_text())
        s["validation"] = {k: v.get(k) for k in ("answers", "validated", "pass", "fail", "P2_complete_packets", "remaining")}

    logs = sorted((WORK / "rereview_log").glob("KHM*.json")) if (WORK / "rereview_log").exists() else []
    dec = Counter()
    by_item = Counter()
    status = Counter()
    for f in logs:
        g = json.loads(f.read_text())
        status[str(g.get("assemble_status"))] += 1
        for r in g.get("reviewed_items") or []:
            dec[str(r.get("decision"))] += 1
            if r.get("decision") == "CHANGED":
                by_item[str(r.get("item"))] += 1
    s["rereview"] = {"studies_logged": len(logs), "decisions": dict(dec), "assemble_status": dict(status),
                     "changed_by_item": dict(by_item.most_common())}

    sw = WORK / "CONSISTENCY_SWEEP.json"
    if sw.exists():
        d = json.loads(sw.read_text())
        s["sweep"] = {"studies_checked": d.get("studies_checked"), "flags": d.get("flags"),
                      "by_rule_counts": {k: len(v) for k, v in d.get("by_rule", {}).items()}}
    rc = WORK / "CONVENTION_RECODE_LOG.json"
    if rc.exists():
        r = json.loads(rc.read_text())
        s["convention_recode"] = {"entries": len(r), "changes": sum(len(x.get("changes") or []) for x in r)}

    (WORK / "P2_RUN_SUMMARY.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: s[k] for k in ("studies", "unit_totals", "evidence_records", "performance_metrics", "visual_objects")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
