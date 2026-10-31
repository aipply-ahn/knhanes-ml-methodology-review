#!/usr/bin/env python3
"""Claim-evidence synthesis for the restructured Results (prompt 090).

Every value is computed from the adjudicated study records already used by
make_streamlined_figures.py (the same records that populate Supplementary
Table S7). No new extraction is performed. Output:
results/derived/claim_evidence_synthesis.json
"""
from __future__ import annotations

import json
import os
from collections import Counter

import make_streamlined_figures as m
from study_reporting import threshold_reported

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

PROJ = m.PROJ
OUT = os.path.join(PROJ, "results/derived/claim_evidence_synthesis.json")
EXP = {x["study_id"]: x for x in json.load(open(os.path.join(PROJ, "results/derived/expanded_model_task_audit.json")))["studies"]}
P = m.PURPOSE_BY_ID
V13 = m.PURPOSE_V13_BY_ID
CORE = m.CLS
HEALTH = m.HEALTH
METHOD = m.METHOD
INDIVIDUAL_USE = {"SCREENING", "DIAGNOSTIC_SUPPORT", "PERSONALISED_MANAGEMENT", "RISK_GROUP_IDENTIFICATION"}
PERIODS = ["≤2019", "2020–2022", "2023–2024", "2025–2026"]


def has(d, key, accepted):
    return m.has(d, key, accepted)


# Evidence components (study level), identical to the definitions used in the manuscript.
def outcome_full(d):
    return m.reduce_recoverability(d, "OUT16") == "FULL"


def predictors_full(d):
    return m.reduce_recoverability(d, "PRD13") == "FULL"


def tuning_status(d):
    return EXP[d["study_id"]]["algorithm_development"]["tuning_selection_status"]


def evaluation_apart_from_tuning(d):
    # Tuning demonstrably separated from final evaluation, or no tuning performed.
    return tuning_status(d) in {"TUNING_REPORTED_SEPARATED", "NO_TUNING_OR_DEFAULT_MODEL"}


def classification_supported(d):
    return outcome_full(d) and predictors_full(d) and evaluation_apart_from_tuning(d)


def stability(d):
    return has(d, "VI16", {"USED"})


def importance(d):
    return has(d, "VI01", {"USED"})


def interpretation_purpose(d):
    return "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION" in P[d["study_id"]]["health_analysis_purpose_components"]


def association_purpose(d):
    return "POPULATION_ASSOCIATION_ANALYSIS" in P[d["study_id"]]["health_analysis_purpose_components"]


def association_supported(d):
    return V13[d["study_id"]]["association_audit"]["population_association_was_survey_aware"] == "Y"


def policy_use(d):
    return "POPULATION_SURVEILLANCE_OR_POLICY" in P[d["study_id"]]["proposed_use"]


def policy_supported(d):
    return has(d, "SUR04", {"USED"}) and any(has(d, k, {"USED"}) for k in ("SUR08", "SUR09", "SUR10"))


def individual_use(d):
    return bool(set(P[d["study_id"]]["proposed_use"]) & INDIVIDUAL_USE)


def validated_beyond_development(d):
    return has(d, "VAL02", {"EXTERNAL", "TEMPORAL"})


def calibrated(d):
    return any(has(d, k, {"R"}) for k in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R"))


def individual_supported(d):
    return validated_beyond_development(d) and calibrated(d) and threshold_reported(d)


def individual_relaxed(d):
    return validated_beyond_development(d) and (calibrated(d) or threshold_reported(d))


def weights_used(d):
    return has(d, "SUR06", {"USED"}) or has(d, "SUR07", {"USED"})


def design_variance(d):
    return has(d, "SUR10", {"USED"})


CLAIMS = [
    # key, label, claim test, evidence test
    ("classification", "Classify a current health state", lambda d: True, classification_supported),
    ("interpretation", "Variable interpretation as a stated purpose", interpretation_purpose, stability),
    ("association", "Population-association purpose", association_purpose, association_supported),
    ("policy", "Surveillance or policy use", policy_use, policy_supported),
    ("individual", "Screening or individual use", individual_use, individual_supported),
]


def period(d):
    return m.period(int(d["metadata"]["publication_year"]))


def build():
    core_n = len(CORE)
    rows = []
    for d in sorted(CORE, key=lambda x: x["study_id"]):
        claims = {k: bool(c(d)) for k, _, c, _ in CLAIMS}
        met = {k: (bool(e(d)) if claims[k] else None) for k, _, _, e in CLAIMS}
        rows.append({
            "study_id": d["study_id"], "period": period(d), "claims": claims, "evidence_met": met,
            "importance_produced": importance(d),
            "components": {
                "outcome_fully_specified": outcome_full(d), "predictor_set_fully_recoverable": predictors_full(d),
                "evaluation_apart_from_tuning": evaluation_apart_from_tuning(d), "stability_checked": stability(d),
                "weights_used": weights_used(d), "design_based_variance": design_variance(d),
                "validated_beyond_development": validated_beyond_development(d), "calibration": calibrated(d),
                "threshold_reported": bool(threshold_reported(d)),
                "final_model_fully_specified": has(d, "REP17", {"R"}), "code_link": has(d, "MOD15", {"USED"}),
            },
        })
    claim_summary = []
    for k, label, _, _ in CLAIMS:
        made = [r for r in rows if r["claims"][k]]
        claim_summary.append({"claim": k, "label": label, "studies_making_claim": len(made),
                              "studies_with_required_evidence": sum(r["evidence_met"][k] for r in made)})
    n_claims = Counter(sum(r["claims"].values()) for r in rows)
    all_met = sum(all(v for v in r["evidence_met"].values() if v is not None) for r in rows)
    # Additional rows used by the dumbbell and Table 1.
    relaxed = [d for d in CORE if individual_use(d)]
    cls_components = {
        "outcome_fully_specified": sum(outcome_full(d) for d in CORE),
        "predictor_set_fully_recoverable": sum(predictors_full(d) for d in CORE),
        "tuning_separated": sum(tuning_status(d) == "TUNING_REPORTED_SEPARATED" for d in CORE),
        "no_tuning": sum(tuning_status(d) == "NO_TUNING_OR_DEFAULT_MODEL" for d in CORE),
        "evaluation_apart_from_tuning": sum(evaluation_apart_from_tuning(d) for d in CORE),
        "outcome_and_predictors_full": sum(outcome_full(d) and predictors_full(d) for d in CORE),
        "all_three": sum(classification_supported(d) for d in CORE),
    }
    # Individual use versus other core studies.
    ind = [d for d in CORE if individual_use(d)]
    other = [d for d in CORE if not individual_use(d)]
    comp = lambda group: {"n": len(group), "validated_beyond_development": sum(validated_beyond_development(d) for d in group),
                          "calibration": sum(calibrated(d) for d in group), "threshold_reported": sum(bool(threshold_reported(d)) for d in group),
                          "all_three": sum(individual_supported(d) for d in group)}
    # Survey design by claim group.
    assoc = [d for d in CORE if association_purpose(d)]
    pol = [d for d in CORE if policy_use(d)]
    neither = [d for d in CORE if not association_purpose(d) and not policy_use(d)]
    sgroup = lambda group: {"n": len(group), "weights_in_fitting_or_evaluation": sum(weights_used(d) for d in group),
                            "design_based_variance": sum(design_variance(d) for d in group),
                            "any_weight_mention": sum(has(d, "SUR04", {"USED"}) for d in group),
                            # Prompt 091: the two claim criteria, evaluated in every group.
                            "association_criterion_met": sum(association_supported(d) for d in group),
                            "policy_criterion_met": sum(policy_supported(d) for d in group)}
    # Method claims (36 method-focused studies).
    method_rows = []
    for d in METHOD:
        r = P[d["study_id"]]
        method_rows.append({"study_id": d["study_id"], "kind": r["method_research_category"],
                            "evaluation_mode": r["method_evaluation_mode"], "knhanes_position": r["knhanes_position"]})
    dev = [x for x in method_rows if x["kind"] == "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT"]
    cmpr = [x for x in method_rows if x["kind"] == "EXISTING_METHODS_COMPARISON_OR_EVALUATION"]
    beyond = lambda x: (x["evaluation_mode"] in {"SIMULATION_AND_EMPIRICAL_APPLICATION", "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"}
                        or x["knhanes_position"] in {"ONE_OF_MULTIPLE_PRIMARY_DATASETS", "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"})
    by_id = {d["study_id"]: d for d in METHOD}
    uncertainty = lambda x: has(by_id[x["study_id"]], "MET_PAIR", {"Y", "USED"}) or has(by_id[x["study_id"]], "MET_CI", {"Y"})
    method = {
        "development": {"n": len(dev), "comparator_evaluation": sum(x["evaluation_mode"] == "EMPIRICAL_COMPARATOR_EVALUATION" for x in dev),
                        "beyond_single_knhanes_application": sum(beyond(x) for x in dev)},
        "comparison": {"n": len(cmpr), "uncertainty_or_paired_comparison": sum(uncertainty(x) for x in cmpr),
                       "beyond_single_knhanes_application": sum(beyond(x) for x in cmpr)},
    }
    # Analysis functions actually performed (184 health-focused studies).
    fkeys = ["FUN_PRED", "FUN_INTERP", "FUN_COMPARE", "FUN_TRANSPORT", "FUN_TOOL", "FUN_PROCESS", "FUN_PATTERN"]
    functions = {k: sum(has(d, k, {"PRESENT"}) for d in HEALTH) for k in fkeys}
    # Use composition (220).
    health_tasks = Counter(m.first(d, "TSK01") for d in HEALTH)
    timing = Counter(m.first_applicable(d, "OUT10") for d in CORE)
    method_kinds = Counter(x["kind"] for x in method_rows)
    use = {"classify_current_state": timing["CURRENT"], "classification_timing_unclear": timing["UNC"],
           "estimate_continuous_or_ordered": health_tasks["CONT"], "other_health_analyses": health_tasks["OTHER"],
           "develop_or_improve_method": method_kinds["METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT"],
           "compare_existing_methods": method_kinds["EXISTING_METHODS_COMPARISON_OR_EVALUATION"]}
    # Period series with importance-reporting denominators.
    per = {}
    for p in PERIODS:
        g = [d for d in CORE if period(d) == p]
        imp = [d for d in g if importance(d)]
        per[p] = {"n": len(g), "shap": sum(has(d, "VI02", {"SHAP"}) for d in g), "importance": len(imp),
                  "stability_among_importance": sum(stability(d) for d in imp)}
    uses184 = Counter(x for d in HEALTH for x in P[d["study_id"]]["proposed_use"])
    # Prompt 091: claim-count groups, beyond-classification result, and the ranking-as-claim sensitivity.
    extra = ["interpretation", "association", "policy", "individual"]
    all_met_row = lambda r: all(v for v in r["evidence_met"].values() if v is not None)
    beyond_rows = [r for r in rows if any(r["claims"][k] for k in extra)]
    only_cls = [r for r in rows if not any(r["claims"][k] for k in extra)]
    groups = {}
    for n in sorted(n_claims):
        g = [r for r in rows if sum(r["claims"].values()) == n]
        groups[str(n)] = {"n": len(g), "all_claims_supported": sum(all_met_row(r) for r in g)}
    # Prompt 093: requirement fulfilment by number of claims (pooled requirements met / requirements
    # applicable). Computed to test the sentence "the further a study's claims went beyond
    # classification, the less was reported"; the proportions rise, so the sentence was deleted.
    by_count = {}
    for label, test in (("1", lambda n: n == 1), ("2", lambda n: n == 2), ("3", lambda n: n == 3), ("4-5", lambda n: n >= 4)):
        g = [r for r in rows if test(sum(r["claims"].values()))]
        vals = [v for r in g for v in r["evidence_met"].values() if v is not None]
        by_count[label] = {"studies": len(g), "requirements_met": sum(vals), "requirements_applicable": len(vals),
                           "percent": round(100 * sum(vals) / len(vals), 1)}
    sensitivity = sum(all_met_row(r) and (r["components"]["stability_checked"] or not r["importance_produced"]) for r in rows)
    cls_met_rows = [r for r in rows if r["evidence_met"]["classification"]]
    flow = lambda d: d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {})
    fkeys = ["source_population_size_reported", "eligibility_criteria_reported", "exclusion_numbers_reported",
             "exclusion_reasons_reported", "final_analytic_sample_reported", "complete_cohort_traceability"]
    assoc_audit = [V13[d["study_id"]]["association_audit"] for d in HEALTH]
    estimates = [a for a in assoc_audit if a["any_association_estimate_reported"] == "Y"]
    result = {
        "schema": "claim_evidence_synthesis_v2",
        "source": "adjudicated study records (data/protocol_v1_2/final, purpose audits); same records as Supplementary Table S7",
        "core_n": core_n,
        "claims": claim_summary,
        "importance_produced_row": {"studies_producing_importance": sum(importance(d) for d in CORE), "stability_checked": sum(stability(d) for d in CORE if importance(d))},
        "studies_with_purpose_or_use_claims": sum(any(r["claims"][k] for k in r["claims"] if k != "classification") for r in rows),
        "studies_with_all_purpose_or_use_claims_supported": sum(any(r["claims"][k] for k in r["claims"] if k != "classification")
            and all(r["evidence_met"][k] for k in r["claims"] if k != "classification" and r["claims"][k]) for r in rows),
        "individual_relaxed_row": {"studies_making_claim": len(relaxed), "studies_with_required_evidence": sum(individual_relaxed(d) for d in relaxed)},
        "claims_per_study": dict(sorted(n_claims.items())),
        "studies_with_all_claims_supported": all_met,
        "classification_components": cls_components,
        "individual_vs_other": {"individual_use": comp(ind), "other": comp(other)},
        "survey_by_claim_group": {"population_association": sgroup(assoc), "surveillance_or_policy": sgroup(pol), "neither": sgroup(neither)},
        "method_claims": method,
        "health_functions": functions,
        "use_composition": use,
        "health_proposed_use": {"individual_use_any": sum(individual_use(d) for d in HEALTH), **{k: uses184[k] for k in sorted(uses184)}},
        "reproducibility": {"predictor_set_fully_recoverable": cls_components["predictor_set_fully_recoverable"],
                            "final_model_fully_specified": sum(has(d, "REP17", {"R"}) for d in CORE),
                            "code_link": sum(has(d, "MOD15", {"USED"}) for d in CORE)},
        "period_importance": per,
        "beyond_classification": {"studies": len(beyond_rows), "all_claims_supported": sum(all_met_row(r) for r in beyond_rows)},
        "classification_only": {"studies": len(only_cls), "all_claims_supported": sum(all_met_row(r) for r in only_cls)},
        "claim_count_groups": groups,
        "requirement_fulfilment_by_claim_count": by_count,
        "classification_met_studies": {"n": len(cls_met_rows),
                                        "with_further_claims": sum(any(r["claims"][k] for k in extra) for r in cls_met_rows)},
        "sensitivity_every_ranking_is_a_claim": {"all_claims_supported": sensitivity, "core_n": core_n},
        "participant_flow_core": {k: sum(flow(d).get(k, {}).get("value") is True for d in CORE) for k in fkeys},
        "association_estimates_health": {"studies_with_estimate": len(estimates),
                                         "survey_design_uncertainty": sum(a["population_association_was_survey_aware"] == "Y" for a in estimates)},
        "causal_purpose": {"health_focused": sum("CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION" in P[d["study_id"]]["health_analysis_purpose_components"] for d in HEALTH),
                           "core": sum("CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION" in P[d["study_id"]]["health_analysis_purpose_components"] for d in CORE)},
        "studies": rows,
    }
    _pin(sum(use.values()), 249, "claim_evidence_analysis.py:277")  # prompt 106 pin
    _pin(result["beyond_classification"], {"studies": 120, "all_claims_supported": 0}, "claim_evidence_analysis.py:278")  # prompt 106 pin
    _pin(result["classification_only"], {"studies": 45, "all_claims_supported": 3}, "claim_evidence_analysis.py:279")  # prompt 106 pin
    _pin(result["importance_produced_row"], {"studies_producing_importance": 129, "stability_checked": 25}, "claim_evidence_analysis.py:280")  # prompt 106 pin
    _pin((result["claims"][0]["studies_with_required_evidence"], result["claims"][1]["studies_making_claim"], result["claims"][1]["studies_with_required_evidence"]), (12, 82, 15), "claim_evidence_analysis.py:281")  # prompt 106 pin
    _pin([c["studies_making_claim"] for c in result["claims"][2:]], [19, 37, 48], "claim_evidence_analysis.py:282")  # prompt 106 pin
    _pin([c["studies_with_required_evidence"] for c in result["claims"][2:]], [4, 8, 5], "claim_evidence_analysis.py:283")  # prompt 106 pin
    # Prompt 093: not a monotone decline (6.7%, 12.7%, 13.8%, 14.3%), so no dose-response sentence.
    _pin([v["percent"] for v in by_count.values()], [6.7, 12.7, 13.8, 14.3], "claim_evidence_analysis.py:285")  # prompt 106 pin
    _pin([(v["requirements_met"], v["requirements_applicable"]) for v in by_count.values()], [(3, 45), (17, 134), (17, 123), (7, 49)], "claim_evidence_analysis.py:286")  # prompt 106 pin
    return result


def main():
    result = build()
    with open(OUT, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    brief = {k: v for k, v in result.items() if k != "studies"}
    print(json.dumps(brief, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
