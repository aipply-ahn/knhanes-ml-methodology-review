#!/usr/bin/env python3
"""Independently validate the closed 27-record scope and propagated classifications."""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prompts/implementation_records/evidence_resolution_20260924"


def main():
    decisions = json.loads((ROOT / "data/protocol_v1_3/evidence_resolution_20260924.json").read_text())
    records = {r["study_id"]: r for r in json.loads((ROOT / "data/protocol_v1_3/purpose_evidence_addendum.json").read_text())["records"]}
    categories = {r["study_id"]: r for r in json.loads((ROOT / "results/derived/study_purpose_audit.json").read_text())["records"]}
    baseline = list(csv.DictReader((OUT / "scope_remaining_before.tsv").open(), delimiter="\t"))
    assert len(baseline) == len(decisions["resolutions"]) == 27
    field_kind = {"analytic_output_records": "output", "proposed_use_records": "use"}
    assert {(b["study_id"], field_kind[b["field"]], b["code"]) for b in baseline} == {
        (a["study_id"], a["kind"], a["old_code"]) for a in decisions["resolutions"]}
    wb = load_workbook(ROOT / "manuscript/bmc_supplementary_table_s7.xlsx", read_only=True, data_only=True)
    public = {r[1]: r for r in list(wb["RECORD_DETAILS"].values)[1:]}
    rows = []
    for action in decisions["resolutions"] + decisions["additional_corrections"]:
        sid = action["study_id"]
        record = records[sid]
        field, atom = ("analytic_output_records", "output_code") if action["kind"] == "output" else ("proposed_use_records", "use_code")
        rid = f"{sid}-REV-{action['kind'].upper()}-{action['old_code']}"
        revision = next(r for r in record["classification_revisions"] if r["revision_id"] == rid)
        assert revision["previous_record"][atom] == action["old_code"]
        assert revision["new_code"] == action["new_code"]
        delivered = json.loads(public[rid][13])
        assert all(delivered[k] == v for k, v in revision.items())
        assert public[rid][2] == "classification_revision" and action["reason"] in public[rid][8]
        if action["new_code"] != action["old_code"]:
            assert action["old_code"] not in {e[atom] for e in record[field]}
        if action["new_code"] is not None:
            entry = next(e for e in record[field] if e[atom] == action["new_code"])
            assert entry["evidence_ids"] == action["evidence_ids"]
        rows.append([sid, action["kind"], action["old_code"], action["new_code"] or "WITHDRAWN",
                     revision["decision"], action["reason"], " | ".join(action["evidence_ids"])])
    for sid, record in records.items():
        doc = json.loads((ROOT / f"data/protocol_v1_2/final/{sid}_final.json").read_text())
        assert doc["adjudication"]["purpose_evidence_v1_3"] == record
        assert doc["adjudication"]["study_category_and_dataset_use"] == categories[sid]
        if record["primary_orientation"] != "HEALTH_FOCUSED":
            continue
        for key in ("analytic_output_records", "proposed_use_records"):
            assert all(r["evidence_ids"] for r in record[key]), sid
            assert all(r.get("review_status") != "CLASSIFICATION_REQUIRES_REVIEW" for r in record[key]), sid
        if record.get("classification_revisions"):
            expected = [u["use_code"] for u in record["proposed_use_records"]] or ["NO_SPECIFIC_USE"]
            assert expected == categories[sid]["proposed_use"]
            assert record["no_specific_use"] == (not record["proposed_use_records"])
            codes = set(expected)
            claims = {c["claim_type"] for c in record["claim_evidence_records"]}
            if "POPULATION_SURVEILLANCE_OR_POLICY" not in codes:
                assert "POPULATION_SURVEILLANCE_OR_POLICY" not in claims
    khm038 = records["KHM038"]
    assert khm038["association_audit"]["statistical_analysis_id"] == "KHM038-SA01"
    assert khm038["association_audit"]["association_was_substantive_output"] == "N"
    assert "Rao–Scott" in public["KHM038-SA01"][3]
    health = [r for r in records.values() if r["primary_orientation"] == "HEALTH_FOCUSED"]
    outputs = Counter(e["output_code"] for r in health for e in r["analytic_output_records"])
    uses = Counter(e["use_code"] for r in health for e in r["proposed_use_records"])
    assert outputs["ASSOCIATION_ESTIMATE"] == 56 and outputs["MODEL_PERFORMANCE"] == 175 and outputs["CAUSAL_EFFECT"] == 5
    assert uses == Counter({"RESEARCH_OR_HYPOTHESIS_GENERATION":105, "POPULATION_SURVEILLANCE_OR_POLICY":42,
                           "SCREENING":22, "DIAGNOSTIC_SUPPORT":16, "RISK_GROUP_IDENTIFICATION":14,
                           "PERSONALISED_MANAGEMENT":7, "OTHER":2})
    assert sum(r["no_specific_use"] for r in health) == 48
    fig_audit = json.loads((ROOT / "results/derived/figure11_reporting_probast_domain_audit.json").read_text())
    assert fig_audit["claim_evidence"] == {"claim_present":[129,19,48,37], "matched_evidence":[25,4,5,8]}
    en = subprocess.check_output(["pdftotext", str(ROOT / "manuscript/bmc_main.pdf"), "-"], text=True)
    compact = " ".join(en.split())
    for token in ("(n=175)", "(n=56)", "(n=105)", "(n=42)", "5/48", "8/37"):
        assert token in compact, token
    wb.close()
    with (OUT / "resolved_records.tsv").open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["study_id", "kind", "previous_code", "current_code", "decision", "reason", "evidence_ids"])
        w.writerows(rows)
    result = {"status":"PASS", "scope":"All 27 listed records and one analysis-ID gap; not a new full-corpus re-extraction",
              "remaining_in_scope":0, "retained_with_evidence":5, "reclassified":8, "withdrawn_false_positive_records":14,
              "additional_negated_causal_output_corrected":1, "analysis_id_resolved":"KHM038-SA01",
              "health_output_counts":dict(outputs), "proposed_use_counts":dict(uses), "no_specific_use":48,
              "sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [ROOT / "KNHANES_ML_study_audit_protocol.md", ROOT / "manuscript/bmc_main.pdf", ROOT / "manuscript/bmc_main_ko.pdf",
                 ROOT / "manuscript/bmc_supplementary.pdf", ROOT / "manuscript/bmc_supplementary_table_s7.xlsx"]}}
    (OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
