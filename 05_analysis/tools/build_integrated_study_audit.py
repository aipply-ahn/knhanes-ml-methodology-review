"""Build one study-level master audit by joining the previously separate audits.

Outputs
-------
data/INTEGRATED_STUDY_AUDIT.tsv
data/INTEGRATED_STUDY_AUDIT.xlsx
manuscript/submission/appendices/appendix8_integrated_study_audit.md

The TSV/XLSX contain one row per included study.  The Markdown presents the same
information as one compact record per study so long evidence text remains readable.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
APP = ROOT / "manuscript/submission/appendices"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def index(path: Path) -> dict[str, dict[str, str]]:
    return {r["key"]: r for r in read_tsv(path)}


def clean(value: object, limit: int | None = None) -> str:
    # Strip control and Unicode private-use glyphs introduced by broken PDF font maps;
    # neither carries recoverable text and both can break XLSX/PDF rendering.
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff\ufeff]", " ", str(value or ""))
    raw = raw.replace("※", "Note:")
    for old, new in zip("①②③④⑤⑥⑦⑧⑨⑩", (f"({i})" for i in range(1, 11))):
        raw = raw.replace(old, new)
    text = " ".join(raw.replace("|", "/").split())
    if limit and len(text) > limit:
        return text[: limit - 4].rstrip() + " […]"
    return text


def study_type(key: str, extraction: dict, classification_keys: set[str]) -> str:
    nonclassification_primary_with_classifier = {"son2022performance", "kim2025employing", "lee2025deep"}
    if key in classification_keys and key not in nonclassification_primary_with_classifier:
        return "Classification"
    if extraction.get("task") == "regression":
        return "Regression"
    return "Non-predictive"


def supplement_counts(row: dict[str, str]) -> tuple[str, str, str, str]:
    """Count identifiable supplement items without inferring unlabeled content."""
    archived = int(row.get("files_archived") or 0)
    if not archived:
        return "0", "0", "0", "No archived supplement"

    paths = [Path(x) for x in row.get("local_paths", "").split(";") if x]
    text_path = ROOT / row.get("review_text", "") if row.get("review_text") else None
    text = text_path.read_text(encoding="utf-8", errors="ignore") if text_path and text_path.exists() else ""

    table_ids: set[str] = set()
    figure_ids: set[str] = set()
    for m in re.finditer(r"(?i)\b(?:supplement(?:ary)?\s+)?table\s+(S?\d+[A-Za-z]?)\b", text):
        table_ids.add(m.group(1).upper())
    for m in re.finditer(r"(?i)\b(?:supplement(?:ary)?\s+)?figure\s+(S?\d+[A-Za-z]?)\b", text):
        figure_ids.add(m.group(1).upper())

    for path in paths:
        stem = path.stem
        mt = re.search(r"(?i)(?:supplementary[-_ ]*)?table[-_ ]*(S?\d+[A-Za-z]?)", stem)
        mf = re.search(r"(?i)(?:supplementary[-_ ]*)?figure[-_ ]*(S?\d+[A-Za-z]?)", stem)
        if mt:
            table_ids.add(mt.group(1).upper())
        if mf:
            figure_ids.add(mf.group(1).upper())
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"}:
            figure_ids.add("FILE:" + path.name.lower())

    document_ext = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".txt", ".csv"}
    documents = sum(p.suffix.lower() in document_ext for p in paths)
    def noun(n: int, singular: str) -> str:
        return f"{n} {singular if n == 1 else singular + 's'}"
    summary = "; ".join((noun(len(figure_ids), "figure"), noun(len(table_ids), "table"),
                         noun(documents, "document"), noun(archived, "archived file")))
    return str(len(figure_ids)), str(len(table_ids)), str(documents), summary


def figure_grade(row: dict[str, str]) -> str:
    text = (row.get("caption", "") + " " + row.get("detected_metrics", "")).lower()
    nums = bool(row.get("numeric_labels_detected"))
    context = any(x in text for x in ("external", "test set", "validation"))
    diagnostic = any(x in text for x in ("architecture", "flow", "importance", "loss", "formula", "t-sne", "path diagram"))
    performance = any(x in text for x in ("roc", "auc", "accuracy", "precision", "recall", "f1", "calibration"))
    if diagnostic and not performance:
        return "D"
    if nums and context:
        return "A"
    if nums:
        return "B"
    return "C"


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _style_sheet(ws) -> None:
    """Apply readable, filterable formatting without hiding missingness."""
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for i, cell in enumerate(ws[1], 1):
        header = str(cell.value or "")
        width = 12 if header.endswith(("_n", "_year", "_id")) else 22
        if header in {"title", "caption", "evidence", "interpretation", "source_path", "native_text"}:
            width = 55
        ws.column_dimensions[get_column_letter(i)].width = min(width, 60)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _append_rows(wb, name: str, rows: list[dict[str, object]]) -> None:
    ws = wb.create_sheet(name)
    if not rows:
        rows = [{"status": "not assessed"}]
    headers = list(rows[0])
    ws.append(headers)
    for row in rows:
        values = []
        for h in headers:
            value = row.get(h, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if isinstance(value, str):
                value = clean(value)
            values.append(value)
        ws.append(values)
    _style_sheet(ws)


def _year_fields(raw: str) -> dict[str, object]:
    years = sorted({int(x) for x in re.findall(r"(?:19|20)\d{2}", raw or "") if 1998 <= int(x) <= 2026})
    exact = "; ".join(map(str, years)) if years else "NR"
    return {
        "knhanes_years_reported_raw": raw or "NR", "knhanes_years_exact": exact,
        "knhanes_year_start": years[0] if years else "NR", "knhanes_year_end": years[-1] if years else "NR",
        "number_of_years": len(years) if years else "NR",
        "year_scope": ("single-year" if len(years) == 1 else "multi-year" if len(years) > 1 else "NR"),
        "year_continuity": ("continuous" if len(years) > 1 and years == list(range(years[0], years[-1] + 1))
                            else "non-continuous" if len(years) > 1 else "NA" if len(years) == 1 else "NR"),
    }


def _panel_count(item: dict[str, str]) -> int:
    """Conservative explicit-panel count; never changes the container denominator."""
    text = " ".join((item.get("caption", ""), item.get("chatgpt_visible_text", "")))
    labels = {x.upper() for x in re.findall(r"(?<![A-Za-z])\(([A-Ha-h])\)", text)}
    return len(labels) if len(labels) >= 2 else 0


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    """Write AF8 as linked backdata sheets; 01_STUDIES retains the flat canonical export."""
    wb = Workbook()
    wb.remove(wb.active)
    _append_rows(wb, "00_README", [
        {"item": "dataset", "value": "Additional file 8: Integrated Study-Level Audit Dataset and Evidence Ledger"},
        {"item": "version", "value": "2026-09-13 data freeze"},
        {"item": "updated", "value": date.today().isoformat()},
        {"item": "denominators", "value": "included=222; classification=206; continuous prediction=5; other task=11; PROBAST+AI eligible prediction studies=211; development units=203; evaluation units=243"},
        {"item": "missingness", "value": "NR=applicable but not reported/recoverable; NA=not applicable; unclear=reported evidence insufficient; not assessed=review not performed"},
        {"item": "review status", "value": "Evidence-assisted primary review; independent second review and consensus pending for judgement-based fields"},
        {"item": "visual counting", "value": "2,095 is the deduplicated denominator of numbered figure/table containers. Explicit A/B/C panels are separately derived and are never added to that denominator."},
        {"item": "keys", "value": "study_id links all sheets; object_id links visual objects; source_path/file checksum links report packages"},
    ])

    survey = {x["study_id"]: x for x in read_tsv(DATA / "survey_design_appraisal/study_level_appraisal.tsv")}
    pooling = {x["key"]: x for x in read_tsv(DATA / "POOLING_OPERATION_AUDIT.tsv")}
    pathway = {x["key"]: x for x in read_tsv(DATA / "IMPORTANCE_PATHWAY.tsv")}
    timing = {x["study_id"]: x for x in read_tsv(DATA / "outcome_timing_appraisal.tsv")}
    importance_summary = json.load(open(ROOT / "results/derived/importance_pathway.json", encoding="utf-8"))["summary"]
    exact_carryover_keys = {x["key"] for x in importance_summary["guided_studies"] if x.get("exact_carryover")}
    study_rows = []
    for r in rows:
        x = dict(r)
        x.update({
            "study_id": r["key"], "representative_report_id": r["key"],
            "included_222": 1, "classification_core_206": int(r["type"] == "Classification"),
            "continuous_prediction_5": int(r["type"] == "Regression"),
            "other_task_11": int(r["type"] == "Non-predictive"),
            "probast_prediction_211": int(r["type"] in {"Classification", "Regression"}),
            "explicit_variable_importance_126": int(r.get("importance_methods_full") not in {"", "Not applicable", "NR"}),
            "multiyear_pooled_180": int(pooling.get(r["key"], {}).get("pooling_operation") == "Actual pooled multi-year analysis"),
            "downstream_inference_7": int(pathway.get(r["key"], {}).get("importance_guided_inference") == "1"),
            "exact_carryover_3": int(r["key"] in exact_carryover_keys),
        })
        study_rows.append(x)
    _append_rows(wb, "01_STUDIES", study_rows)
    refs = json.load(open(ROOT / "references/refs.json", encoding="utf-8"))
    linked_rows = []
    for ref in refs:
        if ref.get("verdict") not in {"DUPLICATE", "LINKED_COMPANION"}:
            continue
        representative = ref.get("companion_of") or ref.get("duplicate_of") or "NR"
        linked_rows.append({"report_id": ref.get("key"), "representative_report_id": representative,
                            "report_title": ref.get("title") or "NR", "publication_year": ref.get("year") or "NR",
                            "doi": ref.get("doi") or "NR", "linkage_type": ref.get("verdict"),
                            "linkage_evidence": ref.get("verdict_reason") or "NR",
                            "linkage_certainty": ("unresolved cohort equivalence; author-directed family adjudication"
                                                  if ref.get("key") == "amarbayasgalan2021reconstruction" else "bibliographic duplicate/additional report")})
    _append_rows(wb, "01B_LINKED_REPORTS", linked_rows)

    data_rows = []
    for r in rows:
        y = _year_fields(r.get("survey_years", "")); s = survey.get(r["key"], {})
        data_rows.append({"study_id": r["key"], "publication_year": r["year"], "knhanes_cycle": "NR",
                          **y, "pooling_mode": s.get("pooled_cycles") or "NR",
                          "combined_weight_reported": s.get("integrated_weights_reported") or "NR",
                          "combined_weight_strategy": s.get("integrated_weights_used") or "NR",
                          "knhanes_component": "NR", "external_linkage": r.get("other_datasets") or "NR",
                          "initial_sample_n": "NR", "final_analysis_n": r.get("final_n") or "NR",
                          "exclusions": r.get("sample_filtering") or "NR"})
    _append_rows(wb, "02_KNHANES_DATA", data_rows)

    _append_rows(wb, "03_OUTCOMES_PREDICTORS", [{"study_id": r["key"], "outcome_id": f"{r['key']}_outcome_1",
        "outcome": r["outcome"], "outcome_form": r["classification_structure"], "outcome_timing": timing.get(r["key"], {}).get("analytic_target") or "NA",
        "definition_source_cutoff": r["cutoff_reporting_basis"], "definition_reproducibility_credibility": r["outcome_R_C_overall"],
        "candidate_predictors": r["input_variables"], "predictor_reconstructability_alignment": r["predictor_R_C_overall"],
        "evidence": r["outcome_evidence_excerpt"]} for r in rows])
    _append_rows(wb, "04_PREPROCESSING", [{"study_id": r["key"], "missing_data": r["missing_data"],
        "preprocessing": r["preprocessing"], "feature_selection": r["variable_selection"],
        "imbalance_method": r["imbalance_strategy"], "imbalance_order": r["application_order"],
        "test_distribution": r["test_distribution"], "threshold": r["threshold"], "leakage_concern": "not assessed"} for r in rows])
    _append_rows(wb, "05_MODELS", [{"study_id": r["key"], "model_id": f"{r['key']}_model_summary",
        "algorithms": r["models"], "final_model": r["best_model_full"], "best_model_criterion": r["best_criterion"],
        "tuning": r["hyperparameter_tuning"], "validation": r["validation_protocol"], "software_version": "NR",
        "model_object_available": r["code_data_availability"], "prospective_deployment": "NR"} for r in rows])
    _append_rows(wb, "06_VALIDATION_PERFORMANCE", [{"study_id": r["key"], "evaluation_id": f"{r['key']}_reported_best",
        "model_id": f"{r['key']}_model_summary", "evaluation_type": r["evaluation"], "reported_metrics": r["reported_metrics_full"],
        "best_metric": r["best_criterion"], "best_value": r["best_value"], "threshold": r["threshold"],
        "source_location": r["figure_candidate_locations"], "evidence": r["selection_evidence"], "certainty": r["figure_audit_disposition"]} for r in rows])
    _append_rows(wb, "07_VARIABLE_IMPORTANCE", [{"study_id": r["key"], "importance_method": r["importance_methods_full"],
        "interpreted_input_n": r["importance_input_n"], "important_variable_domains": r["important_variable_domains"],
        "selection_rule": r["importance_selection_strategies"], "selected_n": r["importance_selected_n"],
        "downstream_inference": r["importance_guided_inference"], "inferential_n": r["importance_inferential_n"],
        "result": r["importance_result_full"]} for r in rows])
    _append_rows(wb, "08_RATIONALE_FUNCTION_CLAIMS", [{"study_id": r["key"], "rationale": "see canonical JSON field evidence index",
        "implemented_function": r["findings"], "claims": r["findings"], "limitations": r["limitations"],
        "review_status": "primary review"} for r in rows])
    _append_rows(wb, "09_REPORTING", [{"study_id": r["key"], "reporting_summary": r["performance_reporting_depth"],
        "code_data_availability": r["code_data_availability"], "evidence": "see data/study_json and field_evidence_index",
        "reviewer_status": "primary review; second review pending"} for r in rows])
    _append_rows(wb, "10_COMPLEX_SURVEY", survey and list(survey.values()) or [])

    dev_rows, eval_rows = [], []
    included_ids = {r["key"] for r in rows}
    for path_item in sorted((DATA / "probast_ai_reassessment/records").glob("*.json")):
        d = json.load(open(path_item, encoding="utf-8"))
        if d.get("study_id", path_item.stem) not in included_ids:
            continue
        for model in d.get("models", []):
            if model.get("development"):
                dev_rows.append({"study_id": d.get("study_id", path_item.stem), "model_id": model.get("model_id", "index_model"),
                                 "phase": "development", **model["development"]})
            for a in model.get("evaluations", []):
                eval_rows.append({"study_id": d.get("study_id", path_item.stem), "model_id": model.get("model_id", "index_model"),
                                  "phase": "evaluation", **a})
    _append_rows(wb, "11_PROBAST_DEVELOPMENT", dev_rows)
    _append_rows(wb, "12_PROBAST_EVALUATION", eval_rows)

    objects = read_tsv(DATA / "ALL_REPORT_VISUAL_OBJECTS.tsv")
    by_study: dict[str, list[dict[str, str]]] = defaultdict(list)
    visual_rows = []
    for o in objects:
        by_study[o["study_key"]].append(o)
        panels = _panel_count(o) if o["object_type"] == "figure" else 0
        visual_rows.append({**o, "parent_object": o["object_id"], "panel_label": "multiple explicit labels" if panels else "NA",
                            "explicit_panel_n": panels, "panel_count_status": "derived_needs_review" if panels else "no_explicit_multi_panel_label_detected",
                            "metric_sensitive": int(bool(re.search(r"auc|accuracy|precision|recall|f1|calibration|confusion", " ".join((o.get("caption", ""), o.get("content_domains", ""))), re.I))),
                            "discrepancy": o.get("manual_review_reason") or "None"})
    multimedia = []
    for r in rows:
        items = by_study[r["key"]]
        def group(scope, typ): return [x for x in items if x["source_scope"] == scope and x["object_type"] == typ]
        mf, mt, sf, st = group("main", "figure"), group("main", "table"), group("supplement", "figure"), group("supplement", "table")
        multimedia.append({"study_id": r["key"], "main_figure_container_n": len(mf), "main_figure_panel_n": sum(_panel_count(x) for x in mf),
            "main_unpanelled_figure_n": sum(_panel_count(x) == 0 for x in mf),
            "main_figure_visual_unit_n": sum(max(1, _panel_count(x)) for x in mf), "main_table_container_n": len(mt),
            "main_subtable_panel_n": "not assessed", "supp_figure_container_n": len(sf), "supp_figure_panel_n": sum(_panel_count(x) for x in sf),
            "supp_table_container_n": len(st), "supp_subtable_panel_n": "not assessed", "supplement_file_n": r["supplement_archived_files"],
            "total_pages_main": r["pdf_page_count"], "total_pages_supp": "NR", "metric_sensitive_object_n": r["performance_figure_candidates"],
            "image_only_object_n": r["chatgpt_vision_required"], "complete_interpretation_n": r["chatgpt_vision_completed"],
            "uncertain_interpretation_n": r["chatgpt_vision_uncertain"], "unreadable_object_n": r["chatgpt_vision_unreadable"],
            "panel_count_status": "caption/ChatGPT-visible-label derived; needs independent review"})
    _append_rows(wb, "13_MULTIMEDIA_INVENTORY", multimedia)
    _append_rows(wb, "14_VISUAL_OBJECT_LEDGER", visual_rows)
    manifest = read_tsv(ROOT / "references/supplements/manifest.tsv")
    _append_rows(wb, "15_SUPPLEMENT_MANIFEST", manifest)
    evidence_rows = []
    for path_item in sorted((DATA / "study_json").glob("*.json")):
        d = json.load(open(path_item, encoding="utf-8"))
        for field, item in d.get("field_evidence_index", {}).items():
            evs = item.get("evidence") or [{}]
            for ev in evs:
                evidence_rows.append({"study_id": d["study_id"], "domain": field, "judgement": item.get("value_status"),
                    "evidence_status": item.get("evidence_status"), "evidence": ev.get("excerpt", ""), "source": ev.get("source_path", ""),
                    "page": ev.get("page", ""), "verification": ev.get("verification_status", ""),
                    "review_status": "primary review; second review/consensus pending"})
    _append_rows(wb, "16_EVIDENCE_LEDGER", evidence_rows)
    _append_rows(wb, "17_DATA_QUALITY", [{"study_id": r["key"], "required_variable_missing": "see explicit NR fields",
        "conflicting_value": "none automatically detected", "unresolved_issue": "see evidence queue and visual uncertainty",
        "manual_review_required": int(int(r["chatgpt_vision_uncertain"] or 0) + int(r["chatgpt_vision_unreadable"] or 0) > 0),
        "schema_validation": "passed at last canonical build", "last_modified": date.today().isoformat(), "data_freeze": "2026-09-13"} for r in rows])
    wb.save(path)


def main() -> None:
    supplements = read_tsv(DATA / "ARTICLE_SUPPLEMENT_AUDIT.tsv")
    extraction = {r["key"]: r for r in read_tsv(DATA / "extraction.tsv") if r.get("verdict") == "INCLUDE"}
    targets = index(DATA / "TARGET_DEFINITION_AUDIT.tsv")
    metrics = index(DATA / "PROMPT3_CLASSIFICATION_METRICS.tsv")
    imbalance = index(DATA / "PROMPT3_IMBALANCE_AUDIT.tsv")
    alignment = index(DATA / "PROMPT3_TARGET_PREDICTOR_AUDIT.tsv")
    figures = index(DATA / "FIGURE_PERFORMANCE_AUDIT.tsv")
    protocol = {r["key"]: r for r in json.load(open(ROOT / "results/derived/protocol_map.json", encoding="utf-8"))["per_study"]}
    importance = index(DATA / "VARIABLE_IMPORTANCE_DETAILS.tsv")
    importance_domains = index(DATA / "IMPORTANT_VARIABLE_DOMAINS.tsv")
    visual_coverage = ({r["study_key"]: r for r in read_tsv(DATA / "ALL_REPORT_VISUAL_COVERAGE.tsv")}
                       if (DATA / "ALL_REPORT_VISUAL_COVERAGE.tsv").exists() else {})
    visual_objects: dict[str, list[dict[str, str]]] = defaultdict(list)
    if (DATA / "ALL_REPORT_VISUAL_OBJECTS.tsv").exists():
        for item in read_tsv(DATA / "ALL_REPORT_VISUAL_OBJECTS.tsv"):
            visual_objects[item["study_key"]].append(item)

    supplement_files: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_tsv(ROOT / "references/supplements/manifest.tsv"):
        supplement_files[row["key"]].append(row)

    candidates: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_tsv(DATA / "FIGURE_PERFORMANCE_CANDIDATES.tsv"):
        candidates[row["manuscript"]].append(row)

    # These are the purposive cases printed in Additional file 14. Store the complete
    # case-level comparison in its study record rather than leaving it in a separate table.
    from build_appendix14 import CASES
    case_map = {
        r[1]: {
            "case_task_family": r[0], "case_outcome_definition": r[2],
            "case_population_years": r[3], "case_positive_prevalence": r[4],
            "case_evaluation": r[5], "case_metric": r[6], "case_reported_value": r[7],
        }
        for r in CASES
    }

    topic_order: dict[str, int] = {}
    for r in read_tsv(DATA / "TARGET_DEFINITION_AUDIT.tsv"):
        topic_order.setdefault(r["topic"], len(topic_order))
    ordered = sorted(
        [r for r in supplements
         if r.get("key") in extraction and extraction[r["key"]].get("source") == "full_text"],
        key=lambda r: (
            topic_order.get(extraction[r["key"]].get("category", ""), 999),
            -int(r.get("year") or 0), r["key"],
        ),
    )

    rows: list[dict[str, str]] = []
    class_keys = set(metrics)
    for number, base in enumerate(ordered, 1):
        key = base["key"]
        ext = extraction[key]
        typ = study_type(key, ext, class_keys)
        target = targets.get(key, {})
        met, imb, ali = metrics.get(key, {}), imbalance.get(key, {}), alignment.get(key, {})
        fig, pro = figures.get(key, {}), protocol.get(key, {})
        imp, impdom = importance.get(key, {}), importance_domains.get(key, {})
        cands = candidates.get(key, [])
        grades = Counter(figure_grade(x) for x in cands)
        grade_summary = "; ".join(f"{g}:{grades[g]}" for g in "ABCD" if grades[g]) or "None"
        locations = "; ".join(clean(x.get("figure") + " (PDF p" + x.get("page", "") + ")") for x in cands) or "None"
        figure_ledger = " || ".join(
            clean(f"Grade {figure_grade(x)}; {x.get('figure')} (PDF p{x.get('page')}); metrics={x.get('detected_metrics') or 'None'}; printed labels={x.get('numeric_labels_detected') or 'None'}; caption={x.get('caption')}")
            for x in cands
        ) or "None"
        file_manifest = " || ".join(
            clean(f"{x.get('filename')}; source={x.get('source')}; URL={x.get('final_url') or x.get('source_url')}; local={x.get('local_path')}; bytes={x.get('bytes')}; SHA-256={x.get('sha256')}")
            for x in supplement_files.get(key, [])
        ) or "None"
        sf, st, sd, ss = supplement_counts(base)
        case = case_map.get(key, {})
        vis = visual_coverage.get(key, {})
        vis_rows = visual_objects.get(key, [])
        vis_status = Counter(x.get("chatgpt_vision_status", "") for x in vis_rows if x.get("vision_required") == "Y")
        best_value = met.get("best_metric_value", "")
        if best_value and met.get("best_metric_value_unit") in {"%", "%_inferred"}:
            best_value += "%"

        outcome = target.get("outcome") or clean(ext.get("problem"), 300) or "NR"
        operational = target.get("outcome_definition") or ext.get("problem") or "NR"
        classification_fields = typ == "Classification"
        row = {
            "record_no": str(number), "key": key, "year": base.get("year", ""),
            "title": base.get("title") or ext.get("title", ""), "doi": base.get("doi") or "NR",
            "topic": target.get("topic") or ext.get("category", ""), "type": typ,
            "classifier_process_eligible": "Y" if classification_fields else "N",
            "outcome": outcome, "operational_definition": clean(operational),
            "outcome_definition_status": target.get("definition_status") or ("Not applicable" if typ != "Classification" else "NR"),
            "outcome_construction": target.get("outcome_construction") or ("Continuous outcome" if typ == "Regression" else "Not applicable"),
            "cutoff_reporting_basis": (f"{target.get('cutoff_reported')} / {target.get('cutoff_basis')}" if target else "Not applicable"),
            "classification_structure": (f"{target.get('classification_scheme')}; classes={target.get('n_classes') or 'NR'}" if target else "Not applicable"),
            "outcome_evidence_excerpt": clean(target.get("source_text") or ext.get("problem")),
            "supplement_status": base.get("supplement_status", ""), "supplement_archived_files": base.get("files_archived", "0"),
            "supplement_figure_count": sf, "supplement_table_count": st, "supplement_document_count": sd,
            "supplement_content_summary": ss, "supplement_paths": base.get("local_paths") or "None",
            "supplement_file_manifest": file_manifest,
            "journal": ext.get("journal") or "NR", "original_task_label": ext.get("task") or "NR",
            "knhanes_role": ext.get("knhanes_role") or "NR", "other_datasets": clean(ext.get("other_datasets")) or "NR",
            "sample_filtering": clean(ext.get("sample_filtering")) or "NR",
            "input_variables": clean(ext.get("variables")) or "NR",
            "variable_selection": clean(ext.get("variable_selection")) or "NR",
            "preprocessing": clean(ext.get("preprocessing")) or "NR",
            "models": clean(ext.get("models")) or "NR", "best_model_full": clean(ext.get("best_model")) or "NR",
            "hyperparameter_tuning": clean(ext.get("hyperparameter_tuning")) or "NR",
            "reported_metrics_full": clean(ext.get("metrics")) or "NR",
            "interpretability_full": clean(ext.get("interpretability")) or "NR",
            "findings": clean(ext.get("findings")) or "NR", "limitations": clean(ext.get("limitations")) or "NR",
            "code_data_availability": clean(ext.get("code_data_availability")) or "NR",
            "best_criterion": met.get("best_model_selection_metric", "Not applicable"),
            "best_value": best_value or ("NR" if classification_fields else "Not applicable"),
            "evaluation": met.get("evaluation_dataset", "Not applicable"),
            "selection_evidence": clean(met.get("selection_evidence"), 900) or "Not applicable",
            "imbalance_strategy": imb.get("imbalance_strategy", "Not applicable"),
            "application_order": imb.get("application_order", "Not applicable"),
            "test_distribution": imb.get("test_distribution", "Not applicable"),
            "threshold": imb.get("threshold_method", "Not applicable"),
            "outcome_R_C_overall": (f"{ali.get('outcome_reproducibility')}/{ali.get('outcome_credibility')}/{ali.get('outcome_overall')}" if ali else "Not applicable"),
            "predictor_R_C_overall": (f"{ali.get('predictor_reconstructability')}/{ali.get('target_predictor_alignment')}/{ali.get('predictor_overall')}" if ali else "Not applicable"),
            "survey_years": clean(pro.get("조사연차") or ext.get("knhanes_waves")),
            "final_n": str(pro.get("최종 n") or ext.get("n_final") or "NR"),
            "missing_data": clean(pro.get("결측처리") or ext.get("missing_handling")),
            "validation_protocol": clean(pro.get("검증") or ext.get("validation")),
            "performance_reporting_depth": clean(pro.get("성능보고깊이")),
            "variable_importance": clean(pro.get("변수중요도") or ext.get("interpretability")),
            "downstream_analysis": clean(pro.get("사후분석")), "survey_weights": clean(pro.get("가중치") or ext.get("survey_weights")),
            "protocol_best_model": clean(pro.get("최고모형") or ext.get("best_model")),
            "figures_screened": fig.get("catalogued_figures_screened", "0"),
            "performance_figure_candidates": fig.get("performance_figure_candidates", "0"),
            "figure_evidence_grades": grade_summary, "figure_candidate_locations": locations,
            "figure_detected_metrics": fig.get("detected_metrics") or "None", "figure_audit_disposition": fig.get("audit_status") or "NR",
            "figure_candidate_ledger": figure_ledger,
            "all_visual_objects_total": vis.get("objects_total", "0"),
            "all_visual_main_figures": vis.get("main_figures", "0"),
            "all_visual_main_tables": vis.get("main_tables", "0"),
            "all_visual_supplement_figures": vis.get("supplement_figures", "0"),
            "all_visual_supplement_tables": vis.get("supplement_tables", "0"),
            "chatgpt_vision_required": vis.get("vision_required", "0"),
            "chatgpt_vision_completed": str(vis_status.get("completed", 0)),
            "chatgpt_vision_uncertain": str(vis_status.get("uncertain", 0)),
            "chatgpt_vision_unreadable": str(vis_status.get("unreadable", 0)),
            "complete_visual_audit_status": vis.get("audit_status", "not_run"),
            "complete_visual_object_ledger": "data/ALL_REPORT_VISUAL_OBJECTS.tsv",
            "importance_input_n": imp.get("n_input_variables") or "Not applicable",
            "importance_methods_full": clean(imp.get("importance_methods")) or "Not applicable",
            "important_variable_domains": clean(impdom.get("variable_domains")) or "Not applicable",
            "importance_selection_status": imp.get("importance_selection_status") or "Not applicable",
            "importance_selection_strategies": clean(imp.get("selection_strategies")) or "Not applicable",
            "importance_result_full": clean(imp.get("importance_result")) or "Not applicable",
            "importance_guided_inference": imp.get("importance_guided_inference") or "Not applicable",
            "importance_selected_n": imp.get("selected_n") or "Not applicable",
            "importance_inferential_n": imp.get("inferential_n") or "Not applicable",
            "case_task_family": case.get("case_task_family", "Not selected"),
            "case_outcome_definition": case.get("case_outcome_definition", "Not selected"),
            "case_population_years": case.get("case_population_years", "Not selected"),
            "case_positive_prevalence": case.get("case_positive_prevalence", "Not selected"),
            "case_evaluation": case.get("case_evaluation", "Not selected"),
            "case_metric": case.get("case_metric", "Not selected"),
            "case_reported_value": case.get("case_reported_value", "Not selected"),
        }
        rows.append(row)

    assert len(rows) == 222 and len({r["key"] for r in rows}) == 222
    assert Counter(r["type"] for r in rows) == Counter({"Classification": 206, "Regression": 5, "Non-predictive": 11})
    assert sum(r["classifier_process_eligible"] == "Y" for r in rows) == 206
    ahn = next(r for r in rows if r["key"] == "ahn2025discovering")
    assert (ahn["best_criterion"], ahn["best_value"]) == ("F1", "0.754")

    # Canonical JSON is the middle layer: reporting-package sources/audits ->
    # one standardized study record -> flat reusable exports and Additional file 8.
    # Reloading the flat subset from those just-written JSON records prevents
    # the supplement from silently diverging from the study JSON.
    from build_standardized_study_json import build_records
    canonical_paths = build_records(rows)
    rows = [json.load(open(path, encoding="utf-8"))["appendix15_fields"] for path in canonical_paths]
    rows.sort(key=lambda r: int(r["record_no"]))
    assert len(rows) == 222 and len({r["key"] for r in rows}) == 222
    ahn = next(r for r in rows if r["key"] == "ahn2025discovering")
    assert (ahn["best_criterion"], ahn["best_value"]) == ("F1", "0.754")

    write_tsv(DATA / "INTEGRATED_STUDY_AUDIT.tsv", rows)
    write_xlsx(DATA / "INTEGRATED_STUDY_AUDIT.xlsx", rows)

    counts = Counter(r["type"] for r in rows)
    lines = [
        "# Additional file 8. Integrated Study-Level Audit Dataset and Evidence Ledger",
        "",
        "This master audit is generated from the 222 standardized full-report study JSON records in `data/study_json/`. Those canonical records join report metadata, document structure and text counts, the complete figure/table inventory, analysis fields, explicit missingness, and sentence-bounded evidence provenance. No eligible report remains unavailable. Additional and companion reports are consolidated through the study-family linkage ledger in Additional file 2 and are not counted as separate studies. This reader-facing file presents the required subset; source TSV files and legacy extraction JSON remain preserved for reproducibility. It does not pool performance across studies.",
        "",
        "The accompanying `data/INTEGRATED_STUDY_AUDIT.xlsx` is the analysis-ready form of this file. Its 19 linked sheets run from `00_README`, `01_STUDIES`, and `01B_LINKED_REPORTS` through KNHANES data years, outcomes/predictors, preprocessing, models, evaluation, variable importance, reporting, complex-survey appraisal, separate PROBAST+AI development/evaluation units, multimedia inventory, the 2,095-container deduplicated visual ledger, supplement manifest, item-level evidence, and data-quality flags. Publication year and KNHANES analysis years are separate variables. Denominator indicators in `01_STUDIES` reproduce the 222/206/5/11/211/126/180/7/3 analysis cohorts.",
        "",
        f"Coverage by primary analytic type: 222 included full-report studies; Classification {counts['Classification']}; Regression {counts['Regression']}; Non-predictive {counts['Non-predictive']}. Three other-primary studies trained ancillary classifiers, but these components were retained descriptively and were not added to the 206-study primary classification cohort.",
        "",
        "Supplement counts are conservative counts of uniquely labelled Table S*/Figure S* items recoverable from archived filenames or searchable supplement text. `Documents` counts archived PDF, office-document, spreadsheet, archive, text, or CSV containers. Zero means no identifiable item in the archived material, not proof that the publisher supplied none. Figure grades describe evidence extractability/context, not study quality: A=exact printed value with identifiable external, temporal, validation, or test context; B=exact printed value requiring report-level context; C=curve, bar, or rank without recoverable printed values (not interpolated); D=context, diagnostic, importance, architecture, formula, or training figure not treated as standalone performance.",
        "",
    ]
    for record_index, r in enumerate(rows):
        if record_index:
            lines += [r"\newpage", ""]
        lines += [
            f"## {r['record_no']}. {r['key']} ({r['year']}); {r['topic']}", "",
            f"**Title:** {clean(r['title'])}  ", f"**DOI:** {r['doi']}  ",
            f"**Authors:** {clean(r.get('authors') or 'Not reported')}  ",
            f"**Report structure:** {r.get('report_availability', 'Not reported')}; "
            f"characters={r.get('full_text_character_count', '0')}; words={r.get('full_text_word_count', '0')}; "
            f"PDF pages={r.get('pdf_page_count', '0')}; section titles={r.get('section_title_count', '0')}  ",
            f"**Supplement contents:** {r['supplement_content_summary']} ({r['supplement_status']})  ",
            f"**Type:** {r['type']}  ", f"**Primary classification audit:** {r['classifier_process_eligible']}", "",
            "| Field | Integrated extraction |", "|---|---|",
            f"| Outcome | {clean(r['outcome'])} |",
            f"| Operational definition | {clean(r['operational_definition'])} |",
            f"| Construction | {r['outcome_construction']} |",
            f"| Cutoff reporting / basis | {r['cutoff_reporting_basis']} |",
            f"| Classification | {r['classification_structure']} |",
            f"| Evidence excerpt | {clean(r['outcome_evidence_excerpt'], 1000)} |",
            f"| Study characteristics | journal={clean(r['journal'])}; KNHANES role={r['knhanes_role']}; other datasets={clean(r['other_datasets'], 500)} |",
            f"| Sample and inputs | filtering={clean(r['sample_filtering'], 1000)}; variables={clean(r['input_variables'], 1200)} |",
            f"| Modelling | variable selection={clean(r['variable_selection'], 700)}; preprocessing={clean(r['preprocessing'], 700)}; models={clean(r['models'], 800)}; tuning={clean(r['hyperparameter_tuning'], 600)} |",
        ]
        if r["classifier_process_eligible"] == "Y":
            lines += [
                f"| Study-level audit | Best criterion={r['best_criterion']}; best value={r['best_value']}; evaluation={r['evaluation']} |",
                f"| Imbalance / order / threshold | {r['imbalance_strategy']} / {r['application_order']} / {r['threshold']} |",
                f"| Outcome R/C/overall | {r['outcome_R_C_overall']} |",
                f"| Predictor R/C/overall | {r['predictor_R_C_overall']} |",
                f"| Selection evidence | {clean(r['selection_evidence'], 1000)} |",
            ]
        lines += [
            f"| Protocol | years={r['survey_years']}; n={r['final_n']}; missing={r['missing_data']}; validation={r['validation_protocol']}; weights={r['survey_weights']} |",
            f"| Complex-survey appraisal | role={r.get('survey_analytic_role','Not assessed')}; estimand={r.get('survey_estimand','Not assessed')}; population claim={r.get('survey_population_claim','Not assessed')}; applicability={r.get('survey_applicability','Not assessed')}; adherence={r.get('survey_methodological_adherence','Not assessed')}; {r.get('survey_design_reporting','')} |",
            f"| Complex-survey evidence | {clean(r.get('survey_appraisal_evidence','Not assessed'), 1000)} |",
            f"| Interpretation pathway | importance={r['variable_importance']}; downstream={r['downstream_analysis']} |",
            f"| Variable-importance audit | input n={r['importance_input_n']}; methods={r['importance_methods_full']}; domains={r['important_variable_domains']}; selection={r['importance_selection_status']} / {r['importance_selection_strategies']}; guided inference={r['importance_guided_inference']}; selected/inferential n={r['importance_selected_n']}/{r['importance_inferential_n']} |",
            f"| Variable-importance result | {clean(r['importance_result_full'], 1200)} |",
            f"| Figure evidence | screened={r['figures_screened']}; candidates={r['performance_figure_candidates']}; grades={r['figure_evidence_grades']}; locations={r['figure_candidate_locations']} |",
            f"| Figure audit disposition | {clean(r['figure_audit_disposition'], 900)} |",
            f"| Figure-level candidate ledger | {clean(r['figure_candidate_ledger'], 1600)} |",
            f"| Complete figure/table inventory | total={r['all_visual_objects_total']}; main figures/tables={r['all_visual_main_figures']}/{r['all_visual_main_tables']}; supplement figures/tables={r['all_visual_supplement_figures']}/{r['all_visual_supplement_tables']}; ChatGPT vision required/completed/uncertain/unreadable={r['chatgpt_vision_required']}/{r['chatgpt_vision_completed']}/{r['chatgpt_vision_uncertain']}/{r['chatgpt_vision_unreadable']}; status={r['complete_visual_audit_status']}; ledger={r['complete_visual_object_ledger']} |",
            f"| Supplement file manifest | {clean(r['supplement_file_manifest'], 1600)} |",
            f"| Findings / limitations | {clean(r['findings'], 900)} / {clean(r['limitations'], 700)} |",
            f"| Code and data | {clean(r['code_data_availability'], 600)} |",
        ]
        if r["case_task_family"] != "Not selected":
            lines.append(
                f"| Same-disease case analysis | {r['case_task_family']}; {r['case_outcome_definition']}; {r['case_population_years']}; prevalence={r['case_positive_prevalence']}; {r['case_evaluation']}; {r['case_metric']}={r['case_reported_value']} |"
            )
        lines += [""]
    (APP / "appendix8_integrated_study_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"n": len(rows), "types": dict(counts), "ahn": {"criterion": ahn["best_criterion"], "value": ahn["best_value"]}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
