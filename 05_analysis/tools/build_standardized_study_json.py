"""Build one canonical, evidence-aware JSON record per included study.

The canonical record is the lossless middle layer between report/package sources
and reader-facing exports such as Additional file 8.  It does not overwrite the
legacy ``data/extraction/*.json`` files; those remain provenance inputs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz
import jsonschema


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "study_json"
SCHEMA_VERSION = "1.0.0"

NOT_APPLICABLE = {"not applicable", "n/a", "na", "해당 없음", "해당없음"}
NOT_REPORTED = {"nr", "not reported", "미기재", "보고되지 않음", "언급 없음", "없음"}
NOT_RECOVERABLE = {"not recoverable", "회수 불가", "복구 불가"}
STOP = {
    "the", "and", "for", "with", "from", "that", "this", "were", "was", "are", "had",
    "into", "using", "used", "study", "model", "models", "data", "analysis", "reported",
    "not", "none", "applicable", "full", "report", "other", "than", "among", "after",
}

MODEL_TERMS = [
    (r"\bcatboost\b", "CatBoost"), (r"\blightgbm\b|light gradient", "LightGBM"),
    (r"\bxgboost(?:-rf)?\b|extreme gradient", "XGBoost"),
    (r"\brandom forest\b", "Random forest"), (r"\bextra trees?\b", "Extra Trees"),
    (r"\bgradient boost", "Gradient boosting"), (r"\badaboost\b|ada boost", "AdaBoost"),
    (r"\blogistic regression\b", "Logistic regression"),
    (r"\blinear discriminant", "Linear discriminant analysis"),
    (r"\bsupport vector|\bsvm\b", "Support vector machine"),
    (r"\bk[- ]?nearest|\bknn\b", "k-nearest neighbors"),
    (r"\bnaive bayes|naïve bayes", "Naive Bayes"), (r"\bdecision tree\b", "Decision tree"),
    (r"\bridge\b", "Ridge classifier/regression"), (r"\blasso\b", "LASSO"),
    (r"\belastic net\b", "Elastic net"), (r"\bneural network|\bann\b|인공신경망|신경망", "Neural network"),
    (r"\bdeep learning\b", "Deep learning model"), (r"\btransformer\b", "Transformer"),
]

METRIC_COLUMNS = ["Accuracy", "Balanced accuracy", "AUROC", "AUPRC/average precision",
                  "Sensitivity/recall", "Specificity/TNR", "Precision/PPV", "NPV", "F1", "MCC",
                  "Cohen kappa", "Brier score", "Log loss", "Calibration", "Decision curve/net benefit",
                  "Confidence interval", "SD/resampling distribution", "Paired model comparison"]


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def index_tsv(name: str, key: str = "key") -> dict[str, dict[str, str]]:
    return {r[key]: r for r in read_tsv(DATA / name) if r.get(key)}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def status_for(value: Any) -> str:
    text = clean(value).lower()
    if text in NOT_APPLICABLE or text.startswith("not applicable"):
        return "not_applicable"
    if text in NOT_RECOVERABLE or text.startswith("not recoverable"):
        return "not_recoverable"
    if not text or text in NOT_REPORTED or text.startswith("nr "):
        return "not_reported"
    return "reported_or_derived"


def full_text(markdown: str) -> str:
    marker = "## Full text"
    text = markdown.split(marker, 1)[1] if marker in markdown else markdown
    text = re.sub(r"<!--\s*page\s+\d+\s*-->", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def page_sentences(markdown: str) -> list[dict[str, Any]]:
    marker = "## Full text"
    text = markdown.split(marker, 1)[1] if marker in markdown else markdown
    parts = re.split(r"<!--\s*page\s+(\d+)\s*-->", text, flags=re.I)
    pages: list[tuple[int | None, str]] = []
    if len(parts) == 1:
        pages = [(None, text)]
    else:
        for i in range(1, len(parts), 2):
            pages.append((int(parts[i]), parts[i + 1]))
    result = []
    for page, body in pages:
        body = re.sub(r"\s+", " ", body).strip()
        # Exact source strings are kept; segmentation only defines auditable
        # start/end boundaries and never rewrites the quotation.
        sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ가-힣0-9])", body) if len(x.strip()) >= 12]
        for i, sentence in enumerate(sentences):
            result.append({"page": page, "index": i, "sentence": sentence})
    return result


def tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ가-힣][A-Za-zÀ-ÖØ-öø-ÿ가-힣0-9_-]{2,}", text.lower()) if x not in STOP}


def numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?%?", text))


def controlled_terms(flat: dict[str, str], legacy: dict[str, Any], metric_row: dict[str, str]) -> dict[str, Any]:
    model_text = " ".join(legacy.get("models") or []) if isinstance(legacy.get("models"), list) else clean(flat.get("models"))
    models = [name for pattern, name in MODEL_TERMS if re.search(pattern, model_text, re.I)]
    validation = clean(flat.get("validation_protocol")).lower()
    validation_types = []
    for pattern, name in ((r"train.?test|hold.?out|split|단일\s*분할|훈련.?검증", "train_test_split"),
                          (r"cross.?validation|\bcv\b|fold|교차\s*검증", "cross_validation"),
                          (r"external|외부\s*검증", "external_validation"),
                          (r"temporal|시간적\s*검증|시계열\s*검증", "temporal_validation"),
                          (r"bootstrap|부트스트랩", "bootstrap")):
        if re.search(pattern, validation): validation_types.append(name)
    interp = clean(flat.get("interpretability_full") + " " + flat.get("variable_importance")).lower()
    methods = []
    for pattern, name in ((r"\bshap", "SHAP"), (r"\blime\b", "LIME"),
                          (r"permutation", "Permutation importance"), (r"feature importance|variable importance", "Model-native importance"),
                          (r"partial dependence|\bpdp\b", "Partial dependence"),
                          (r"nomogram", "Nomogram"), (r"coefficient|odds ratio", "Coefficient/association measure")):
        if re.search(pattern, interp): methods.append(name)
    return {
        "primary_analytic_type": flat.get("type") or "Not reported",
        "task_type": legacy.get("task") or flat.get("original_task_label") or "Not reported",
        "classifier_process_eligible": flat.get("classifier_process_eligible") == "Y",
        "knhanes_role": legacy.get("knhanes_role") or flat.get("knhanes_role") or "Not reported",
        "model_names": models,
        "performance_metrics_reported": [name for name in METRIC_COLUMNS if metric_row.get(name) == "Y"],
        "validation_types": validation_types,
        "interpretability_methods": methods,
        "survey_weights_status": ("used" if re.search(r"\byes\b|사용|반영", clean(flat.get("survey_weights")), re.I)
                                  else "not_reported" if status_for(flat.get("survey_weights")) != "reported_or_derived" else "reported_other"),
    }


def source_span(excerpt: str, source_path: str, evidence_type: str, page: Any = None,
                verification: str = "direct_source_excerpt") -> dict[str, Any]:
    excerpt = clean(excerpt)
    bits = [x.strip() for x in re.split(r"(?<=[.!?])\s+", excerpt) if x.strip()]
    return {
        "source_type": evidence_type,
        "source_path": source_path,
        "page": page,
        "start_sentence": bits[0] if bits else "",
        "end_sentence": bits[-1] if bits else "",
        "excerpt": excerpt,
        "verification_status": verification,
    }


def candidate_span(value: Any, sentences: list[dict[str, Any]], source_path: str) -> list[dict[str, Any]]:
    query = clean(value)
    qt, qn = tokens(query), numbers(query)
    if not query or not sentences or (not qt and not qn):
        return []
    best: tuple[float, int, int] | None = None
    for i in range(len(sentences)):
        for width in (1, 2, 3):
            window = sentences[i:i + width]
            if not window or any(x["page"] != window[0]["page"] for x in window):
                continue
            text = " ".join(x["sentence"] for x in window)
            overlap = len(qt & tokens(text)) / max(1, min(12, len(qt)))
            n_overlap = len(qn & numbers(text)) / max(1, len(qn)) if qn else 0
            score = overlap + 0.55 * n_overlap
            if best is None or score > best[0]:
                best = (score, i, width)
    if not best:
        return []
    score, i, width = best
    # A candidate is retained only when it has meaningful lexical alignment or
    # reproduces numerical details. Low-scoring legacy summaries remain honestly
    # marked as lacking a verified source span.
    if score < 0.30 and not (qn and score >= 0.22):
        return []
    window = sentences[i:i + width]
    excerpt = " ".join(x["sentence"] for x in window)
    return [source_span(excerpt, source_path, "main_report", window[0]["page"],
                        f"automated_candidate_score={score:.3f}; requires_review")]


def section_structure(pdf: Path, markdown: str = "") -> list[dict[str, Any]]:
    if not pdf.exists():
        return []
    doc = fitz.open(pdf)
    toc = doc.get_toc(simple=True)
    if toc:
        result = [{"order": i, "level": int(level), "title": clean(title), "page": int(page),
                   "detection_method": "pdf_toc"}
                  for i, (level, title, page) in enumerate(toc, 1) if clean(title)]
        doc.close()
        return result
    # Numbered headings in the preserved full-text stream are more reliable
    # than font heuristics for theses without embedded PDF bookmarks.
    md_sections = []
    page = None
    for raw in markdown.splitlines():
        pm = re.match(r"<!--\s*page\s+(\d+)\s*-->", raw, re.I)
        if pm:
            page = int(pm.group(1)); continue
        text = clean(raw)
        m = re.match(r"^(\d+(?:\.\d+)*\.)\s+([A-ZÀ-ÖØ-ÞĞİŞÇÖÜ가-힣].{2,120})$", text)
        if not m or re.search(r"\.{4,}|https?://|\bdoi\b", text, re.I):
            continue
        title = clean(m.group(2)).rstrip(".")
        if len(title.split()) > 16:
            continue
        number = m.group(1).rstrip(".")
        md_sections.append({"order": len(md_sections) + 1, "level": len(number.split(".")),
                            "title": f"{m.group(1)} {title}", "page": page,
                            "detection_method": "numbered_fulltext_heading"})
    if len(md_sections) >= 3:
        doc.close()
        return md_sections
    candidates: list[tuple[int, float, str]] = []
    body_sizes = []
    pages = []
    for page_no, page in enumerate(doc, 1):
        info = page.get_text("dict", sort=True)
        pages.append((page_no, info))
        for block in info.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = clean(span.get("text"))
                    if len(text) > 25:
                        body_sizes.append(float(span.get("size", 0)))
    median = sorted(body_sizes)[len(body_sizes) // 2] if body_sizes else 10.0
    for page_no, info in pages:
        for block in info.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = clean(" ".join(str(x.get("text", "")) for x in spans))
                if not (3 <= len(text) <= 150) or re.match(r"(?i)^(fig(?:ure)?|table|그림|표)\b", text):
                    continue
                if re.search(r"(?i)conference|authorized|licen[cs]e|copyright|\bdoi\b|https?://|www\.|isbn|[©${}]|SAMME", text):
                    continue
                size = max((float(x.get("size", 0)) for x in spans), default=0)
                bold = any("bold" in str(x.get("font", "")).lower() for x in spans)
                numbered = bool(re.match(r"^(?:[IVXLC]+\.?|\d+(?:\.\d+)*\.?)\s+[A-ZÀ-ÖØ-Þ가-힣]", text))
                uppercase = text.upper() == text and bool(re.search(r"[A-Z]{3}", text))
                # On title/front-matter pages, large-font lines are usually the
                # article title, authors, or institution rather than sections.
                large_heading = size >= median * 1.18 and (bold or len(text) < 80) and page_no > 1
                if numbered or (uppercase and len(text.split()) <= 12) or large_heading:
                    candidates.append((page_no, size, text))
    doc.close()
    seen = set(); result = []
    sizes = sorted({round(x[1], 1) for x in candidates}, reverse=True)
    for page, size, title in candidates:
        norm = re.sub(r"\W+", " ", title.lower()).strip()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        m = re.match(r"^(\d+(?:\.\d+)*)", title)
        level = len(m.group(1).split(".")) if m else (sizes.index(round(size, 1)) + 1 if round(size, 1) in sizes else 1)
        result.append({"order": len(result) + 1, "level": min(level, 6), "title": title,
                       "page": page, "detection_method": "pdf_layout_heuristic"})
    return result


def explicit_evidence(key: str, sources: dict[str, dict[str, dict[str, str]]]) -> dict[str, list[dict[str, Any]]]:
    target = sources["target"].get(key, {})
    metrics = sources["metrics"].get(key, {})
    importance = sources["importance"].get(key, {})
    align = sources["alignment"].get(key, {})
    mapping: dict[str, tuple[str, str]] = {}
    if target.get("source_text"):
        for field in ("outcome", "operational_definition", "outcome_definition_status",
                      "outcome_construction", "cutoff_reporting_basis", "classification_structure"):
            mapping[field] = (target["source_text"], "data/TARGET_DEFINITION_AUDIT.tsv")
    if metrics.get("selection_evidence"):
        for field in ("best_criterion", "best_value", "selection_evidence", "best_model_full"):
            mapping[field] = (metrics["selection_evidence"], "data/PROMPT3_CLASSIFICATION_METRICS.tsv")
    if metrics.get("evaluation_evidence"):
        mapping["evaluation"] = (metrics["evaluation_evidence"], "data/PROMPT3_CLASSIFICATION_METRICS.tsv")
    if importance.get("input_variables_source_text"):
        mapping["input_variables"] = (importance["input_variables_source_text"], "data/VARIABLE_IMPORTANCE_DETAILS.tsv")
    if importance.get("selection_rule_source_text"):
        for field in ("importance_selection_status", "importance_selection_strategies"):
            mapping[field] = (importance["selection_rule_source_text"], "data/VARIABLE_IMPORTANCE_DETAILS.tsv")
    if importance.get("importance_result"):
        for field in ("importance_result_full", "important_variable_domains"):
            mapping[field] = (importance["importance_result"], "data/VARIABLE_IMPORTANCE_DETAILS.tsv")
    if align.get("outcome_evidence"):
        mapping["outcome_R_C_overall"] = (align["outcome_evidence"], "data/PROMPT3_TARGET_PREDICTOR_AUDIT.tsv")
    if align.get("predictor_evidence"):
        mapping["predictor_R_C_overall"] = (align["predictor_evidence"], "data/PROMPT3_TARGET_PREDICTOR_AUDIT.tsv")
    return {field: [source_span(text, path, "curated_audit_excerpt")] for field, (text, path) in mapping.items()}


GROUPS = {
    "identity_and_scope": ["topic", "type", "classifier_process_eligible", "original_task_label", "knhanes_role", "other_datasets"],
    "outcome": ["outcome", "operational_definition", "outcome_definition_status", "outcome_construction", "cutoff_reporting_basis", "classification_structure", "outcome_evidence_excerpt"],
    "sample_and_data": ["survey_years", "final_n", "sample_filtering", "input_variables", "missing_data", "preprocessing", "survey_weights"],
    "modelling": ["variable_selection", "models", "best_model_full", "protocol_best_model", "hyperparameter_tuning", "validation_protocol"],
    "performance": ["reported_metrics_full", "performance_reporting_depth", "best_criterion", "best_value", "evaluation", "selection_evidence", "imbalance_strategy", "application_order", "test_distribution", "threshold"],
    "interpretation_and_inference": ["interpretability_full", "variable_importance", "downstream_analysis", "importance_input_n", "importance_methods_full", "important_variable_domains", "importance_selection_status", "importance_selection_strategies", "importance_result_full", "importance_guided_inference", "importance_selected_n", "importance_inferential_n"],
    "reporting_and_results": ["findings", "limitations", "code_data_availability"],
    "quality_audit": ["outcome_R_C_overall", "predictor_R_C_overall"],
    "supplement_and_visual_audit": ["supplement_status", "supplement_archived_files", "supplement_figure_count", "supplement_table_count", "supplement_document_count", "supplement_content_summary", "supplement_paths", "supplement_file_manifest", "figures_screened", "performance_figure_candidates", "figure_evidence_grades", "figure_candidate_locations", "figure_detected_metrics", "figure_audit_disposition", "figure_candidate_ledger", "all_visual_objects_total", "all_visual_main_figures", "all_visual_main_tables", "all_visual_supplement_figures", "all_visual_supplement_tables", "chatgpt_vision_required", "chatgpt_vision_completed", "chatgpt_vision_uncertain", "chatgpt_vision_unreadable", "complete_visual_audit_status", "complete_visual_object_ledger"],
    "case_analysis": ["case_task_family", "case_outcome_definition", "case_population_years", "case_positive_prevalence", "case_evaluation", "case_metric", "case_reported_value"],
}


def visual_item(row: dict[str, str]) -> dict[str, Any]:
    try:
        values = json.loads(row.get("chatgpt_key_values") or "[]")
    except Exception:
        values = [row.get("chatgpt_key_values", "")] if row.get("chatgpt_key_values") else []
    return {
        "object_id": row.get("object_id", ""), "type": row.get("object_type", ""),
        "label": row.get("object_label", ""), "number": row.get("object_number", ""),
        "scope": row.get("source_scope", ""), "source_path": row.get("source_path", ""),
        "page_or_sheet": row.get("page_or_sheet", ""), "caption": row.get("caption", ""),
        "native_text": row.get("native_text", ""), "structured_table_path": row.get("structured_table_path", ""),
        "image_path": row.get("image_path", ""), "content_domains": row.get("content_domains", ""),
        "interpretation": row.get("chatgpt_interpretation") or row.get("native_interpretation", ""),
        "visible_text": row.get("chatgpt_visible_text", ""), "key_values": values,
        "vision_status": row.get("chatgpt_vision_status", ""), "vision_review_stage": row.get("chatgpt_review_stage", ""),
        "uncertainty": row.get("chatgpt_uncertainty", ""), "manual_review_reason": row.get("manual_review_reason", ""),
    }


def build_records(flat_rows: list[dict[str, str]] | None = None) -> list[Path]:
    if flat_rows is None:
        flat_rows = read_tsv(DATA / "INTEGRATED_STUDY_AUDIT.tsv")
    refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json", encoding="utf-8"))}
    extraction = {}
    for p in (DATA / "extraction").glob("*.json"):
        try:
            d = json.load(open(p, encoding="utf-8")); extraction[d["key"]] = d
        except Exception:
            pass
    visuals: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_tsv(DATA / "ALL_REPORT_VISUAL_OBJECTS.tsv"):
        visuals[row["study_key"]].append(row)
    sources = {
        "target": index_tsv("TARGET_DEFINITION_AUDIT.tsv"),
        "metrics": index_tsv("PROMPT3_CLASSIFICATION_METRICS.tsv"),
        "importance": index_tsv("VARIABLE_IMPORTANCE_DETAILS.tsv"),
        "alignment": index_tsv("PROMPT3_TARGET_PREDICTOR_AUDIT.tsv"),
    }
    survey_path = DATA / "survey_design_appraisal/study_level_appraisal.tsv"
    survey_appraisals = ({r["study_id"]: r for r in read_tsv(survey_path)}
                         if survey_path.exists() else {})
    OUT.mkdir(parents=True, exist_ok=True)
    schema = json.load(open(DATA / "STANDARDIZED_STUDY.schema.json", encoding="utf-8"))
    expected = {r["key"] for r in flat_rows}
    for old in OUT.glob("*.json"):
        if old.stem not in expected and old.name != "schema.json":
            old.unlink()
    written = []
    schema_errors = []
    evidence_counts = Counter()
    evidence_queue = []
    for flat in flat_rows:
        key = flat["key"]; ref = refs.get(key, {}); legacy = extraction.get(key, {})
        md_path = ROOT / "references/md" / f"{key}.md"
        pdf_path = ROOT / "references/pdf" / f"{key}.pdf"
        markdown = md_path.read_text(encoding="utf-8", errors="ignore") if md_path.exists() else ""
        body = full_text(markdown) if markdown else ""
        sentences = page_sentences(markdown) if markdown else []
        explicit = explicit_evidence(key, sources)
        field_evidence = {}
        grouped = {}
        grouped_fields = {x for vals in GROUPS.values() for x in vals}
        for group, fields in GROUPS.items():
            grouped[group] = {}
            for field in fields:
                value = flat.get(field, "Not applicable")
                status = status_for(value)
                evidence = explicit.get(field, [])
                if not evidence and status == "reported_or_derived":
                    evidence = candidate_span(value, sentences, f"references/md/{key}.md")
                if not evidence and (field.startswith("all_visual_") or field.startswith("chatgpt_vision_") or field in {"complete_visual_audit_status", "figures_screened", "performance_figure_candidates"}):
                    evidence = [source_span(f"study_key={key}; {field}={value}", "data/ALL_REPORT_VISUAL_OBJECTS.tsv", "derived_dataset", verification="deterministic_join")]
                evidence_state = ("verified_or_curated" if evidence and all("requires_review" not in x["verification_status"] for x in evidence)
                                  else "candidate_needs_review" if evidence else "source_span_not_yet_recorded")
                evidence_counts[evidence_state] += 1
                item = {"value": value, "status": status, "evidence_status": evidence_state, "evidence": evidence}
                grouped[group][field] = item
                field_evidence[field] = item
                if status == "reported_or_derived" and evidence_state != "verified_or_curated":
                    first = evidence[0] if evidence else {}
                    evidence_queue.append({
                        "study_id": key, "analysis_group": group, "field": field,
                        "value": clean(value), "status": status, "evidence_status": evidence_state,
                        "source_path": first.get("source_path", f"references/md/{key}.md"),
                        "page": first.get("page", ""), "start_sentence": first.get("start_sentence", ""),
                        "end_sentence": first.get("end_sentence", ""),
                        "verification_status": first.get("verification_status", "source span required"),
                    })
        # Any future Appendix-15 field is preserved even before GROUPS is updated.
        for field, value in flat.items():
            if field not in grouped_fields and field not in {"record_no", "key", "year", "title", "doi", "journal"}:
                field_evidence[field] = {"value": value, "status": status_for(value),
                                         "evidence_status": "source_span_not_yet_recorded", "evidence": []}
        objects = [visual_item(x) for x in visuals.get(key, [])]
        counts = Counter((x["scope"], x["type"]) for x in objects)
        sources_list = []
        for kind, path in (("main_pdf", pdf_path), ("extracted_markdown", md_path), ("legacy_extraction", DATA / "extraction" / f"{key}.json")):
            if path.exists():
                sources_list.append({"type": kind, "path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size})
        pdf_pages = 0
        if pdf_path.exists():
            with fitz.open(pdf_path) as pdf_doc:
                pdf_pages = len(pdf_doc)
        appendix_fields = dict(flat)
        survey = survey_appraisals.get(key, {})
        if survey:
            appendix_fields.update({
                "survey_analytic_role": survey["analytic_role"],
                "survey_estimand": survey["estimand"],
                "survey_population_claim": survey["population_claim"],
                "survey_applicability": survey["applicability"],
                "survey_methodological_adherence": survey["methodological_adherence"],
                "survey_design_reporting": (
                    f"weights reported/training/evaluation={survey['weights_reported']}/"
                    f"{survey['weights_used_in_training']}/{survey['weights_used_in_evaluation']}; "
                    f"strata-clusters reported/uncertainty={survey['strata_clusters_reported']}/"
                    f"{survey['strata_clusters_used_in_uncertainty']}; integrated weights "
                    f"reported/used={survey['integrated_weights_reported']}/{survey['integrated_weights_used']}"),
                "survey_appraisal_evidence": survey["evidence_quote"] or
                    "No explicit design-method statement located in retained report text",
            })
        appendix_fields.update({
            "authors": ref.get("authors") or "Not reported",
            "report_availability": "full_report" if pdf_path.exists() else "abstract_only",
            "full_text_character_count": str(len(body)),
            "full_text_word_count": str(len(body.split())),
            "pdf_page_count": str(pdf_pages),
        })
        sections = section_structure(pdf_path, markdown)
        appendix_fields["section_title_count"] = str(len(sections))
        record = {
            "schema_version": SCHEMA_VERSION,
            "study_id": key,
            "metadata": {
                "title": ref.get("title") or flat.get("title", ""), "year": ref.get("year") or flat.get("year", ""),
                "authors": ref.get("author_list") or ([ref.get("authors")] if ref.get("authors") else []),
                "authors_citation": ref.get("authors") or "Not reported", "journal": ref.get("journal") or flat.get("journal") or "Not reported",
                "doi": ref.get("doi") or flat.get("doi") or "Not reported", "pmid": ref.get("pmid") or "Not applicable",
                "pmcid": ref.get("pmcid") or "Not applicable", "keywords": ref.get("keywords") or [],
                "language": "Not systematically coded", "included": True,
            },
            "source_document": {
                "availability": "full_report" if pdf_path.exists() else "abstract_only",
                "files": sources_list,
                "text_statistics": {
                    "character_count_with_spaces": len(body),
                    "character_count_without_spaces": len(re.sub(r"\s", "", body)),
                    "word_count_whitespace_tokenized": len(body.split()),
                    "pdf_pages": pdf_pages,
                    "counting_basis": "references/md full-text segment after whitespace normalization",
                },
                "section_title_structure": sections,
            },
            "analysis": {**grouped, "complex_survey_appraisal": survey},
            "controlled_vocabulary": controlled_terms(flat, legacy, sources["metrics"].get(key, {})),
            "field_evidence_index": field_evidence,
            "visual_objects": {
                "counts": {"total": len(objects), "main_figures": counts[("main", "figure")],
                           "main_tables": counts[("main", "table")], "supplement_figures": counts[("supplement", "figure")],
                           "supplement_tables": counts[("supplement", "table")]},
                "items": objects,
            },
            "appendix15_fields": appendix_fields,
            "legacy_extraction_snapshot": legacy,
            "provenance": {
                "canonical_role": "source record for Integrated study-level audit exports",
                "builder": "tools/build_standardized_study_json.py",
        "generated_date": "2026-09-12",
                "missingness_vocabulary": ["not_reported", "not_applicable", "not_recoverable", "reported_or_derived"],
                "evidence_rule": "Exact/curated spans are distinguished from automated candidates and missing legacy spans; no evidence is fabricated.",
            },
        }
        try:
            jsonschema.validate(record, schema)
        except jsonschema.ValidationError as exc:
            schema_errors.append({"study_id": key, "path": list(exc.absolute_path), "message": exc.message})
        target = OUT / f"{key}.json"
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(target)
    index_path = DATA / "STANDARDIZED_STUDY_JSON_INDEX.jsonl"
    with index_path.open("w", encoding="utf-8") as f:
        for p in written:
            record = json.load(open(p, encoding="utf-8"))
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    queue_path = DATA / "STANDARDIZED_STUDY_EVIDENCE_QUEUE.tsv"
    with queue_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["study_id", "analysis_group", "field", "value", "status", "evidence_status",
                  "source_path", "page", "start_sentence", "end_sentence", "verification_status"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(evidence_queue)
    report = {
        "schema_version": SCHEMA_VERSION, "records": len(written), "expected_records": len(flat_rows),
        "unique_study_ids": len({p.stem for p in written}), "evidence_status_counts": dict(evidence_counts),
        "visual_objects": sum(len(json.load(open(p, encoding="utf-8"))["visual_objects"]["items"]) for p in written),
        "schema_errors": schema_errors,
        "evidence_review_queue": len(evidence_queue),
        "validation": "pass" if len(written) == len(flat_rows) == len({p.stem for p in written}) and not schema_errors else "fail",
    }
    (DATA / "STANDARDIZED_STUDY_JSON_VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return written


if __name__ == "__main__":
    paths = build_records()
    print(json.dumps({"records": len(paths), "directory": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
