#!/usr/bin/env python3
"""Build the post-hoc mutually exclusive study-category and KNHANES-use audit.

This is deliberately separate from the prespecified 382-item protocol.  It
uses the already adjudicated task/data-role fields and the evidence linked to
the author-stated objective.  A paper is not called a benchmark merely
because it compared several algorithms.
"""
from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/protocol_v1_2/final"
OUT = ROOT / "results/derived/study_purpose_audit.json"

# Studies categorised as method research rather than health analysis. IDs were
# reviewed against the title and author-objective evidence in the final packets.
METHOD_DEVELOPMENT = {
    "KHM018", "KHM022", "KHM025", "KHM026", "KHM028", "KHM030",
    "KHM042", "KHM048", "KHM057", "KHM060", "KHM062", "KHM078",
    "KHM097", "KHM112", "KHM116", "KHM119", "KHM120", "KHM129",
    "KHM131", "KHM145", "KHM151", "KHM154", "KHM157", "KHM158",
    "KHM166", "KHM205", "KHM206", "KHM207", "KHM211", "KHM215",
    "KHM222", "KHM223",  # prompt 106: KHM223 CHAID imputation method (criterion-A addition)
}
METHOD_DEVELOPMENT -= {"KHM129"}  # prompt 106: excluded under criterion A (logistic regression only)

# Performance comparison itself is the stated principal contribution.  Health
# prediction papers that merely compare candidate models are not placed here.
ALGORITHM_BENCHMARK = {
    "KHM054", "KHM127", "KHM165", "KHM170", "KHM171",
}

# Mutually exclusive method-research categories, re-read from title, objective,
# and conclusion evidence. A comparison is a benchmark when it evaluates
# existing alternatives without proposing the focal method as a new solution.
NEW_PROBLEM_OR_WORKFLOW_SOLUTION = {"KHM042", "KHM154", "KHM158"}
EXISTING_METHOD_COMPARISON_BENCHMARK = {
    "KHM018", "KHM030", "KHM054", "KHM057", "KHM127", "KHM151",
    "KHM157", "KHM165", "KHM170", "KHM171",
}
METHOD_RESEARCH = METHOD_DEVELOPMENT | ALGORITHM_BENCHMARK
NEW_OR_IMPROVED_METHOD = METHOD_RESEARCH - (
    NEW_PROBLEM_OR_WORKFLOW_SOLUTION | EXISTING_METHOD_COMPARISON_BENCHMARK
)
METHOD_RESEARCH_CATEGORIES = {
    "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT": NEW_OR_IMPROVED_METHOD | NEW_PROBLEM_OR_WORKFLOW_SOLUTION,
    "EXISTING_METHODS_COMPARISON_OR_EVALUATION": EXISTING_METHOD_COMPARISON_BENCHMARK,
    "MIXED_OR_UNCLEAR": set(),
}

# Mutually exclusive primary-purpose status for the 184 health-focused studies.
# There is no priority hierarchy: explicitly co-primary aims remain multiple,
# while genuinely insufficient reporting is kept separate as unclear.
CAUSAL_EFFECT_OR_STRUCTURE = {
    "KHM012", "KHM088", "KHM092", "KHM179",
}
HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY = {"KHM031", "KHM059", "KHM143"}  # prompt 106: KHM156 excluded (criterion A)
MULTIPLE_CO_PRIMARY_HEALTH_PURPOSE = {
    "KHM001", "KHM011", "KHM013", "KHM016", "KHM017", "KHM019", "KHM020",
    "KHM027", "KHM050", "KHM053", "KHM056", "KHM061", "KHM077",  # prompt 106: KHM073 excluded
    "KHM084", "KHM090", "KHM094", "KHM099", "KHM102", "KHM106", "KHM108",
    "KHM109", "KHM110", "KHM115", "KHM121", "KHM122", "KHM123", "KHM125",
    "KHM130", "KHM136", "KHM139", "KHM142", "KHM152", "KHM155", "KHM161",
    "KHM164", "KHM168", "KHM172", "KHM177", "KHM182", "KHM186", "KHM188",
    "KHM190", "KHM196", "KHM199", "KHM200", "KHM201", "KHM202", "KHM210",
    "KHM212", "KHM214", "KHM216", "KHM218",
}
PRIMARY_PURPOSE_UNCLEAR = set()
ASSOCIATED_FACTOR_OR_DETERMINANT = {
    "KHM001", "KHM004", "KHM006", "KHM007", "KHM008", "KHM011",
    "KHM013", "KHM015", "KHM016", "KHM017", "KHM019", "KHM020",
    "KHM027", "KHM031", "KHM034", "KHM036", "KHM038", "KHM040",
    "KHM045", "KHM049", "KHM052", "KHM053", "KHM056", "KHM061",
    "KHM066", "KHM077", "KHM081", "KHM082", "KHM084",  # prompt 106: KHM073 excluded
    "KHM090", "KHM091", "KHM093", "KHM096", "KHM098", "KHM099",
    "KHM100", "KHM101", "KHM102", "KHM106", "KHM108", "KHM109",
    "KHM110", "KHM113", "KHM115", "KHM117", "KHM118", "KHM121",
    "KHM122", "KHM123", "KHM125", "KHM130", "KHM133", "KHM134",
    "KHM136", "KHM139", "KHM141", "KHM142", "KHM147", "KHM152",
    "KHM155", "KHM161", "KHM164", "KHM168", "KHM169", "KHM172",
    "KHM175", "KHM177", "KHM180", "KHM182", "KHM185", "KHM186",
    "KHM190", "KHM192", "KHM196", "KHM199", "KHM200", "KHM201",
    "KHM202", "KHM204", "KHM210", "KHM212", "KHM214", "KHM216",
    "KHM218", "KHM220",
}

# A population-association purpose requires an author-stated association,
# relationship, or population-correlate question supported by conventional
# association/complex-survey analysis.  Merely calling an ML input a "risk
# factor" or displaying feature importance is coded as variable relevance.
# These evidence-reviewed IDs split the former combined primary-purpose class.
POPULATION_ASSOCIATION_PRIMARY = {
    "KHM006", "KHM008", "KHM036", "KHM038", "KHM045", "KHM081", "KHM082",
    "KHM093", "KHM101", "KHM113", "KHM147", "KHM169", "KHM204", "KHM220",
}
POPULATION_ASSOCIATION_COMPONENT = POPULATION_ASSOCIATION_PRIMARY | {
    "KHM001", "KHM011", "KHM027", "KHM053", "KHM136", "KHM202", "KHM210",
}

assert set().union(*METHOD_RESEARCH_CATEGORIES.values()) == METHOD_RESEARCH
_pin(sum(map(len, METHOD_RESEARCH_CATEGORIES.values())), 36, "build_study_purpose_audit.py:106")  # prompt 106 pin
assert not (CAUSAL_EFFECT_OR_STRUCTURE & ASSOCIATED_FACTOR_OR_DETERMINANT)
assert not (MULTIPLE_CO_PRIMARY_HEALTH_PURPOSE & METHOD_RESEARCH)


def values(d, code):
    return [x.get("value") for x in d.get("protocol_items", {}).get(code, [])]


def first(d, code, default=None):
    vals = values(d, code)
    return vals[0] if vals else default


def included(d):
    return d.get("corpus_status", {}).get("include", first(d, "ELG04") == "Y")


def evidence_for(d, codes=("TSK02", "TSK06")):
    registry = {e.get("evidence_id"): e for e in d.get("evidence_registry", [])}
    ids = []
    for code in codes:
        for item in d.get("protocol_items", {}).get(code, []):
            ids.extend(item.get("evidence_ids", []))
    out = []
    for evidence_id in dict.fromkeys(ids):
        e = registry.get(evidence_id)
        if not e:
            continue
        out.append({k: e.get(k) for k in (
            "evidence_id", "source_file", "section", "pdf_page",
            "start_anchor", "end_anchor", "excerpt",
        )})
    return out


def legacy_record(d):
    p = ROOT / "data/extraction" / f"{d.get('canonical_key')}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def study_category(study_id):
    return "METHOD_RESEARCH" if study_id in METHOD_RESEARCH else "HEALTH_ANALYSIS"


def method_research_category(study_id):
    for subtype, study_ids in METHOD_RESEARCH_CATEGORIES.items():
        if study_id in study_ids:
            return subtype
    return "NOT_APPLICABLE"


def health_analysis_purpose(study_id, category):
    if category != "HEALTH_ANALYSIS":
        return "NOT_APPLICABLE"
    if study_id in CAUSAL_EFFECT_OR_STRUCTURE:
        return "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION"
    if study_id in HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY:
        return "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY"
    if study_id in MULTIPLE_CO_PRIMARY_HEALTH_PURPOSE:
        return "MULTIPLE_CO_PRIMARY_PURPOSES"
    if study_id in PRIMARY_PURPOSE_UNCLEAR:
        return "PRIMARY_PURPOSE_UNCLEAR"
    if study_id in ASSOCIATED_FACTOR_OR_DETERMINANT:
        return ("POPULATION_ASSOCIATION_ANALYSIS" if study_id in POPULATION_ASSOCIATION_PRIMARY
                else "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION")
    return "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION"


def health_purpose_components(d, study_id, category, primary_purpose):
    """Nonexclusive author-stated scientific-purpose components.

    Components are separate from technical task and analytic output.  They
    make the content of the 53 co-primary records auditable without forcing a
    hierarchy, and retain secondary author-stated aims in single-primary
    studies where present.
    """
    if category != "HEALTH_ANALYSIS":
        return ["NOT_APPLICABLE"]
    text = objective_text(d)
    components = []
    if primary_purpose == "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION" or (
        first(d, "TSK01") in {"CLS", "CONT"} and any(x in text for x in
        ("predict", "classif", "detect", "screen", "diagnos", "estim", "nomogram", "model develop"))
    ):
        components.append("HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION")
    if primary_purpose == "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION" or (
        study_id in ASSOCIATED_FACTOR_OR_DETERMINANT and any(x in text for x in
        ("factor", "predictor", "importance", "contribution", "determinant", "influenc", "interpret"))
    ) or (study_id in MULTIPLE_CO_PRIMARY_HEALTH_PURPOSE and has_value(d, "VI01", "USED")):
        components.append("VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION")
    if primary_purpose == "POPULATION_ASSOCIATION_ANALYSIS" or study_id in POPULATION_ASSOCIATION_COMPONENT:
        components.append("POPULATION_ASSOCIATION_ANALYSIS")
    if primary_purpose == "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY" or study_id in HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY:
        components.append("HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY")
    if primary_purpose == "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION" or study_id in CAUSAL_EFFECT_OR_STRUCTURE:
        components.append("CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION")
    # Every co-primary record must expose its combination.  Rare records whose
    # objective used generic "factor" language but lacked VI01 still receive
    # the variable-relevance component after evidence review.
    if study_id in MULTIPLE_CO_PRIMARY_HEALTH_PURPOSE and len(components) < 2:
        components.append("VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION")
    return list(dict.fromkeys(components))


def has_value(d, code, value):
    return value in values(d, code)


def objective_text(d):
    return " ".join(str(x) for x in (
        d.get("metadata", {}).get("title") or "", first(d, "TSK03", ""),
        first(d, "TSK02", ""),
    )).lower()


def proposed_uses(d, purpose, purpose_components=()):
    text = objective_text(d)
    out = []
    if any(x in text for x in ("screen", "case-finding", "case finding", "prioriti")):
        out.append("SCREENING")
    if any(x in text for x in ("diagnos", "clinical decision", "decision support", "cdss")):
        out.append("DIAGNOSTIC_SUPPORT")
    if any(x in text for x in ("personal", "individual management", "management", "intervention")):
        out.append("PERSONALISED_MANAGEMENT")
    if any(x in text for x in ("high-risk", "high risk", "risk group", "risk strat", "vulnerable", "at risk")):
        out.append("RISK_GROUP_IDENTIFICATION")
    if any(x in text for x in ("policy", "population", "surveillance", "public health", "national")):
        out.append("POPULATION_SURVEILLANCE_OR_POLICY")
    if set(purpose_components) & {"VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION", "POPULATION_ASSOCIATION_ANALYSIS", "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION"} or any(
        x in text for x in ("factor", "association", "correlate", "determinant", "contribution", "importance")
    ):
        out.append("RESEARCH_OR_HYPOTHESIS_GENERATION")
    return list(dict.fromkeys(out)) or ["NO_SPECIFIC_USE"]


def analytic_outputs(d, purpose, purpose_components=()):
    text = objective_text(d)
    out = []
    if first(d, "TSK01") in {"CLS", "CONT"} and d.get("performance_metrics"):
        out.append("MODEL_PERFORMANCE")
    if has_value(d, "VI01", "USED") or any(x in text for x in ("importance", "contribution", "influenc", "predictor", "risk factor")):
        out.append("VARIABLE_CONTRIBUTION_OR_RANK")
    if has_value(d, "VI10", "USED") or any(x in text for x in ("reduced predictor", "feature selection", "parsimonious")):
        out.append("REDUCED_PREDICTOR_SET")
    if purpose == "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY" or any(x in text for x in ("cluster", "topic model", "pattern discovery")):
        out.append("CLUSTER_OR_PATTERN")
    # This is deliberately narrower than any reported regression coefficient:
    # it denotes a purpose-linked population-association estimate.  The former
    # count of 74 was a legacy keyword/variable-relevance heuristic and was not
    # retained as an independently evidenced output field.
    if "POPULATION_ASSOCIATION_ANALYSIS" in purpose_components and any(
        x in text for x in ("association", "associated", "factor", "correlate", "determinant", "regression")
    ):
        out.append("POPULATION_ASSOCIATION_ESTIMATE")
    if purpose == "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION" or "causal" in text or "intervention effect" in text:
        out.append("CAUSAL_EFFECT")
    if any(x in text for x in ("calculator", "web-based", "web based", "android app", "interface", "implemented tool")):
        out.append("IMPLEMENTED_TOOL")
    return list(dict.fromkeys(out)) or ["OTHER_OR_UNCLEAR_OUTPUT"]


def method_intervention_stages(d):
    text = objective_text(d)
    stages = []
    rules = [
        ("DATA_INTEGRATION_OR_HARMONISATION", ("integrat", "harmoni", "linkage", "multiple datasets")),
        ("MISSING_DATA", ("missing", "imput")),
        ("FEATURE_ENGINEERING_OR_SELECTION", ("feature selection", "feature extraction", "pca", "outlier", "encoding")),
        ("PREDICTION_OR_CLASSIFICATION", ("predict", "classif", "risk assessment")),
        ("CLUSTERING_OR_REPRESENTATION", ("cluster", "represent", "autoencoder", "latent")),
        ("EXPLAINABLE_AI", ("explain", "interpret", "lime", "shap", "attention")),
        ("CAUSAL_OR_STRUCTURE_LEARNING", ("causal", "bayesian network", "structure")),
        ("VALIDATION_OR_PERFORMANCE_EVALUATION", ("validat", "performance", "compar", "accuracy", "benchmark")),
        ("USER_TOOL_OR_WORKFLOW", ("workflow", "framework", "tool", "system", "recommend", "decision support")),
    ]
    for label, terms in rules:
        if any(term in text for term in terms):
            stages.append(label)
    return stages or ["OTHER_OR_UNCLEAR_STAGE"]


def method_evaluation_mode(d):
    # Use the objective plus its linked source excerpts.  The earlier objective-
    # only keyword screen left seven clearly described designs in an undifferentiated
    # other/unclear bin.
    text = " ".join([objective_text(d)] + [
        str(e.get("excerpt") or "").lower()
        for e in evidence_for(d, codes=("TSK02", "TSK03", "TSK06"))
    ])
    study_id = d.get("study_id")
    if study_id == "KHM097":
        return "EMPIRICAL_COMPARATOR_EVALUATION"
    if study_id in {"KHM062", "KHM154"}:
        return "APPLICATION_OR_DEMONSTRATION"
    if study_id == "KHM042":
        return "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"
    if "simulation" in text and ("knhanes" in text or "real" in text):
        return "SIMULATION_AND_EMPIRICAL_APPLICATION"
    if first(d, "TSK06") == "EXTVAL" or "external" in text or "transport" in text:
        return "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"
    if any(x in text for x in ("compar", "benchmark", "outperform", "performance", "evaluat")):
        return "EMPIRICAL_COMPARATOR_EVALUATION"
    if any(x in text for x in ("demonstrat", "application", "case study", "applied")):
        return "APPLICATION_OR_DEMONSTRATION"
    return "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"


def actual_task(d):
    task = first(d, "TSK01")
    if task == "CLS":
        return "CLASSIFICATION"
    if task == "CONT":
        return "CONTINUOUS_OR_ORDERED_ESTIMATION"
    text = " ".join(str(x) for x in (d.get("metadata", {}).get("title"), first(d, "TSK02"))).lower()
    if "imput" in text or "missing response" in text:
        return "MISSING_DATA_IMPUTATION"
    if "cluster" in text:
        return "CLUSTER_DISCOVERY"
    if any(x in text for x in ("causal", "x-learner", "meta-learner", "intervention effect")):
        return "CAUSAL_OR_HETEROGENEOUS_EFFECT_ESTIMATION"
    if any(x in text for x in ("topic model", "dietary pattern", "natural language processing")):
        return "PATTERN_OR_REPRESENTATION_DISCOVERY"
    if "recommend" in text:
        return "RECOMMENDATION_OR_DATA_INTEGRATION"
    return "OTHER_ML_ANALYSIS"


def data_use_mode(role, combined_text, other_datasets):
    if role == "EXTVAL":
        return "SEPARATE_EXTERNAL_OR_TRANSPORT_EVALUATION"
    if not other_datasets and role == "PRIMARY":
        return "KNHANES_ONLY"
    text = combined_text.lower()
    if any(x in text for x in ("participant-level link", "record linkage", "linked to", "integrated data from")):
        return "PARTICIPANT_LEVEL_LINKAGE_OR_DATA_INTEGRATION"
    if any(x in text for x in ("train", "development")) and any(x in text for x in ("validat", "test", "evaluation")):
        return "DEVELOPMENT_EVALUATION_DIVISION"
    if role == "MULTI":
        return "SEPARATE_COMPARISON_OR_PARALLEL_USE"
    return "OTHER_OR_UNCLEAR_MULTI_DATA_USE"


def main():
    records = []
    for path in sorted(glob.glob(str(FINAL / "KHM*_final.json"))):
        d = json.loads(Path(path).read_text())
        if not included(d):
            continue
        study_id = d["study_id"]
        legacy = legacy_record(d)
        category = study_category(study_id)
        method_category = method_research_category(study_id)
        role = first(d, "TSK06", "UNC")
        ev = evidence_for(d, codes=("TSK02", "TSK03", "TSK06"))
        evidence_text = " ".join(e.get("excerpt") or "" for e in ev)
        other = legacy.get("other_datasets")
        health_purpose = health_analysis_purpose(study_id, category)
        purpose_components = health_purpose_components(d, study_id, category, health_purpose)
        if role == "EXTVAL":
            refined_role = "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"
        elif role == "MULTI":
            refined_role = "ONE_OF_MULTIPLE_PRIMARY_DATASETS"
        elif category == "METHOD_RESEARCH":
            refined_role = "APPLICATION_OR_TEST_DATASET"
        elif role == "PRIMARY":
            refined_role = "PRIMARY_ANALYSIS_DATASET"
        else:
            refined_role = "UNCLEAR"
        record = {
            "study_id": study_id,
            "canonical_key": d.get("canonical_key"),
            "title": d.get("metadata", {}).get("title"),
            "publication_year": d.get("metadata", {}).get("publication_year"),
            "study_category": category,
            "method_research_category": method_category,
            "health_analysis_purpose": health_purpose,
            "health_analysis_purpose_components": purpose_components,
            "purpose_component_combination": "+".join(purpose_components) if category == "HEALTH_ANALYSIS" else "NOT_APPLICABLE",
            "proposed_use": proposed_uses(d, health_purpose, purpose_components) if category == "HEALTH_ANALYSIS" else ["NOT_APPLICABLE"],
            "analytic_outputs": analytic_outputs(d, health_purpose, purpose_components) if category == "HEALTH_ANALYSIS" else ["NOT_APPLICABLE"],
            "method_intervention_stages": method_intervention_stages(d) if category == "METHOD_RESEARCH" else ["NOT_APPLICABLE"],
            "method_evaluation_mode": method_evaluation_mode(d) if category == "METHOD_RESEARCH" else "NOT_APPLICABLE",
            "knhanes_position": refined_role,
            "other_datasets": other if other else "NOT_APPLICABLE_OR_NOT_REPORTED",
            "multi_dataset_use_mode": data_use_mode(role, evidence_text + " " + str(legacy.get("ml_usage") or ""), other),
            "knhanes_actual_ml_task": actual_task(d),
            "health_topic_role": "HEALTH_RESEARCH_TOPIC" if category == "HEALTH_ANALYSIS" else "METHOD_APPLICATION_EXAMPLE",
            "source_fields": ["TSK01", "TSK02", "TSK03", "TSK06", "data/extraction.other_datasets"],
            "evidence": ev,
            "adjudication_method": "POST_HOC_EVIDENCE_ASSISTED_REVIEW_WITH_PRESPECIFIED_DECISION_RULES",
            "purpose_judgement_confidence": "MODERATE" if health_purpose == "PRIMARY_PURPOSE_UNCLEAR" else "HIGH",
            "purpose_judgement_basis": {
                "primary_objective_anchor": first(d, "TSK03", "NOT_REPORTED"),
                "main_result_or_conclusion_contribution": evidence_text or "NOT_REPORTED",
                "topic_role": "health question" if category == "HEALTH_ANALYSIS" else "method application setting",
                "final_judgement": health_purpose if category == "HEALTH_ANALYSIS" else method_category,
                "exception_or_mixed_note": (
                    "Multiple explicit co-primary aims retained without priority ordering."
                    if health_purpose == "MULTIPLE_CO_PRIMARY_PURPOSES" else
                    "Reporting was insufficient to identify a primary purpose."
                    if health_purpose == "PRIMARY_PURPOSE_UNCLEAR" else "NOT_APPLICABLE"
                ),
            },
            "rationale": (
                "Categorised as method research because the study develops or evaluates the named analytic method; the health outcome is its application setting."
                if category == "METHOD_RESEARCH" else
                "Categorised as health analysis because the reported research question concerns a health state, measure, population subgroup, or contributing variables."
            ),
        }
        from complete_protocol_evidence import project_public_classification
        record = project_public_classification(record, d.get("adjudication", {}).get("purpose_evidence_v1_3", {}))
        records.append(record)
        adjudication = d.setdefault("adjudication", {})
        adjudication.pop("study_purpose_and_dataset_use", None)
        adjudication["study_category_and_dataset_use"] = record
        Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

    summary = {
        "status": "PASS",
        "analysis_status": "POST_HOC_DESCRIPTIVE_EXTENSION",
        "denominator": len(records),
        "study_category": dict(Counter(r["study_category"] for r in records)),
        "method_research_category": dict(Counter(r["method_research_category"] for r in records if r["study_category"] == "METHOD_RESEARCH")),
        "health_analysis_purpose": dict(Counter(r["health_analysis_purpose"] for r in records if r["study_category"] == "HEALTH_ANALYSIS")),
        "health_analysis_purpose_components": dict(Counter(x for r in records if r["study_category"] == "HEALTH_ANALYSIS" for x in r["health_analysis_purpose_components"])),
        "multiple_co_primary_combinations": dict(Counter(r["purpose_component_combination"] for r in records if r["health_analysis_purpose"] == "MULTIPLE_CO_PRIMARY_PURPOSES")),
        "proposed_use": dict(Counter(x for r in records if r["study_category"] == "HEALTH_ANALYSIS" for x in r["proposed_use"])),
        "analytic_outputs": dict(Counter(x for r in records if r["study_category"] == "HEALTH_ANALYSIS" for x in r["analytic_outputs"])),
        "method_intervention_stages": dict(Counter(x for r in records if r["study_category"] == "METHOD_RESEARCH" for x in r["method_intervention_stages"])),
        "method_evaluation_mode": dict(Counter(r["method_evaluation_mode"] for r in records if r["study_category"] == "METHOD_RESEARCH")),
        "knhanes_position": dict(Counter(r["knhanes_position"] for r in records)),
        "multi_dataset_use_mode": dict(Counter(r["multi_dataset_use_mode"] for r in records)),
        "knhanes_actual_ml_task": dict(Counter(r["knhanes_actual_ml_task"] for r in records)),
        "health_topic_role": dict(Counter(r["health_topic_role"] for r in records)),
    }
    OUT.write_text(json.dumps({"schema": "study_category_audit_v2", "summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
