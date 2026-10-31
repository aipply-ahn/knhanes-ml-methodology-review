#!/usr/bin/env python3
"""Compare canonical Markdown to delivered workbooks, without importing the generator."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook
from protocol_response_labels import response_choices
from protocol_public_english import english_item

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "manuscript/supplementary/tables"
OUT = ROOT / "prompts/implementation_records/protocol_content_audit_20260924"
FIELDS = ["number", "item_id", "subsection", "item_role", "primary_unit",
          "required_related_ids", "construct", "applicability", "question",
          "response_type", "allowed_values", "evidence_required", "decision_rule",
          "json_key", "output_mapping", "official_item_id", "required_components"]


def workbook(name, sheet=None):
    wb = load_workbook(TABLES / name, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.values)
    wb.close()
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    text = (ROOT / "KNHANES_ML_study_audit_protocol.md").read_text()
    items = {}
    for line in text.splitlines():
        if re.match(r"^\|\s*\d+\s*\|\s*`", line):
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            assert len(cells) == 17, line
            item = dict(zip(FIELDS, cells))
            assert item["item_id"] not in items
            items[item["item_id"]] = item
    s2 = workbook("Supplementary_Table_S02_Operational_definitions_coding_rules.xlsx")
    s2_by_id = {r[0]: r for r in s2[1:] if r[1]}
    cross = workbook("Supplementary_Table_S07_Master_study_level_dataset.xlsx", "PROTOCOL_CROSSWALK")
    cross_by_id = {r[0]: dict(zip(cross[0], r)) for r in cross[1:]}
    s5 = workbook("Supplementary_Table_S05_Data_dictionary.xlsx")
    technical = workbook("Supplementary_Table_S07_Master_study_level_dataset.xlsx", "DATA_DICTIONARY")
    studies = workbook("Supplementary_Table_S07_Master_study_level_dataset.xlsx", "STUDIES")
    readable = workbook("Supplementary_Table_S07_Master_study_level_dataset.xlsx", "RECORD_DETAILS")
    evidence_links = workbook("Supplementary_Table_S07_Master_study_level_dataset.xlsx", "RECORD_EVIDENCE")
    readable_by_id = {r[1]: r for r in readable[1:]}
    assert len(readable_by_id) == len(readable) - 1, "Duplicate publication record ID"
    errors, comparisons = [], []
    for key, item in items.items():
        row_errors = []
        stored = json.loads(cross_by_id[key]["Canonical metadata JSON"])
        if stored != item:
            row_errors.append("canonical metadata differs")
        if item["item_role"] in {"reviewer_entered", "appraisal_judgement"}:
            item = english_item(item)
            row = s2_by_id.get(key)
            if row is None:
                row_errors.append("missing S2 row")
            else:
                response = item["allowed_values"] or item["response_type"]
                if any(x in item["response_type"].lower() for x in ("integer", "numeric", "decimal", "text", "date", "identifier")):
                    response = f"Value ({response}); Status: REPORTED | NR | NA | UNCLEAR"
                response = response_choices(response, key)
                expected = [key, item["question"],
                            f"{item['primary_unit']}; required: {item['required_related_ids'] or 'study_id'}",
                            item["applicability"], response]
                if list(row[:5]) != expected:
                    row_errors.append("question/unit/linkage/applicability/response differs")
                for field in ("decision_rule", "required_components"):
                    if item[field] and item[field] not in str(row[5]):
                        row_errors.append(f"lost {field}")
                if not row[6]:
                    row_errors.append("missing evidence instruction")
        comparisons.append([key, item["item_role"], "PASS" if not row_errors else "FAIL", "; ".join(row_errors)])
        errors.extend(f"{key}: {e}" for e in row_errors)
    for line in text.splitlines():
        if re.match(r"^\| (?:ORI|PUR|AOUT|USE|MTH|ASSOC)\d+ \|", line):
            c = [x.strip() for x in line.strip("|").split("|")]
            expected = [c[0], c[1], f"{c[7]}; required: {c[8]}", c[2], response_choices(c[3].replace("; ", " | "), c[0]),
                        f"{c[4]} Exception/example: {c[5]}", c[6]]
            if list(s2_by_id[c[0]]) != expected:
                errors.append(f"{c[0]}: public canonical row differs")
    assert len(items) == 382 and len(s2_by_id) == 306
    assert len(s5[0]) == 8 and len(technical[0]) == 14
    assert [r[0] for r in s5[1:]] == list(studies[0])
    for reader, detail in zip(s5[1:], technical[1:]):
        if list(reader) != [detail[i] for i in (0, 1, 2, 3, 4, 7, 11, 12)]:
            errors.append(f"{reader[0]}: S5 technical projection differs")
        for item_id in detail[11].split(";"):
            if item_id not in cross_by_id:
                errors.append(f"{reader[0]}: unresolved/non-specific crosswalk {item_id}")
    by_field = {r[0]: r for r in s5[1:]}
    if "R2=R-squared" not in by_field["H_metrics_reported"][5]:
        errors.append("metric R2 label incorrect")
    if by_field["B_health_topic"][6] != "TSK04;TSK05":
        errors.append("health topic crosswalk incorrect")
    empty_evidence = []
    content_gaps = []
    detailed_stage_counts = Counter()
    display_stage_counts = Counter()
    association_count = 0
    stage_count = 0
    source_anchors = {}
    source_docs = {}
    figure5_sources = {r["study_id"]: r for r in json.loads(
        (ROOT / "results/derived/study_purpose_audit.json").read_text())["records"]}
    for raw in studies[1:]:
        row = dict(zip(studies[0], raw))
        sid = row["A_study_id"]
        source = json.loads((ROOT / f"data/protocol_v1_2/final/{sid}_final.json").read_text())
        source_docs[sid] = source
        source_anchors[sid] = {a["evidence_id"]: a for a in source["evidence_registry"]}
        v13 = source["adjudication"]["purpose_evidence_v1_3"]
        if row["B_primary_orientation"] == "HEALTH_FOCUSED":
            for summary, detail, atom in (("B_scientific_purposes", "B_scientific_purpose_records", "purpose_code"),
                                           ("B_analytic_outputs", "B_analytic_output_records", "output_code"),
                                           ("B_proposed_uses", "B_proposed_use_records", "use_code")):
                records = json.loads(row[detail])
                source_key = {"purpose_code": "purpose_records", "output_code": "analytic_output_records", "use_code": "proposed_use_records"}[atom]
                aliases = {"HEALTH_STATE_OR_VALUE_ESTIMATION": "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION",
                           "POPULATION_ASSOCIATION": "POPULATION_ASSOCIATION_ANALYSIS",
                           "PATTERN_OR_SUBGROUP_DISCOVERY": "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY",
                           "CAUSAL_EFFECT_OR_STRUCTURE": "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION",
                           "REDUCED_VARIABLE_SET": "REDUCED_PREDICTOR_SET", "CAUSAL_EFFECT": "CAUSAL_EFFECT_ESTIMATE",
                           "CLUSTER_OR_PATTERN": "CLUSTER_OR_PATTERN_RESULT", "INTERFACE_OR_TOOL": "IMPLEMENTED_TOOL",
                           "POPULATION_ASSOCIATION_ESTIMATE": "ASSOCIATION_ESTIMATE"}
                expected_records = json.loads(json.dumps(v13[source_key]))
                for index, original in enumerate(expected_records, 1):
                    kind = {"purpose_code": "purpose", "output_code": "output", "use_code": "use"}[atom]
                    original[f"{kind}_record_id"] = f"{sid}-{kind.upper()}-{index:03d}"
                    original[atom] = aliases.get(original[atom], original[atom])
                    if atom == "use_code":
                        if original.get("claim_strength") == "EMPIRICALLY_TESTED_USE":
                            original["claim_strength"] = "TESTED_USE"
                        complete = original.pop("review_complete", None)
                        original["review_status"] = "COMPLETE" if complete is True else "INCOMPLETE" if complete is False else "UNCLEAR"
                if records != expected_records:
                    errors.append(f"{sid}/{detail}: source information lost beyond documented alias conversion")
                for record in records:
                    record_id = record[f"{kind}_record_id"]
                    if record_id not in readable_by_id or json.loads(readable_by_id[record_id][13]) != record:
                        errors.append(f"{sid}/{record_id}: readable record differs from STUDIES detail")
                expected = {r[atom] for r in records}
                if not expected and atom == "use_code":
                    expected = {"NO_SPECIFIC_USE" if v13.get("no_specific_use") is True else "UNCLEAR"}
                if expected != set(row[summary].split(" | ")):
                    errors.append(f"{sid}/{summary}: detailed/summary mismatch")
                if atom == "output_code" and "ASSOCIATION_ESTIMATE" in expected:
                    association_count += 1
                for r in records:
                    evidence_ids = [value for key, value in r.items() if key.endswith("evidence_ids")]
                    if not any(evidence_ids):
                        empty_evidence.append([sid, detail, r[atom], "Source record has no evidence IDs; not repaired by this schema audit"])
        if row["B_primary_orientation"] == "METHOD_FOCUSED":
            original = set(v13["method_research"]["target_analysis_stages"])
            delivered = set(row["B_method_target_stages_detailed"].split(" | "))
            if original != delivered:
                errors.append(f"{sid}: detailed method stages lost")
            stage_count += 1
            detailed_stage_counts.update(original)
            stage_map = {"DATA_INTEGRATION": "DATA_INTEGRATION_OR_HARMONISATION",
                         "FEATURE_CONSTRUCTION_OR_SELECTION": "VARIABLE_CONSTRUCTION_OR_SELECTION",
                         "REPRESENTATION_OR_CLUSTERING": "MODEL_DEVELOPMENT", "CAUSAL_OR_STRUCTURE": "MODEL_DEVELOPMENT"}
            expected_display = {stage_map.get(s, s) for s in original if s != "OTHER"}
            display_stage_counts.update(expected_display)
            if expected_display != set(row["B_method_target_stages_display"].split(" | ")):
                errors.append(f"{sid}: Figure 5 stage mapping differs")
            legacy_stage_map = {"FEATURE_ENGINEERING_OR_SELECTION": "VARIABLE_CONSTRUCTION_OR_SELECTION",
                                "PREDICTION_OR_CLASSIFICATION": "MODEL_DEVELOPMENT",
                                "CLUSTERING_OR_REPRESENTATION": "MODEL_DEVELOPMENT",
                                "CAUSAL_OR_STRUCTURE_LEARNING": "MODEL_DEVELOPMENT",
                                "EXPLAINABLE_AI": "EXPLANATION_OR_INTERPRETATION",
                                "VALIDATION_OR_PERFORMANCE_EVALUATION": "VALIDATION_OR_PERFORMANCE"}
            figure_source = figure5_sources[sid]
            figure_display = {legacy_stage_map.get(s, s) for s in figure_source["method_intervention_stages"]}
            if figure_display != expected_display:
                errors.append(f"{sid}: actual Figure 5 source disagrees with detailed records")
            if figure_source["method_research_category"] != row["B_method_contribution"] or figure_source["method_evaluation_mode"] != row["B_method_evaluation_design"]:
                errors.append(f"{sid}: Figure 5 contribution/evaluation disagrees with S7")
            for index, stage in enumerate(v13["method_research"]["target_analysis_stages"], 1):
                rid = f"{sid}-STAGE-{index:03d}"
                if rid not in readable_by_id or readable_by_id[rid][3] != stage:
                    errors.append(f"{sid}: method stage ID not actually published: {rid}")
            criteria = v13["method_research"]["primary_evaluation_criteria"]
            if not criteria or all(c in {"Y", "N", "NA", "NR", "UNC", "UNCLEAR"} for c in criteria):
                content_gaps.append([sid, "METHOD_CRITERION_NAME_UNRESOLVED", json.dumps(criteria),
                                     "Stored flags do not identify a primary metric/criterion; original source required"])
            for public, source_key in (("B_method_comparators", "comparators"),
                                       ("B_method_evaluation_datasets", "evaluation_datasets"),
                                       ("B_method_primary_evaluation_criteria", "primary_evaluation_criteria")):
                if json.loads(row[public]) != v13["method_research"][source_key]:
                    errors.append(f"{sid}/{public}: detailed array changed")
    unresolved_ids = []
    for r in evidence_links[1:]:
        if r[1] not in readable_by_id:
            errors.append(f"orphan evidence record {r[1]}")
        if r[4] == "UNRESOLVED_ID":
            unresolved_ids.append([r[0], r[1], r[3]])
        if r[4] == "RESOLVED":
            original = source_anchors[r[0]].get(r[3])
            if original is None:
                errors.append(f"false resolved anchor {r[0]}/{r[3]}")
                continue
            expected = [re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(original.get(k) if original.get(k) not in (None, "") else "NR"))
                        for k in ("source_file", "section", "pdf_page", "printed_page", "object_label", "start_anchor", "end_anchor", "excerpt")]
            if list(r[6:14]) != expected:
                errors.append(f"anchor location/excerpt changed {r[0]}/{r[3]}")
    for r in readable[1:]:
        value = source_docs[r[0]]
        try:
            for part in r[12].split("."):
                match = re.fullmatch(r"([^\[]+)(?:\[(\d+)\])?", part)
                value = value[match[1]]
                if match[2] is not None:
                    value = value[int(match[2])]
        except (TypeError, KeyError, IndexError):
            errors.append(f"{r[1]}: non-resolving source record path {r[12]}")
        if r[2] == "association" and r[9] == "UNCLEAR":
            content_gaps.append([r[0], "STATISTICAL_ANALYSIS_ID_UNRESOLVED", r[1],
                                 "Retained study-level audit has no statistical_analysis_id; publication record ID is not a substitute"])
    use_row = s2_by_id["USE01"]
    if "NO_SPECIFIC_USE" in use_row[4]:
        errors.append("USE01 exposes derived NO_SPECIFIC_USE as input")
    if re.search(r"(?<![a-z_])analysis_id(?![a-z_])", text):
        errors.append("noncanonical bare analysis_id remains")
    if association_count != 56:
        errors.append(f"association outputs {association_count} differ from source-resolved manuscript count 56")
    if "공개 S5/S7과 Figure 5에는 7단계만 사용한다" in text:
        errors.append("obsolete seven-stage-only publication rule")
    for name, header, data in (
        ("item_comparison.tsv", ["item_id", "item_role", "status", "differences"], comparisons),
        ("retained_evidence_gaps.tsv", ["study_id", "field", "code", "note"], empty_evidence),
        ("source_content_gaps.tsv", ["study_id", "issue", "stored_value_or_record", "meaning"], content_gaps),
        ("unresolved_evidence_ids.tsv", ["study_id", "record_id", "evidence_id"], unresolved_ids),
    ):
        with (OUT / name).open("w", newline="") as f:
            w = csv.writer(f, delimiter="\t"); w.writerow(header); w.writerows(data)
    files = [ROOT / "KNHANES_ML_study_audit_protocol.md", ROOT / "manuscript/bmc_main.pdf", ROOT / "manuscript/bmc_supplementary.pdf"]
    files += list(TABLES.glob("Supplementary_Table_S0[257]*.xlsx"))
    result = {"status": "PASS" if not errors else "FAIL", "scope": "publication content preservation and consistency; not re-extraction of 220 source papers",
              "source_content_status": "REQUIRES_SOURCE_CONFIRMATION" if empty_evidence or content_gaps or unresolved_ids else "NO_LISTED_GAPS",
              "canonical_items": len(items), "s2_content_items": len(s2_by_id), "s5_variables": len(s5)-1,
              "method_studies_compared_to_source": stage_count, "health_association_outputs": association_count,
              "retained_records_without_evidence_ids": len(empty_evidence), "errors": errors,
              "readable_records": len(readable)-1, "readable_evidence_rows": len(evidence_links)-1,
              "source_content_gap_counts": dict(Counter(r[1] for r in content_gaps)),
              "unresolved_evidence_ids": len(unresolved_ids),
              "method_detailed_stage_counts": dict(detailed_stage_counts),
              "method_display_stage_counts": dict(display_stage_counts),
              "method_OTHER_stage_count": detailed_stage_counts["OTHER"],
              "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (OUT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "sha256"}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
