#!/usr/bin/env python3
"""File-level release gate for protocol, S5, S7, and manuscript alignment."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
S5 = ROOT / "manuscript/bmc_supplementary_table_s5.xlsx"
S7 = ROOT / "manuscript/bmc_supplementary_table_s7.xlsx"
PROTOCOL = ROOT / "KNHANES_ML_study_audit_protocol.md"
MANUSCRIPT = ROOT / "manuscript/bmc_main.tex"
SUPPLEMENT = ROOT / "manuscript/bmc_supplementary.tex"
SUPPLEMENT_LOG = ROOT / "build/submission/bmc_supplementary.log"
OUTPUT = ROOT / "results/derived/preverification_alignment_validation.json"

REQUIRED_FIELDS = {
    "B_primary_orientation", "B_display_orientation_group",
    "M_association_estimate_linked", "M_survey_weights_linked_to_association",
    "M_design_uncertainty_linked_to_association",
    "M_importance_stability_support_criteria_met",
    "M_population_association_support_criteria_met",
    "M_individual_application_support_criteria_met",
    "M_surveillance_policy_support_criteria_met",
}
FORBIDDEN_PUBLIC_FIELDS = {
    "A_core_protocol_version", "A_posthoc_protocol_version",
    "A_human_verification_protocol_version", "B_reviewed_primary_orientation",
    "M_importance_reporting_stability_supported", "M_screening_support_criteria_met",
}
HEALTH_FIELDS = {"B_scientific_purposes", "B_health_topic", "B_analytic_outputs", "B_proposed_uses"}
METHOD_FIELDS = {"B_method_contribution", "B_method_target_stages_display", "B_method_evaluation_design"}
ASSOCIATION_FIELDS = {
    "M_association_estimate_linked", "M_survey_weights_linked_to_association",
    "M_design_uncertainty_linked_to_association", "M_population_association_support_criteria_met",
}
INDIVIDUAL_CODES = {"SCREENING", "DIAGNOSTIC_SUPPORT", "PERSONALISED_MANAGEMENT", "RISK_GROUP_IDENTIFICATION"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atoms(value) -> set[str]:
    if value in (None, ""):
        return set()
    return {part.strip() for part in str(value).split("|") if part.strip()}


def main() -> None:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "pass" if ok else "fail", "detail": detail})

    s5_ws = load_workbook(S5, read_only=True, data_only=True).active
    s7_ws = load_workbook(S7, read_only=True, data_only=True)["STUDIES"]
    s7_book = load_workbook(S7, read_only=True, data_only=True)
    s5_rows = list(s5_ws.iter_rows(values_only=True))
    technical_rows = list(s7_book["DATA_DICTIONARY"].iter_rows(values_only=True))
    dictionary_header = list(technical_rows[0])
    dictionary = {row[0]: dict(zip(dictionary_header, row)) for row in technical_rows[1:]}
    s5_names = [row[0] for row in s5_rows[1:]]
    s7_rows = list(s7_ws.iter_rows(values_only=True))
    s7_names = list(s7_rows[0])
    records = [dict(zip(s7_names, row)) for row in s7_rows[1:]]
    check('final_response_and_selection_tables',
          {'ITEM_RESPONSES','MODEL_SELECTIONS','ANALYSIS_FIELDS','SOURCE_JSON','TEXT_CONTINUATIONS'} <= set(s7_book.sheetnames),
          'Actual final repeated responses and author-selected models must be public, independently of provenance sheets')
    check('no_placeholder_variable_definitions',
          all('value for ' not in str(row[2]) for row in s5_rows[1:]),
          'Variable definitions explain content, rather than restating field names')

    check("s5_dictionary_count", len(s5_names) == 158, f"variables={len(s5_names)}")
    check("s5_reader_columns", len(s5_rows[0]) == 8, f"columns={len(s5_rows[0])}")
    check("s7_technical_dictionary_columns", len(dictionary_header) == 14, f"columns={len(dictionary_header)}")
    check("s5_variable_uniqueness", len(set(s5_names)) == len(s5_names), "no duplicate variable names")
    check("s5_s7_header_identity", s5_names == s7_names,
          f"S5={len(s5_names)}, S7={len(s7_names)}, same_names_and_order={s5_names == s7_names}")
    check("required_publication_fields", REQUIRED_FIELDS <= set(s7_names),
          f"missing={sorted(REQUIRED_FIELDS-set(s7_names))}")
    check("forbidden_legacy_publication_fields", not (FORBIDDEN_PUBLIC_FIELDS & set(s7_names)),
          f"present={sorted(FORBIDDEN_PUBLIC_FIELDS & set(s7_names))}")

    ids = [row["A_study_id"] for row in records]
    check("study_census", len(records) == 220 and len(set(ids)) == 220,
          f"rows={len(records)}, unique_ids={len(set(ids))}")

    applicability_errors = []
    code_errors = []
    for row in records:
        sid = row["A_study_id"]
        health = row["B_display_orientation_group"] == "HEALTH_ANALYSIS"
        method = row["B_display_orientation_group"] == "METHOD_RESEARCH"
        purposes = atoms(row["B_scientific_purposes"])
        uses = atoms(row["B_proposed_uses"])
        association = health and "POPULATION_ASSOCIATION_ANALYSIS" in purposes
        individual = health and bool(uses & INDIVIDUAL_CODES)
        surveillance = health and "POPULATION_SURVEILLANCE_OR_POLICY" in uses
        importance = "USED" in atoms(row["I_importance_reported"])

        for field in HEALTH_FIELDS:
            if not health and row[field] != "NA":
                applicability_errors.append(f"{sid}:{field}={row[field]}")
        for field in METHOD_FIELDS:
            if not method and row[field] != "NA":
                applicability_errors.append(f"{sid}:{field}={row[field]}")
        for field in ASSOCIATION_FIELDS:
            if association == (row[field] == "NA"):
                applicability_errors.append(f"{sid}:{field}={row[field]}")
        for field, eligible in (
            ("M_importance_stability_support_criteria_met", importance),
            ("M_individual_application_support_criteria_met", individual),
            ("M_surveillance_policy_support_criteria_met", surveillance),
        ):
            if eligible == (row[field] == "NA"):
                applicability_errors.append(f"{sid}:{field}={row[field]}")

        for field in REQUIRED_FIELDS | {"K_code_available"}:
            allowed_text = dictionary[field]["Permitted codes/format"] or ""
            allowed = {part.strip() for part in str(allowed_text).split("|")}
            values = atoms(row[field]) if dictionary[field]["Multiple selection"] == "Yes" else {str(row[field])}
            unknown = values - allowed
            if unknown:
                code_errors.append(f"{sid}:{field}:{sorted(unknown)}")

    check("conditional_applicability", not applicability_errors,
          f"errors={applicability_errors[:10]}; total={len(applicability_errors)}")
    check("controlled_codes", not code_errors, f"errors={code_errors[:10]}; total={len(code_errors)}")

    protocol = PROTOCOL.read_text(encoding="utf-8")
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    protocol_terms = (
        "Core extraction layer: 382 locked v1.2 core items", "This section retains the established specification for new independent verification",
        "PUBLIC_ACCESS_VERIFIED", "M_association_estimate_linked",
        "S5 dictionary rows and S7 `STUDIES` headers must match the same 158 names and order",
    )
    adjudication_terms = (
        "AI_A_BLINDED", "AI_B_BLINDED", "HUMAN_ADJUDICATION", "FINAL_CONSENSUS",
        "primary_orientation", "method_target_stages_detailed[]", "association_estimate_linked",
        "survey_weights_linked_to_association", "design_uncertainty_linked_to_association",
        "human packet",
    )
    manuscript_terms = ("158 study-level", "four orientation states", "Review-defined supporting evidence")
    check("master_active_layer_terms", all(term in protocol for term in protocol_terms),
          f"missing={[term for term in protocol_terms if term not in protocol]}")
    check("dual_ai_human_adjudication_terms", all(term in protocol for term in adjudication_terms),
          f"missing={[term for term in adjudication_terms if term not in protocol]}")
    check("obsolete_root_h2_form_absent", not (ROOT / "KNHANES_v1.4_H2_blinded_review_form.md").exists(),
          "standalone second-human form is not an active root document")
    check("manuscript_alignment_terms", all(term in manuscript for term in manuscript_terms),
          f"missing={[term for term in manuscript_terms if term not in manuscript]}")
    supplement_structure = ("\\input{" not in supplement and "\\include{" not in supplement and
                            all(f"Supplementary Table S{i}." in supplement for i in range(1, 7)) and
                            "Supplementary Table S8." in supplement and "Supplementary Figure S1." in supplement)
    check("supplement_self_contained_structure", supplement_structure,
          "self-contained S1--S6, S8, and Figure S1 source")
    log_text = SUPPLEMENT_LOG.read_text(encoding="utf-8", errors="replace") if SUPPLEMENT_LOG.exists() else ""
    check("supplement_no_horizontal_overflow", bool(log_text) and "Overfull \\hbox" not in log_text,
          "compiled log exists and contains no Overfull hbox")

    files = [PROTOCOL, MANUSCRIPT, SUPPLEMENT, S5, S7]
    report = {
        "schema": "KNHANES_preverification_alignment_v1.4",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(row["status"] == "pass" for row in checks) else "FAIL",
        "checks": checks,
        "hashes": {str(path.relative_to(ROOT)): sha256(path) for path in files},
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in checks:
        print(f"{row['status'].upper()} {row['check']}: {row['detail']}")
    print(f"{report['status']} -> {OUTPUT.relative_to(ROOT)}")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
