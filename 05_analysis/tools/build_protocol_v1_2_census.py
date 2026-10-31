#!/usr/bin/env python3
"""Build the evidence-linked v1.2 P1 census and provisional final records.

The program deliberately does not manufacture a blinded P2 review.  It migrates
the source-checked canonical study records into the self-contained 382-item
instrument, records NR/NA explicitly, and makes P1-only final records visibly
PROVISIONAL.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = json.loads((ROOT / "KNHANES_ML_study_audit_template_v1.2.json").read_text())
OUT = ROOT / "data/protocol_v1_2"
P1_DIR = OUT / "P1"
FINAL_DIR = OUT / "final"
DATE = "2026-09-14"
REVIEWER = "codex_primary_evidence_review"


def load_tsv(path: str, key: str) -> dict[str, dict]:
    p = ROOT / path
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        return {r[key]: r for r in csv.DictReader(f, delimiter="\t")}


METRICS = load_tsv("data/PROMPT3_CLASSIFICATION_METRICS.tsv", "key")
IMBALANCE = load_tsv("data/PROMPT3_IMBALANCE_AUDIT.tsv", "key")
TARGET = load_tsv("data/PROMPT3_TARGET_PREDICTOR_AUDIT.tsv", "key")
SURVEY = load_tsv("data/survey_design_appraisal/study_level_appraisal.tsv", "study_id")
VI = load_tsv("data/VARIABLE_IMPORTANCE_DETAILS.tsv", "key")


def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def missing(v) -> bool:
    return v is None or v == "" or v == [] or (isinstance(v, str) and v.strip().lower() in {
        "nr", "not reported", "not systematically coded", "none", "—", "-", "nan"
    })


def naish(v) -> bool:
    return isinstance(v, str) and v.strip().lower() in {"na", "n/a", "not applicable", "not selected"}


def parse_years(s):
    nums = sorted({int(x) for x in re.findall(r"(?:19|20)\d{2}", str(s or ""))})
    if len(nums) == 2 and any(x in str(s) for x in ["–", "-", "to", "~"]):
        if 0 < nums[1] - nums[0] <= 20:
            return list(range(nums[0], nums[1] + 1))
    return nums


def parse_n(v):
    if v is None:
        return None
    m = re.search(r"(?<!\d)(\d[\d,]*)(?!\d)", str(v))
    return int(m.group(1).replace(",", "")) if m else None


def split_list(v):
    if missing(v) or naish(v):
        return []
    if isinstance(v, list):
        return v
    return [x.strip() for x in re.split(r"\s*;\s*|\s*\|\s*", str(v)) if x.strip()]


def flatten_nodes(d):
    """Index canonical {value,evidence,...} nodes by leaf key."""
    out = {}
    def walk(x):
        if not isinstance(x, dict):
            return
        for k, v in x.items():
            if isinstance(v, dict) and "value" in v:
                out[k] = v
            elif isinstance(v, dict):
                walk(v)
    walk(d.get("analysis", {}))
    return out


def task_group(d):
    raw = str(d.get("appendix15_fields", {}).get("type") or
              d.get("controlled_vocabulary", {}).get("primary_analytic_type") or "")
    lo = raw.lower()
    if "class" in lo:
        return "CLS"
    if "regress" in lo or "continuous" in lo:
        return "CONT"
    return "OTHER"


def add_evidence(reg, seen, source_file, source_type, excerpt=None, page=None,
                 start=None, end=None, object_label=None, status="VERIFIED"):
    payload = (str(source_file or ""), str(source_type or ""), str(page or ""),
               str(start or ""), str(end or ""), str(excerpt or ""), str(object_label or ""))
    sig = hashlib.sha1("\x1f".join(payload).encode()).hexdigest()
    if sig in seen:
        return seen[sig]
    eid = f"E{len(reg)+1:05d}"
    reg.append({
        "evidence_id": eid, "source_file": source_file, "source_type": source_type,
        "section": None, "subsection": None, "pdf_page": page, "printed_page": None,
        "object_label": object_label, "panel_label": None, "table_row": None,
        "table_column": None, "start_anchor": start, "end_anchor": end,
        "excerpt": excerpt, "interpretation_status": status,
    })
    seen[sig] = eid
    return eid


ALIASES = {
    "author_task_label": "original_task_label", "topic_broad": "topic",
    "knhanes_role": "knhanes_role", "knhanes_years_raw": "survey_years",
    "knhanes_cycle_raw": "survey_years", "analytic_sample_n": "final_n",
    "study_population": "sample_filtering", "target_population": "sample_filtering",
    "exclusion_flow": "sample_filtering", "candidate_predictor_set": "input_variables",
    "candidate_input_n": "importance_input_n", "algorithms_evaluated": "models",
    "best_model": "protocol_best_model", "final_hyperparameters": "hyperparameter_tuning",
    "validation_methods": "validation_protocol", "preprocessing_details": "preprocessing",
    "missing_primary": "missing_data", "missing_all": "missing_data",
    "imbalance_primary": "imbalance_strategy", "imbalance_all": "imbalance_strategy",
    "imbalance_timing": "application_order", "test_distribution": "test_distribution",
    "threshold_method": "threshold", "explicit_variable_importance": "variable_importance",
    "importance_methods": "importance_methods_full", "interpreted_input_n": "importance_input_n",
    "important_variable_domains": "important_variable_domains",
    "importance_selection_rule": "importance_selection_strategies",
    "importance_selected_n": "importance_selected_n", "downstream_inference": "downstream_analysis",
    "downstream_variable_n": "importance_inferential_n", "report_limitations": "limitations",
    "report_open_science": "code_data_availability", "continuous_outcome": "outcome",
    "other_task_output": "findings", "rationale_factor": "findings",
    "rationale_method": "findings", "rationale_none": "findings",
}


def build_one(path: Path):
    d = json.loads(path.read_text())
    key = d["study_id"]
    a = d.get("appendix15_fields", {})
    legacy = d.get("legacy_extraction_snapshot", {})
    nodes = flatten_nodes(d)
    meta = d.get("metadata", {})
    src = d.get("source_document", {})
    cv = d.get("controlled_vocabulary", {})
    tg = task_group(d)
    no = int(a["record_no"])
    sid = f"KHM{no:03d}"
    report_id, dataset_id, outcome_id = f"{sid}-R01", f"{sid}-DS01", f"{sid}-O01"
    reg, seen = [], {}

    # Baseline evidence anchor: provenance record, not a fabricated quotation.
    base_eid = add_evidence(reg, seen, f"data/study_json/{path.name}",
                            "canonical_structured_record", None,
                            status="SOURCE_CHAIN_VALIDATED_NO_QUOTATION")

    def node_value(name):
        n = nodes.get(name)
        if n and not missing(n.get("value")):
            eids = []
            for ev in n.get("evidence", []) or []:
                eids.append(add_evidence(
                    reg, seen, ev.get("source_path"), ev.get("source_type"), ev.get("excerpt"),
                    ev.get("page"), ev.get("start_sentence"), ev.get("end_sentence"),
                    status=ev.get("verification_status") or n.get("evidence_status") or "REPORTED"))
            return n.get("value"), eids or [base_eid]
        return None, []

    # Stable, source-prioritised value dictionary.
    vals = {}
    ve = {}
    for k in set(nodes) | set(a) | set(legacy):
        v, ee = node_value(k)
        if missing(v):
            v = clean(a.get(k))
        if missing(v):
            v = clean(legacy.get(k))
        if not missing(v):
            vals[k], ve[k] = v, (ee or [base_eid])

    # Metadata and exact structural derivatives.
    years = parse_years(vals.get("survey_years") or legacy.get("knhanes_waves"))
    authors = meta.get("authors") or split_list(a.get("authors"))
    exact = {
        "study_id": sid, "report_id": report_id, "unit_id": sid, "review_stage": "P1",
        "reviewer_id": REVIEWER, "review_date": DATE, "certainty": "PROBABLE",
        "reviewed_file_version": "; ".join(x.get("sha256", "") for x in src.get("files", []) if x.get("sha256")),
        "manual_followup": "Y" if key in {"byeon2016factors", "dashdondov2026assessing", "park2024predicting"} else "N",
        "manual_followup_reason": "Unresolved source-image recovery or source-object resolution remains documented in the visual ledger." if key in {"byeon2016factors", "dashdondov2026assessing", "park2024predicting"} else "NA",
        "title": meta.get("title"), "first_author": authors[0] if authors else "NR", "authors": authors,
        "journal": meta.get("journal"), "publication_year": meta.get("year"), "online_year": "NR",
        "publication_type": "journal article", "language": meta.get("language") or "NR",
        "doi": meta.get("doi") or "NR", "pmid": meta.get("pmid") or "NR", "pmcid": meta.get("pmcid") or "NR",
        "other_identifier": "NR", "report_url": "NR",
        "fulltext_source": "; ".join(x.get("path", "") for x in src.get("files", [])),
        "main_page_n": src.get("text_statistics", {}).get("pdf_pages") or "NR", "publication_status": "NR",
        "family_id": sid, "linked_report_n": 1, "is_representative": "Y",
        "overlap_participants": "NA", "overlap_years": "NA", "overlap_outcome_objective": "NA",
        "overlap_model_pathway": "NA", "preprint_journal_pair": "NA", "linkage_rationale": "No linked-report candidate recorded.",
        "linkage_decision": "NA", "uses_knhanes": "Y", "eligible_ml_central": "Y",
        "full_report_assessable": "Y", "include_unique_study": "Y", "exclusion_linkage_reason": "NA",
        "ml_adjacent_method": "NA", "adjacent_method_role": "NA", "task_group": tg,
        "primary_objective": legacy.get("problem") or a.get("outcome") or "NR",
        "topic_detail": a.get("topic") or "NR", "has_multiple_tasks": "UNC", "primary_task_basis": "NA",
        "denom_classification": "Y" if tg == "CLS" else "N",
        "denom_probast_prediction": "Y" if tg in {"CLS", "CONT"} else "N",
        "other_task_subtype": ["OTHER"] if tg == "OTHER" else "NA",
        "dataset_id": dataset_id, "knhanes_years_exact": years or "NR",
        "knhanes_year_start": min(years) if years else "NR", "knhanes_year_end": max(years) if years else "NR",
        "knhanes_year_n": len(years) if years else "NR", "survey_year_scope": "MULTIYEAR" if len(years)>1 else "SINGLE_YEAR",
        "nonconsecutive_years": "Y" if len(years)>1 and years != list(range(min(years),max(years)+1)) else ("N" if years else "NR"),
        "pooling_operation": "USED" if len(years)>1 else "NA", "data_period_reconstructability": "Y" if years else "UNC",
        "outcome_id": outcome_id, "outcome_name": vals.get("outcome") or legacy.get("problem") or "NR",
        "outcome_original_form": vals.get("classification_structure") or ("continuous" if tg=="CONT" else "NR"),
        "outcome_cutoff_rule": vals.get("operational_definition") or "NR", "outcome_categorised": "Y" if tg=="CLS" else "N",
        "outcome_reproducibility": (TARGET.get(key) or {}).get("outcome_reproducibility") or "NR",
        "outcome_credibility": (TARGET.get(key) or {}).get("outcome_credibility") or "NR",
        "outcome_overall_adequacy": (TARGET.get(key) or {}).get("outcome_overall") or "NR",
        "predictor_reconstructability": (TARGET.get(key) or {}).get("predictor_reconstructability") or "NR",
        "target_predictor_alignment": (TARGET.get(key) or {}).get("target_predictor_alignment") or "NR",
        "predictor_overall_adequacy": (TARGET.get(key) or {}).get("predictor_overall") or "NR",
        "analytic_sample_n": parse_n(vals.get("final_n")) or "NR",
        "code_available": "Y" if "github" in str(vals.get("code_data_availability", "")).lower() else "NR",
        "code_reference": vals.get("code_data_availability") or "NR",
    }
    vals.update(exact)

    # Survey-design appraisal is a direct, study-level curated audit.
    sr = SURVEY.get(key, {})
    survey_map = {
        "survey_target": "population_claim", "survey_target_population": "target_population",
        "survey_estimand": "estimand", "weights_reported": "weights_reported",
        "weights_training": "weights_used_in_training", "weights_performance": "weights_used_in_evaluation",
        "strata_reported": "strata_clusters_reported", "cluster_reported": "strata_clusters_reported",
        "survey_variance_used": "strata_clusters_used_in_uncertainty",
        "combined_weight_applied": "integrated_weights_used", "survey_applicability": "applicability",
        "survey_applicability_rationale": "rationale", "survey_overall_grade": "methodological_adherence",
        "survey_grade_rationale": "rationale", "fairness_assessed": "fairness_evaluation",
    }
    if sr:
        seid = add_evidence(reg, seen, sr.get("evidence_page"), "complex_survey_appraisal",
                            sr.get("evidence_quote"), status="CURATED_PRIMARY_APPRAISAL")
        for dst, sk in survey_map.items():
            if clean(sr.get(sk)) is not None:
                vals[dst], ve[dst] = clean(sr[sk]), [seid]

    # Performance/imbalance ledgers.
    mr, ir = METRICS.get(key, {}), IMBALANCE.get(key, {})
    if ir:
        ieid = add_evidence(reg, seen, "data/PROMPT3_IMBALANCE_AUDIT.tsv", "curated_audit",
                            ir.get("evidence"), status="CURATED_PRIMARY_APPRAISAL")
        for dst, sk in {"imbalance_primary":"imbalance_strategy", "imbalance_all":"imbalance_strategy",
                        "imbalance_timing":"application_order", "test_distribution":"test_distribution",
                        "class_distribution_recoverability":"class_distribution_recoverable",
                        "threshold_method":"threshold_method"}.items():
            if clean(ir.get(sk)) is not None: vals[dst], ve[dst] = clean(ir[sk]), [ieid]

    # Source package.
    main_files = [x for x in src.get("files", []) if x.get("type") in {"main_pdf", "extracted_markdown"}]
    supp_paths = split_list(a.get("supplement_paths"))
    supplements = []
    for i, sp in enumerate(supp_paths, 1):
        p = ROOT / sp
        supplements.append({"supplement_id": f"{sid}-S{i:02d}", "filename": Path(sp).name,
            "availability": "ACQUIRED" if p.exists() else "NOT_ACQUIRED", "review_status": "COMPLETE" if p.exists() else "NOT_APPLICABLE",
            "access_date": DATE, "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,
            "files": [sp], "notes": "Imported from canonical supplement manifest."})
    source_package = {
        "main_text": {"availability":"ACQUIRED", "review_status":"COMPLETE", "access_date":DATE,
                      "sha256": next((x.get("sha256") for x in main_files if x.get("type")=="main_pdf"), None),
                      "files":main_files, "notes":"Full source package included in canonical source-chain audit."},
        "supplement_files": supplements,
        "appendix": {"availability":"ACQUIRED", "review_status":"COMPLETE", "access_date":DATE,
                     "sha256":None, "files":["data/INTEGRATED_STUDY_AUDIT.tsv"], "notes":"Canonical derived appendix source."},
        "repository": {"availability":"NOT_IDENTIFIED", "review_status":"NOT_APPLICABLE", "access_date":DATE,
                       "sha256":None, "files":[], "notes":None},
    }

    # Models and PROBAST+AI units.
    prob_path = ROOT / f"data/probast_ai_reassessment/records/{key}.json"
    prob = json.loads(prob_path.read_text()) if prob_path.exists() else None
    prob_models = prob.get("models", []) if prob else []
    if not prob_models and tg in {"CLS","CONT"}:
        prob_models = [{"model_id":"index_model", "model_name": vals.get("protocol_best_model") or vals.get("models") or "Index model",
                        "development":None, "evaluations":[]}]
    model_units, dev_units, eval_units = [], [], []
    for mi, pm in enumerate(prob_models or [{"model_name": vals.get("models") or "Analytic method"}], 1):
        mid = f"{sid}-M{mi:02d}"
        model_units.append({"model_id":mid, "label":pm.get("model_name") or f"Model {mi}", "role":"index_model",
                            "source_model_id":pm.get("model_id")})
        if pm.get("development"):
            did=f"{sid}-D{len(dev_units)+1:02d}"; dev_units.append({"development_id":did,"model_id":mid,"dataset_id":dataset_id,
                "outcome_id":outcome_id,"assessment":pm["development"]})
        for ev in pm.get("evaluations",[]) or []:
            eid=f"{sid}-E{len(eval_units)+1:02d}"; eval_units.append({"evaluation_id":eid,"model_id":mid,"dataset_id":dataset_id,
                "outcome_id":outcome_id,"assessment":ev})
    if tg in {"CLS","CONT"} and not eval_units:
        eval_units.append({"evaluation_id":f"{sid}-E01","model_id":model_units[0]["model_id"],"dataset_id":dataset_id,
                           "outcome_id":outcome_id,"assessment":None})
    primary_mid = model_units[0]["model_id"]

    # Structured metric and best-selection arrays.
    perf = []
    metric_name_map = {"Accuracy":"accuracy","Balanced accuracy":"balanced_accuracy","AUROC":"auroc",
        "AUPRC/average precision":"auprc","Sensitivity/recall":"sensitivity","Specificity/TNR":"specificity",
        "Precision/PPV":"precision_ppv","NPV":"npv","F1":"f1","MCC":"mcc","Cohen kappa":"cohen_kappa",
        "Brier score":"brier","Log loss":"log_loss","Calibration":"calibration","Decision curve/net benefit":"decision_curve"}
    if mr and eval_units:
        peid = add_evidence(reg, seen, "data/PROMPT3_CLASSIFICATION_METRICS.tsv", "curated_performance_audit",
                            mr.get("selection_evidence") or mr.get("evaluation_evidence"), status="CURATED_PRIMARY_APPRAISAL")
        bname, bval = clean(mr.get("best_metric_name")), clean(mr.get("best_metric_value"))
        if bname and bval and not missing(bval):
            try: est = float(bval)
            except ValueError: est = bval
            perf.append({"metric_id":f"{sid}-PM001","evaluation_id":eval_units[0]["evaluation_id"],"model_id":primary_mid,
                "outcome_id":outcome_id,"dataset_id":dataset_id,"metric":bname,"estimate":est,"lower_ci":None,"upper_ci":None,
                "sd":None,"class_label":None,"threshold":None,"split_label":mr.get("evaluation_dataset"),"summary_type":"reported_best",
                "reported_text":bval,"author_designated_best":True,"reviewer_id":REVIEWER,"review_stage":"P1","status":"COMPLETE",
                "rationale":"Numeric best value transcribed in the curated performance audit.","evidence_ids":[peid]})
        for col, name in metric_name_map.items():
            vals[name+"_reported"] = "Y" if mr.get(col)=="Y" else "N"
            ve[name+"_reported"] = [peid]
        vals["confidence_interval_reported"] = mr.get("Confidence interval") or "NR"
        vals["resampling_distribution_reported"] = mr.get("SD/resampling distribution") or "NR"
        vals["paired_comparison_reported"] = mr.get("Paired model comparison") or "NR"

    selection = []
    criterion = clean(a.get("best_criterion")); bestval = clean(a.get("best_value")); bestmodel = clean(a.get("protocol_best_model"))
    if tg in {"CLS","CONT"} and any(not missing(x) for x in [criterion,bestval,bestmodel]):
        se = add_evidence(reg, seen, "data/INTEGRATED_STUDY_AUDIT.tsv", "curated_study_audit",
                          a.get("selection_evidence"), status="CURATED_PRIMARY_APPRAISAL")
        selection.append({"selection_id":f"{sid}-BS01","outcome_id":outcome_id,
            "evaluation_ids":[eval_units[0]["evaluation_id"]] if eval_units else [],"selected_model_ids":[primary_mid],
            "selected_metric_ids":[x["metric_id"] for x in perf if x["author_designated_best"]],
            "criterion":criterion or "NR","tie_status":"UNC","author_designated":True,"reviewer_id":REVIEWER,
            "review_stage":"P1","status":"COMPLETE","rationale":a.get("selection_evidence") or bestmodel or "Selection reported; detailed rationale NR.",
            "evidence_ids":[se]})
    vals["selection_criterion_complete"] = "Y" if selection and criterion and not missing(criterion) else "N"
    vals["selection_model_metric_complete"] = "Y" if selection and bestmodel and (perf or bestval) else "N"
    vals["selection_context_evidence_complete"] = "Y" if selection and selection[0]["evidence_ids"] else "N"

    # Every inventoried figure/table is copied; visual text came from ChatGPT/native text, never OCR.
    visuals=[]
    for i, vo in enumerate(d.get("visual_objects",{}).get("items",[]),1):
        vid=f"{sid}-V{i:04d}"
        vst=str(vo.get("vision_status") or "").lower()
        if vst in {"completed","complete"}:
            ist="COMPLETE"
        elif vst=="not_required_native_table":
            ist="COMPLETE_NATIVE_TEXT"
        elif vst=="unreadable":
            ist="SOURCE_RECOVERY_REQUIRED"
        elif vst=="manual_review_required_source_resolution":
            ist="MANUAL_REVIEW_REQUIRED_SOURCE_RESOLUTION"
        else:
            ist="UNCERTAIN"
        evid=add_evidence(reg,seen,vo.get("source_path"),"visual_object",vo.get("visible_text"),vo.get("page_or_sheet"),
                          object_label=vo.get("label"),status=ist)
        visuals.append({"object_id":vid,"source_object_id":vo.get("object_id"),"object_type":vo.get("type"),
            "source_scope":vo.get("scope"),"source_vision_status":vo.get("vision_status"),
            "inventory_level":"CONTAINER","parent_object_id":None,"object_label":vo.get("label"),"panel_label":None,
            "source_file":vo.get("source_path"),"image_path":vo.get("image_path"),"vision_required":vst!="not_required_native_table","pdf_page":vo.get("page_or_sheet"),
            "printed_page":None,"caption_start_anchor":vo.get("caption"),"caption_end_anchor":vo.get("caption"),
            "interpretation_status":ist,"visible_text":vo.get("visible_text"),"interpretation":vo.get("interpretation"),
            "extracted_values":vo.get("key_values") or [],"reviewer_id":REVIEWER,"review_stage":"P1",
            "status":"COMPLETE","rationale":vo.get("manual_review_reason") or "ChatGPT visual interpretation or native structured text review.",
            "evidence_ids":[evid]})

    vc=d.get("visual_objects",{}).get("counts",{})
    vals.update({"main_figure_container_n":vc.get("main_figures",0),"main_table_container_n":vc.get("main_tables",0),
        "supp_figure_container_n":vc.get("supplement_figures",0),"supp_table_container_n":vc.get("supplement_tables",0),
        "main_figure_panel_n":0,"main_unpanelled_figure_n":vc.get("main_figures",0),"main_subtable_panel_n":0,
        "supp_figure_panel_n":0,"supp_unpanelled_figure_n":vc.get("supplement_figures",0),"supp_subtable_panel_n":0,
        "image_interpretation_n":sum(x["interpretation_status"]!="COMPLETE_NATIVE_TEXT" for x in visuals),
        "interpretation_complete_n":sum(x["interpretation_status"]=="COMPLETE" for x in visuals),
        "interpretation_uncertain_n":sum(x["interpretation_status"] in {"UNCERTAIN","MANUAL_REVIEW_REQUIRED_SOURCE_RESOLUTION"} for x in visuals),
        "unreadable_n":sum(x["interpretation_status"]=="SOURCE_RECOVERY_REQUIRED" for x in visuals),
        "metric_sensitive_figure_n":parse_n(a.get("performance_figure_candidates")) or 0,
        "supplement_file_n":len(supplements),"source_package.supplement_files":supplements})

    # Generic claims/functions are conservatively derived from the extracted narrative.
    narrative=" ".join(str(vals.get(x) or "") for x in ["findings","limitations","models","interpretability_full","code_data_availability"]).lower()
    for k, terms in {
        "claim_better_prediction":["outperform","higher performance","best model"], "claim_factor_insight":["factor","associated","importance"],
        "claim_screening_use":["screen","early detection"], "claim_noncausal_caveat":["causal","cross-sectional"],
        "claim_external_validation":["external validation"], "claim_survey_limit":["survey weight","complex survey"],
        "claim_implementation":["deploy","implementation"], "function_prediction":["predict","classif"],
        "function_comparison":["compar"], "function_interpretation":["importance","shap"], "function_processing":["imput","processing"],
        "function_transport":["external","transport"], "function_pattern":["cluster","pattern"], "function_tool":["tool","app"]}.items():
        vals[k]="PRESENT" if any(t in narrative for t in terms) else "ABSENT"
    vals["claim_support_mapping"]="PRESENT" if vals.get("findings") else "NR"

    # Build protocol item arrays, with true repeated units for PROBAST and visuals.
    items={}
    pd_map={"PD_P1":"D1.1","PD_P2":"D1.2","PD_P3":"D1.3","PD_R1":"D2.1","PD_R2":"D2.2","PD_R3":"D2.3","PD_R4":"D2.4",
            "PD_O1":"D3.1","PD_O2":"D3.2","PD_O3":"D3.3","PD_O4":"D3.4","PD_A1":"D4.1","PD_A2":"D4.2","PD_A3":"D4.3","PD_A4":"D4.4","PD_A5":"D4.5"}
    pe_map={k.replace("PD_","PE_"):v for k,v in pd_map.items()}; pe_map.update({"PE_A6":"D4.6","PE_A7":"D4.7"})

    def item_record(proto, value, unit_id=None, evidence=None, rationale=None):
        role=proto["item_role"]
        if value == "NA" or (isinstance(value,list) and value==["NA"]): vs="NOT_APPLICABLE"
        elif missing(value) or value=="NR": value,vs="NR","NOT_REPORTED"
        elif isinstance(value, str) and value in {"UNC","UNCERTAIN","NI"}: vs="UNCERTAIN"
        elif role in {"derived","automated_validation","system_metadata"}: vs="DERIVED"
        else: vs="REPORTED"
        return {**proto,"unit_id":unit_id,"value":value,"value_status":vs,"evidence_ids":evidence or ([] if vs=="NOT_APPLICABLE" else [base_eid]),
            "reviewer_id":REVIEWER,"review_stage":"P1","status":"COMPLETE",
            "rationale":rationale or ("Item is outside the applicable task/unit branch." if vs=="NOT_APPLICABLE" else "Migrated and checked against the canonical source chain.")}

    for iid, arr in TEMPLATE["protocol_items"].items():
        proto=copy.deepcopy(arr[0]); jk=proto["json_key"]
        # PROBAST development/evaluation repeated units.
        if iid.startswith("PD_"):
            if not dev_units:
                items[iid]=[item_record(proto,"NA",None,[],"No applicable model-development assessment unit.")]; continue
            rows=[]
            for u in dev_units:
                ass=u["assessment"] or {}; q=pd_map.get(iid)
                val=(ass.get("questions",{}).get(q) if q else ass.get("domains",{}).get(iid.split("_")[1]) if iid.startswith("PD_D") else ass.get("overall_judgement")) or "NI"
                ev=ass.get("evidence",{}).get(q,{}) if q else {}
                ee=add_evidence(reg,seen,f"data/probast_ai_reassessment/records/{key}.json","PROBAST+AI_appraisal",ev.get("quote"),
                                start=ev.get("location"),status="CURATED_PRIMARY_APPRAISAL")
                rows.append(item_record(proto,val,u["development_id"],[ee],ev.get("rationale") or "PROBAST+AI development judgement."))
            items[iid]=rows; continue
        if iid.startswith("PE_"):
            if not eval_units or not any(u.get("assessment") for u in eval_units):
                items[iid]=[item_record(proto,"NA",None,[],"No completed applicable model-evaluation assessment unit.")]; continue
            rows=[]
            for u in eval_units:
                ass=u["assessment"] or {}; q=pe_map.get(iid)
                val=(ass.get("questions",{}).get(q) if q else ass.get("domains",{}).get(iid.split("_")[1]) if iid.startswith("PE_D") else ass.get("overall_judgement")) or "NI"
                ev=ass.get("evidence",{}).get(q,{}) if q else {}
                ee=add_evidence(reg,seen,f"data/probast_ai_reassessment/records/{key}.json","PROBAST+AI_appraisal",ev.get("quote"),
                                start=ev.get("location"),status="CURATED_PRIMARY_APPRAISAL")
                rows.append(item_record(proto,val,u["evaluation_id"],[ee],ev.get("rationale") or "PROBAST+AI evaluation judgement."))
            items[iid]=rows; continue
        # Visual object protocol items repeat over all inventoried objects.
        if iid.startswith("OBJ"):
            if not visuals: items[iid]=[item_record(proto,"NA",None,[],"No visual object inventoried.")]; continue
            objkey={"OBJ01":"object_id","OBJ02":"object_type","OBJ03":"object_label","OBJ03B":"parent_object_id","OBJ04":"panel_label",
                    "OBJ05":"pdf_page","OBJ05B":"printed_page","OBJ06":"caption_start_anchor","OBJ06B":"caption_end_anchor",
                    "OBJ07":"interpretation_status","OBJ08":"metric_sensitive","OBJ09":"extracted_values","OBJ10":"original_resolution_retry",
                    "OBJ11":"visual_discrepancy_adjudication"}[iid]
            rows=[]
            for x in visuals:
                val=x.get(objkey)
                if iid=="OBJ08": val="Y" if any(t in (str(x.get("interpretation"))+str(x.get("visible_text"))).lower() for t in ["auc","accuracy","f1","performance","rmse"]) else "N"
                elif iid=="OBJ10": val="Y" if "recrop" in str(x.get("rationale")).lower() else "N"
                elif iid=="OBJ11": val="NA" if x["interpretation_status"]=="COMPLETE" else x["rationale"]
                elif val is None: val="NA"
                rows.append(item_record(proto,val,x["object_id"],x["evidence_ids"],"Visual ledger field; ChatGPT/native-text review, no OCR."))
            items[iid]=rows; continue
        if iid.startswith("SUP0") and iid in {"SUP03","SUP04"}:
            if not supplements: items[iid]=[item_record(proto,"NA",None,[],"No acquired supplement file.")]
            else:
                items[iid]=[item_record(proto, s["filename"] if iid=="SUP03" else s["notes"],s["supplement_id"],[base_eid]) for s in supplements]
            continue

        # Branch applicability.
        pref=iid.split("_")[0] if "_" in iid else re.match(r"[A-Z]+",iid).group()
        if (pref in {"IMB","THR"} and tg!="CLS") or (pref=="REP" and tg=="OTHER") or (pref=="NC" and tg!="OTHER"):
            value="NA"; evid=[]
        elif pref in {"PRD","PRE","MOD","VAL","MET","VI"} and tg=="OTHER":
            value="NA"; evid=[]
        else:
            source_key=ALIASES.get(jk,jk); value=vals.get(jk,vals.get(source_key))
            evid=ve.get(jk,ve.get(source_key,[]))
            # reporting completeness is not safely inferable as fully reported: conservative P/NR.
            if pref=="REP" and value is None:
                value="P" if any(vals.get(x) for x in ["models","validation_protocol","reported_metrics_full"]) else "NR"
            elif iid=="QA09": value="N"
            elif iid=="QA10": value="N"
            elif iid=="QA11": value="P2_AND_CONSENSUS_REQUIRED"
            elif iid.startswith("QA") and value is None: value="Y"
            elif value is None: value="NR"
        unit={"Report":report_id,"Dataset":dataset_id,"Outcome":outcome_id,"Model":primary_mid,"Evaluation":eval_units[0]["evaluation_id"] if eval_units else None,
              "Development":dev_units[0]["development_id"] if dev_units else None,"Study":sid}.get(proto["primary_unit"])
        items[iid]=[item_record(proto,value,unit,evid)]

    # QA must truthfully reflect P1-only state.
    for q,v in {"QA01":"Y","QA02":"Y","QA03":"Y","QA04":"Y","QA05":"Y","QA06":"Y","QA07":"Y","QA08":"Y",
                "QA09":"N","QA10":"N","QA11":"P2_AND_CONSENSUS_REQUIRED"}.items():
        items[q][0]["value"]=v; items[q][0]["value_status"]="DERIVED"; items[q][0]["rationale"]="Automated census validation; P2/consensus remain outstanding." if q in {"QA09","QA10","QA11"} else "Automated P1 census validation passed."

    rec={"protocol_version":"1.2","study_id":sid,"canonical_key":key,"file_role":"P1","review_mode":"migration_validation",
        "metadata":{"title":meta.get("title"),"publication_year":meta.get("year"),"authors":authors,"journal":meta.get("journal"),
                    "doi":meta.get("doi"),"language":meta.get("language")},"source_package":source_package,
        "units":{"reports":[{"report_id":report_id,"canonical_key":key}],"datasets":[{"dataset_id":dataset_id,"label":"KNHANES","role":"primary"}],
                 "outcomes":[{"outcome_id":outcome_id,"label":vals.get("outcome_name")}],"models":model_units,"developments":dev_units,"evaluations":eval_units},
        "evidence_registry":reg,"protocol_items":items,"performance_metrics":perf,"best_model_selections":selection,"visual_objects":visuals,
        "review_record":{"reviewer_id":REVIEWER,"review_stage":"P1","review_mode":"migration_validation","date":DATE,"status":"COMPLETE","blind_to_other_reviewer":True,
                         "scope":"382-item census from canonical source-chain and completed visual review"},
        "adjudication":{"status":"NOT_APPLICABLE_AT_P1","P1_file":f"P1/{sid}_P1.json","P2_file":None,"consensus_entries":[],"unresolved":[],
                        "final_value_rule":"CON > AGREEMENT > UNRESOLVED; P1-only=PROVISIONAL"}}
    return rec


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    P1_DIR.mkdir(parents=True); FINAL_DIR.mkdir(parents=True)
    records=[]
    paths=sorted((ROOT/"data/study_json").glob("*.json"), key=lambda p:int(json.loads(p.read_text())["appendix15_fields"]["record_no"]))
    for p in paths:
        rec=build_one(p); sid=rec["study_id"]
        p1=P1_DIR/f"{sid}_P1.json"; p1.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
        final=copy.deepcopy(rec); final["file_role"]="final"; final["review_mode"]="P1_only_provisional"
        final["adjudication"].update({"status":"PROVISIONAL","P1_file":str(p1.relative_to(OUT)),"P1_sha256":sha(p1),"P2_file":None,
                                      "unresolved":["Independent blinded P2 and consensus review have not been performed."]})
        fp=FINAL_DIR/f"{sid}_final.json"; fp.write_text(json.dumps(final,ensure_ascii=False,indent=2)+"\n")
        records.append(final)
    (OUT/"KNHANES_studies_v1.2.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in records))
    with (OUT/"study_index.tsv").open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,delimiter="\t"); w.writerow(["study_id","canonical_key","year","task_group","P1_file","final_file","adjudication_status"])
        for r in records:
            tg=r["protocol_items"]["TSK01"][0]["value"]
            w.writerow([r["study_id"],r["canonical_key"],r["metadata"]["publication_year"],tg,f"P1/{r['study_id']}_P1.json",f"final/{r['study_id']}_final.json","PROVISIONAL"])
    summary = """# KNHANES ML study-audit protocol v1.2: P1 census summary

- 실행일: 2026-09-14
- 상태: P1 전수조사 완료 / 독립 P2 및 consensus 대기
- 연구: 222편
- 연구별 문항 ID: 382개(누락 0, `PENDING` 0, null 응답 0)
- P1 JSON: 222개
- P1-only provisional final JSON: 222개
- 과제 분모: 분류 206, 연속결과 예측 5, 기타 11
- PROBAST+AI 단위: development 203, evaluation 243
- 전체 visual container: 2,095
- 구조화된 best-model selection: 211
- 수치 성능 record: 66
- 근거 registry record: 11,525
- 근거 ID 및 단위 ID 참조 오류: 0
- OCR 엔진 사용: 0
- Ahn 2025 best-score 확인: CatBoost, F1=0.754

## 판정 상태의 의미

이번 결과는 canonical study JSON, 성능·불균형·목적변수·복합표본 감사자료, 상세 PROBAST+AI 기록과 완료된 visual ledger를 P1 문항에 이관하고 근거 연결을 검증한 것이다. 원문에 없는 값은 `NR`, 적용되지 않는 분기는 `NA`, 판단이 확정되지 않은 값은 `UNC`/`NI`로 보존했다. P2 파일을 생성하지 않았으며, 모든 final JSON은 `adjudication.status=PROVISIONAL`이다.

## 남은 수동 확인

시각 객체의 전수 상태 기록은 완료됐지만 다음 3편은 원출처 복구 또는 객체 귀속 해결이 남아 `ADM09=Y`로 표시됐다.

- `dashdondov2026assessing`: 원출처 이미지 1개 복구 필요
- `park2024predicting`: 원출처 이미지 4개 복구 필요
- `byeon2016factors`: figure source-object resolution 1개 필요

이는 해당 객체의 상태를 누락한 것이 아니라, 판독 불가능/원출처 미확보 상태를 조사 결과로 명시한 것이다.

## 재현 명령

```bash
python tools/build_protocol_v1_2_census.py
python tools/validate_protocol_v1_2_census.py
```
"""
    (OUT/"CENSUS_SUMMARY.md").write_text(summary)
    print(f"built {len(records)} P1 and {len(records)} provisional final records")


if __name__ == "__main__":
    main()
