#!/usr/bin/env python3
"""Prompt 106: apply criterion A to the study records.

1. KHM223-KHM254 (32 re-screen additions, single blinded P2 review, p2_assemble PASS) become FINAL records
   (file_role FINAL, review_mode single_review_criterion_a, corpus_status include).
2. KHM073, KHM129, KHM156 fail criterion A: corpus_status include False (the record itself is kept).
3. verdicts.json / screen.json: the 33 re-screened uids become INCLUDE (tier T1; the KHM072 duplicate becomes
   DUPLICATE of KHM072); the 3 dropped studies' uids become EXCLUDE with the criterion-A reason.
4. final_selection_flow.json and study_index.tsv are rebuilt from the updated verdicts.

Run once; refuses to run if any P2 packet is not COMPLETE.
"""
import copy
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
DER = ROOT / "results/derived"
DATE = "2026-09-28"
ADJ = "criterion_a_single_review_integration"
DROP = {
    "KHM156": ("EXCLUDE_CRITERION_A_NO_DESIGNATED_OUTCOME", "Latent Dirichlet allocation topic model of diets; no model fitted to a designated outcome (criterion A, prompt 105)."),
    "KHM073": ("EXCLUDE_CRITERION_A_REGRESSION_ONLY", "Only logistic regression was fitted ('machine learning-based logistic regression'); regression family (criterion A, prompt 105)."),
    "KHM129": ("EXCLUDE_CRITERION_A_REGRESSION_ONLY", "WEKA attribute filters with logistic regression as the only classifier; regression family (criterion A, prompt 105)."),
}


def load(p):
    return json.loads(Path(p).read_text())


def dump(obj, p):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def set_item(rec, iid, value, why):
    for row in rec["protocol_items"][iid]:
        row.update(value=value, value_status="ANSWERED", reviewer_id=ADJ, review_stage="CON", status="COMPLETE", rationale=why)


def main():
    adds = list(csv.DictReader(open(BASE / "criterion_a_additions.tsv"), delimiter="\t"))
    assert len(adds) == 32
    # 1. finals for additions
    for a in adds:
        sid = a["study_id"]
        p2 = load(BASE / f"P2_blinded/{sid}_P2.json")
        assert p2["review_record"].get("status") == "COMPLETE", sid
        fin = copy.deepcopy(p2)
        fin.update(file_role="FINAL", review_mode="single_review_criterion_a")
        set_item(fin, "QA09", "Y", "Blinded P2 passed source/evidence/unit validation.")
        set_item(fin, "QA10", "N", "Single review: added after the criterion-A re-screen; no second independent review.")
        set_item(fin, "QA11", "P2 complete; evidence/unit validation PASS; single review (criterion-A addition).", "No P1 record exists.")
        fin["review_record"] = {"reviewer_id": ADJ, "reviewer_type": "LLM_COORDINATOR", "review_stage": "CON", "review_mode": "single_review",
                                "date": DATE, "status": "COMPLETE", "blind_to_other_reviewer": True,
                                "scope": "Criterion-A re-screen addition; the blinded P2 record is final (author final human review applies as for all records)."}
        fin["adjudication"] = {"status": "COMPLETE", "adjudicator_id": ADJ, "date": DATE, "P1_file": None, "P2_file": f"P2_blinded/{sid}_P2.json",
                               "agreement_items": None, "adjudicated_items": 0, "resolution_policy": "Single review; P2 values are final.",
                               "corpus_decision": {"decision": "INCLUDE_CRITERION_A", "include": True, "source_uid": a["uid"]}, "disagreements": []}
        fin["corpus_status"] = {"decision": "INCLUDE_CRITERION_A", "include": True, "source_uid": a["uid"],
                                "rationale": "Single decision tree (or other learner outside the regression family) fitted to a designated outcome; added by the criterion-A re-screen."}
        body = json.dumps(fin["protocol_items"], ensure_ascii=False, sort_keys=True).encode()
        fin["protocol_items_sha256"] = hashlib.sha256(body).hexdigest()
        dump(fin, BASE / f"final/{sid}_final.json")
        dump({"protocol_version": "1.2", "study_id": sid, "file_role": "CON", "status": "SINGLE_REVIEW", "adjudicator_id": ADJ, "date": DATE,
              "agreement_items": None, "adjudicated_items": 0, "corpus_decision": fin["corpus_status"], "disagreements": []},
             BASE / f"final_consensus/{sid}_CON.json")
    # 2. drops
    for sid, (dec, why) in DROP.items():
        p = BASE / f"final/{sid}_final.json"
        rec = load(p)
        assert rec.get("corpus_status", {}).get("include", True)
        set_item(rec, "ELG04", "N", why)
        rec["corpus_status"] = {"decision": dec, "include": False, "rationale": why}
        rec["adjudication"]["corpus_decision"] = rec["corpus_status"]
        rec["protocol_items_sha256"] = hashlib.sha256(json.dumps(rec["protocol_items"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        dump(rec, p)
    # 3. verdicts / screen
    V = load(DER / "verdicts.json")
    S = load(DER / "screen.json")
    srow = {r["uid"]: r for r in S["rows"]}
    R = load(DER / "criterion_a_rescreen.json")
    linked = R["projection"]["linked_to_included"]
    sid_by_uid = {a["uid"]: a["study_id"] for a in adds}
    for row in R["new_include"]:
        u = row["uid"]
        v = V[u]
        assert v["verdict"] == "INCLUDE_ADJACENT", u
        if u in linked:
            v.update(verdict="DUPLICATE", reason=f"Same report as included {linked[u]} (Korean/English title pair; criterion-A family linkage)")
        else:
            v.update(verdict="INCLUDE", reason=f"Criterion A: {row['basis']} ({sid_by_uid[u]})", study_id=sid_by_uid[u])
        v["criterion_a"] = {"date": DATE, "previous_verdict": "INCLUDE_ADJACENT"}
        s = srow[u]
        s["tier"] = "T1"
        s["t1"] = sorted(set((s.get("t1") or []) + ["decision tree"]))
    fin_uid = {}
    for sid in DROP:
        rec = load(BASE / f"final/{sid}_final.json")
        doi = str(rec["metadata"].get("doi") or "").lower()
        hits = [u for u, v in V.items() if v.get("verdict") == "INCLUDE" and (u.lower() == doi or u.lower().endswith(doi) and doi not in ("", "nr"))]
        if not hits:
            key = rec["canonical_key"]
            refs = load(ROOT / "references/refs.json")
            refs = refs if isinstance(refs, list) else refs.get("records", [])
            hits = [r["uid"] for r in refs if r.get("key") == key and V.get(r.get("uid"), {}).get("verdict") == "INCLUDE"]
        assert len(hits) == 1, (sid, hits)
        fin_uid[sid] = hits[0]
        dec, why = DROP[sid]
        tag = "NO_ML" if "REGRESSION" in dec else "NO_OUTCOME_MODEL"
        V[hits[0]].update(verdict="EXCLUDE", reason=f"{tag}: {why}", criterion_a={"date": DATE, "previous_verdict": "INCLUDE", "study_id": sid})
    dump(V, DER / "verdicts.json")
    dump(S, DER / "screen.json")
    # 4. selection flow: records assessed, exclusion reasons, included reports and studies
    F = load(DER / "final_selection_flow.json")
    f = F["flow"]
    old = dict(f, report_exclusion_reasons=dict(f["report_exclusion_reasons"]))
    r = f["report_exclusion_reasons"]
    added_reports = len(R["new_include"]) - len(linked)          # 32 new reports (one per new study)
    r["ml_adjacent_catalogued_separately"] -= len(R["new_include"])  # 33 leave the adjacent list
    r["no_eligible_machine_learning"] += sum(1 for s in DROP if "REGRESSION" in DROP[s][0])
    r["other_or_unassessable"] += sum(1 for s in DROP if "REGRESSION" not in DROP[s][0])
    f["ml_adjacent_reports_catalogued"] = r["ml_adjacent_catalogued_separately"]
    f["ineligible_reports"] = sum(v for k, v in r.items() if k != "ml_adjacent_catalogued_separately")
    f["eligible_reports_entering_family_linkage"] = old["eligible_reports_entering_family_linkage"] + added_reports + len(linked) - len(DROP)
    f["additional_or_companion_reports_linked"] = old["additional_or_companion_reports_linked"] + len(linked)
    f["unique_full_report_studies_included"] = old["unique_full_report_studies_included"] + added_reports - len(DROP)
    f["reports_excluded_total"] = f["ineligible_reports"] + f["ml_adjacent_reports_catalogued"]
    assert f["reports_excluded_total"] + f["eligible_reports_entering_family_linkage"] == f["records_assessed_against_eligibility"], f
    assert f["eligible_reports_entering_family_linkage"] - f["additional_or_companion_reports_linked"] == f["unique_full_report_studies_included"]
    F["criterion_a"] = {"date": DATE, "before": {k: old[k] for k in ("ineligible_reports", "ml_adjacent_reports_catalogued", "reports_excluded_total",
                        "eligible_reports_entering_family_linkage", "additional_or_companion_reports_linked", "unique_full_report_studies_included")},
                        "added_studies": added_reports, "linked_companion": linked, "dropped_studies": sorted(DROP),
                        "provenance": "tools/integrate_criterion_a.py; results/derived/criterion_a_rescreen.json"}
    dump(F, DER / "final_selection_flow.json")
    print(json.dumps({"finals_written": len(adds), "dropped": fin_uid,
                      "verdicts": dict(Counter(v["verdict"] for u, v in V.items() if srow.get(u, {}).get("tier") not in (None, "", "--")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
