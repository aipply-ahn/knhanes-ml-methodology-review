#!/usr/bin/env python3
"""Author decisions D23-D26 (2026-10-24): integrate the review-loop inclusions (tools/add_review_inclusions.py).

    python tools/integrate_review_inclusions.py KHM257 KHM259 KHM260

Same record rules as tools/integrate_exclusion_recheck.py: the adjudicated P2 record (two independent extractions,
data/protocol_v1_2/P2_work/adjudication/<ID>.tsv) becomes FINAL with corpus_status include; the verdict becomes
INCLUDE with study_id (key review_inclusion, so the study is not counted as added under the final criterion: each
fitted a learner the earlier criterion already accepted). Selection flow: these were catalogued as regression-only or
unsupervised reports, so that catalogue and the excluded total drop by one each, and eligible reports and unique
studies rise by one each. Idempotent per study."""
import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
DER = ROOT / "results/derived"
DATE = "2026-10-24"
ADJ = "review_loop_two_extraction_adjudication"
UID = {"KHM257": ("10.1186/1472-6947-13-106", "X009"), "KHM258": ("10.3390/nu16050724", "X057"),
       "KHM259": ("10.2139/ssrn.5347786", "X068"), "KHM260": ("kci:ART003234795", "X080")}
# D24 A: the classifiers target K-means cluster membership (as KHM059); importance = cluster separation, not disease risk.
BASIS = {"KHM258": "the full text shows tree-based PyCaret classifiers trained on K-means nutrient-intake cluster membership (as KHM059); "
                   "their importance describes cluster separation, not metabolic-syndrome risk"}


def load(p):
    return json.loads(Path(p).read_text())


def dump(obj, p):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def set_item(rec, iid, value, why):
    for row in rec["protocol_items"][iid]:
        row.update(value=value, value_status="ANSWERED", reviewer_id=ADJ, review_stage="CON", status="COMPLETE", rationale=why)


def main(sids):
    V = load(DER / "verdicts.json")
    F = load(DER / "final_selection_flow.json")
    done = set(F.get("review_inclusions", {}).get("added", []))
    new = [s for s in sids if s not in done]
    for sid in new:
        uid, xid = UID[sid]
        p2 = load(BASE / f"P2_blinded/{sid}_P2.json")
        assert p2["review_record"].get("status") == "COMPLETE", sid
        assert V[uid]["verdict"] == "INCLUDE_ADJACENT", (uid, V[uid]["verdict"])
        rows = list(csv.reader(open(BASE / f"P2_work/adjudication/{sid}.tsv", encoding="utf-8"), delimiter="\t"))[1:]
        n_diff = sum(r[2] != r[3] for r in rows if len(r) > 3)  # agreement-only rows excluded
        fin = copy.deepcopy(p2)
        fin.update(file_role="FINAL", review_mode="two_extractions_adjudicated")
        set_item(fin, "QA09", "Y", "Adjudicated P2 passed source/evidence/unit validation.")
        set_item(fin, "QA10", "Y", "Two independent AI extractions (answers_A, answers_B), differences adjudicated against the source.")
        set_item(fin, "QA11", f"Two extractions; {n_diff} differences adjudicated (P2_work/adjudication/{sid}.tsv); validation PASS.", "Review-loop inclusion (author decision).")
        fin["review_record"] = {"reviewer_id": ADJ, "reviewer_type": "LLM_COORDINATOR", "review_stage": "CON", "review_mode": "two_extractions_adjudicated",
                                "date": DATE, "status": "COMPLETE", "blind_to_other_reviewer": True,
                                "scope": f"{xid} re-read in full text in the Additional Data 1 review and included by author decision; author final check applies as for all records."}
        decision = {"decision": "INCLUDE_REVIEW_LOOP", "include": True, "source_uid": uid}
        fin["adjudication"] = {"status": "COMPLETE", "adjudicator_id": ADJ, "date": DATE, "P1_file": None, "P2_file": f"P2_blinded/{sid}_P2.json",
                               "agreement_items": None, "adjudicated_items": n_diff, "resolution_policy": "Two independent extractions; differences settled against the source.",
                               "corpus_decision": decision, "disagreements": []}
        basis = BASIS.get(sid, "the full text shows a supervised learner outside the regression family fitted to a KNHANES health outcome")
        fin["corpus_status"] = dict(decision, rationale=f"{xid}: catalogued as regression-only/unsupervised at screening; {basis} (author decision, review loop {DATE}).")
        fin["protocol_items_sha256"] = hashlib.sha256(json.dumps(fin["protocol_items"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        dump(fin, BASE / f"final/{sid}_final.json")
        (BASE / "final_consensus").mkdir(exist_ok=True)
        dump({"protocol_version": "1.2", "study_id": sid, "file_role": "CON", "status": "TWO_EXTRACTIONS_ADJUDICATED", "adjudicator_id": ADJ, "date": DATE,
              "agreement_items": None, "adjudicated_items": n_diff, "corpus_decision": fin["corpus_status"], "disagreements": []},
             BASE / f"final_consensus/{sid}_CON.json")
        prev = V[uid]["reason"]
        V[uid].update(verdict="INCLUDE", reason=f"Review loop {DATE}: {BASIS.get(sid, 'full text shows a supervised non-regression learner fitted to a KNHANES health outcome')} ({sid}, was {xid})",
                      study_id=sid, review_inclusion={"date": DATE, "previous_verdict": "INCLUDE_ADJACENT", "previous_reason": prev})
    if not new:
        print("nothing to integrate"); return
    dump(V, DER / "verdicts.json")
    f = F["flow"]; r = f["report_exclusion_reasons"]
    before = {k: f[k] for k in ("ml_adjacent_reports_catalogued", "reports_excluded_total", "eligible_reports_entering_family_linkage", "unique_full_report_studies_included")}
    n = len(new)
    f["ml_adjacent_reports_catalogued"] -= n; r["ml_adjacent_catalogued_separately"] -= n
    f["reports_excluded_total"] -= n
    f["eligible_reports_entering_family_linkage"] += n; f["unique_full_report_studies_included"] += n
    assert f["reports_excluded_total"] + f["eligible_reports_entering_family_linkage"] == f["records_assessed_against_eligibility"]
    assert f["eligible_reports_entering_family_linkage"] - f["additional_or_companion_reports_linked"] == f["unique_full_report_studies_included"]
    assert f["ineligible_reports"] + f["ml_adjacent_reports_catalogued"] == f["reports_excluded_total"]
    ri = F.setdefault("review_inclusions", {"date": DATE, "added": [], "before": before, "provenance": "tools/add_review_inclusions.py; tools/integrate_review_inclusions.py"})
    ri["added"] += new
    dump(F, DER / "final_selection_flow.json")
    print(json.dumps({k: f[k] for k in before}), new)


if __name__ == "__main__":
    main(sys.argv[1:])
