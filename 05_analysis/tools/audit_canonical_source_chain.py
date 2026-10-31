"""Verify source -> canonical JSON -> Additional file 8 -> manuscript/figure derivations."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import jsonschema
import openpyxl

from canonical_data import canonical_records

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PAPER = ROOT / "manuscript/submission/bmc_main.tex"
OUT_JSON = DATA / "CANONICAL_SOURCE_CHAIN_AUDIT.json"
OUT_MD = DATA / "CANONICAL_SOURCE_CHAIN_AUDIT.md"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def check(name: str, ok: bool, detail: str, checks: list[dict]) -> None:
    checks.append({"check": name, "status": "pass" if ok else "fail", "detail": detail})


def manuscript_value(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1) if m else None


def main() -> None:
    records = canonical_records()
    checks: list[dict] = []
    schema = json.load(open(DATA / "STANDARDIZED_STUDY.schema.json", encoding="utf-8"))
    schema_errors = []
    for record in records:
        try:
            jsonschema.validate(record, schema)
        except jsonschema.ValidationError as exc:
            schema_errors.append({"study_id": record.get("study_id"), "path": list(exc.absolute_path), "message": exc.message})
    check("canonical_schema", not schema_errors, f"records={len(records)}; errors={len(schema_errors)}", checks)
    check("canonical_unique_222", len(records) == len({x["study_id"] for x in records}) == 222,
          f"records={len(records)}; unique={len({x['study_id'] for x in records})}", checks)

    raw_mismatch = []
    for record in records:
        raw_path = DATA / "extraction" / f"{record['study_id']}.json"
        raw = json.load(open(raw_path, encoding="utf-8")) if raw_path.exists() else None
        if raw != record.get("legacy_extraction_snapshot"):
            raw_mismatch.append(record["study_id"])
    check("report_summary_snapshot_lossless", not raw_mismatch,
          f"value mismatches={len(raw_mismatch)}", checks)

    tsv = read_tsv(DATA / "INTEGRATED_STUDY_AUDIT.tsv")
    json_rows = [x["appendix15_fields"] for x in records]
    json_rows.sort(key=lambda x: int(x["record_no"])); tsv.sort(key=lambda x: int(x["record_no"]))
    row_mismatch = []
    for a, b in zip(json_rows, tsv):
        if a != b:
            fields = sorted(k for k in set(a) | set(b) if str(a.get(k, "")) != str(b.get(k, "")))
            row_mismatch.append({"study_id": a.get("key") or b.get("key"), "fields": fields})
    check("canonical_json_to_integrated_tsv_exact", len(json_rows) == len(tsv) == 222 and not row_mismatch,
          f"rows={len(tsv)}; mismatched records={len(row_mismatch)}", checks)

    wb = openpyxl.load_workbook(DATA / "INTEGRATED_STUDY_AUDIT.xlsx", read_only=True, data_only=True)
    ws = wb["01_STUDIES"]
    xheaders = [str(x.value or "") for x in ws[1]]
    xrows = [{h: "" if c.value is None else str(c.value) for h, c in zip(xheaders, row)} for row in ws.iter_rows(min_row=2)]
    xrows.sort(key=lambda x: int(x["record_no"])); x_mismatch = []
    def xnorm(value: object) -> str:
        raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff\ufeff]", " ", str(value or "")).replace("※", "Note:")
        for old, new in zip("①②③④⑤⑥⑦⑧⑨⑩", (f"({i})" for i in range(1, 11))):
            raw = raw.replace(old, new)
        return " ".join(raw.replace("|", "/").split())
    for a, b in zip(tsv, xrows):
        fields = [h for h in a if xnorm(a.get(h, "")) != xnorm(b.get(h, ""))]
        if fields: x_mismatch.append({"study_id": a["key"], "fields": fields})
    check("integrated_tsv_to_xlsx_exact", len(xrows) == 222 and not x_mismatch,
          f"rows={len(xrows)}; mismatched records={len(x_mismatch)}", checks)
    required_sheets = ["00_README", "01_STUDIES", "01B_LINKED_REPORTS", "02_KNHANES_DATA", "03_OUTCOMES_PREDICTORS",
                       "04_PREPROCESSING", "05_MODELS", "06_VALIDATION_PERFORMANCE", "07_VARIABLE_IMPORTANCE",
                       "08_RATIONALE_FUNCTION_CLAIMS", "09_REPORTING", "10_COMPLEX_SURVEY",
                       "11_PROBAST_DEVELOPMENT", "12_PROBAST_EVALUATION", "13_MULTIMEDIA_INVENTORY",
                       "14_VISUAL_OBJECT_LEDGER", "15_SUPPLEMENT_MANIFEST", "16_EVIDENCE_LEDGER", "17_DATA_QUALITY"]
    check("af8_multisheet_structure", wb.sheetnames == required_sheets,
          f"sheets={len(wb.sheetnames)}; expected={len(required_sheets)}", checks)
    flag_counts = {h: sum(int(x.get(h, 0) or 0) for x in xrows) for h in
                   ("included_222", "classification_core_206", "continuous_prediction_5", "other_task_11",
                    "probast_prediction_211", "explicit_variable_importance_126", "multiyear_pooled_180",
                    "downstream_inference_7", "exact_carryover_3")}
    expected_flags = {"included_222":222, "classification_core_206":206, "continuous_prediction_5":5,
                      "other_task_11":11, "probast_prediction_211":211, "explicit_variable_importance_126":126,
                      "multiyear_pooled_180":180, "downstream_inference_7":7, "exact_carryover_3":3}
    check("af8_denominator_flags", flag_counts == expected_flags,
          f"observed={flag_counts}", checks)
    check("af8_probast_unit_sheets", wb["11_PROBAST_DEVELOPMENT"].max_row - 1 == 203
          and wb["12_PROBAST_EVALUATION"].max_row - 1 == 243,
          f"development={wb['11_PROBAST_DEVELOPMENT'].max_row-1}; evaluation={wb['12_PROBAST_EVALUATION'].max_row-1}", checks)
    check("af8_visual_container_sheet", wb["14_VISUAL_OBJECT_LEDGER"].max_row - 1 == 2095,
          f"visual containers={wb['14_VISUAL_OBJECT_LEDGER'].max_row-1}", checks)

    appendix = (ROOT / "manuscript/submission/appendices/appendix8_integrated_study_audit.md").read_text(encoding="utf-8")
    missing_headings = [r["key"] for r in tsv if not re.search(rf"^##\s+\d+\.\s+{re.escape(r['key'])}\b", appendix, re.M)]
    appendix_norm = re.sub(r"\s+", " ", appendix)
    missing_titles = [r["key"] for r in tsv if r["title"] and re.sub(r"\s+", " ", r["title"]).strip() not in appendix_norm]
    check("integrated_tsv_to_appendix8_records", not missing_headings and not missing_titles,
          f"missing headings={len(missing_headings)}; missing exact titles={len(missing_titles)}", checks)

    object_rows = read_tsv(DATA / "ALL_REPORT_VISUAL_OBJECTS.tsv")
    json_objects = sum(len(r["visual_objects"]["items"]) for r in records)
    object_ids = [x["object_id"] for r in records for x in r["visual_objects"]["items"]]
    check("visual_ledger_to_canonical_json", json_objects == len(object_rows) == 2095 and len(set(object_ids)) == 2095,
          f"canonical={json_objects}; ledger={len(object_rows)}; unique IDs={len(set(object_ids))}", checks)

    evidence = Counter()
    containment_errors = []
    for record in records:
        for field, item in record["field_evidence_index"].items():
            evidence[item["evidence_status"]] += 1
            for ev in item["evidence"]:
                if ev["source_type"] == "main_report" and ev.get("source_path"):
                    path = ROOT / ev["source_path"]
                    if not path.exists() or ev.get("start_sentence", "") not in re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="ignore")):
                        containment_errors.append({"study_id": record["study_id"], "field": field})
    check("candidate_evidence_exact_source_containment", not containment_errors,
          f"main-report spans tested; containment errors={len(containment_errors)}", checks)

    analysis = json.load(open(ROOT / "results/derived/analysis.json", encoding="utf-8"))
    prompt3 = json.load(open(ROOT / "results/derived/prompt3_audit.json", encoding="utf-8"))
    importance = json.load(open(ROOT / "results/derived/importance_pathway.json", encoding="utf-8"))
    canonical_types = Counter(r["controlled_vocabulary"]["primary_analytic_type"] for r in records)
    canonical_tasks = Counter(r["legacy_extraction_snapshot"].get("task") or "missing" for r in records)
    check("derived_primary_counts", analysis["n_include"] == 222 and canonical_tasks["classification"] == 206
          and canonical_tasks["regression"] == 5 and canonical_types["Non-predictive"] == 11,
          f"included={analysis['n_include']}; classification={canonical_tasks['classification']}; regression={canonical_tasks['regression']}; non-predictive={canonical_types['Non-predictive']}", checks)
    check("derived_classifier_audit_denominator", prompt3.get("n_classification") == 206,
          f"prompt3 n_classification={prompt3.get('n_classification')}", checks)
    imp_summary = importance.get("summary", {})
    check("derived_importance_pathway", imp_summary.get("n_predictive") == 206
          and imp_summary.get("n_algorithm_comparison") == 177
          and imp_summary.get("n_comparison_and_explicit_importance") == 117
          and imp_summary.get("n_no_comparison_and_explicit_importance") == 9
          and imp_summary.get("n_importance_guided_inference") == 7
          and imp_summary.get("n_exact_carryover") == 3,
          f"predictive={imp_summary.get('n_predictive')}; comparison={imp_summary.get('n_algorithm_comparison')}; "
          f"comparison+importance={imp_summary.get('n_comparison_and_explicit_importance')}; "
          f"importance without comparison={imp_summary.get('n_no_comparison_and_explicit_importance')}; "
          f"guided={imp_summary.get('n_importance_guided_inference')}; exact={imp_summary.get('n_exact_carryover')}", checks)

    canonical_ids = {r["study_id"] for r in records}
    perf_studies = [r for r in read_tsv(DATA / "FIGURE_PERFORMANCE_AUDIT.tsv") if r["key"] in canonical_ids]
    perf_figures = [r for r in read_tsv(DATA / "FIGURE_PERFORMANCE_CANDIDATES.tsv") if r["manuscript"] in canonical_ids]
    perf_headers = set(perf_figures[0]) if perf_figures else set()
    check("chatgpt_only_performance_figure_subset",
          len(perf_studies) == 222 and sum(int(x["catalogued_figures_screened"]) for x in perf_studies) == 976
          and len(perf_figures) == 539 and len({x["manuscript"] for x in perf_figures}) == 177
          and "ocr_excerpt" not in perf_headers and "vision_text_excerpt" in perf_headers,
          f"studies={len(perf_studies)}; figures={sum(int(x['catalogued_figures_screened']) for x in perf_studies)}; candidates={len(perf_figures)}; "
          f"candidate studies={len({x['manuscript'] for x in perf_figures})}; OCR field present={'ocr_excerpt' in perf_headers}", checks)

    ahn = next(r for r in tsv if r["key"] == "ahn2025discovering")
    check("ahn_best_score_propagation", ahn["best_criterion"] == "F1" and ahn["best_value"] == "0.754"
          and "Best criterion=F1; best value=0.754" in appendix,
          f"integrated criterion={ahn['best_criterion']}; value={ahn['best_value']}; Additional file 8 match="
          f"{'Best criterion=F1; best value=0.754' in appendix}", checks)
    huang = next(r for r in tsv if r["key"] == "hunag2023predicting")
    extractable_best = [r for r in tsv if r["classifier_process_eligible"] == "Y" and r["best_value"] != "NR"]
    check("huang_best_score_propagation", huang["best_criterion"] == "Accuracy" and huang["best_value"] == "0.818",
          f"criterion={huang['best_criterion']}; value={huang['best_value']}", checks)
    check("extractable_best_value_count", len(extractable_best) == 66,
          f"numeric/non-NR best values={len(extractable_best)}", checks)
    check("appendix8_no_legacy_ocr_disposition", "OCR-screened" not in appendix,
          f"legacy OCR-screened occurrences={appendix.count('OCR-screened')}", checks)

    manuscript = PAPER.read_text(encoding="utf-8")
    # Expand generated protocol-v1.2 count macros before numeric text checks.
    # The active manuscript intentionally uses these macros to prevent denominator drift.
    macro_path = PAPER.parent / "protocol_v1_2_numbers.tex"
    if macro_path.exists():
        for macro, value in re.findall(r"\\newcommand\{\\(\w+)\}\{([\d,]+)\}", macro_path.read_text(encoding="utf-8")):
            manuscript = manuscript.replace(f"\\{macro}{{}}", value)
    methods = manuscript.split(r"\section{Methods}", 1)[1].split(r"\section{Results}", 1)[0]
    results = manuscript.split(r"\section{Results}", 1)[1].split(r"\section{Discussion}", 1)[0]
    method_af = re.findall(r"\\mmapp\{(\d+)\}", methods)
    results_af8_count = results.count(r"\mmapp{8}")
    methods_af8_count = methods.count(r"\mmapp{8}")
    results_af = re.findall(r"\\mmapp\{(\d+)\}", results)
    results_first_order = list(dict.fromkeys(results_af))
    check("methods_only_additional_files_1_2", set(method_af) <= {"1", "2"} and {"1", "2"} <= set(method_af),
          f"Methods Additional-file citations={method_af}", checks)
    check("af8_first_and_once_at_results_end", results_af8_count == 1 and methods_af8_count == 0,
          f"Results AF8 citations={results_af8_count}; Methods={methods_af8_count}", checks)
    check("results_additional_file_first_order", results_first_order == ["3", "4", "5", "6", "7", "8"],
          f"first-citation order={results_first_order}", checks)
    af2 = (ROOT / "manuscript/submission/appendices/additional_file2_methods.md").read_text(encoding="utf-8")
    required_s2 = [f"## Table S2.{i}." for i in range(1, 18)]
    af2_heading_count = len(re.findall(r"^## Table S2\.\d+\.", af2, re.M))
    check("af2_exact_table_hierarchy", all(x in af2 for x in required_s2)
          and af2_heading_count == 17,
          f"required={len(required_s2)}; found={af2_heading_count}", checks)
    af4 = (ROOT / "manuscript/submission/appendices/additional_file4_classification.md").read_text(encoding="utf-8")
    check("af4_s4_12_uncertainty", "Table S4.12. Confidence intervals, resampling distributions, and paired comparisons" in af4,
          "S4.12 contains comparative uncertainty rather than a duplicated study-level ledger", checks)
    af5 = (ROOT / "manuscript/submission/appendices/additional_file5_analytic_function.md").read_text(encoding="utf-8")
    af5_figure_count = len(re.findall(r"^## Figure S5\.\d+\.", af5, re.M))
    check("af5_exact_figure_hierarchy", all(f"## Figure S5.{i}." in af5 for i in range(1,4))
          and af5_figure_count == 3,
          f"supplementary figures={af5_figure_count}", checks)
    claims = [
        ("manuscript_included_n", 222, r"(\d+) (?:unique )?full-report studies(?: \([^)]*\))? (?:were )?included"),
        ("manuscript_classification_n", 206, r"all (\d+) classification studies"),
        ("manuscript_visual_objects_n", 2095, r"final ledger contains ([\d,]+) (?:numbered figure/table )?containers"),
        ("manuscript_vision_objects_n", 1529, r"Of these, ([\d,]+) required image"),
        ("manuscript_main_figures_n", 809, r"([\d,]+) main-report figures"),
        ("manuscript_main_tables_n", 817, r"([\d,]+) main-report tables"),
        ("manuscript_supp_figures_n", 167, r"([\d,]+) supplementary figures"),
        ("manuscript_supp_tables_n", 302, r"([\d,]+) supplementary tables"),
    ]
    for name, wanted, pattern in claims:
        got = manuscript_value(manuscript, pattern)
        check(name, got is not None and int(got.replace(",", "")) == wanted,
              f"expected={wanted}; manuscript={got}", checks)
    manuscript_importance = [
        (177, r"Among them, (\d+)\s+compared algorithms"),
        (117, r"Of these, (\d+) proceeded to a named or operationally defined model-based"),
        (9, r"another (\d+) studies reported model-based variable importance without an"),
        (31, r"(\d+) used model-derived importance or\s+selection to define a reduced model subset"),
        (7, r"Only (\d+) \(5\.6\\%\) explicitly used model-derived"),
        (3, r"Exact one-to-one carryover\s+was reported in (\d+) studies"),
    ]
    for wanted, pattern in manuscript_importance:
        got = manuscript_value(manuscript, pattern)
        check(f"manuscript_importance_{wanted}", got is not None and int(got) == wanted,
              f"expected={wanted}; manuscript={got}", checks)

    active_figures = re.findall(r"\\includegraphics\[[^]]*\]\{figs/([^}]+)\}", manuscript)
    missing_figures = [name for name in active_figures if not (ROOT / "figures/submission" / name).exists()]
    check("active_manuscript_figures_exist", not missing_figures,
          f"referenced={len(active_figures)}; missing={missing_figures}", checks)

    result = {
        "audit_date": "2026-09-13", "checks": checks,
        "summary": dict(Counter(x["status"] for x in checks)),
        "evidence_status_counts": dict(evidence),
        "evidence_interpretation": "candidate_needs_review is structurally traceable but not semantically adjudicated; source_span_not_yet_recorded is an explicit evidence gap.",
        "details": {"schema_errors": schema_errors, "raw_mismatches": raw_mismatch,
                    "json_tsv_mismatches": row_mismatch, "tsv_xlsx_mismatches": x_mismatch,
                    "evidence_containment_errors": containment_errors},
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Canonical source-chain audit", "",
             f"Checks: pass {result['summary'].get('pass', 0)}; fail {result['summary'].get('fail', 0)}.", "",
             "| Check | Status | Detail |", "|---|---|---|"]
    lines += [f"| {x['check']} | {x['status']} | {x['detail']} |" for x in checks]
    lines += ["", "## Evidence maturity", "",
              f"- Verified or curated: {evidence['verified_or_curated']}",
              f"- Automated candidate needing semantic review: {evidence['candidate_needs_review']}",
              f"- Original-report span not yet recorded: {evidence['source_span_not_yet_recorded']}", "",
              "Structural consistency does not promote automated candidates to verified evidence. Remaining items are retained in `STANDARDIZED_STUDY_EVIDENCE_QUEUE.tsv`."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    if result["summary"].get("fail"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
