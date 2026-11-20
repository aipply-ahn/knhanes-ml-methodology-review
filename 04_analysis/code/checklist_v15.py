"""v15 core checklist (author 2026-10-28): every core item (RC01-RC45) is judged for all 193 core studies, so the
checklist, Additional Data 1 and Figure 5 are aligned (no uncoded item). Items are single reporting requirements judged
met (1), not met (0) or not applicable (NA). Source per item: 'E' = derived from the existing coded data with the rule
below; 'N' = read from the full text in the v15 recoding (prompts/implementation_records/v15_recode, guide
CODING_GUIDE.md). Run: python tools/checklist_v15.py -> results/derived/checklist_v15_scores.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from checklist_v12 import TRIPOD, NRSET, _ctx  # noqa: E402

STAGE = {"D": ("", "Data"), "M": ("", "Model"), "I": ("", "Importance"), "R": ("", "Reporting")}
TYPE = {"R": ("", "Specified"), "RS": ("", "Specified (KNHANES)"), "N": ("", "New"), "NS": ("", "New (KNHANES)")}
GROUPS = {"importance": ("", "Variable importance"), "after": ("", "Analyses after the ranking")}
RECODE = ROOT / "prompts/implementation_records/v15_recode"


def items(ms):
    f = lambda d, k: ms.first(d, k)

    def ok(v):
        if isinstance(v, list):
            return any(ok(x) for x in v)
        return v not in NRSET and not str(v).startswith(("Not reported", "NR"))
    rep = lambda *ks: (lambda d, r: all(ok(f(d, k)) for k in ks))
    num = lambda x: str(x).replace(".", "", 1).isdigit()
    ALL = lambda d, r: True
    multi = lambda d, r: r["Combining survey years"] in ("Several cycles", "Several years of one cycle")
    rank = lambda d, r: r["Importance ranking produced"] == "Yes"
    N = None  # read from the full text
    # (id, element, item ko, en, criterion ko, en, stage, type, source, met, app)
    return [
     ("RC01", 3, "", "Population the results describe", "", "States whom the results describe (analytic sample or target population)", "R", "RS", "E", rep("SUR02"), ALL),
     ("RC02", 4, "", "Survey years analysed", "", "The exact survey years (cycles) analysed can be identified", "D", "RS", "E", lambda d, r: f(d, "DAT18") == "R", ALL),
     ("RC03", 4, "", "Survey components", "", "States the survey components used (interview, examination, laboratory, nutrition)", "D", "RS", "E", rep("DAT14"), ALL),
     ("RC04", 4, "", "Raw data files", "", "Identifies the raw data files or release used", "D", "RS", "N", N, ALL),
     ("RC05", 4, "", "Combining years and harmonising variables", "", "Reports how years were combined and how variables that changed across years were made comparable", "D", "RS", "N", N, multi),
     ("RC06", 4, "", "Choice of survey weights", "", "States whether weights were used and which weight, or why not", "D", "RS", "N", N, ALL),
     ("RC07", 4, "", "Combined-year survey weights", "", "When weights were used with combined years, reports how they were adjusted", "D", "RS", "E", lambda d, r: f(d, "DAT11") == "R", lambda d, r: multi(d, r) and f(d, "DAT11") != "NA" and f(d, "SUR04") == "USED"),
     ("RC08", 5, "", "Inclusion and exclusion conditions", "", "Reports the inclusion and exclusion conditions of the analytic sample, such as age and sex", "D", "R", "E", lambda d, r: (num(f(d, "POP03")) or num(f(d, "POP04"))) and ok(f(d, "POP06")), ALL),
     ("RC09", 5, "", "Sample-selection steps", "", "Reports the selection steps and the sample size at each step", "D", "R", "E", rep("POP11"), ALL),
     ("RC10", 6, "", "Rebuilding the outcome", "", "Reports the raw variables and codes and the derivation and categorisation rule of the outcome", "D", "R", "E", lambda d, r: f(d, "OUT16") == "R2" and ok(f(d, "OUT08")), ALL),
     ("RC11", 6, "", "Timing of the outcome", "", "Whether the outcome was measured in the same survey as the predictors can be determined", "D", "RS", "E", lambda d, r: f(d, "OUT10") != "UNC", ALL),
     ("RC12", 6, "", "Outcome-predictor overlap", "", "Reports whether variables defining the outcome were among the predictors and how this was handled", "D", "RS", "N", N, ALL),
     ("RC13", 8, "", "Outcome distribution", "", "Reports the number and proportion in each outcome class", "D", "R", "E", rep("POP12", "POP14"), ALL),
     ("RC14", 7, "", "Final input variables and coding", "", "Reports the predictors entered into the model and their coding", "D", "R", "E", lambda d, r: f(d, "PRD13") == "R2", ALL),
     ("RC15", 7, "", "Variable selection process", "", "Reports the number of candidate and final predictors", "D", "R", "E", rep("PRD02", "PRD04"), ALL),
     ("RC16", 7, "", "Derived predictors", "", "Reports derivation rules (formulas, cut-offs, categories) for derived predictors", "D", "R", "N", N, ALL),
     ("RC17", 10, "", "Amount of missingness", "", "Reports the amount of missingness by variable", "D", "R", "E", rep("PRE04"), ALL),
     ("RC18", 10, "", "Missing-value rules", "", "Reports the handling or imputation method and variable-specific rules", "D", "R", "E", rep("PRE01", "PRE03"), ALL),
     ("RC19", 10, "", "Special response codes", "", "Reports the handling of special response codes (such as not applicable or don't know)", "D", "RS", "N", N, ALL),
     ("RC20", 11, "", "Timing of preprocessing", "", "Whether each data-dependent preprocessing step was done before or after the split can be determined", "M", "R", "E",
      lambda d, r: r["Preprocessing over all applied steps"] != "Timing unclear", lambda d, r: r["Preprocessing over all applied steps"] != "No data-dependent step"),
     ("RC21", 11, "", "Class rebalancing", "", "Reports the rebalancing method and when it was applied", "M", "R", "E", lambda d, r: f(d, "IMB03") not in ("ORDER_NR", "NA", "NR", "UNC"), lambda d, r: f(d, "IMB01") != "NONE"),
     ("RC22", 11, "", "Algorithms and software", "", "Reports the algorithms fitted and the software and packages", "M", "R", "E", rep("MOD02", "MOD09"), ALL),
     ("RC23", 11, "", "Pipeline order", "", "Reports the order of preprocessing and training steps so it can be repeated", "M", "R", "N", N, ALL),
     ("RC24", 11, "", "Survey weights in model fitting", "", "States whether weights were used in model fitting and how, or why not", "M", "RS", "N", N, ALL),
     ("RC25", 12, "", "Tuning procedure", "", "Reports the tuning method and search space", "M", "R", "E", rep("MOD07", "MOD08"), lambda d, r: f(d, "MOD12") == "USED"),
     ("RC26", 12, "", "Tuning kept apart from evaluation", "", "Whether the final evaluation data were used for model choice or tuning can be determined", "M", "R", "E",
      lambda d, r: r["Tuning kept apart from the final evaluation"] != "Not reported", ALL),
     ("RC27", 12, "", "Final hyperparameters", "", "Reports the hyperparameter values of the final model", "M", "R", "E", rep("MOD06"), ALL),
     ("RC28", 13, "", "Internal-validation design", "", "Reports the split proportions or the number of cross-validation folds", "M", "R", "E",
      lambda d, r: ms.has(d, "VAL02", {"SPLIT", "CV"}) and (ok(f(d, "VAL04")) if ms.has(d, "VAL02", {"CV"}) else True) and (ok(f(d, "VAL03")) if ms.has(d, "VAL02", {"SPLIT"}) else True), ALL),
     ("RC29", 13, "", "Reproducible split", "", "Reports the random seed or the split indices", "M", "R", "E", rep("MOD10"), ALL),
     ("RC30", 14, "", "Performance measures", "", "Reports discrimination measures (such as AUROC) and the data on which they were calculated", "M", "R", "E", lambda d, r: r["AUROC reported"] == "Yes", ALL),
     ("RC31", 14, "", "Decision threshold", "", "When threshold-based measures are reported, reports the threshold and how it was chosen", "M", "R", "E", rep("THR01"), lambda d, r: r["Decision threshold reported"] == "Yes"),
     ("RC32", 14, "", "Survey weights in performance evaluation", "", "States whether performance measures were weighted and how, or why not", "M", "RS", "N", N, ALL),
     ("RC33", 16, "", "Uncertainty of performance", "", "Reports confidence intervals or resampling distributions", "R", "R", "E", lambda d, r: r["Confidence interval reported"] == "Yes", ALL),
     ("RC34", 16, "", "Strata and PSUs", "", "Reports whether and how strata and PSUs were used for design-based uncertainty", "M", "RS", "E", lambda d, r: r["Strata or PSUs in variance estimation"] in ("Yes", "No"), ALL),
     ("RC35", 17, "", "Final model specification", "", "Specifies the final model fully enough to apply it to new data", "M", "R", "E", lambda d, r: f(d, "MOD14") == "USED", ALL),
     ("RC36", 19, "", "Code availability", "", "Analysis code is available", "M", "R", "E", lambda d, r: f(d, "MOD15") == "USED", ALL),
     ("RC37", 14, "", "Calibration", "", "Reports calibration of predicted probabilities", "R", "R", "E", lambda d, r: r["Calibration reported"] == "Yes", ALL),
     ("RC38", 18, "", "Sensitivity to weighting", "", "Reports results with and without weights, or why not", "R", "RS", "N", N, ALL),
     ("RC39", "importance", "", "Importance method and object", "", "Reports the importance method and the model and data partition used", "I", "N", "E", rep("VI02", "VI04"), rank),
     ("RC40", "importance", "", "Importance settings", "", "Reports the settings needed to recompute importance (such as the SHAP explainer and background data)", "I", "N", "N", N, rank),
     ("RC41", "importance", "", "Ranking rule", "", "Reports the full ranking or the rule used to choose the top variables", "I", "N", "E", rep("VI08"), rank),
     ("RC42", "importance", "", "Survey weights in importance aggregation", "", "States whether weights were used when aggregating importance", "I", "NS", "N", N, rank),
     ("RC43", "importance", "", "Ranking stability", "", "Checks ranking stability across resamples, survey cycles or subgroups", "R", "NS", "E", lambda d, r: r["Ranking stability checked"] == "Yes", rank),
     ("RC44", "importance", "", "Scope of interpretation", "", "States that the ranking describes model behaviour, not causal effects or population associations", "R", "N", "N", N, rank),
     ("RC45", "after", "", "Rule after the ranking", "", "Reports the rule for carrying variables forward and the data used for that selection", "R", "N", "N", N,
      lambda d, r: ms.has(d, "VI10", {"USED"}) or ms.has(d, "VI11", {"USED"})),
    ]


GUIDE_ID = {"RC04": "RC04", "RC05": "RC05", "RC06": "RC06", "RC12": "RC12", "RC16": "RC16", "RC19": "RC19", "RC23": "RC23",
            "RC24": "RC24", "RC32": "RC32", "RC38": "RC39", "RC40": "RC41", "RC42": "RC43", "RC44": "RC45", "RC45": "RC46"}


def recoded():
    out = {}
    for p in sorted(RECODE.glob("batch_*_output.json")):
        for rec in json.load(open(p)):
            out[rec["study_id"]] = rec
    ov = RECODE / "review_overrides.json"  # author-side review of the full-text judgements (criterion applied strictly)
    for sid, items in (json.load(open(ov)).items() if ov.exists() else []):
        for k, v in items.items():
            out[sid][k] = {"v": v["v"], "e": out[sid][k]["e"] + " [review: " + v["why"] + "]"}
    return out


if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = items(ms); R = recoded()
    missing = [d["study_id"] for d in CORE if d["study_id"] not in R]
    out = {"items": [], "studies": {}, "missing_recode": missing}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "id": it[0], "tripod": it[1], "item_en": it[3], "item_ko": it[2], "stage": it[6], "note": it[7],
                             "source": it[8], "repro": it[6] in ("D", "M", "I"), "scored": True})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}; ev = {}
        for k, it in enumerate(I):
            if it[8] == "E":
                if it[10](d, r):
                    rec[str(k)] = bool(it[9](d, r))
            else:
                g = R.get(sid, {}).get(GUIDE_ID[it[0]])
                if g is None:
                    continue
                v = g.get("v")
                if v in ("NA", None) or not it[10](d, r):
                    continue
                rec[str(k)] = int(v) == 1; ev[it[0]] = g.get("e", "")
        tri = {str(i): r[[h for h in r if str(h).startswith(f"Reporting {i:02d}:")][0]] for i in range(1, 20)}
        out["studies"][sid] = {"items": rec, "tripod": tri, "evidence": ev}
    json.dump(out, open(ROOT / "results/derived/checklist_v15_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    print("missing recode", len(missing))
    for k, it in enumerate(I):
        v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
        print(it[0], it[8], it[3][:40], f"{sum(v)}/{len(v)}")
