#!/usr/bin/env python3
"""Validate the reader-facing S2 -> S5 -> S7 publication chain."""
from __future__ import annotations

import json
import re
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "manuscript" / "supplementary" / "tables"
OUT = ROOT / "results" / "derived" / "human_protocol_publication_audit.json"
# Prompt 093: the study-level workbook is Supplementary Table S5; the 306-item instrument and the reader
# dictionary are its PROTOCOL_ITEMS and VARIABLE_DICTIONARY sheets.
S7 = TABLES / "Supplementary_Data_1_Study_level_dataset.xlsx"  # Prompt 097: workbook renamed Additional Data 1
S2 = S5 = S7


def main() -> None:
    s2 = load_workbook(S2, read_only=True, data_only=True)["PROTOCOL_ITEMS"]
    s2_rows = list(s2.iter_rows(values_only=True))
    s5 = load_workbook(S5, read_only=True, data_only=True)["VARIABLE_DICTIONARY"]
    s5_rows = list(s5.iter_rows(values_only=True))
    s7 = load_workbook(S7, read_only=True, data_only=True)
    studies = s7["STUDIES"]
    technical_rows = list(s7["DATA_DICTIONARY"].iter_rows(values_only=True))
    technical_header = list(technical_rows[0])
    technical = {row[0]: dict(zip(technical_header, row)) for row in technical_rows[1:]}
    s5_names = [row[0] for row in s5_rows[1:]]
    s7_names = [cell.value for cell in next(studies.iter_rows())]
    required_addenda = {"ORI01", "ORI02", "PUR01", "AOUT01", "USE01", "USE02",
                        "MTH01", "MTH02", "MTH03", "ASSOC01", "ASSOC02", "ASSOC03"}
    s2_ids = {row[0] for row in s2_rows[1:]}
    decimal_items = {"POP03", "POP04", "POP14", "THR02", "VAL12"}
    decimal_status = {
        row[0]: row[4]
        for row in s2_rows[1:]
        if row[0] in decimal_items
    }
    crosswalk_ids = {row[0] for row in s7["PROTOCOL_CROSSWALK"].iter_rows(min_row=2, values_only=True)}
    bad_refs = []
    for row in technical_rows[1:]:
        for part in str(row[11]).split(";"):
            token = part.strip()
            if not token:
                continue
            endpoints = token.split("-", 1) if "-" in token else [token]
            if any(endpoint not in crosswalk_ids for endpoint in endpoints):
                bad_refs.append({"field": row[0], "reference": token})
    detailed_fields = {
        "B_scientific_purpose_records", "B_analytic_output_records", "B_proposed_use_records",
        "B_method_contribution_detailed", "B_method_target_stages_detailed", "B_method_comparators",
        "B_method_evaluation_datasets", "B_method_primary_evaluation_criteria",
    }
    role_row = next(row for row in s5_rows[1:] if row[0] == "B_KNHANES_role")
    s2_content_rows = [row for row in s2_rows[1:] if row[0] and any(value not in (None, "") for value in row[1:])]
    direct_refs = {
        "D_final_sample": "POP09", "D_event_count": "POP12", "D_prevalence": "POP14",
        "H_evaluation_sample_size": "VAL10", "H_evaluation_prevalence": "VAL12",
        "H_threshold_reported": "THR01", "H_confidence_interval_reported": "MET_CI",
        "H_paired_comparison_reported": "MET_PAIR",
    }
    checks = {
        "workflow_controls_absent_from_public_s2": not any(str(x).startswith(("FLOW", "PUBQA")) for x in s2_ids),
        "twelve_core_classification_items_present": required_addenda <= s2_ids,
        "public_s2_UNC_only_in_explicit_legacy_correspondence": not any(re.search(r"(?<![A-Z_])UNC(?![A-Z_])", str(cell)) for row in s2_content_rows for j, cell in enumerate(row) if not (j == 5 and (row[0] == 'TSK06' or (str(row[0]).startswith('REP') and 'Enter UNC in the historical §15 response set; enter UNCLEAR in the current layer.' in str(cell))))),
        "final_response_reader_tables_present": {'ITEM_RESPONSES','MODEL_SELECTIONS','SOURCE_PACKAGE','VISUAL_DETAILS','SOURCE_JSON'} <= set(s7.sheetnames),
        "s5_no_placeholder_definitions": not any('value for ' in str(row[2]) for row in s5_rows[1:]),
        "five_decimal_items_have_status": set(decimal_status) == decimal_items and all("Status: Reported; Not reported; Not applicable; Unclear" in str(value) for value in decimal_status.values()),
        "s2_has_unit_and_linkage_column": s2_rows[0][2] == "Record unit / required linkage IDs" and all("required:" in str(row[2]) for row in s2_content_rows),
        "s2_uses_item_specific_rules": sum(not str(row[5]).startswith("Apply the canonical item definition") for row in s2_content_rows) >= 149,
        "domain_rows_are_section_headings": not any(str(x).startswith("DOMAIN_") for x in s2_ids),
        "s5_is_reader_facing_eight_columns": s5.max_column == 8,
        "s5_s7_headers_identical": s5_names == s7_names and len(s5_names) == 158,
        "result_counts_absent_from_variable_names": not any(re.search(r"_(220|184|36|165|19)$", name) for name in s7_names),
        "detailed_information_fields_present": detailed_fields <= set(s7_names),
        "all_protocol_crosswalk_references_resolve": not bad_refs,
        "knhanes_role_code_is_canonical": "EXTERNAL_OR_TRANSPORT_EVALUATION_DATASET" in str(role_row[5]) and "UNCLEAR" in str(role_row[5]) and "TRANSPORTABILITY" not in str(role_row[5]),
        "listed_crosswalks_are_direct": all(technical[name]["Protocol item ID(s)"] == ids for name, ids in direct_refs.items()),
        "technical_dictionary_preserved_in_s7": len(technical_rows) == 159 and len(technical_header) == 14,
        "detailed_records_are_authoritative": all(str(technical[name]["Derivation"]).startswith("Authoritative detailed record") for name in {"B_scientific_purpose_records", "B_analytic_output_records", "B_proposed_use_records", "B_method_contribution_detailed", "B_method_target_stages_detailed"}),
        "relational_s7_preserved": studies.max_row == 251 and  # prompt 106: 250 studies
            {'README','STUDIES','REPORTS','DATASETS','OUTCOMES','MODELS',
            'DEVELOPMENTS','EVALUATIONS','PERFORMANCE_METRICS','EVIDENCE_ANCHORS','RECORD_DETAILS',
            'RECORD_EVIDENCE','AI_DISAGREEMENTS','FINAL_ADJUDICATION','DATA_DICTIONARY',
            'PROTOCOL_CROSSWALK','ITEM_RESPONSES','MODEL_SELECTIONS','ANALYSIS_FIELDS',
            'SOURCE_PACKAGE','VISUAL_DETAILS','SOURCE_METADATA','SOURCE_JSON','TEXT_CONTINUATIONS'} <= set(s7.sheetnames),
    }
    result = {
        "schema": "human_protocol_publication_audit_v1",
        "s2_rows_excluding_header": len(s2_rows) - 1,
        "s5_s7_study_level_fields": len(s5_names),
        "protocol_crosswalk_items": len(crosswalk_ids),
        "bad_crosswalk_references": bad_refs,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(result["status"], f"{sum(checks.values())}/{len(checks)} checks")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
