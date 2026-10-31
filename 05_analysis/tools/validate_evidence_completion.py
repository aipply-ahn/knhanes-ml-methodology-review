#!/usr/bin/env python3
"""Check repaired source data and delivered evidence rows independently."""
import copy
import csv
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook
from complete_protocol_evidence import apply_repairs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prompts/implementation_records/evidence_completion_20260924"


def main():
    decisions = json.loads((ROOT / "data/protocol_v1_3/evidence_repairs_20260924.json").read_text())
    closure = json.loads((ROOT / "data/protocol_v1_3/evidence_resolution_20260924.json").read_text())
    decisions["statistical_analyses"]["KHM038"] = closure["statistical_analysis"]
    aggregate = json.loads((ROOT / "data/protocol_v1_3/purpose_evidence_addendum.json").read_text())
    source = {r["study_id"]: r for r in aggregate["records"]}
    path = ROOT / "manuscript/bmc_supplementary_table_s7.xlsx"
    wb = load_workbook(path, read_only=True, data_only=True)
    public = {r[1]: r for r in list(wb["RECORD_DETAILS"].values)[1:]}
    gaps, caution, repaired = [], [], []
    criteria_count = analysis_count = 0
    for sid, record in source.items():
        doc = json.loads((ROOT / f"data/protocol_v1_2/final/{sid}_final.json").read_text())
        assert doc["adjudication"]["purpose_evidence_v1_3"] == record, sid
        check_doc = copy.deepcopy(doc)
        assert apply_repairs(check_doc, copy.deepcopy(record), decisions) == record, sid
        assert check_doc == doc, f"Non-idempotent source anchors: {sid}"
        anchors = {e["evidence_id"]: e for e in doc["evidence_registry"]}
        assert len(anchors) == len(doc["evidence_registry"]), sid
        for spec in decisions.get("source_spans", {}).get(sid, []) + closure.get("source_spans", {}).get(sid, []):
            anchor = anchors[spec["evidence_id"]]
            assert anchor["excerpt"] in (ROOT / anchor["source_file"]).read_text()
        if sid in decisions["method_criteria"]:
            criteria_count += 1
            method = record["method_research"]
            assert method["primary_evaluation_criteria"] == decisions["method_criteria"][sid]["criteria"]
            for i, criterion in enumerate(method["primary_evaluation_criteria"], 1):
                row = public[f"{sid}-METHOD-PRIMARY_EVALUATION_CRITERIA-{i:03d}"]
                assert row[3] == criterion
                assert row[10].split(" | ") == method["primary_evaluation_criteria_evidence_ids"]
        if sid in decisions["statistical_analyses"]:
            analysis_count += 1
            analysis = decisions["statistical_analyses"][sid]
            delivered = json.loads(public[analysis["statistical_analysis_id"]][13])
            assert all(delivered[k] == v for k, v in analysis.items()), sid
            canonical_analysis = next(a for a in record["statistical_analysis_records"]
                                      if a["statistical_analysis_id"] == analysis["statistical_analysis_id"])
            assert all(delivered[k] == v for k, v in canonical_analysis.items()), sid
            before = json.loads((OUT / f"{sid}_before.json").read_text())["association_audit"]
            current = record["association_audit"]
            for key, value in before.items():
                if key not in {"statistical_analysis_id", "evidence_ids", "analysis_linkage_note"}:
                    assert current[key] == value, f"Unintended judgment change: {sid}/{key}"
        if record["primary_orientation"] != "HEALTH_FOCUSED":
            continue
        for field, kind, atom in (("analytic_output_records", "OUTPUT", "output_code"),
                                  ("proposed_use_records", "USE", "use_code")):
            for i, entry in enumerate(record[field], 1):
                if not entry.get("evidence_ids"):
                    gaps.append([sid, field, entry[atom], entry.get("other_text") or
                                 "Direct support for this specific code remains unconfirmed; no guessed linkage added."])
                elif entry.get("previous_evidence_ids") == []:
                    repaired.append([sid, field, entry[atom], " | ".join(entry["evidence_ids"])])
                if entry.get("review_status") == "CLASSIFICATION_REQUIRES_REVIEW":
                    caution.append(sid)
                for eid in entry.get("evidence_ids", []):
                    assert eid in anchors, (sid, eid)
                assert public[f"{sid}-{kind}-{i:03d}"][10] == (" | ".join(entry.get("evidence_ids", [])) or "NR")
    unresolved_analysis = [sid for sid, r in source.items()
        if r["primary_orientation"] == "HEALTH_FOCUSED"
        and any(x["purpose_code"] in {"POPULATION_ASSOCIATION", "POPULATION_ASSOCIATION_ANALYSIS"} for x in r["purpose_records"])
        and not r["association_audit"].get("statistical_analysis_id")]
    wb.close()
    canonical = ROOT / "manuscript/supplementary/tables/Supplementary_Table_S07_Master_study_level_dataset.xlsx"
    assert path.read_bytes() == canonical.read_bytes(), "Public S7 copy differs"
    result = {"validation":"PASS", "completion":"LISTED_GAPS_RESOLVED" if not gaps and not unresolved_analysis and not caution else "PARTIAL_WITH_EXPLICIT_REMAINING_GAPS",
              "evaluation_criteria_repaired":criteria_count, "evidence_records_repaired":len(repaired),
              "statistical_analysis_ids_repaired":analysis_count, "remaining_evidence_records":len(gaps),
              "remaining_analysis_studies":unresolved_analysis, "classification_cautions":caution,
              "s7_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    for name, rows in (("remaining_evidence.tsv", gaps), ("repaired_evidence.tsv", repaired)):
        with (OUT / name).open("w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["study_id", "field", "code", "evidence_or_reason"])
            writer.writerows(rows)
    (OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
