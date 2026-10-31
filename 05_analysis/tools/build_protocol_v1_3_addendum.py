#!/usr/bin/env python3
"""Build the v1.3 post-hoc purpose-and-evidence addendum from locked v1.2 evidence.

This builder never labels LLM verification as independent human review and never
copies a population-association purpose directly into an association-output field.
"""
from __future__ import annotations
from review_support import POSITIVE_THRESHOLD_CODES

import glob
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/protocol_v1_2/final"
PURPOSE_PATH = ROOT / "results/derived/study_purpose_audit.json"
EXPANDED_PATH = ROOT / "results/derived/expanded_model_task_audit.json"
OUT_DIR = ROOT / "data/protocol_v1_3"
OUT = OUT_DIR / "purpose_evidence_addendum.json"
# prompt 106: the published 18-topic mapping (topic_crosswalk.tsv canonical_topic) is authoritative for the studies it covers
import csv as _csv
PUBLISHED = json.loads((OUT_DIR / "published_purpose_evidence_v1_3.json").read_text())["records"]  # prompt 106
CROSSWALK_TOPIC = {r["study_id"]: r["canonical_topic"] for r in _csv.DictReader(open(OUT_DIR / "topic_crosswalk.tsv", encoding="utf-8-sig"), delimiter="\t") if r.get("canonical_topic")}
VALIDATION = OUT_DIR / "VALIDATION.json"

PURPOSE_MAP = {
    "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION": "HEALTH_STATE_OR_VALUE_ESTIMATION",
    "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION": "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION",
    "POPULATION_ASSOCIATION_ANALYSIS": "POPULATION_ASSOCIATION",
    "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY": "PATTERN_OR_SUBGROUP_DISCOVERY",
    "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION": "CAUSAL_EFFECT_OR_STRUCTURE",
}
METHOD_DETAILED = {
    # Preserves the three-way source coding documented in the v1.2 builder.
    "KHM042": "NEW_PROBLEM_OR_WORKFLOW_SOLUTION",
    "KHM154": "NEW_PROBLEM_OR_WORKFLOW_SOLUTION",
    "KHM158": "NEW_PROBLEM_OR_WORKFLOW_SOLUTION",
    "KHM018": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM030": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM054": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM057": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM127": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM151": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM157": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM165": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM170": "EXISTING_METHOD_COMPARISON_BENCHMARK",
    "KHM171": "EXISTING_METHOD_COMPARISON_BENCHMARK",
}

TOPIC_RULES = [
    ("MENTAL_HEALTH", ("mental", "depress", "stress", "suicid", "quality of life")),
    ("CARDIOVASCULAR", ("cardiovascular", "hypertension", "blood pressure", "stroke", "angina", "heart")),
    ("METABOLIC_ENDOCRINE", ("metabolic", "diabet", "glucose", "lipid", "obesity", "thyroid")),
    ("MUSCULOSKELETAL", ("musculoskeletal", "bone", "osteoporosis", "arthritis", "back pain", "sarcopen")),
    ("ORAL_HEALTH", ("oral", "dental", "periodont")),
    ("RESPIRATORY", ("respiratory", "copd", "asthma", "lung function")),
    ("KIDNEY_UROLOGIC", ("kidney", "renal", "egfr", "urinary")),
    ("CANCER", ("cancer", "malignan")),
    ("NUTRITION_DIET", ("nutrition", "diet", "food", "nutrient")),
    ("HEALTH_BEHAVIOUR", ("smoking", "tobacco", "alcohol", "physical activity", "sleep")),
    ("OPHTHALMOLOGIC", ("eye", "vision", "ophthalm", "cataract")),
    ("OTORHINOLARYNGOLOGIC", ("otorhino", "hearing", "voice", "tinnitus")),
    ("DERMATOLOGIC_ALLERGIC", ("skin", "dermat", "allerg")),
    ("INFECTIOUS_IMMUNE", ("infect", "hepatitis", "immune")),
    ("REPRODUCTIVE_WOMENS_HEALTH", ("pregnan", "menopaus", "women", "female")),
    ("AGING_GERIATRIC", ("aging", "ageing", "elder", "frailty")),
    ("GENERAL_HEALTH_MULTIMORBIDITY", ("general health", "multimorbid", "chronic disease")),
]


def vals(d, code):
    out = []
    for row in d.get("protocol_items", {}).get(code, []):
        value = row.get("value")
        out.extend(value if isinstance(value, list) else [value])
    return [x for x in out if x is not None]


def first(d, code, default=None):
    return vals(d, code)[0] if vals(d, code) else default


def included(d):
    return d.get("corpus_status", {}).get("include", first(d, "ELG04") == "Y")


def evidence_index(d):
    return {x.get("evidence_id"): x for x in d.get("evidence_registry", []) if x.get("evidence_id")}


def item_evidence(d, *codes):
    ids = []
    for code in codes:
        for row in d.get("protocol_items", {}).get(code, []):
            ids.extend(row.get("evidence_ids", []))
    return list(dict.fromkeys(ids))


def section_evidence(d, patterns):
    out = []
    for ev in d.get("evidence_registry", []):
        section = " ".join(str(ev.get(k) or "") for k in ("section", "subsection")).lower()
        if any(p in section for p in patterns):
            out.append(ev.get("evidence_id"))
    return [x for x in dict.fromkeys(out) if x]


def relevant_evidence(d, patterns, sections=()):
    out = []
    for ev in d.get("evidence_registry", []):
        text = " ".join(str(ev.get(k) or "") for k in ("section", "subsection", "excerpt")).lower()
        section = str(ev.get("section") or "").lower()
        if (not sections or any(x in section for x in sections)) and any(x in text for x in patterns):
            out.append(ev.get("evidence_id"))
    return [x for x in dict.fromkeys(out) if x]


def purpose_patterns(code):
    return {
        "HEALTH_STATE_OR_VALUE_ESTIMATION": ("predict", "classif", "detect", "diagnos", "estim", "model"),
        "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION": ("importance", "contribution", "predictor", "factor", "shap", "interpret"),
        "POPULATION_ASSOCIATION": ("association", "associated", "odds ratio", "regression coefficient", "correlat"),
        "PATTERN_OR_SUBGROUP_DISCOVERY": ("cluster", "pattern", "subgroup", "latent"),
        "CAUSAL_EFFECT_OR_STRUCTURE": ("causal", "effect", "intervention", "structure learning"),
    }.get(code, ("objective",))


def make_purpose_records(d, old):
    if old["study_category"] != "HEALTH_ANALYSIS":
        return []
    components = [PURPOSE_MAP.get(x, x) for x in old["health_analysis_purpose_components"]]
    multi = old["health_analysis_purpose"] == "MULTIPLE_CO_PRIMARY_PURPOSES"
    primary = PURPOSE_MAP.get(old["health_analysis_purpose"])
    records = []
    for code in components:
        priority = "CO_PRIMARY" if multi else ("PRIMARY" if code == primary else "SECONDARY")
        pats = purpose_patterns(code)
        objective = relevant_evidence(d, pats, ("title", "abstract", "background", "introduction", "method"))
        results = relevant_evidence(d, pats, ("result", "table", "figure"))
        conclusion = relevant_evidence(d, pats, ("discussion", "conclusion", "abstract"))
        if not objective:
            objective = item_evidence(d, "TSK02", "TSK03")
        records.append({
            "purpose_code": code, "priority": priority,
            "objective_evidence_ids": objective, "result_evidence_ids": results,
            "conclusion_evidence_ids": conclusion,
            "confidence": old.get("purpose_judgement_confidence", "MODERATE"),
        })
    return records


USE_PATTERNS = {
    "SCREENING": ("screen", "case-finding"),
    "DIAGNOSTIC_SUPPORT": ("diagnos", "decision support"),
    "RISK_GROUP_IDENTIFICATION": ("high-risk", "high risk", "risk group", "risk strat", "at risk"),
    "PERSONALISED_MANAGEMENT": ("personalis", "personaliz", "individual management", "tailored"),
    "POPULATION_SURVEILLANCE_OR_POLICY": ("policy", "surveillance", "public health", "population"),
    "RESEARCH_OR_HYPOTHESIS_GENERATION": ("research", "hypothesis", "factor", "importance", "association"),
}


def proposed_use_records(d, old):
    if old["study_category"] != "HEALTH_ANALYSIS":
        return [], False
    rows = []
    for code in old.get("proposed_use", []):
        if code == "NO_SPECIFIC_USE":
            continue
        ids = relevant_evidence(d, USE_PATTERNS.get(code, (code.lower(),)), ("discussion", "conclusion", "abstract"))
        # Existing source-read objective evidence is retained when discussion wording was not separately indexed.
        if not ids:
            ids = relevant_evidence(d, USE_PATTERNS.get(code, (code.lower(),)))
        text = " ".join(str(evidence_index(d).get(i, {}).get("excerpt") or "").lower() for i in ids)
        if any(x in text for x in ("implemented", "deployed", "in practice")):
            strength = "IMPLEMENTED_USE"
        elif any(x in text for x in ("evaluated", "validated", "tested")):
            strength = "EMPIRICALLY_TESTED_USE"
        elif any(x in text for x in ("should", "recommend", "can be used")):
            strength = "RECOMMENDED_USE"
        else:
            strength = "POSSIBLE_FUTURE_USE"
        rows.append({"use_code": code, "claim_strength": strength, "evidence_ids": ids,
                     "review_complete": True, "support_status": "EVIDENCE_LINKED" if ids else "INSUFFICIENT_EVIDENCE"})
    source_complete = d.get("source_package", {}).get("main_text", {}).get("review_status") == "COMPLETE"
    no_specific = source_complete and not rows
    return rows, no_specific


# Upper-case abbreviations are deliberately case-sensitive: a case-insensitive
# ``OR 45`` pattern misclassifies ordinary prose such as "eGFR <60 or 45".
ASSOC_RE = re.compile(
    r"(?:(?i:odds ratio|risk ratio|hazard ratio)\s*(?:=|:|of)?\s*\d+(?:\.\d+)?|"
    r"(?i:correlation coefficient|regression coefficient|beta)\s*(?:=|:)?\s*-?\d+(?:\.\d+)?|"
    r"\b(?:aOR|OR|RR|HR)\b\s*(?:=|:|,)?\s*\d+(?:\.\d+)?|β\s*(?:=|:)?\s*-?\d+(?:\.\d+)?)"
)
ASSOC_REPORT_RE = re.compile(
    r"aOR|adjusted\s+OR|odds\s+ratio|승산비|correlation\s+coefficient|"
    r"상관\s*\(?r|regression\s+coefficient|회귀계수|β",
    re.I,
)


def legacy(d):
    path = ROOT / "data/extraction" / f"{d.get('canonical_key')}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def source_association_anchors(d):
    """Return conservative line anchors from the acquired searchable main text."""
    files = d.get("source_package", {}).get("main_text", {}).get("files", [])
    rel = next((x.get("path") for x in files if x.get("type") == "extracted_markdown"), None)
    path = ROOT / rel if rel else None
    if not path or not path.exists():
        return []
    out = []
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if ASSOC_RE.search(line) or re.search(r"(?:odds ratio|adjusted odds ratio|correlation coefficient).{0,50}(?:95%|confidence interval|p\s*[<=>])", line, re.I):
            out.append({"source_file": rel, "line": lineno, "excerpt": line.strip()[:1000]})
    return out[:50]


def association_audit(d, old):
    ev = d.get("evidence_registry", [])
    direct = [x.get("evidence_id") for x in ev if ASSOC_RE.search(str(x.get("excerpt") or ""))]
    leg = legacy(d)
    fields = " ".join(str(leg.get(k) or "") for k in ("findings", "variable_selection", "metrics", "ml_usage"))
    legacy_direct = bool(ASSOC_RE.search(fields))
    legacy_reported = bool(ASSOC_REPORT_RE.search(fields))
    source_anchors = source_association_anchors(d)
    any_value = "Y" if direct or legacy_direct or legacy_reported or source_anchors else "N"
    substantive = "Y" if any_value == "Y" and "POPULATION_ASSOCIATION_ANALYSIS" in old.get("health_analysis_purpose_components", []) else "N"
    survey = "Y" if substantive == "Y" and "USED" in vals(d, "SUR04") and "USED" in vals(d, "SUR10") else "N"
    return {
        "any_association_estimate_reported": any_value,
        "association_was_substantive_output": substantive,
        "population_association_was_survey_aware": survey,
        "evidence_ids": [x for x in direct if x],
        "source_text_anchors": source_anchors,
        "legacy_text_match_without_unit_link": (legacy_direct or legacy_reported) and not direct,
        "linkage_status": "DIRECTLY_LINKED" if direct or source_anchors else ("STUDY_LEVEL_ONLY" if legacy_direct or legacy_reported else "NOT_REPORTED"),
    }


def method_record(d, old):
    if old["study_category"] != "METHOD_RESEARCH":
        return None
    sid = d["study_id"]
    detailed = METHOD_DETAILED.get(sid, "NEW_OR_IMPROVED_METHOD")
    fig4 = ("EXISTING_METHODS_COMPARISON_OR_EVALUATION" if detailed == "EXISTING_METHOD_COMPARISON_BENCHMARK"
            else "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT")
    mode_map = {
        "EMPIRICAL_COMPARATOR_EVALUATION": "EMPIRICAL_COMPARATOR",
        "SIMULATION_AND_EMPIRICAL_APPLICATION": "SIMULATION_PLUS_EMPIRICAL",
        "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION": "EXTERNAL_TRANSPORT",
        "APPLICATION_OR_DEMONSTRATION": "APPLICATION_DEMONSTRATION",
        "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED": "INSUFFICIENTLY_DESCRIBED",
    }
    stage_map = {
        "DATA_INTEGRATION_OR_HARMONISATION": "DATA_INTEGRATION",
        "MISSING_DATA": "MISSING_DATA", "FEATURE_ENGINEERING_OR_SELECTION": "FEATURE_CONSTRUCTION_OR_SELECTION",
        "PREDICTION_OR_CLASSIFICATION": "MODEL_DEVELOPMENT", "EXPLAINABLE_AI": "EXPLANATION_OR_INTERPRETATION",
        "VALIDATION_OR_PERFORMANCE_EVALUATION": "VALIDATION_OR_PERFORMANCE",
        "CAUSAL_OR_STRUCTURE_LEARNING": "CAUSAL_OR_STRUCTURE",
        "CLUSTERING_OR_REPRESENTATION": "REPRESENTATION_OR_CLUSTERING",
        "USER_TOOL_OR_WORKFLOW": "USER_TOOL_OR_WORKFLOW",
    }
    return {
        "method_research_type_detailed": detailed,
        "method_research_type_figure4": fig4,
        "target_analysis_stages": list(dict.fromkeys(stage_map.get(x, "OTHER") for x in old["method_intervention_stages"])),
        "evaluation_mode": mode_map.get(old["method_evaluation_mode"], "OTHER"),
        "comparators": vals(d, "MOD04"),
        "evaluation_datasets": [x.get("dataset_id") for x in d.get("units", {}).get("evaluations", []) if x.get("dataset_id")],
        "primary_evaluation_criteria": [x.get("criterion") for x in d.get("best_model_selections", []) if x.get("criterion")] or ["NR"],
        "improvement_evidence": ("EXTERNAL_VALIDATION" if "EXTERNAL" in vals(d, "VAL02") else
                                 "REPEATED_EVALUATION" if any(x in vals(d, "VAL02") for x in ("CV", "BOOT")) else
                                 "SIMPLE_EXAMPLE" if mode_map.get(old["method_evaluation_mode"]) == "APPLICATION_DEMONSTRATION" else
                                 "INSUFFICIENT"),
        "evidence_ids": item_evidence(d, "TSK02", "TSK03", "TSK06", "MOD04", "BEST02", "VAL02"),
    }


def topic_code(raw):
    text = str(raw or "").lower()
    for code, terms in TOPIC_RULES:
        if any(re.search(r"\b" + re.escape(x), text) for x in terms):
            return code
    return "OTHER_OR_CROSS_CUTTING"


def restriction_flags(d):
    pop5 = str(first(d, "POP05", "")).lower()
    pop6 = str(first(d, "POP06", "")).lower()
    pop7 = str(first(d, "POP07", "")).lower()
    return {
        "age_restriction": first(d, "POP03") not in (None, "NR", "UNC") or bool(re.search(r"age[ds]?\s*(?:>=|>|under|over|younger|older)", pop6 + pop7)),
        "sex_restriction": not any(x in pop5 for x in ("none", "both", "men and women", "male and female")) and pop5 not in ("", "nr", "unc"),
        "disease_or_risk_group_restriction": bool(re.search(r"diagnos|disease|patient|risk|copd|diabet|hypertens|cancer", pop6)),
        "measurement_or_data_availability_restriction": bool(re.search(r"missing|complete|available|measur|questionnaire|wear", pop6 + " " + pop7)),
        "other_restriction": first(d, "POP06") not in (None, "NR", "UNC"),
        "evidence_ids": item_evidence(d, "POP03", "POP04", "POP05", "POP06", "POP07"),
    }


def specification(d):
    rep = first(d, "REP17", "NA")
    status = {"R": "COMPLETE", "P": "PARTIAL", "NR": "INSUFFICIENT", "UNC": "UNC", "NA": "NA"}.get(rep, "UNC")
    code = first(d, "MOD15", "NA")
    code_status = {"USED": "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED", "NOT_USED": "NOT_PROVIDED_OR_NOT_REPORTED", "NR": "NOT_PROVIDED_OR_NOT_REPORTED", "NA": "NA", "UNC": "UNC"}.get(code, "UNC")
    return {"completeness": status, "source_rep17": rep, "required_components": [
        "ALGORITHM_OR_STRUCTURE", "INPUT_VARIABLES_AND_ORDER", "PREPROCESSING_OR_ENCODING",
        "FINAL_HYPERPARAMETERS", "COEFFICIENTS_WEIGHTS_OR_SAVED_OBJECT", "CLASSIFICATION_THRESHOLD", "APPLICATION_INSTRUCTIONS"],
        "code_availability_status": code_status,
        "evidence_ids": item_evidence(d, "MOD06", "MOD14", "MOD15", "MOD16", "REP17")}


def claim_records(d, old, purposes, uses, assoc):
    rows = []
    def add(kind, ids, support, model=None, outcome=None, evaluation=None, stat=None):
        rows.append({"claim_id": f"{d['study_id']}-C{len(rows)+1:02d}", "claim_type": kind,
                     "claim_strength": "AUTHOR_STATED", "model_id": model, "outcome_id": outcome,
                     "evaluation_id": evaluation, "statistical_analysis_id": stat,
                     "support_elements": support, "support_status": "STUDY_LEVEL_ONLY",
                     "evidence_ids": list(dict.fromkeys(ids))})
    purpose_ids = [i for p in purposes for i in p["objective_evidence_ids"] + p["result_evidence_ids"] + p["conclusion_evidence_ids"]]
    if any(p["purpose_code"] == "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION" for p in purposes):
        add("VARIABLE_CONTRIBUTION", purpose_ids, ["VARIABLE_IMPORTANCE"] if "USED" in vals(d, "VI01") else [])
    if any(p["purpose_code"] == "POPULATION_ASSOCIATION" for p in purposes):
        add("POPULATION_ASSOCIATION", purpose_ids + assoc["evidence_ids"],
            [x for x, ok in (("ASSOCIATION_ESTIMATE", assoc["any_association_estimate_reported"] == "Y"),
                             ("SURVEY_WEIGHT_AND_DESIGN_VARIANCE", assoc["population_association_was_survey_aware"] == "Y")) if ok])
    use_codes = {x["use_code"] for x in uses}
    if use_codes & {"SCREENING", "DIAGNOSTIC_SUPPORT", "RISK_GROUP_IDENTIFICATION", "PERSONALISED_MANAGEMENT"}:
        add("INDIVIDUAL_APPLICATION", [i for u in uses for i in u["evidence_ids"]],
            [x for x, ok in (("INDEPENDENT_OR_TEMPORAL_VALIDATION", any(v in vals(d, "VAL02") for v in ("EXTERNAL", "TEMPORAL"))),
                             ("CALIBRATION", any("R" in vals(d, k) for k in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R"))),
                             ("DECISION_THRESHOLD", any(x in POSITIVE_THRESHOLD_CODES for x in vals(d, "THR01")))) if ok])
    if "POPULATION_SURVEILLANCE_OR_POLICY" in use_codes:
        add("POPULATION_SURVEILLANCE_OR_POLICY", [i for u in uses for i in u["evidence_ids"]],
            ["SURVEY_DESIGN"] if "USED" in vals(d, "SUR04") and any("USED" in vals(d, x) for x in ("SUR08", "SUR09", "SUR10")) else [])
    return rows


def main():
    purpose = json.loads(PURPOSE_PATH.read_text())
    old_by_id = {x["study_id"]: x for x in purpose["records"]}
    expanded = json.loads(EXPANDED_PATH.read_text())
    stability_by_id = {x["study_id"]: x.get("importance_stability_methods", []) for x in expanded["studies"]}
    records = []
    for path in sorted(glob.glob(str(FINAL / "KHM*_final.json"))):
        d = json.loads(Path(path).read_text())
        if not included(d):
            continue
        old = old_by_id[d["study_id"]]
        health = old["study_category"] == "HEALTH_ANALYSIS"
        purposes = make_purpose_records(d, old)
        uses, no_specific = proposed_use_records(d, old)
        assoc = association_audit(d, old)
        outputs = [x for x in old.get("analytic_outputs", []) if x not in ("POPULATION_ASSOCIATION_ESTIMATE", "NOT_APPLICABLE")]
        outputs = [{"output_code": x.replace("REDUCED_PREDICTOR_SET", "REDUCED_VARIABLE_SET").replace("IMPLEMENTED_TOOL", "INTERFACE_OR_TOOL").replace("OTHER_OR_UNCLEAR_OUTPUT", "OTHER"),  # prompt 106: purpose-audit fallback published as OTHER
                    "evidence_ids": item_evidence(d, "TSK02", "TSK03", "VI01", "VI10", "MOD17", "MOD18")}
                   for x in outputs]
        if assoc["any_association_estimate_reported"] == "Y":
            outputs.append({"output_code": "ASSOCIATION_ESTIMATE", "evidence_ids": assoc["evidence_ids"]})
        if not outputs and health:
            outputs = [{"output_code": "OTHER", "evidence_ids": item_evidence(d, "TSK02", "TSK03")}]
        position = old["knhanes_position"].replace("EXTERNAL_OR_TRANSPORTABILITY_EVALUATION", "EXTERNAL_OR_TRANSPORT_EVALUATION_DATASET")
        relation_map = {"SEPARATE_COMPARISON_OR_PARALLEL_USE": "INDEPENDENT_PARALLEL_ANALYSIS",
                        "DEVELOPMENT_EVALUATION_DIVISION": "DEVELOPMENT_EVALUATION_DATA_SPLIT",
                        "PARTICIPANT_LEVEL_LINKAGE_OR_DATA_INTEGRATION": "PARTICIPANT_LEVEL_LINKAGE",
                        "SEPARATE_EXTERNAL_OR_TRANSPORT_EVALUATION": "EXTERNAL_VALIDATION",
                        "OTHER_OR_UNCLEAR_MULTI_DATA_USE": "UNCLEAR"}
        relation = relation_map.get(old["multi_dataset_use_mode"], old["multi_dataset_use_mode"])
        orientation_ids = item_evidence(d, "TSK02", "TSK03", "TSK06")
        orientation_basis = {
            "title_evidence_ids": relevant_evidence(d, ("title",), ("title",)),
            "objective_evidence_ids": orientation_ids,
            "main_evaluation_evidence_ids": section_evidence(d, ("method", "evaluation")),
            "main_result_evidence_ids": section_evidence(d, ("result",)),
            "conclusion_evidence_ids": section_evidence(d, ("discussion", "conclusion")),
        }
        record = {
            "study_id": d["study_id"], "canonical_key": d.get("canonical_key"),
            "title": d.get("metadata", {}).get("title"), "publication_year": d.get("metadata", {}).get("publication_year"),
            "orientation_components": ["HEALTH_SCIENTIFIC"] if health else ["METHODOLOGICAL"],
            "primary_orientation": "HEALTH_FOCUSED" if health else "METHOD_FOCUSED",
            "orientation_basis": orientation_basis,
            "orientation_confidence": old.get("purpose_judgement_confidence", "MODERATE"),
            "purpose_records": purposes,
            "proposed_use_records": uses,
            "no_specific_use": no_specific,
            "individual_application": bool({x["use_code"] for x in uses} & {"SCREENING", "DIAGNOSTIC_SUPPORT", "RISK_GROUP_IDENTIFICATION", "PERSONALISED_MANAGEMENT"}),
            "analytic_output_records": outputs,
            "association_audit": assoc,
            "tool_stages": {"example_interface_only": "USED" in vals(d, "MOD17"),
                            "executable_tool_provided": "USED" in vals(d, "MOD15") and "USED" in vals(d, "MOD17"),
                            "access_verified": False, "prospective_deployment_evaluated": "USED" in vals(d, "MOD18")},
            "method_research": method_record(d, old),
            "knhanes_position": position,
            "multi_dataset_relation": [relation],
            "participant_level_external_linkage": relation == "PARTICIPANT_LEVEL_LINKAGE",
            "claim_evidence_records": [],
            "variable_importance_stability": {"methods": stability_by_id.get(d["study_id"], []),
                                               "evidence_ids": item_evidence(d, "VI16")},
            "final_model_specification": specification(d),
            "health_topic": {"primary_topic_18": (json.loads((OUT_DIR / "topic_adjudications.json").read_text()).get("overrides", {}).get(d["study_id"], {}).get("primary_topic_18") if (OUT_DIR / "topic_adjudications.json").exists() else None) or CROSSWALK_TOPIC.get(d["study_id"]) or topic_code(first(d, "TSK04")),  # prompt 106: published crosswalk before the keyword rule
                             "secondary_topics_18": [], "raw_broad_topic": first(d, "TSK04"),
                             "raw_detailed_topic": first(d, "TSK05"),
                             "topic_role": old["health_topic_role"], "evidence_ids": item_evidence(d, "TSK04", "TSK05")},
            "population_restrictions": restriction_flags(d),
            "review_provenance": {"review_type": "POST_HOC_EVIDENCE_ASSISTED_RECODING_FROM_COMPLETE_SOURCE_READ_REGISTRY",
                                  "llm_verification_complete": True, "coordinator_consensus_complete": True,
                                  "independent_human_review_complete": False, "human_review_scope": "NONE"},
        }
        record["claim_evidence_records"] = claim_records(d, old, purposes, uses, assoc)
        # Retain explicitly reviewed repairs when rebuilding this historical layer.
        from complete_protocol_evidence import apply_repairs, DECISIONS
        if DECISIONS.exists():
            record = apply_repairs(d, record, json.loads(DECISIONS.read_text()))
        if d["study_id"] in PUBLISHED:  # prompt 106: already-published studies keep their published record verbatim
            record = PUBLISHED[d["study_id"]]
        records.append(record)
        # Keep the canonical study JSON -> derived supplement chain explicit.
        # The locked v1.2 protocol items are unchanged; this is a separately
        # labelled post-hoc adjudication namespace.
        d.setdefault("adjudication", {})["purpose_evidence_v1_3"] = record
        Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

    summary = {
        "denominator": len(records),
        "primary_orientation": dict(Counter(x["primary_orientation"] for x in records)),
        "orientation_components": dict(Counter(v for x in records for v in x["orientation_components"])),
        "task_denominators": {"D_CLS": sum(first(json.loads(Path(p).read_text()), "TSK01") == "CLS" for p in glob.glob(str(FINAL / "KHM*_final.json")) if included(json.loads(Path(p).read_text()))),
                              "D_HEALTH_CLS": sum(x["primary_orientation"] == "HEALTH_FOCUSED" and first(json.loads((FINAL / f"{x['study_id']}_final.json").read_text()), "TSK01") == "CLS" for x in records)},
        "association_audit": {k: dict(Counter(x["association_audit"][k] for x in records)) for k in
                              ("any_association_estimate_reported", "association_was_substantive_output", "population_association_was_survey_aware")},
        "health_focused_association_audit": {k: dict(Counter(x["association_audit"][k] for x in records if x["primary_orientation"] == "HEALTH_FOCUSED")) for k in
                                             ("any_association_estimate_reported", "association_was_substantive_output", "population_association_was_survey_aware")},
        "method_research_detailed": dict(Counter(x["method_research"]["method_research_type_detailed"] for x in records if x["method_research"])),
        "method_research_figure4": dict(Counter(x["method_research"]["method_research_type_figure4"] for x in records if x["method_research"])),
        "knhanes_position": dict(Counter(x["knhanes_position"] for x in records)),
        "independent_human_review_complete": False,
    }
    checks = {
        "n_250": len(records) == json.loads((ROOT/"results/derived/final_selection_flow.json").read_text())["flow"]["unique_full_report_studies_included"],  # key name kept; prompt 106 (250) + review-loop inclusions 2026-10-24
        "orientation_214_36": summary["primary_orientation"] == {"HEALTH_FOCUSED": 214, "METHOD_FOCUSED": 36},  # prompt 106: was 184/36
        "denominators_222_192": summary["task_denominators"] == {"D_CLS": 222, "D_HEALTH_CLS": 192},  # prompt 106: was 196/165
        "method_n_36": sum(summary["method_research_detailed"].values()) == 36,
        "method_figure4_26_10": summary["method_research_figure4"] == {"METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT": 26, "EXISTING_METHODS_COMPARISON_OR_EVALUATION": 10},
        "all_orientation_evidence": all(any(x["orientation_basis"].values()) for x in records),
        "no_specific_use_rule": all(not x["no_specific_use"] or not x["proposed_use_records"] for x in records),
        "human_review_not_fabricated": not summary["independent_human_review_complete"],
    }
    status = "PASS_WITH_HUMAN_REVIEW_PENDING" if all(checks.values()) else "FAIL"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "protocol_v1.3_posthoc_purpose_evidence_addendum",
                               "analysis_status": "POST_HOC_DESCRIPTIVE_EXTENSION",
                               "summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n")
    VALIDATION.write_text(json.dumps({"status": status, "checks": checks,
                                      "human_review_note": "Independent human review has not been performed and is not represented as complete."}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": status, "summary": summary, "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
