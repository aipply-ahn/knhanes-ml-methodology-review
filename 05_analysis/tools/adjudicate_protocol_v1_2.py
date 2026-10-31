#!/usr/bin/env python3
"""Validate P2, compare P1/P2, and create evidence-preserving final records."""
from __future__ import annotations
import copy, hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
P1, P2, WORK = BASE / "P1", BASE / "P2_blinded", BASE / "P2_work"
CON, FINAL = BASE / "final_consensus", BASE / "final"
SPEC = json.loads((WORK / "ITEM_SPEC.json").read_text())
DATE, ADJUDICATOR = "2026-09-14", "codex_coordinator_rule_adjudication"
REVIEWER_ROLES = {"reviewer_entered", "appraisal_judgement"}
UNIT_KEYS = {"Report": ("reports", "report_id"), "Dataset": ("datasets", "dataset_id"),
             "Outcome": ("outcomes", "outcome_id"), "Model": ("models", "model_id"),
             "Development": ("developments", "development_id"),
             "Evaluation": ("evaluations", "evaluation_id")}

# Decisions required by prompt.txt. KHM191/KHM195 and KHM197/KHM198 remain separate.
CORPUS_DECISIONS = {
 "KHM065": {"decision": "EXCLUDE_NO_ELIGIBLE_ML", "include": False,
   "rationale": "AHP weights, radar-chart similarity and a scanned threshold form a deterministic score; no learning algorithm was fitted."},
 "KHM076": {"decision": "MERGE_PREPRINT_INTO_KHM100", "include": False, "family_id": "KHM100", "representative": False,
   "rationale": "Confirmed Research Square preprint–journal pair (same authors and DAE_OE_XGB analysis); KHM100 is the representative journal report."},
 "KHM100": {"decision": "REPRESENTATIVE_FOR_KHM076_KHM100", "include": True, "family_id": "KHM100", "representative": True,
   "rationale": "Representative journal report for the confirmed KHM076/KHM100 preprint–journal family."},
 "KHM068": {"decision": "RETAIN_CORPUS_EXCLUDE_VALID_EVIDENCE", "include": True, "exclude_from_valid_evidence": True,
   "rationale": "Retracted 2026-08-19 for concerns about third-party submission involvement and compromised peer review (JMIR notice DOI 10.2196/108367)."},
 "KHM178": {"decision": "INCLUDE_EXTERNAL_VALIDATION", "include": True,
   "rationale": "Eligibility covers KNHANES use in model development or evaluation; KNHANES is the external evaluation dataset."},
 "KHM221": {"decision": "INCLUDE_EXTERNAL_VALIDATION", "include": True,
   "rationale": "Eligibility covers KNHANES use in model development or evaluation; KNHANES is the external evaluation dataset."},
 "KHM222": {"decision": "INCLUDE_EXTERNAL_VALIDATION", "include": True,
   "rationale": "Eligibility covers KNHANES use in model development or evaluation; KNHANES is the external evaluation dataset."},
}

def load(path): return json.loads(path.read_text())

def unit_index(record):
    out = {}
    for group, key in UNIT_KEYS.values():
        for row in record.get("units", {}).get(group, []): out[row.get(key)] = row
    return out

def semantic_unit(record, primary, unit_id):
    """Stable crosswalk key; repeated rows are never compared by list position."""
    if primary == "Study" or unit_id in (None, record.get("study_id")): return "STUDY"
    idx, u = unit_index(record), unit_index(record).get(unit_id, {})
    if primary == "Report": return "REPORT:" + str(u.get("canonical_key") or record.get("canonical_key"))
    if primary == "Dataset": return "DATASET:" + "|".join(str(u.get(k) or "") for k in ("label", "role"))
    if primary == "Outcome": return "OUTCOME:" + str(u.get("label") or "")
    if primary == "Model": return "MODEL:" + "|".join(str(u.get(k) or "") for k in ("label", "role"))
    if primary in ("Development", "Evaluation"):
        parts = [primary.upper()]
        for key in ("model_id", "outcome_id", "dataset_id"):
            linked = idx.get(u.get(key), {})
            parts.append(str(linked.get("label") or linked.get("role") or u.get(key) or ""))
        return ":" + "|".join(parts)
    return f"{primary}:{unit_id}"

def normalized_rows(record, iid):
    primary = SPEC[iid]["primary_unit"]
    rows = [{"unit": semantic_unit(record, primary, r.get("unit_id")), "value": r.get("value")}
            for r in record.get("protocol_items", {}).get(iid, [])]
    return sorted(rows, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True))

def validate_p2(record, validation):
    sid, errors = record.get("study_id"), []
    rr = record.get("review_record", {})
    for ok, msg in [(rr.get("status") == "COMPLETE", "review status"),
                    (rr.get("reviewer_id") == "P2-CLAUDE-OPUS5", "reviewer id"),
                    (rr.get("reviewer_type") == "LLM_AGENT", "reviewer type"),
                    (rr.get("blind_to_other_reviewer") is True, "blinding flag"),
                    (validation.get("status") == "PASS", "assembler validation")]:
        if not ok: errors.append(msg)
    idx, unit_ids = unit_index(record), set(unit_index(record))
    visual_ids = {v.get("object_id") for v in record.get("visual_objects", [])}
    supplement_ids = {s.get("supplement_id") for s in record.get("source_package", {}).get("supplement_files", [])}
    reference_ids = unit_ids | visual_ids | supplement_ids
    evidence_ids = {e.get("evidence_id") for e in record.get("evidence_registry", [])}
    if None in evidence_ids or len(evidence_ids) != len(record.get("evidence_registry", [])): errors.append("evidence IDs")
    for iid, spec in SPEC.items():
        rows = record.get("protocol_items", {}).get(iid)
        if not rows: errors.append(f"{iid}: missing"); continue
        for row in rows:
            if row.get("status") != "COMPLETE" or row.get("value") is None: errors.append(f"{iid}: incomplete")
            if set(row.get("evidence_ids") or []) - evidence_ids: errors.append(f"{iid}: evidence reference")
            uid = row.get("unit_id")
            if spec["primary_unit"] not in ("Study", "VisualObject", "SupplementFile") and uid is not None and uid not in unit_ids:
                errors.append(f"{iid}: unit {uid}")
            for rid in (row.get("related_ids") or {}).values():
                if isinstance(rid, str) and rid.startswith(sid + "-") and rid not in reference_ids: errors.append(f"{iid}: relation {rid}")
    for group in ("developments", "evaluations"):
        for u in record.get("units", {}).get(group, []):
            for key in ("model_id", "outcome_id", "dataset_id"):
                if u.get(key) not in idx: errors.append(f"{group}: {key}")
    for metric in record.get("performance_metrics", []):
        if metric.get("evaluation_id") not in idx or metric.get("model_id") not in idx: errors.append(f"metric {metric.get('metric_id')}: units")
        if not metric.get("evidence_ids") or set(metric["evidence_ids"]) - evidence_ids: errors.append(f"metric {metric.get('metric_id')}: evidence")
        if metric.get("reviewer_id") != "P2-CLAUDE-OPUS5" or metric.get("review_stage") != "P2": errors.append(f"metric {metric.get('metric_id')}: provenance")
    for visual in record.get("visual_objects", []):
        if visual.get("inventory_level") == "PANEL" and visual.get("parent_object_id") not in visual_ids: errors.append(f"visual {visual.get('object_id')}: parent")
        if set(visual.get("evidence_ids") or []) - evidence_ids: errors.append(f"visual {visual.get('object_id')}: evidence")
    return errors

def set_item(record, iid, value, rationale):
    for row in record["protocol_items"][iid]:
        row.update(value=value, reviewer_id=ADJUDICATOR, review_stage="CON", status="COMPLETE", rationale=rationale)

def apply_corpus_decision(record):
    sid, dec = record["study_id"], CORPUS_DECISIONS.get(record["study_id"])
    if not dec: return
    if sid == "KHM076":
        set_item(record, "ELG04", "N", dec["rationale"]); set_item(record, "ELG05", "DUPLICATE_RETRIEVAL", dec["rationale"])
        values = (("FAM03", "N"), ("FAM04", "Y"), ("FAM05", "Y"), ("FAM06", "Y"),
                  ("FAM07", "Y"), ("FAM08", "Y"), ("FAM09", dec["rationale"]), ("FAM10", "MERGE"), ("FAM01", "KHM100"))
        for iid, value in values: set_item(record, iid, value, dec["rationale"])
    elif sid == "KHM100":
        values = (("FAM03", "Y"), ("FAM04", "Y"), ("FAM05", "Y"), ("FAM06", "Y"),
                  ("FAM07", "Y"), ("FAM08", "Y"), ("FAM09", dec["rationale"]), ("FAM10", "MERGE"),
                  ("FAM01", "KHM100"), ("FAM02", 2))
        for iid, value in values: set_item(record, iid, value, dec["rationale"])
    record.setdefault("corpus_status", {}).update(dec)

def main():
    CON.mkdir(parents=True, exist_ok=True); FINAL.mkdir(parents=True, exist_ok=True)
    validation = {p.stem: load(p) for p in (WORK / "validation").glob("KHM*.json")}
    paths = sorted(P2.glob("KHM*_P2.json"))
    if len(paths) != 222: raise SystemExit(f"expected 222 P2 packets, found {len(paths)}")
    failures, finals, totals = {}, [], Counter()
    for path in paths:
        p2, sid = load(path), load(path)["study_id"]
        p1path = P1 / f"{sid}_P1.json"
        if not p1path.exists(): failures[sid] = ["P1 missing"]; continue
        errors = validate_p2(p2, validation.get(sid, {}))
        if errors: failures[sid] = errors; continue
        p1, disagreements, agreements = load(p1path), [], 0
        for iid, spec in SPEC.items():
            if spec["item_role"] not in REVIEWER_ROLES: continue
            a, b = normalized_rows(p1, iid), normalized_rows(p2, iid)
            if a == b: agreements += 1
            else: disagreements.append({"item_id": iid, "primary_unit": spec["primary_unit"], "P1": a, "P2": b,
                    "decision": "P2", "rationale": "Selected independently source-read, unit-complete P2; P1 was a legacy migration record."})
        final = copy.deepcopy(p2); final.update(file_role="FINAL", review_mode="coordinator_adjudicated_consensus")
        apply_corpus_decision(final)
        set_item(final, "QA09", "Y", "Blinded P2 passed source/evidence/unit validation.")
        set_item(final, "QA10", "Y", "P1-P2 comparison and coordinator adjudication completed.")
        set_item(final, "QA11", "P2 complete; evidence/unit validation PASS; P1-P2 comparison and coordinator adjudication complete.", "Final record retains P1/P2 provenance.")
        final["review_record"] = {"reviewer_id": ADJUDICATOR, "reviewer_type": "LLM_COORDINATOR", "review_stage": "CON",
            "review_mode": "rule_based_adjudication", "date": DATE, "status": "COMPLETE", "blind_to_other_reviewer": False,
            "scope": "Locked P1-P2 comparison; corpus decisions C13/C35-C38 and external-validation eligibility"}
        final["adjudication"] = {"status": "COMPLETE", "adjudicator_id": ADJUDICATOR, "date": DATE,
            "P1_file": f"P1/{sid}_P1.json", "P2_file": f"P2_blinded/{sid}_P2.json", "agreement_items": agreements,
            "adjudicated_items": len(disagreements), "resolution_policy": "Semantic-unit agreements retained; disagreements resolved to source-read P2; named corpus decisions override named items.",
            "corpus_decision": CORPUS_DECISIONS.get(sid), "disagreements": disagreements}
        body = json.dumps(final["protocol_items"], ensure_ascii=False, sort_keys=True).encode()
        final["protocol_items_sha256"] = hashlib.sha256(body).hexdigest()
        (FINAL / f"{sid}_final.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")
        con = {"protocol_version": "1.2", "study_id": sid, "file_role": "CON", "status": "AGREED",
               "adjudicator_id": ADJUDICATOR, "date": DATE, "agreement_items": agreements,
               "adjudicated_items": len(disagreements), "corpus_decision": CORPUS_DECISIONS.get(sid), "disagreements": disagreements}
        (CON / f"{sid}_CON.json").write_text(json.dumps(con, ensure_ascii=False, indent=2) + "\n")
        totals.update(studies=1, agreement_items=agreements, adjudicated_items=len(disagreements)); finals.append(final)
    if failures:
        report = {"status": "BLOCKED_VALIDATION", "failures": failures}
        (BASE / "ADJUDICATION_SUMMARY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        raise SystemExit(json.dumps({"status": report["status"], "failed_studies": len(failures)}))
    with (BASE / "KNHANES_studies_v1.2.jsonl").open("w") as f:
        for record in finals: f.write(json.dumps(record, ensure_ascii=False) + "\n")
    included = [r for r in finals if r.get("corpus_status", {}).get("include", r["protocol_items"]["ELG04"][0]["value"] == "Y")]
    summary = {"status": "COMPLETE", "date": DATE, "adjudicator_id": ADJUDICATOR,
      "reviewers": {"P1": "codex_primary_evidence_review", "P2": "P2-CLAUDE-OPUS5 (LLM_AGENT)"},
      "counts": dict(totals), "final_records": len(finals), "included_unique_studies": len(included),
      "task_counts": dict(Counter(r["protocol_items"]["TSK01"][0]["value"] for r in included)), "decisions": CORPUS_DECISIONS,
      "integrity_policy": "Signals remain in ADM09/ADM10 and conflicting_evidence; no study excluded solely for an unconfirmed integrity signal.",
      "retraction_policy": "KHM068 retained for corpus history but excluded from valid performance/methodological evidence."}
    (BASE / "ADJUDICATION_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
