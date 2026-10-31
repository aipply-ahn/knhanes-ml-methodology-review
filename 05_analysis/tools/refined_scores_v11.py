"""v11 (author 2026-10-25): refined KNHANES sub-item scores within TRIPOD+AI-aligned domains, per core study.
Coarse judgement = the TRIPOD+AI-derived element (Reported / Partly reported / Not reported). Refined score = % of the
applicable KNHANES sub-items reported. Source: Additional Data 1 (core rows) and protocol OUT11/OUT12 for the cut-off.
Writes results/derived/refined_scores_v11.json."""
import json, sys
from pathlib import Path
import openpyxl
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import make_streamlined_figures as ms, claim_evidence_analysis as ce

wb = openpyxl.load_workbook(ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx", read_only=True)
ws = wb[wb.sheetnames[0]]; it = ws.iter_rows(values_only=True); hdr = next(it)
rows = [dict(zip(hdr, r)) for r in it if r and r[8] == "Core classification"]
cut = {d["study_id"]: ms.first(d, "OUT12") not in ("NR", "UNEXPLAINED") for d in ce.CORE}
cat = {d["study_id"]: ms.first(d, "OUT11") == "Y" for d in ce.CORE}
Y = lambda col: (lambda r: r[col] == "Yes")
ALL = lambda r: True
# (key, TRIPOD+AI column, [(sub-item key, met, applicable)])
DOMAINS = [
 ("data", "Reporting 04: Data source, design, and dates", [
   ("years_combination_stated", lambda r: r["Combining survey years"] != "Unclear", ALL),
   ("weights_mentioned", Y("KNHANES sampling weights mentioned"), ALL),
   ("weights_fitting", Y("Weights in model fitting"), ALL),
   ("weights_evaluation", Y("Weights in performance evaluation"), ALL),
   ("strata_psu", Y("Strata or PSUs in variance estimation"), ALL),
   ("combined_year_weights", Y("Combined-year weights"), lambda r: r["Combined-year weights"] != "Not applicable")]),
 ("outcome", "Reporting 06: Outcome definition, timing, and source", [
   ("source_reported", lambda r: r["Outcome source"] != "Not reported", ALL),
   ("timing_clear", lambda r: not str(r["Outcome timing"]).startswith("Timing unclear"), ALL),
   ("rebuildable", Y("Outcome rebuildable from the report"), ALL),
   ("cutoff_basis", lambda r: cut[r["Study ID"]], lambda r: cat[r["Study ID"]])]),
 ("predictors", "Reporting 07: Predictor definition and timing", [
   ("candidate_count", lambda r: r["Initial candidate predictors"] != "Not reported", ALL),
   ("set_rebuildable", Y("Predictor set rebuildable from the report"), ALL),
   ("selection_within_training", lambda r: r["Supervised feature selection timing"] == "Within the training data",
    lambda r: r["Supervised feature selection timing"] != "Not applied")]),
 ("missing", "Reporting 10: Missing-data handling", [
   ("method_reported", lambda r: r["Missing-value handling"] != "Not reported", ALL),
   ("within_training", lambda r: r["Missing-value handling timing"] == "Within the training data", lambda r: r["Missing-value handling timing"] != "Not applied")]),
 ("development", "Reporting 11: Preprocessing, selection, and model development", [
   ("all_preprocessing_within_training", lambda r: str(r["Preprocessing over all applied steps"]).startswith("All within"),
    lambda r: r["Preprocessing over all applied steps"] != "No data-dependent step"),
   ("rebalancing_within_training", lambda r: r["Class rebalancing timing"] == "Within the training data",
    lambda r: not str(r["Class rebalancing timing"]).startswith("No active")),
   ("several_algorithms", Y("Several algorithms compared"), ALL),
   ("final_model_specified", Y("Final model fully specified"), ALL),
   ("code_shared", Y("Analysis code shared"), ALL)]),
 ("tuning_validation", "Reporting 12: Hyperparameters and tuning", [
   ("systematic_search", Y("Systematic hyperparameter search"), ALL),
   ("tuning_apart", Y("Tuning kept apart from the final evaluation"), ALL),
   ("split_or_cv", lambda r: r["Train-test split"] == "Yes" or r["Cross-validation"] == "Yes", ALL),
   ("beyond_development", lambda r: r["Validation on a later survey period"] == "Yes" or r["Validation on external data"] == "Yes", ALL)]),
 ("performance", "Reporting 16: Performance estimates and uncertainty", [
   ("auroc", Y("AUROC reported"), ALL), ("confidence_interval", Y("Confidence interval reported"), ALL),
   ("calibration", Y("Calibration reported"), ALL), ("threshold_reported", Y("Decision threshold reported"), ALL),
   ("threshold_without_test", Y("Threshold chosen without the final evaluation data"), lambda r: r["Decision threshold reported"] == "Yes")]),
]
out = {"domains": [], "studies": {}}
for key, col, subs in DOMAINS:
    out["domains"].append({"key": key, "tripod_column": col, "subitems": [s[0] for s in subs]})
for r in rows:
    sid = r["Study ID"]; rec = {}
    for key, col, subs in DOMAINS:
        app = [s for s in subs if s[2](r)]
        met = [s[0] for s in app if s[1](r)]
        rec[key] = {"tripod": r[col], "applicable": len(app), "met": met, "score": round(100 * len(met) / len(app), 1)}
    rec["tripod_complete_19"] = sum(r[f] == "Reported" for f in hdr if str(f).startswith("Reporting "))
    out["studies"][sid] = rec
json.dump(out, open(ROOT / "results/derived/refined_scores_v11.json", "w"), indent=1)
if __name__ == "__main__":
    import statistics as st
    for key, col, subs in DOMAINS:
        for lev in ("Not reported", "Partly reported", "Reported"):
            v = [s[key]["score"] for s in out["studies"].values() if s[key]["tripod"] == lev]
            if v: print(key, lev, len(v), "median", st.median(v), "range", min(v), max(v), "distinct", len(set(v)))
