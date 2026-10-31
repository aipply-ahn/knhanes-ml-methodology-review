#!/usr/bin/env python3
"""Prompt 106: create blank blinded P2 packets for the 32 criterion-A additions (KHM223...), same schema as
tools/build_protocol_v1_2_p2_packets.py, with metadata and source package taken from references/refs.json.
Writes data/protocol_v1_2/P2_blinded/KHMxxx_P2.json (new files only) and data/protocol_v1_2/criterion_a_additions.tsv."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/protocol_v1_2/P2_blinded"
TEMPLATE = json.loads((ROOT / "KNHANES_ML_study_audit_template_v1.2.json").read_text())
R = json.loads((ROOT / "results/derived/criterion_a_rescreen.json").read_text())
LINKED = R["projection"]["linked_to_included"]
refs = json.loads((ROOT / "references/refs.json").read_text())
refs = refs if isinstance(refs, list) else refs.get("records", [])
BY = {r.get("uid"): r for r in refs}
KCI = {"kci:" + r["kci_id"]: r for r in json.loads((ROOT / "references/kci_refs.json").read_text())}


def fileinfo(path, kind):
    p = ROOT / path
    b = p.read_bytes()
    return {"type": kind, "path": path, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def main():
    rows = [r for r in R["new_include"] if r["uid"] not in LINKED]
    rows.sort(key=lambda r: (r["year"], r["uid"]))
    assert len(rows) == 32
    existing = sorted(OUT.glob("KHM*_P2.json"))
    assert existing[-1].name == "KHM222_P2.json", existing[-1]
    table = ["study_id\tuid\tcanonical_key\tyear\tsources"]
    for i, r in enumerate(rows, start=223):
        sid = f"KHM{i:03d}"
        ref = BY[r["uid"]]
        key = ref["key"]
        files = []
        if ref.get("pdf_file") and (ROOT / "references/pdf" / ref["pdf_file"]).exists():
            files.append(fileinfo(f"references/pdf/{ref['pdf_file']}", "main_pdf"))
        if (ROOT / f"references/md/{key}.md").exists():
            files.append(fileinfo(f"references/md/{key}.md", "extracted_markdown"))
        assert files, sid
        full = any(f["type"] == "main_pdf" for f in files)
        k = KCI.get(r["uid"], {})
        authors = ref.get("author_list") or [a.strip() for a in str(ref.get("authors") or "").split(" and ") if a.strip()]
        items = {}
        for iid, proto_rows in TEMPLATE["protocol_items"].items():
            proto = copy.deepcopy(proto_rows[0])
            proto.update({"unit_id": None, "related_ids": {}, "value": None, "value_status": "PENDING", "evidence_ids": [],
                          "reviewer_id": None, "review_stage": "P2", "status": "NOT_STARTED", "rationale": None})
            items[iid] = [proto]
        packet = {
            "protocol_version": "1.2", "study_id": sid, "canonical_key": key, "file_role": "P2", "review_mode": "independent_review",
            "metadata": {"title": ref.get("title") or k.get("title"), "publication_year": int(r["year"]), "authors": authors,
                         "journal": ref.get("journal") or k.get("journal") or "NR", "doi": ref.get("doi") or k.get("doi") or "NR",
                         "language": "Not systematically coded"},
            "source_package": {
                "main_text": {"availability": "ACQUIRED" if full else "PARTIAL", "review_status": "COMPLETE" if full else "PARTIAL",
                              "access_date": "2026-09-28", "sha256": files[0]["sha256"], "files": files,
                              "notes": "Criterion-A re-screen addition (prompt 106); single independent review."},
                "supplement_files": [],
                "appendix": {"availability": "NOT_APPLICABLE", "review_status": "NOT_APPLICABLE", "access_date": "2026-09-28", "sha256": None, "files": [], "notes": None},
                "repository": {"availability": "NOT_IDENTIFIED", "review_status": "NOT_APPLICABLE", "access_date": "2026-09-28", "sha256": None, "files": [], "notes": None}},
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
        table.append(f"{sid}\t{r['uid']}\t{key}\t{r['year']}\t{','.join(f['path'] for f in files)}")
    (ROOT / "data/protocol_v1_2/criterion_a_additions.tsv").write_text("\n".join(table) + "\n")
    print("\n".join(table))


if __name__ == "__main__":
    main()
