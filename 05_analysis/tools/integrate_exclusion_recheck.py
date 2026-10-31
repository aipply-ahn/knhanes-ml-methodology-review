#!/usr/bin/env python3
"""Prompt 106: integrate the two criterion-A studies found by the exclusion recheck (KHM255, KHM256).

Same record rules as tools/integrate_criterion_a.py step 1 (single blinded P2 review -> FINAL, corpus_status include)
and step 3 (verdict INCLUDE with study_id).  Selection flow: both were NO_ML_OR_DATASET exclusions
('no eligible analysis'), so that reason drops by 2 and eligible reports and unique studies rise by 2.
The OpenAlex duplicate of byeon2015feature (W2525892710) was already counted among the linked related reports.
Run once; refuses to run unless both P2 packets are COMPLETE."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
DER = ROOT / "results/derived"
DATE = "2026-09-30"
ADJ = "criterion_a_single_review_integration"


def load(p):
    return json.loads(Path(p).read_text())


def dump(obj, p):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def set_item(rec, iid, value, why):
    for row in rec["protocol_items"][iid]:
        row.update(value=value, value_status="ANSWERED", reviewer_id=ADJ, review_stage="CON", status="COMPLETE", rationale=why)


def main():
    R = load(DER / "criterion_a_rescreen.json")
    adds = R["exclusion_recheck"]["added"]
    F = load(DER / "final_selection_flow.json")
    if "exclusion_recheck" in F:
        print("already integrated"); return
    V = load(DER / "verdicts.json")
    for a in adds:
        sid, uid = a["study_id"], a["uid"]
        p2 = load(BASE / f"P2_blinded/{sid}_P2.json")
        assert p2["review_record"].get("status") == "COMPLETE", sid
        assert V[uid]["verdict"] == "EXCLUDE" and V[uid]["reason"].startswith("NO_ML_OR_DATASET"), uid
        fin = copy.deepcopy(p2)
        fin.update(file_role="FINAL", review_mode="single_review_criterion_a")
        set_item(fin, "QA09", "Y", "Blinded P2 passed source/evidence/unit validation.")
        set_item(fin, "QA10", "N", "Single review: added after the exclusion recheck under criterion A; no second independent review.")
        set_item(fin, "QA11", "P2 complete; evidence/unit validation PASS; single review (criterion-A exclusion recheck).", "No P1 record exists.")
        fin["review_record"] = {"reviewer_id": ADJ, "reviewer_type": "LLM_COORDINATOR", "review_stage": "CON", "review_mode": "single_review",
                                "date": DATE, "status": "COMPLETE", "blind_to_other_reviewer": True,
                                "scope": "Criterion-A exclusion-recheck addition; the blinded P2 record is final (author final human review applies as for all records)."}
        decision = {"decision": "INCLUDE_CRITERION_A", "include": True, "source_uid": uid}
        fin["adjudication"] = {"status": "COMPLETE", "adjudicator_id": ADJ, "date": DATE, "P1_file": None, "P2_file": f"P2_blinded/{sid}_P2.json",
                               "agreement_items": None, "adjudicated_items": 0, "resolution_policy": "Single review; P2 values are final.",
                               "corpus_decision": decision, "disagreements": []}
        fin["corpus_status"] = dict(decision, rationale=f"{a['basis']}; excluded at the original eligibility pass and restored by the criterion-A exclusion recheck.")
        fin["protocol_items_sha256"] = hashlib.sha256(json.dumps(fin["protocol_items"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        dump(fin, BASE / f"final/{sid}_final.json")
        dump({"protocol_version": "1.2", "study_id": sid, "file_role": "CON", "status": "SINGLE_REVIEW", "adjudicator_id": ADJ, "date": DATE,
              "agreement_items": None, "adjudicated_items": 0, "corpus_decision": fin["corpus_status"], "disagreements": []},
             BASE / f"final_consensus/{sid}_CON.json")
        prev = V[uid]["reason"]
        V[uid].update(verdict="INCLUDE", reason=f"Criterion A (exclusion recheck): {a['basis']} ({sid})", study_id=sid,
                      criterion_a={"date": DATE, "previous_verdict": "EXCLUDE", "previous_reason": prev})
    dump(V, DER / "verdicts.json")
    f = F["flow"]
    r = f["report_exclusion_reasons"]
    before = {k: f[k] for k in ("ineligible_reports", "reports_excluded_total", "eligible_reports_entering_family_linkage", "unique_full_report_studies_included")}
    r["no_eligible_knhanes_analysis"] -= len(adds)
    f["ineligible_reports"] -= len(adds)
    f["reports_excluded_total"] -= len(adds)
    f["eligible_reports_entering_family_linkage"] += len(adds)
    f["unique_full_report_studies_included"] += len(adds)
    assert f["reports_excluded_total"] + f["eligible_reports_entering_family_linkage"] == f["records_assessed_against_eligibility"]
    assert f["eligible_reports_entering_family_linkage"] - f["additional_or_companion_reports_linked"] == f["unique_full_report_studies_included"]
    assert f["ineligible_reports"] == sum(v for k, v in r.items() if k != "ml_adjacent_catalogued_separately")
    F["exclusion_recheck"] = {"date": DATE, "before": before, "added": [a["study_id"] for a in adds],
                              "provenance": "tools/add_exclusion_recheck_studies.py; tools/integrate_exclusion_recheck.py"}
    dump(F, DER / "final_selection_flow.json")
    print(json.dumps({k: f[k] for k in before}), r)


if __name__ == "__main__":
    main()
