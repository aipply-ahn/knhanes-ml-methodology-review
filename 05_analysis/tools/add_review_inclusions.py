#!/usr/bin/env python3
"""Author decisions D23-D26 (2026-10-24): four reports catalogued as regression-only/unsupervised were re-read in full
text and fitted a supervised learner outside the regression family to a KNHANES health outcome, so they are included.

* KHM257 oh2013diabetic (X009, 10.1186/1472-6947-13-106): SVM, ANN, RF, naive Bayes, k-NN vs LASSO, diabetic retinopathy.
* KHM258 jeong2024investigating (X057, 10.3390/nu16050724): PyCaret classifiers (LGBM, RF, ET, DT, GBC), metabolic syndrome.
* KHM259 choi2025phenotypic (X068, 10.2139/ssrn.5347786): 14 PyCaret classifiers predicting asthma (full text from the author).
* KHM260 lee2025risk (X080, kci:ART003234795): random forest (Boruta) importance for low back pain (full text from the author).

Writes references/md for the two author-supplied PDFs (same header as tools/make_paper_md.py) and blank blinded P2
packets (same schema as tools/build_criterion_a_packets.py). Two independent extractions follow
(P2_work/answers_A, answers_B), then an adjudicated answers/<ID>.json and tools/p2_assemble.py.
"""
import copy
import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/protocol_v1_2/P2_blinded"
TEMPLATE = json.loads((ROOT / "KNHANES_ML_study_audit_template_v1.2.json").read_text())
ADD = [("KHM257", "10.1186/1472-6947-13-106", "X009"), ("KHM258", "10.3390/nu16050724", "X057"),
       ("KHM259", "10.2139/ssrn.5347786", "X068"), ("KHM260", "kci:ART003234795", "X080")]
DATE = "2026-10-24"


def refs():
    r = json.loads((ROOT / "references/refs.json").read_text())
    by = {x.get("uid"): x for x in (r if isinstance(r, list) else r.get("records", []))}
    for k in json.loads((ROOT / "references/kci_refs.json").read_text()):
        by.setdefault("kci:" + k["kci_id"], dict(k, uid="kci:" + k["kci_id"]))
    return by


def fileinfo(path, kind):
    b = (ROOT / path).read_bytes()
    return {"type": kind, "path": path, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def write_md(ref, key):
    pdf = ROOT / f"references/pdf/{key}.pdf"
    md = ROOT / f"references/md/{key}.md"
    if not pdf.exists() or "full_text: true" in (md.read_text() if md.exists() else ""):
        return
    au = ref.get("authors") or ""
    head = (f"---\nkey: {key}\ntitle: \"{(ref.get('title') or '').replace(chr(34), chr(39))}\"\nauthors: \"{au[:300]}\"\n"
            f"journal: \"{ref.get('journal') or ''}\"\nyear: {ref.get('year')}\ndoi: {ref.get('doi') or ''}\npmid: None\n"
            f"verdict: INCLUDE\ncategory: None\nfull_text: true\n---\n\n# {ref.get('title')}\n\n**{au[:300]}** · {ref.get('journal')} · {ref.get('year')}\n\n")
    doc = fitz.open(pdf)
    body = "".join(f"\n\n<!-- page {i + 1} -->\n\n" + p.get_text() for i, p in enumerate(doc))
    md.write_text(head + body)


def main():
    by = refs()
    for sid, uid, xid in ADD:
        ref = by[uid]
        key = ref.get("key") or ref.get("canonical_key")
        write_md(ref, key)
        dst = OUT / f"{sid}_P2.json"
        if dst.exists():
            continue
        files = [fileinfo(f"references/pdf/{key}.pdf", "main_pdf"), fileinfo(f"references/md/{key}.md", "extracted_markdown")]
        authors = [a.strip() for a in str(ref.get("authors") or "").replace(" and ", ",").split(",") if a.strip()]
        items = {}
        for iid, proto_rows in TEMPLATE["protocol_items"].items():
            proto = copy.deepcopy(proto_rows[0])
            proto.update({"unit_id": None, "related_ids": {}, "value": None, "value_status": "PENDING", "evidence_ids": [],
                          "reviewer_id": None, "review_stage": "P2", "status": "NOT_STARTED", "rationale": None})
            items[iid] = [proto]
        packet = {
            "protocol_version": "1.2", "study_id": sid, "canonical_key": key, "file_role": "P2", "review_mode": "independent_review",
            "metadata": {"title": ref.get("title"), "publication_year": int(ref.get("year")), "authors": authors,
                         "journal": ref.get("journal") or "NR", "doi": ref.get("doi") or "NR", "language": "Not systematically coded"},
            "source_package": {
                "main_text": {"availability": "ACQUIRED", "review_status": "COMPLETE", "access_date": DATE, "sha256": files[0]["sha256"],
                              "files": files, "notes": f"Author decision (review loop {DATE}): {xid} re-read in full text and included; two independent extractions."},
                "supplement_files": [],
                "appendix": {"availability": "NOT_APPLICABLE", "review_status": "NOT_APPLICABLE", "access_date": DATE, "sha256": None, "files": [], "notes": None},
                "repository": {"availability": "NOT_IDENTIFIED", "review_status": "NOT_APPLICABLE", "access_date": DATE, "sha256": None, "files": [], "notes": None}},
            "units": {"reports": [], "datasets": [], "outcomes": [], "models": [], "developments": [], "evaluations": []},
            "evidence_registry": [], "protocol_items": items, "performance_metrics": [], "best_model_selections": [], "visual_objects": [],
            "review_record": {"reviewer_id": None, "review_stage": "P2", "review_mode": "independent_review", "date": None,
                              "status": "NOT_STARTED", "blind_to_other_reviewer": True},
            "adjudication": {"status": "NOT_APPLICABLE_AT_P2", "P1_file": None, "P2_file": f"P2_blinded/{sid}_P2.json",
                             "consensus_entries": [], "unresolved": [], "final_value_rule": "two independent extractions, adjudicated (review-loop inclusion)"},
            "blinding": {"P1_values_included": False, "P1_rationales_included": False, "P1_evidence_selection_included": False,
                         "note": "Use the source-package files and protocol instrument only."}}
        dst.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        print(sid, key, xid)


if __name__ == "__main__":
    main()
