#!/usr/bin/env python3
"""Prompt 105 (review v43): re-screen under criterion A, recorded with its evidence; the manuscript is not changed yet.

Criterion A (author direction, v43):
  1. Scope: supervised analysis -- a model fitted to classify or estimate a designated outcome from predictors
     (judged from the reported procedure, not from stated purposes).
  2. Algorithm: a learner outside the regression family. Regression family = analyst-specified equation with estimated
     coefficients, with or without a penalty (linear, logistic, Poisson, Cox, GLM, LASSO, ridge, elastic net).
     Outside it: single decision trees (CART, CHAID, C4.5, QUEST), tree ensembles, boosting, SVM, kNN, naive Bayes,
     Bayesian-network classifiers/structure learning, neural networks, AutoML, LLMs.
Precedent checked in the original text: Christodoulou et al., J Clin Epidemiol 2019;110:12-22 (doi:10.1016/j.jclinepi.2019.02.004)
classified penalised regression (LASSO, elastic net) with regression ("these methods do not belong to ML using the
'automatic learning from data' definition") and classification trees with ML.

Inputs: results/derived/verdicts.json, screen.json, references/md full texts (decisions below were read from them).
Output: results/derived/criterion_a_rescreen.json (new file; nothing existing is overwritten).
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "results/derived"

# Reports catalogued ML-adjacent (or excluded) that fitted a single decision tree to a designated outcome in KNHANES data.
# basis: what the full text (references/md) states; flag: note for extraction.
NEW_INCLUDE = {
    "10.5720/kjcn.2014.19.5.468": ("CHAID classification tree for fruit and vegetable intake (stroke history)", ""),
    "10.7586/jkbns.25.091": ("decision tree (CART) for sarcopenia risk groups", ""),
    "kci:ART002307924": ("CHAID decision tree for unmet dental care", ""),
    "10.3390/ijerph191610028": ("decision tree for suicidal ideation high-risk groups", ""),
    "10.4094/jkachn.2012.18.3.143": ("CART model for atopic dermatitis", ""),
    "kci:ART001273101": ("CHAID tree strata as auxiliary variable for item-nonresponse imputation (KNHANES 2001)", "method-focused (imputation)"),
    "10.7586/jkbns.2019.21.1.85": ("decision tree for blood-pressure control status", ""),
    "kci:ART003357464": ("decision tree for systolic/diastolic blood pressure", "continuous outcome"),
    "10.35133/kssche.20230228.04": ("decision tree for alcohol use disorder", ""),
    "10.4163/jnh.2023.56.3.300": ("CART prediction model for skipping breakfast", ""),
    "https://openalex.org/W3152568250": ("decision tree for poor glycaemic control", ""),
    "10.1249/01.mss.0000487993.14293.5a": ("decision tree model estimating body fat percentage", "continuous outcome"),
    "10.3746/jkfn.2023.52.8.864": ("decision tree for depression", ""),
    "10.5762/kais.2013.14.7.3368": ("CHAID decision tree for self-reported voice problems", ""),
    "10.5762/kais.2011.12.2.765": ("decision tree for diabetes management-behaviour groups (after k-means)", "outcome derived from clusters"),
    "kci:ART003173987": ("shallow decision tree then elastic net per node for obesity risk", "abstract only; full text to obtain"),
    "kci:ART003237221": ("decision tree for health-related quality of life (coronary artery disease)", "continuous outcome"),
    "10.17079/jkgn.2025.00073": ("decision tree prediction model for hearing loss", ""),
    "10.12972/nhs.2025.24.2.6": ("decision tree (CHAID/CART) for depression and anxiety risk groups", ""),
    "10.7586/jkbns.2018.20.2.103": ("decision tree for sleep problems in cancer survivors", "same report as included KHM072 (Korean title; linkage, prompt 106)"),
    "10.3390/jpm13040663": ("decision tree and random forest for ischaemic heart disease", "random forest: eligible under the old rule too"),
    "10.7586/jkbns.23.023": ("decision tree for quality of life in older adults", "continuous outcome"),
    "10.1111/phn.12219": ("decision tree for suicidal ideation risk groups", ""),
    "10.11149/jkaoh.2023.47.1.26": ("decision tree for number of remaining teeth", "continuous outcome"),
    "kdca:382": ("decision tree for obesity/overweight high-risk groups (KNHANES 2005)", ""),
    "https://openalex.org/W3141385767": ("decision tree for suicide high-risk groups among depressed older adults", ""),
    "10.4258/hir.2015.21.3.167": ("CART rules with fuzzy logic for coronary heart disease", ""),
    "10.2196/16153": ("decision trees fitted to dry eye disease to cut continuous factors, then lasso and weighted logistic", "tree used for discretisation (as KHM053 uses CatBoost for selection)"),
    "10.7586/jkbns.23.0007": ("decision tree for poor lipid control", ""),
    "kci:ART002406200": ("C4.5 decision tree for diabetes, compared with RF, SVM, naive Bayes", "RF/SVM/NB: eligible under the old rule too"),
    "kci:ART002534138": ("CHAID decision tree for readmission in cardiovascular disease (KNHANES IV-VI)", ""),
    "10.17079/jkgn.2021.23.3.285": ("decision tree for quality of life in older women", "continuous outcome"),
    "10.1016/j.anr.2011.11.002": ("CART model for hypertension/CCVD comorbidity in diabetes", ""),
}
UNRESOLVED = {
    "https://openalex.org/W3026041766": "KCI tag 'decision tree'; local text is metadata only (766 characters); full text needed",
}
# Included studies that fail criterion A (study ID -> reason, from references/md full texts).
DROP = {
    "KHM156": "latent Dirichlet allocation topic model of diets; no designated outcome",
    "KHM073": "only logistic regression fitted ('machine learning-based logistic regression'); regression family",
    "KHM129": "WEKA attribute filters, classifier = logistic regression only; regression family",
}
# Included studies checked and kept (criterion A met), with the reason.
KEEP_CHECKED = {
    "KHM012": "Bayesian network with ASCVD risk as the outcome node",
    "KHM031": "Bayesian network modelling metabolic syndrome from its criteria",
    "KHM038": "Bayesian network predicting diabetes and dyslipidaemia",
    "KHM179": "causal Bayesian network prediction model for low bone mineral density",
    "KHM059": "clusters then a machine-learning classifier (SVM) assigning clusters and diabetes prediction",
    "KHM151": "XGBoost/random forest imputation of smoking responses (supervised)",
    "KHM222": "convolutional autoencoder imputing masked activity values (supervised target)",
    "KHM053": "CatBoost fitted to impaired fasting glucose (variables then used in a nomogram)",
}
PERIOD = lambda y: "<=2019" if y <= 2019 else "2020-2022" if y <= 2022 else "2023-2024" if y <= 2024 else "2025-2026"


def main():
    verdicts = json.loads((DER / "verdicts.json").read_text())
    verdicts = verdicts if isinstance(verdicts, dict) else {r["uid"]: r for r in verdicts}
    refs = json.loads((ROOT / "references/refs.json").read_text())
    refs = refs if isinstance(refs, list) else refs.get("records", [])
    by_uid = {r.get("uid"): r for r in refs}
    for u in list(NEW_INCLUDE) + list(UNRESOLVED):
        assert u in verdicts and verdicts[u]["verdict"] in ("INCLUDE_ADJACENT", "EXCLUDE"), u
    prev = Counter(verdicts[u]["verdict"] for u in NEW_INCLUDE)
    assert prev == {"INCLUDE_ADJACENT": 33}, prev
    years = {u: int(by_uid[u]["year"]) for u in NEW_INCLUDE}
    rows = [{"uid": u, "year": years[u], "period": PERIOD(years[u]), "title": by_uid[u].get("title"),
             "previous_verdict": verdicts[u]["verdict"], "basis": b, "note": n} for u, (b, n) in NEW_INCLUDE.items()]
    out = {
        "schema": "criterion_a_rescreen_v1", "date": "2026-09-28", "status": "screening decided; extraction pending",
        "criterion": __doc__.split("Inputs:")[0].strip(),
        "new_include": rows, "unresolved": UNRESOLVED, "drop_from_included": DROP, "kept_after_check": KEEP_CHECKED,
        "projection": {
            "included_before": 220, "added": len(NEW_INCLUDE), "dropped": len(DROP), "unresolved": len(UNRESOLVED),
            "included_after_before_family_linkage": 220 + len(NEW_INCLUDE) - len(DROP),
            "linked_to_included": {"10.7586/jkbns.2018.20.2.103": "KHM072"},  # prompt 106 family linkage
            "included_after_linkage": 220 + len(NEW_INCLUDE) - 1 - len(DROP),
            "added_by_period": dict(sorted(Counter(r["period"] for r in rows).items())),
            "added_continuous_outcome": sum("continuous outcome" in r["note"] for r in rows),
            "old_rule_errors": sum("old rule too" in r["note"] for r in rows),
        },
        "remaining_steps": [
            "family linkage of the 33 against the 245 included reports",
            "full-text extraction (P1, P2, consensus) of the new studies with the v1.2 protocol",
            "obtain full texts for kci:ART003173987 and openalex W3026041766",
            "recompute every count, period denominator, figure and table; replace Methods, Figure 1 and Limitations text",
        ],
    }
    (DER / "criterion_a_rescreen.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out["projection"], ensure_ascii=False))


if __name__ == "__main__":
    main()
