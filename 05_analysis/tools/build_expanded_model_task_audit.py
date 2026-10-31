#!/usr/bin/env python3
"""Derive transparent task/model-development fields from protocol-v1.2 records.

The source protocol did not encode every requested distinction as a separate item.
This script therefore preserves the source item IDs/evidence IDs, labels rule-derived
values explicitly, and uses UNCLEAR where the report cannot support a finer role.
"""
from __future__ import annotations

import csv, glob, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/protocol_v1_2/final"
OUT = ROOT / "results/derived/expanded_model_task_audit.json"
CONTINUOUS_INTERPRETATION = {
    x["study_id"]: x
    for x in json.loads((ROOT / "results/derived/continuous_interpretation_audit.json").read_text())["studies"]
}

with (ROOT / "data/input_counts.tsv").open(encoding="utf-8-sig") as f:
    PIPELINE_ENTRY_COUNTS = {r["key"]: int(r["n_variables"]) for r in csv.DictReader(f, delimiter="\t") if r.get("n_variables")}

FAMILIES = {
    "Random forest": r"random forest|randomforest|\bRF\b",
    "Logistic regression": r"logistic regression|logit",
    "XGBoost": r"xgboost|xgbclassifier|xgbregressor|\bXGB\b",
    "SVM": r"support vector|\bSVM\b",
    "DNN/MLP": r"deep neural|deep learning|\bDNN\b|multilayer perceptron|\bMLP\b|neural network|\bANN\b",
    "Decision tree": r"decision tree|\bCART\b",
    "LightGBM": r"lightgbm|\bLGBM\b",
    "Naive Bayes": r"na[iï]ve bayes|\bNB\b",
    "kNN": r"k[- ]?nearest|\bkNN\b|\bKNN\b",
    "Gradient boosting": r"gradient boosting|\bGBM\b",
}

def rows(d, k): return d.get("protocol_items", {}).get(k, [])
def flat(d, k):
    out=[]
    for x in rows(d,k):
        v=x.get("value"); out.extend(v if isinstance(v,list) else [v])
    return out
def first(d,k,default=None):
    v=flat(d,k); return v[0] if v else default
def included(d): return d.get("corpus_status",{}).get("include", first(d,"ELG04")=="Y")
def usable_text(d,k): return [str(v) for v in flat(d,k) if v not in (None,"", "NA","NR","UNC")]
def evidence_ids(d, keys):
    return sorted({e for k in keys for x in rows(d,k) for e in x.get("evidence_ids",[])})
def families(texts):
    joined="\n".join(texts)
    return [name for name,pat in FAMILIES.items() if re.search(pat,joined,re.I)]

def tuning(d):
    text=" ".join(usable_text(d,"MOD07")).lower()
    used="USED" in flat(d,"MOD12")
    if not used and not text: method="NOT_REPORTED"
    elif "grid" in text: method="GRID_SEARCH"
    elif "random search" in text: method="RANDOM_SEARCH"
    elif any(x in text for x in ("bayesian","optuna","parzen","genetic","tpot")): method="BAYESIAN_OR_OTHER_OPTIMISATION"
    elif any(x in text for x in ("manual","trial","informal","default")): method="MANUAL_OR_DEFAULT"
    elif text: method="OTHER_REPORTED"
    else: method="METHOD_NOT_REPORTED"
    sep=set(flat(d,"MOD13"))
    partition=("SEPARATE" if "USED" in sep else "TEST_OR_EVALUATION_INVOLVED" if "NOT_USED" in sep
               else "UNCLEAR" if sep & {"NR","UNC"} else "NOT_APPLICABLE")
    return method,partition

def tuning_status(d):
    used=set(flat(d,"MOD12")); sep=set(flat(d,"MOD13"))
    if "USED" in used:
        if "NOT_USED" in sep: return "TUNING_REPORTED_EVALUATION_DATA_INVOLVED"
        if "USED" in sep: return "TUNING_REPORTED_SEPARATED"
        return "TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED"
    if "NOT_USED" in used: return "NO_TUNING_OR_DEFAULT_MODEL"
    if used & {"NR","UNC"}: return "TUNING_NOT_REPORTED"
    return "NOT_ASSESSABLE"

def importance_stability_methods(d):
    if "USED" not in flat(d,"VI16"): return []
    text=" ".join(str(x.get("rationale") or "") for x in rows(d,"VI16"))
    text += " " + " ".join(usable_text(d,"VI04")); text=text.lower()
    out=[]
    for label,terms in {
      "RESAMPLING_STABILITY":("bootstrap","resampl","cross-validation","cross validation","repeated"),
      "ACROSS_CYCLE_STABILITY":("cycle","year-to-year","across year","temporal"),
      "EXTERNAL_DATA_REPLICATION":("external","independent data"),
      "SUBGROUP_CONSISTENCY":("subgroup","sex-specific","age group"),
      "METHOD_OR_MODEL_AGREEMENT":("agreement","across model","multiple model","consensus"),
      "UNCERTAINTY_INTERVAL":("confidence interval","interval","standard deviation","uncertainty"),
    }.items():
        if any(t in text for t in terms): out.append(label)
    return out or ["METHOD_NOT_RECOVERABLE"]

def relation(d):
    # Ordered, mutually exclusive summary; stricter downstream categories take precedence.
    if "USED" in flat(d,"VI14"): return "EXACT_CARRYOVER"
    if "USED" in flat(d,"VI11"): return "ML_RANKING_GUIDED_STATISTICS"
    base=" ".join(usable_text(d,"MOD04")).lower()
    if any(x in base for x in ("separate conventional","independent","association analysis","post hoc","post-hoc")):
        return "INDEPENDENT_OR_PARALLEL_STATISTICAL_ANALYSIS"
    if families(usable_text(d,"MOD04")): return "CONVENTIONAL_COMPARATOR"
    if base in ("", "none", "no", "na", "nr"): return "ML_ONLY_OR_NO_REPORTED_STATISTICAL_LINK"
    return "UNCLEAR_RELATIONSHIP"

def nonclassification_support(d):
    task=first(d,"TSK01"); subtype=first(d,"TSK11")
    if task=="CONT":
        metric=bool(usable_text(d,"NC02")); valid=any(v in {"SPLIT","CV","BOOT","TEMPORAL","EXTERNAL"} for v in flat(d,"VAL02"))
        level="SUPPORTED" if metric and valid else "PARTIAL" if metric or valid else "NOT_DOCUMENTED"
        reason="continuous metric context and a validation design" if level=="SUPPORTED" else "only one or neither required component"
        criteria=["NC02 continuous metric context","VAL02 internal/external/temporal validation"]
    elif subtype=="IMPUTATION":
        mask=bool(usable_text(d,"NC04")); recon=bool(usable_text(d,"NC05")); comp=recon and any(x in " ".join(usable_text(d,"NC05")).lower() for x in ("compar","versus","vs ","baseline","complete-case"))
        level="SUPPORTED" if mask and recon and comp else "PARTIAL" if mask or recon else "NOT_DOCUMENTED"
        reason="masking, reconstruction error, and comparison baseline" if level=="SUPPORTED" else "incomplete imputation-evaluation components"
        criteria=["NC04 masking design","NC05 reconstruction error and baseline"]
    elif subtype=="CLUSTERING":
        method=bool(usable_text(d,"NC06")); stable="Y" in flat(d,"NC07")
        level="SUPPORTED" if method and stable else "PARTIAL" if method or stable else "NOT_DOCUMENTED"
        reason="cluster-number/interpretation information plus stability" if level=="SUPPORTED" else "stability or replication was incomplete"
        criteria=["NC06 cluster-number/interpretation","NC07 stability/replication"]
    elif subtype=="CAUSAL":
        txt=" ".join(usable_text(d,"NC08")).lower(); assumptions=bool(txt) and not txt.startswith("no ")
        sensitivity=any(x in txt for x in ("sensitivity","overlap","positivity"))
        level="SUPPORTED" if assumptions and sensitivity else "PARTIAL" if txt else "NOT_DOCUMENTED"
        reason="identification assumptions plus overlap/sensitivity evidence" if level=="SUPPORTED" else "causal assumptions or sensitivity evidence incomplete"
        criteria=["NC08 identification assumptions, overlap, sensitivity"]
    elif subtype=="REPRESENTATION":
        txt=" ".join(usable_text(d,"NC09")); downstream=bool(txt)
        level="SUPPORTED" if downstream else "NOT_DOCUMENTED"; reason="representation validity and downstream/external evaluation" if downstream else "representation evaluation not documented"
        criteria=["NC09 representation validity/downstream evaluation"]
    else:
        level="NOT_ASSESSABLE"; reason="no prespecified task-specific criterion for this residual structural/data-processing task"; criteria=["TSK11 residual task"]
    return {"level":level,"reason":reason,"criteria":criteria,"evidence_ids":evidence_ids(d,["NC02","VAL02","NC04","NC05","NC06","NC07","NC08","NC09"])}

def nonclassification_criteria(d):
    task=first(d,"TSK01"); subtype=first(d,"TSK11"); out={}
    if task=="CONT":
        out={"external_or_temporal_validation":any(v in {"EXTERNAL","TEMPORAL"} for v in flat(d,"VAL02")),
             "uncertainty_reported":any(v in {"Y","USED"} for k in ("MET_CI","MET_SD") for v in flat(d,k))}
    elif subtype=="IMPUTATION":
        recon=" ".join(usable_text(d,"NC05")).lower()
        out={"masking_design":bool(usable_text(d,"NC04")),"reconstruction_error":bool(recon),
             "comparison_baseline":any(x in recon for x in ("compar","versus","vs ","baseline","complete-case"))}
    elif subtype=="CLUSTERING":
        out={"stability_assessment":"Y" in flat(d,"NC07"),"external_replication":any(v=="EXTERNAL" for v in flat(d,"VAL02"))}
    elif subtype=="CAUSAL":
        txt=" ".join(usable_text(d,"NC08")).lower()
        out={"identification_assumptions":bool(txt) and not txt.startswith("no "),
             "sensitivity_or_overlap":any(x in txt for x in ("sensitivity","overlap","positivity"))}
    elif subtype=="REPRESENTATION": out={"downstream_or_external_validation":bool(usable_text(d,"NC09"))}
    return out

def substantive(d, key):
    """Return source-entered values without converting NR/NA into substantive data."""
    return [v for v in flat(d, key) if v not in (None, "", "NA", "NR", "UNC")]

def derived_field(d, source_items, value, status=None, note=None):
    if status is None:
        status = "REPORTED" if value not in (None, [], "", "NR", "NA", "UNC") else str(value or "NR")
    return {
        "value": value,
        "value_status": status,
        "source_item_ids": source_items,
        "evidence_ids": evidence_ids(d, source_items),
        "derivation_note": note,
    }

def _population_category(d):
    amin = next((v for v in substantive(d, "POP03") if isinstance(v, (int, float))), None)
    amax = next((v for v in substantive(d, "POP04") if isinstance(v, (int, float))), None)
    sex = " ".join(map(str, substantive(d, "POP05"))).lower()
    text = " ".join(map(str, substantive(d, "POP01") + substantive(d, "POP02") + substantive(d, "POP06"))).lower()
    sex_limited = bool(sex) and not any(x in sex for x in ("none", "both", "men and women", "no sex", "all sex"))
    child = (amax is not None and amax <= 19) or any(x in text for x in ("child", "adolesc", "pediatric", "school-aged", "youth"))
    # A secondary older-adult subgroup must not replace a broad-adult primary
    # population (KHM001).  Age wording is used only when no lower bound for a
    # broader primary cohort has been reported.
    older = (amin is not None and amin >= 40) or (amin is None and any(x in text for x in ("older adult", "elderly", "middle-aged", "postmenopausal")))
    # Generic phrases such as "participants with accelerometer data" and
    # "subjects with direct LDL-C measurements" are availability restrictions,
    # not disease/risk cohorts (KHM067 and KHM081).  Require an actual clinical
    # condition/risk term rather than the syntactic phrase "participants with".
    disease_terms = ("diagnosed with", "at risk of", "survivors", "patients with cancer",
                     "patients with diabetes", "patients with hypertension", "patients with copd",
                     "copd cases", "metabolic syndrome patients", "disease group")
    disease_limited = any(x in text for x in disease_terms)
    # Mutually exclusive display category; the separate restriction fields below retain overlap.
    if disease_limited: category = "DISEASE_OR_RISK_GROUP"
    elif sex_limited: category = "SEX_RESTRICTED"
    elif child: category = "CHILD_OR_ADOLESCENT"
    elif older: category = "MIDDLE_OR_OLDER_ADULT"
    elif "all ages" in text: category = "GENERAL_ALL_AGES"
    elif text or amin is not None or amax is not None: category = "BROAD_OR_GENERAL_ADULT"
    else: category = "NOT_REPORTED"
    return category, sex_limited, disease_limited

def _feature_selection_approach(d):
    if not any(v == "USED" for v in flat(d, "PRE11")):
        return "NOT_APPLIED" if any(v == "NOT_USED" for v in flat(d, "PRE11")) else "NOT_REPORTED"
    text = " ".join(map(str, substantive(d, "PRE12") + substantive(d, "PRD01") + substantive(d, "PRD03"))).lower()
    found=[]
    rules = [
        ("PRIOR_KNOWLEDGE_OR_CLINICAL", ("clinical", "expert", "prior knowledge", "a priori", "literature")),
        ("UNIVARIATE_OR_STATISTICAL_FILTER", ("univariate", "p-value", "correlation", "chi-square", "anova", "statistical filter")),
        ("FILTER_METHOD", ("mutual information", "relieff", "mrmr", "information gain", "variance threshold")),
        ("WRAPPER_OR_RFE", ("recursive feature elimination", "rfe", "wrapper")),
        ("EMBEDDED_SELECTION", ("lasso", "elastic net", "embedded", "regularization", "regularisation")),
        ("IMPORTANCE_BASED_SELECTION", ("feature importance", "variable importance", "shap", "top-k", "top k")),
    ]
    for label, terms in rules:
        if any(term in text for term in terms): found.append(label)
    if len(found) > 1: return "MULTIPLE_METHODS"
    return found[0] if found else "METHOD_NOT_REPORTED"

def _outcome_source_category(d):
    text = " ".join(map(str, substantive(d, "OUT04"))).lower()
    if not text: return "NOT_REPORTED"
    if any(x in text for x in ("composite", "combined definition", "and/or")): return "COMPOSITE_DEFINITION"
    if any(x in text for x in ("cluster", "latent class", "data-derived", "algorithm")): return "DATA_DERIVED_CLASS"
    if any(x in text for x in ("questionnaire", "scale", "phq", "eq-5d", "instrument")): return "VALIDATED_QUESTIONNAIRE_OR_SCALE"
    if any(x in text for x in ("self-report", "self report", "self-reported", "survey response")): return "SELF_REPORTED_DIAGNOSIS"
    if any(x in text for x in ("physician", "doctor-diagnosed", "doctor diagnosed")): return "PHYSICIAN_DIAGNOSIS"
    if any(x in text for x in ("laboratory", "serum", "blood test", "urine", "biomarker")): return "LABORATORY_THRESHOLD"
    if any(x in text for x in ("measurement", "examination", "blood pressure", "bmi", "spirometr")): return "CLINICAL_OR_PHYSICAL_MEASUREMENT"
    return "OTHER_REPORTED_SOURCE"

def _subgroup_field(d, kind):
    patterns={
      "age": (r"age[- ]stratified", r"stratified by age", r"separate (?:models|analyses) (?:by|for) age", r"age subgroup"),
      "sex": (r"sex[- ]stratified", r"stratified by sex", r"separate (?:models|analyses) (?:by|for) sex", r"men and women separately", r"male and female models"),
      "other": (r"subgroup analys", r"stratified analys"),
    }[kind]
    matched=[]
    for e in d.get("evidence_registry",[]):
        blob=" ".join(str(e.get(k) or "") for k in ("excerpt","start_anchor","end_anchor"))
        if any(re.search(p,blob,re.I) for p in patterns): matched.append(e.get("evidence_id"))
    return derived_field(d,[],"REPORTED" if matched else "NR","DERIVED" if matched else "NOT_REPORTED",
                         "Conservative exact-phrase screen of the evidence registry; eligibility restrictions alone do not qualify.") | {"evidence_ids":sorted(set(filter(None,matched)))}

def analytic_flow(d):
    """Human-readable, stage-specific view without altering the locked 382 source items."""
    include = included(d)
    if not include:
        return {"applicability":"NOT_INCLUDED", "fields":{}}
    category, sex_limited, disease_limited = _population_category(d)
    pop15 = set(flat(d, "POP15"))
    flow = "FULLY_RECONSTRUCTABLE" if "R" in pop15 else "PARTLY_RECONSTRUCTABLE" if "P" in pop15 else "NOT_REPORTED" if "NR" in pop15 else "UNCLEAR"
    prd13 = set(flat(d, "PRD13"))
    candidate_status = "NOT_RECONSTRUCTABLE" if "R0" in prd13 else "PARTLY_RECONSTRUCTABLE" if "R1" in prd13 else "FULLY_RECONSTRUCTABLE" if "R2" in prd13 else "NOT_REPORTED"
    vi14 = set(flat(d, "VI14"))
    exact_values = substantive(d, "VI13") if "USED" in vi14 else []
    fs_approach = _feature_selection_approach(d)
    source_population_reported = bool(substantive(d, "POP08"))
    eligibility_criteria_reported = bool(substantive(d, "POP06"))
    exclusion_numbers_reported = bool(substantive(d, "POP10"))
    exclusion_reasons_reported = bool(substantive(d, "POP11"))
    final_sample_reported = bool(substantive(d, "POP09"))
    outcome_frequency_reported = bool(substantive(d, "POP12") or substantive(d, "POP14"))
    complete_cohort_traceability = all((source_population_reported,
                                        eligibility_criteria_reported,
                                        exclusion_numbers_reported,
                                        exclusion_reasons_reported,
                                        final_sample_reported))
    fields = {
      "target_population_description": derived_field(d,["POP01","POP02"],substantive(d,"POP01")+substantive(d,"POP02") or "NR"),
      "age_inclusion_min": derived_field(d,["POP03"],substantive(d,"POP03") or "NR"),
      "age_inclusion_max": derived_field(d,["POP04"],substantive(d,"POP04") or "NR"),
      "age_group_category": derived_field(d,["POP01","POP02","POP03","POP04","POP06"],category,"DERIVED",
          "Rule-derived from explicit age bounds and population wording; NOT_REPORTED when no source description supports a category."),
      "sex_restriction": derived_field(d,["POP05"],substantive(d,"POP05") or "NR"),
      "sex_restriction_present": derived_field(d,["POP05"],sex_limited,"DERIVED","A general-population or both-sex statement is not a sex restriction."),
      "disease_or_risk_group_restriction": derived_field(d,["POP01","POP02","POP06"],disease_limited,"DERIVED","Conservative phrase-based flag from explicit population or eligibility wording."),
      "initial_eligible_sample_n": derived_field(d,["POP08"],substantive(d,"POP08") or "NR"),
      "exclusion_criteria_reported": derived_field(d,["POP07"],bool(substantive(d,"POP07")),"DERIVED"),
      "excluded_n_by_reason": derived_field(d,["POP10","POP11"],substantive(d,"POP11") or "NR", note="Raw reported exclusion flow; no reason-specific counts are inferred."),
      "final_analytic_sample_n": derived_field(d,["POP09"],substantive(d,"POP09") or "NR"),
      "positive_event_n": derived_field(d,["POP12"],substantive(d,"POP12") or "NR"),
      "positive_prevalence": derived_field(d,["POP14"],substantive(d,"POP14") or "NR"),
      "participant_flow_reconstructable": derived_field(d,["POP15"],flow,"DERIVED"),
      "source_population_size_reported": derived_field(d,["POP08"],source_population_reported,"DERIVED"),
      "eligibility_criteria_reported": derived_field(d,["POP06"],eligibility_criteria_reported,"DERIVED"),
      "exclusion_numbers_reported": derived_field(d,["POP10"],exclusion_numbers_reported,"DERIVED"),
      "exclusion_reasons_reported": derived_field(d,["POP11"],exclusion_reasons_reported,"DERIVED"),
      "final_analytic_sample_reported": derived_field(d,["POP09"],final_sample_reported,"DERIVED"),
      "outcome_cases_or_prevalence_reported": derived_field(d,["POP12","POP14"],outcome_frequency_reported,"DERIVED"),
      "complete_cohort_traceability": derived_field(
          d,["POP06","POP08","POP09","POP10","POP11"],complete_cohort_traceability,"DERIVED",
          "Explicit intersection: source-population size, eligibility criteria, exclusion numbers, exclusion reasons, and final analytic sample; POP15 is not substituted."),
      "age_stratified_analysis": _subgroup_field(d,"age"),
      "sex_stratified_analysis": _subgroup_field(d,"sex"),
      "other_subgroup_analysis": _subgroup_field(d,"other"),
      "outcome_ascertainment_source_category": derived_field(d,["OUT04"],_outcome_source_category(d),"DERIVED"),
      "candidate_predictor_universe_reported": derived_field(d,["PRD01","PRD13"],candidate_status,"DERIVED"),
      "initial_candidate_predictor_count": derived_field(d,[],PIPELINE_ENTRY_COUNTS.get(d.get("canonical_key"),"NR"),
          "REPORTED" if d.get("canonical_key") in PIPELINE_ENTRY_COUNTS else "NOT_REPORTED",
          "First explicitly labelled overall candidate/input count in the legacy full-text extraction; no prose-list counting."),
      "pre_model_selected_predictor_count": derived_field(d,["PRD04"],substantive(d,"PRD04") if any(v=="USED" for v in flat(d,"PRE11")) and substantive(d,"PRD04") else "NR",
          note="Retained only when feature selection was explicitly used; not substituted for fitted-model input in studies without selection."),
      "fitted_model_input_dimension": derived_field(d,["PRD02"],substantive(d,"PRD02") or "NR", note="Existing unit-level input-dimension audit used for the prespecified 120-study denominator; repeated model units remain separate."),
      "importance_ranked_variable_count": derived_field(d,[],"NR","NOT_REPORTED","VI05 is interpreted-model input dimension, not the number of displayed ranks."),
      "importance_selected_subset_count": derived_field(d,["VI09"],substantive(d,"VI09") or "NR"),
      "downstream_inference_variable_count": derived_field(d,["VI13"],substantive(d,"VI13") or "NR"),
      "exact_carryover_count": derived_field(d,["VI13","VI14"],exact_values or ("NA" if "NOT_USED" in vi14 or "NA" in vi14 else "NR")),
      "feature_selection_approach": derived_field(d,["PRE11","PRE12","PRD01","PRD03"],fs_approach,"DERIVED"),
    }
    fields["initial_candidate_predictor_count"]["source_file"] = "data/input_counts.tsv"
    return {"applicability":"INCLUDED", "fields":fields,
            "stage_order":["KNHANES_DATA","PARTICIPANT_SELECTION","OUTCOME_CONSTRUCTION","CANDIDATE_PREDICTORS","PREPROCESSING_AND_FEATURE_SELECTION","MODEL_DEVELOPMENT","EVALUATION","VARIABLE_IMPORTANCE","DOWNSTREAM_ANALYSIS"],
            "non_inference_rule":"NR is retained when the named analytic stage cannot be distinguished from the source report."}

def selection_restriction_dimensions(d):
    """Nonexclusive participant-selection dimensions used in Figure 3C."""
    if not included(d): return {"applicability":"NOT_INCLUDED","fields":{}}
    flow=analytic_flow(d)["fields"]
    age=bool(substantive(d,"POP03") or substantive(d,"POP04"))
    text=" ".join(map(str,substantive(d,"POP01")+substantive(d,"POP02")+substantive(d,"POP06")+substantive(d,"POP07"))).lower()
    measurement=any(x in text for x in ("complete data","complete-case","missing values","available data","laboratory records with","direct ldl","accelerometer data","valid wear","measurement available"))
    return {"applicability":"INCLUDED","mutually_exclusive":False,"fields":{
      "age_restriction":derived_field(d,["POP03","POP04"],age,"DERIVED","Explicit lower or upper age bound."),
      "sex_restriction":flow["sex_restriction_present"],
      "disease_or_risk_restriction":flow["disease_or_risk_group_restriction"],
      "measurement_or_data_availability_restriction":derived_field(d,["POP01","POP02","POP06","POP07"],measurement,"DERIVED","Explicit complete-data, measurement, assay, wear-time, or other data-availability eligibility condition."),
    },"note":"Restrictions may overlap; subgroup analyses are separate."}

def main():
    docs=[json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(FINAL/"KHM*_final.json")))]
    studies=[]
    for d in docs:
        d.setdefault("adjudication",{})["analytic_flow"] = analytic_flow(d)
        d["adjudication"]["selection_restriction_dimensions"] = selection_restriction_dimensions(d)
        if first(d, "TSK01") == "CONT" and d["study_id"] in CONTINUOUS_INTERPRETATION:
            d["adjudication"]["continuous_interpretation_audit"] = CONTINUOUS_INTERPRETATION[d["study_id"]]
        if not included(d):
            Path(FINAL/f"{d['study_id']}_final.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
            continue
        sid=d["study_id"]
        model_labels=[str(m.get("label") or "") for m in d.get("units",{}).get("models",[])]
        evaluated=families(model_labels)
        baseline=[x for x in families(usable_text(d,"MOD04")) if x in evaluated]
        selected_ids={mid for b in d.get("best_model_selections",[]) if b.get("author_designated") for mid in (b.get("selected_model_ids") or [])}
        final=families([str(m.get("label") or "") for m in d.get("units",{}).get("models",[]) if m.get("model_id") in selected_ids])
        interpreted=[x for x in families(usable_text(d,"VI03")) if x in evaluated]
        tm,tp=tuning(d); selections=[b for b in d.get("best_model_selections",[]) if b.get("author_designated")]
        selection_text=" ".join(str(b.get("criterion") or "")+" "+str(b.get("rationale") or "") for b in selections).lower()
        audit={
          "study_id":sid,"task_group":first(d,"TSK01"),"other_task_subtype":first(d,"TSK11"),
          "algorithm_development":{
            "algorithm_family":evaluated,"algorithm_name_as_reported":usable_text(d,"MOD02"),
            "algorithm_role":{"candidate_or_evaluated":evaluated,"baseline_or_comparator":baseline,"feature_selection_or_importance":interpreted,"author_designated_final":final,"unresolved_role":"UNCLEAR" if evaluated and not (baseline or final or interpreted) else "NA"},
            "baseline_or_comparator":baseline,"ensemble_status":"REPORTED" if re.search(r"ensemble|stack|voting", " ".join(usable_text(d,"MOD02")),re.I) else "NOT_REPORTED",
            "hyperparameter_tuning_method":tm,"tuning_data_partition":tp,"tuning_selection_status":tuning_status(d),
            "final_model_selection_metric":[b.get("criterion") for b in selections],"final_model_selection_dataset":[b.get("evaluation_ids") for b in selections],
            "test_set_used_for_selection":"YES_OR_APPARENT" if re.search(r"\btest\b|held[- ]out evaluation",selection_text) else "NOT_REPORTED_OR_NO",
            "final_model_fully_specified":first(d,"MOD14","NR"),"software_and_version":usable_text(d,"MOD09"),
            "evidence_location":evidence_ids(d,["MOD02","MOD04","MOD05","MOD07","MOD09","MOD12","MOD13","MOD14","BEST02","BEST03","VI03"]),
            "derivation_note":"Rule-derived from named protocol fields; unresolved roles remain UNCLEAR and are not inferred from algorithm names alone."
          },
          "ml_statistical_relationship":relation(d),
          "relationship_evidence_ids":evidence_ids(d,["MOD04","VI11","VI12","VI14"]),
          "importance_stability_methods":importance_stability_methods(d),
        }
        if first(d,"TSK01") in {"CONT","OTHER"}:
            audit["task_appropriate_evidence"]=nonclassification_support(d)
            audit["task_appropriate_criteria_reported"]=nonclassification_criteria(d)
        d.setdefault("adjudication",{})["expanded_model_task_audit"]=audit
        Path(FINAL/f"{sid}_final.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
        studies.append(audit)
    agg={"status":"PASS","generated_from":"data/protocol_v1_2/final/KHM*_final.json","n_included":len(studies),
         "task_counts":dict(Counter(x["task_group"] for x in studies)),
         "tuning_method":dict(Counter(x["algorithm_development"]["hyperparameter_tuning_method"] for x in studies if x["task_group"]=="CLS")),
         "tuning_partition":dict(Counter(x["algorithm_development"]["tuning_data_partition"] for x in studies if x["task_group"]=="CLS")),
         "tuning_selection_status":dict(Counter(x["algorithm_development"]["tuning_selection_status"] for x in studies if x["task_group"]=="CLS")),
         "ml_statistical_relationship":dict(Counter(x["ml_statistical_relationship"] for x in studies if x["task_group"]=="CLS")),
         "nonclassification_support":dict(Counter(x["task_appropriate_evidence"]["level"] for x in studies if "task_appropriate_evidence" in x)),
         "importance_stability_methods":dict(Counter(v for x in studies if x["task_group"]=="CLS" for v in x["importance_stability_methods"])),
         "studies":studies}
    OUT.write_text(json.dumps(agg,ensure_ascii=False,indent=2)+"\n")
    merged=[json.loads(p.read_text()) for p in sorted(FINAL.glob("KHM*_final.json"))]
    (ROOT/"data/protocol_v1_2/KNHANES_studies_v1.2.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in merged))
    print(json.dumps({k:v for k,v in agg.items() if k!="studies"},ensure_ascii=False,indent=2))
    assert len(studies)==json.loads((ROOT/"results/derived/final_selection_flow.json").read_text())["flow"]["unique_full_report_studies_included"]  # prompt 106 (250) + review-loop inclusions 2026-10-24

if __name__=="__main__": main()
