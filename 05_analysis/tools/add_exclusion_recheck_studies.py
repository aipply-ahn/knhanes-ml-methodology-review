#!/usr/bin/env python3
"""Prompt 106: two further criterion-A additions found by rechecking every 'no eligible ML' exclusion (469 records:
NO_ML 387 + NO_ML_OR_DATASET 82) against title, abstract and reason text for a supervised non-regression learner.

22 records named such a learner; full texts were checked where the abstract was not decisive.  20 stay excluded
(logistic regression only, ML only in an exposure-product name, cost-effectiveness decision trees, reports with no
KNHANES analysis, conference abstracts, figure/table records, a review).  Two were misclassified at the original
eligibility pass and meet criterion A:

* KHM255 byeon2015feature (10.14569/ijacsa.2015.061213): C4.5 decision tree for stroke, KNHANES 2009.
* KHM256 zhang2026relationship (10.5114/aoms/221898): XGBoost with SHAP for generalised anxiety disorder,
  KNHANES 2001-2023.

Writes blank blinded P2 packets (same schema as tools/build_criterion_a_packets.py) and appends the two rows to
data/protocol_v1_2/criterion_a_additions.tsv and results/derived/criterion_a_rescreen.json (recheck block)."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/protocol_v1_2/P2_blinded"
TEMPLATE = json.loads((ROOT / "KNHANES_ML_study_audit_template_v1.2.json").read_text())
ADD = [("KHM255", "10.14569/ijacsa.2015.061213", "byeon2015feature", "C4.5 decision tree for stroke prevalence, KNHANES 2009 (full text checked)"),
       ("KHM256", "10.5114/aoms/221898", "zhang2026relationship", "XGBoost with SHAP for generalised anxiety disorder, KNHANES 2001-2023 (full text checked)")]
STAY = {
    "10.1097/iae.0000000000004776": "logistic regression only (KHM073 pattern)",
    "10.32388/kiru4o": "health-index framework; no supervised learner fitted to a KNHANES outcome in the abstract",
    "10.1007/s11517-024-03182-0": "ChatGPT-run logistic regression scoring system",
    "10.1186/s12889-025-21604-y": "survey logistic regression; ML only in the exposure product name",
    "10.21203/rs.3.rs-3930338/v1": "preprint of the previous record; same analysis",
    "10.3350/cmh.2021.0236": "cost-effectiveness decision tree; no KNHANES analysis",
    "10.3390/vaccines10060932": "cost-effectiveness decision tree; no KNHANES analysis",
    "10.1038/s41598-021-95341-8": "logistic-regression index",
    "10.1371/journal.pdig.0001486.s014": "supplementary-file record of an included study (KHM002)",
    "10.2139/ssrn.6872765": "SSRN preprint; full text not accessible (bot wall) and indexed abstract empty; not assessable",
    "10.1249/01.mss.0000678436.70420.41": "conference abstract only",
    "10.1111/ijcp.13391": "narrative review",
    "10.1096/fasebj.27.1_supplement.635.5": "conference abstract; dietary intake estimation",
    "10.7326/0003-4819-54-6-1146": "1961 article; 'boost' is a false match",
    "10.2196/preprints.29331": "preprint of the included retracted study 10.2196/29331",
    "10.1371/journal.pone.0323329.t002": "table record of another article",
    "10.1016/j.cdnut.2026.108945": "OpenAlex metadata merge: the DOI is a US child-diet article (Crossref), the indexed abstract is an unlinked conference abstract on Korean older adults (random forest, GLIM); isolated abstract, ineligible",
    "10.1681/asn.2024rggdf78f": "conference abstract only",
    "10.1093/ndt/gfaf116.1930": "conference abstract only",
    "10.2337/db25-1581-p": "conference abstract only",
}


def fileinfo(path, kind):
    b = (ROOT / path).read_bytes()
    return {"type": kind, "path": path, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def main():
    refs = json.loads((ROOT / "references/refs.json").read_text())
    by = {r.get("uid"): r for r in refs}
    tsv = ROOT / "data/protocol_v1_2/criterion_a_additions.tsv"
    lines = tsv.read_text().splitlines()
    assert lines[-1].startswith("KHM254"), lines[-1]
    R = json.loads((ROOT / "results/derived/criterion_a_rescreen.json").read_text())
    assert "exclusion_recheck" not in R
    for sid, uid, key, basis in ADD:
        ref = by[uid]
        assert ref["key"] == key
        files = [fileinfo(f"references/pdf/{key}.pdf", "main_pdf"), fileinfo(f"references/md/{key}.md", "extracted_markdown")]
        items = {}
        for iid, proto_rows in TEMPLATE["protocol_items"].items():
            proto = copy.deepcopy(proto_rows[0])
            proto.update({"unit_id": None, "related_ids": {}, "value": None, "value_status": "PENDING", "evidence_ids": [],
                          "reviewer_id": None, "review_stage": "P2", "status": "NOT_STARTED", "rationale": None})
            items[iid] = [proto]
        authors = [a.strip() for a in str(ref.get("authors") or "").split(",") if a.strip()]
        packet = {
            "protocol_version": "1.2", "study_id": sid, "canonical_key": key, "file_role": "P2", "review_mode": "independent_review",
            "metadata": {"title": ref["title"], "publication_year": int(ref["year"]), "authors": authors, "journal": ref.get("journal") or "NR",
                         "doi": ref.get("doi") or "NR", "language": "Not systematically coded"},
            "source_package": {
                "main_text": {"availability": "ACQUIRED", "review_status": "COMPLETE", "access_date": "2026-09-30", "sha256": files[0]["sha256"],
                              "files": files, "notes": "Criterion-A addition found by the exclusion recheck (prompt 106); single independent review."},
                "supplement_files": [],
                "appendix": {"availability": "NOT_APPLICABLE", "review_status": "NOT_APPLICABLE", "access_date": "2026-09-30", "sha256": None, "files": [], "notes": None},
                "repository": {"availability": "NOT_IDENTIFIED", "review_status": "NOT_APPLICABLE", "access_date": "2026-09-30", "sha256": None, "files": [], "notes": None}},
            "units": {"reports": [], "datasets": [], "outcomes": [], "models": [], "developments": [], "evaluations": []},
            "evidence_registry": [], "protocol_items": items, "performance_metrics": [], "best_model_selections": [], "visual_objects": [],
            "review_record": {"reviewer_id": None, "review_stage": "P2", "review_mode": "independent_review", "date": None,
                              "status": "NOT_STARTED", "blind_to_other_reviewer": True},
            "adjudication": {"status": "NOT_APPLICABLE_AT_P2", "P1_file": None, "P2_file": f"P2_blinded/{sid}_P2.json",
                             "consensus_entries": [], "unresolved": [], "final_value_rule": "single review (criterion-A addition)"},
            "blinding": {"P1_values_included": False, "P1_rationales_included": False, "P1_evidence_selection_included": False,
                         "note": "Use the source-package files and protocol instrument only."}}
        dst = OUT / f"{sid}_P2.json"
        assert not dst.exists(), dst
        dst.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        lines.append(f"{sid}\t{uid}\t{key}\t{ref['year']}\t{','.join(f['path'] for f in files)}")
    tsv.write_text("\n".join(lines) + "\n")
    R["exclusion_recheck"] = {"date": "2026-09-30", "scope": "all 469 NO_ML / NO_ML_OR_DATASET exclusions; learner-term search of title, abstract and reason",
                              "records_with_learner_term": 22, "added": [{"study_id": s, "uid": u, "key": k, "basis": b} for s, u, k, b in ADD],
                              "kept_excluded": STAY, "provenance": "tools/add_exclusion_recheck_studies.py"}
    assert len(STAY) + len(ADD) == 22
    (ROOT / "results/derived/criterion_a_rescreen.json").write_text(json.dumps(R, ensure_ascii=False, indent=2) + "\n")
    print("\n".join(lines[-2:]))


if __name__ == "__main__":
    main()
