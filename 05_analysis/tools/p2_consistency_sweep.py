#!/usr/bin/env python3
"""Flag P2 answers that conflict with REVIEWER_GUIDE §3 rules added during the run.

    python tools/p2_consistency_sweep.py            # all answer files
    python tools/p2_consistency_sweep.py KHM001 ...  # selected studies

Reads only P2_work/answers/*.json (P2 data). Writes P2_work/CONSISTENCY_SWEEP.json.
Each flag is a candidate for re-review, not an automatic correction.
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/protocol_v1_2/P2_work"
THRESHOLD_METRICS = {"ACC", "BACC", "SENS", "SPEC", "PPV", "NPV", "F1", "MCC", "KAPPA"}
REGRESSION_METRICS = {"RMSE", "MSE", "MAE", "R2"}


def rows(a, iid):
    r = a.get("items", {}).get(iid) or []
    return [r] if isinstance(r, dict) else r


def val(a, iid, uid=None):
    for r in rows(a, iid):
        if uid is None or r.get("unit_id") == uid:
            return r.get("value")
    return None


def sweep(a):
    sid = a.get("study_id")
    flags = []
    def flag(rule, item, unit, detail):
        flags.append({"study_id": sid, "rule": rule, "item": item, "unit": unit, "detail": detail})
    units = a.get("units") or {}
    models = {m["model_id"]: m for m in units.get("models", [])}
    evals = {e["evaluation_id"]: e for e in units.get("evaluations", [])}
    metrics = a.get("performance_metrics") or []

    # 1. VI09 only with VI01=USED and VI10=USED
    for r in rows(a, "VI09"):
        u = r.get("unit_id")
        if r.get("value") != "NA" and not (val(a, "VI01", u) == "USED" and val(a, "VI10", u) == "USED"):
            flag("VI09_requires_VI01_VI10_USED", "VI09", u, f"VI09={r.get('value')} VI01={val(a,'VI01',u)} VI10={val(a,'VI10',u)}")

    # 1b. VI11–VI15 only when VI01=USED
    for iid in ("VI11", "VI12", "VI13", "VI14", "VI15"):
        for r in rows(a, iid):
            u = r.get("unit_id")
            if r.get("value") not in (None, "NA") and val(a, "VI01", u) != "USED":
                flag("VI11_15_require_VI01_USED", iid, u, f"{iid}={r.get('value')} VI01={val(a, 'VI01', u)}")

    # 2. VI on FINAL row naming another model
    for r in rows(a, "VI03"):
        u = r.get("unit_id"); m = models.get(u)
        if m and m.get("role") == "FINAL" and val(a, "VI01", u) == "USED":
            label = str(m.get("label", "")).lower()
            v = str(r.get("value", "")).lower()
            if label and v not in ("na", "nr") and not any(tok in v for tok in re.findall(r"[a-z0-9\-\+]{3,}", label)):
                flag("VI_on_nonFINAL_model_row", "VI03", u, f"FINAL label '{m.get('label')}' vs interpreted '{r.get('value')}'")

    # 3. regression metric codes on non-continuous outcomes
    scale = {r.get("unit_id"): r.get("value") for r in rows(a, "OUT09")}
    for m in metrics:
        if m.get("metric") in REGRESSION_METRICS:
            e = evals.get(m.get("evaluation_id"), {})
            if scale.get(e.get("outcome_id")) != "CONTINUOUS":
                flag("regression_metric_on_classification", "performance_metrics", m.get("metric_id"), f"{m.get('metric')} on {scale.get(e.get('outcome_id'))}")

    # 4. resampling items on external/temporal or tuning-only evaluations
    for eid in evals:
        methods = val(a, "VAL02", eid) or []
        methods = methods if isinstance(methods, list) else [methods]
        external_only = methods and set(methods) <= {"EXTERNAL", "TEMPORAL"}
        for iid in ("VAL04", "VAL05", "VAL06", "PE_A5"):
            v = val(a, iid, eid)
            if external_only and v not in (None, "NA"):
                flag("resampling_item_on_external_eval", iid, eid, f"VAL02={methods} {iid}={v}")
        reps = val(a, "VAL05", eid)
        repeated_splits = "OTHER" in methods and isinstance(reps, int) and reps > 1
        if not ({"CV", "BOOT"} & set(methods)) and not repeated_splits:
            for iid in ("VAL06", "PE_A5"):
                v = val(a, iid, eid)
                if v not in (None, "NA"):
                    flag("VAL06_PE_A5_without_resampled_estimate", iid, eid, f"VAL02={methods} {iid}={v}")

    # 4b. apparent-only evaluations: PRE13/IMB03 BEFORE, split items NA
    for eid, e in evals.items():
        methods = val(a, "VAL02", eid) or []
        methods = methods if isinstance(methods, list) else [methods]
        if methods == ["APPARENT"]:
            for iid in ("VAL03", "VAL04", "VAL05", "VAL06", "VAL13", "VAL14"):
                v = val(a, iid, eid)
                if v not in (None, "NA"):
                    flag("apparent_only_split_items_should_be_NA", iid, eid, f"{iid}={v}")
            dev_units = [d["development_id"] for d in units.get("developments", [])
                         if d.get("model_id") == e.get("model_id")]
            for u in dev_units:
                v = val(a, "PRE13", u)
                if v not in (None, "NA", "BEFORE"):
                    flag("apparent_only_PRE13_should_be_BEFORE", "PRE13", u, f"PRE13={v}")

    # 4c. MET_SD NA without resampling; PE_A3 NA without imbalance intervention
    for eid in evals:
        methods = val(a, "VAL02", eid) or []
        methods = methods if isinstance(methods, list) else [methods]
        reps = val(a, "VAL05", eid)
        resampled = bool({"CV", "BOOT"} & set(methods)) or (isinstance(reps, int) and reps > 1)
        v = val(a, "MET_SD", eid)
        if not resampled and v == "NA":
            flag("MET_SD_without_resampling_should_be_N", "MET_SD", eid, f"VAL02={methods} MET_SD=NA")
    imb = {r.get("unit_id"): r.get("value") for r in rows(a, "IMB01")}
    no_imb = imb and all(x in ("NONE", "NR", "NA") for x in imb.values())
    if no_imb:
        for r in rows(a, "PE_A3"):
            if r.get("value") not in (None, "NA"):
                flag("PE_A3_without_imbalance_intervention_should_be_NA", "PE_A3", r.get("unit_id"), f"IMB01={sorted(set(imb.values()))} PE_A3={r.get('value')}")

    # 5. threshold items when no threshold-dependent metric was reported
    for eid in evals:
        has_thr = any(m.get("evaluation_id") == eid and (m.get("metric") in THRESHOLD_METRICS or m.get("metric") == "OTHER"
                                                         or m.get("summary_type") == "hard_label_auc") for m in metrics)
        if not has_thr:
            for iid in ("THR01", "THR02", "THR03"):
                v = val(a, iid, eid)
                if v not in (None, "NA"):
                    flag("threshold_items_without_threshold_metrics", iid, eid, f"{iid}={v}")

    # 5b. POP10 = 0 means "no earlier flow step reported" -> should be NR
    for r in rows(a, "POP10"):
        if r.get("value") == 0:
            flag("POP10_zero_should_be_NR", "POP10", r.get("unit_id"), "POP10=0 (no reported exclusions -> NR)")

    # 6. proportions in 0-1
    for iid in ("POP14", "VAL12"):
        for r in rows(a, iid):
            v = r.get("value")
            if isinstance(v, (int, float)) and v > 1:
                flag("proportion_not_0_1", iid, r.get("unit_id"), f"{iid}={v}")

    # 7. more than one FINAL model per outcome+dataset (allowed only for exact ties)
    finals = defaultdict(list)
    for d in units.get("developments", []):
        if models.get(d.get("model_id"), {}).get("role") == "FINAL":
            finals[(d.get("outcome_id"), d.get("dataset_id"))].append(d.get("model_id"))
    tie_codes = {"TIE", "TIE_AT_REPORTED_PRECISION", "POSSIBLE_TIE"}
    tied = any(str(b.get("tie_status")) in tie_codes for b in (a.get("best_model_selections") or []))
    for k, v in finals.items():
        if len(set(v)) > 1 and not tied:
            flag("multiple_FINAL_same_outcome_dataset", "MOD05", ",".join(k), f"FINAL models {sorted(set(v))} (check exact tie)")

    # 8. conditional-NA items with values
    for iid in ("ELG06", "ELG07", "FAM10"):
        for r in rows(a, iid):
            if r.get("value") not in (None, "NA"):
                flag("check_conditional_item", iid, r.get("unit_id"), f"{iid}={r.get('value')}")

    # 9a. released interface without access route
    for r in rows(a, "MOD17"):
        if r.get("value") == "USED" and not re.search(r"https?://|www\.|app\s*store|google\s*play|github|repositor|\.com|\.org|\.kr", str(r.get("rationale")), re.I):
            flag("interface_USED_without_access_route", "MOD17", r.get("unit_id"), "MOD17=USED but rationale names no URL/app store/repository")

    # 9. printed nomogram coded as interface
    for r in rows(a, "MOD17"):
        if r.get("value") == "USED" and re.search(r"nomogram|points?\s*chart|score\s*chart", str(r.get("rationale")), re.I):
            flag("printed_nomogram_as_interface", "MOD17", r.get("unit_id"), "MOD17=USED with nomogram rationale")

    # 10. survey items: silent paper -> NR; NOT_USED needs explicit evidence
    for iid in ("SUR04", "SUR05", "SUR06", "SUR07", "SUR08", "SUR09", "SUR10", "SUR11"):
        for r in rows(a, iid):
            if r.get("value") == "NOT_USED" and not r.get("evidence_ids"):
                flag("SUR_NOT_USED_without_explicit_evidence", iid, sid, f"{iid}=NOT_USED without evidence (silent paper -> NR)")

    if (val(a, "DAT07") == 1 or val(a, "DAT10") == "SEPARATE") and val(a, "SUR11") not in (None, "NA"):
        flag("SUR11_single_or_unpooled_years_should_be_NA", "SUR11", sid,
             f"DAT07={val(a, 'DAT07')} DAT10={val(a, 'DAT10')} SUR11={val(a, 'SUR11')}")

    for r in rows(a, "MET_PAIR"):
        if r.get("value") == "Y":
            u = r.get("unit_id")
            method = " ".join(str(x.get("value") or "") + " " + str(x.get("rationale") or "") for x in rows(a, "MET_PAIR_M") if x.get("unit_id") == u)
            text = method + " " + str(r.get("rationale") or "")
            if not re.search(r"DeLong|McNemar|paired|permutation|Wilcoxon|t[- ]?test|bootstrap.{0,30}(test|differ|compar)|p\s*[<=>]", text, re.I):
                flag("MET_PAIR_Y_without_formal_paired_test", "MET_PAIR", u, "MET_PAIR=Y but no formal paired test named")

    for r in rows(a, "MOD12"):
        rat = r.get("rationale") or ""
        if (r.get("value") in ("NR", "NOT_USED") and re.search(r"early[\s-]*stop", rat, re.I)
                and not re.search(r"(no|without|not\s+(?:use|mention|report)\w*)\s+(?:\w+\s+){0,3}early[\s-]*stop", rat, re.I)):
            flag("early_stopping_should_be_MOD12_USED", "MOD12", r.get("unit_id"), f"MOD12={r.get('value')} with early stopping in rationale")

    for eid in evals:
        methods = val(a, "VAL02", eid) or []
        methods = methods if isinstance(methods, list) else [methods]
        if "CV" in methods and not ({"OTHER", "BOOT"} & set(methods)) and val(a, "VAL05", eid) == 1:
            flag("check_VAL05_1_for_unrepeated_CV_should_be_NR", "VAL05", eid, f"VAL02={methods} VAL05=1 (NR unless a single run is stated)")

    if len(units.get("outcomes", [])) > 5:
        flag("check_parallel_outcomes_MULTIBIN", "OUT09", sid, f"{len(units.get('outcomes', []))} Outcome units (identical pipeline >5 -> one MULTIBIN outcome)")

    if val(a, "SUR12") == "NOT_REQUIRED" and val(a, "SUR14") not in (None, "NA"):
        flag("SUR14_should_be_NA_when_SUR12_NOT_REQUIRED", "SUR14", sid, f"SUR12=NOT_REQUIRED SUR14={val(a, 'SUR14')}")

    for r in rows(a, "VAL02"):
        v = r.get("value"); v = v if isinstance(v, list) else [v]
        if "NONE_NR" in v:
            flag("check_VAL02_NONE_NR_stated_test_portion_is_SPLIT", "VAL02", r.get("unit_id"), f"VAL02={v}")

    for iid in ("MOD15", "MOD17", "MOD18"):
        for r in rows(a, iid):
            if r.get("value") == "NR":
                flag("released_artefact_silent_should_be_NOT_USED", iid, r.get("unit_id"), f"{iid}=NR")

    # 11b. PRE05 NA when missing data handled by complete-case deletion only
    for r in rows(a, "PRE05"):
        u = r.get("unit_id")
        allm = val(a, "PRE02", u) or []
        allm = allm if isinstance(allm, list) else [allm]
        if set(allm) <= {"COMPLETE", "NONE"} and allm and r.get("value") not in ("NA",):
            flag("PRE05_complete_case_only_should_be_NA", "PRE05", u, f"PRE02={allm} PRE05={r.get('value')}")

    # 11. TSK07=Y needs two ML tasks
    if val(a, "TSK07") == "Y":
        flag("check_TSK07_two_ML_tasks", "TSK07", sid, str(rows(a, "TSK08")[0].get("value") if rows(a, "TSK08") else ""))
    return flags


def main():
    sel = [s for s in sys.argv[1:] if re.fullmatch(r"KHM\d{3}", s)]
    files = [WORK / "answers" / f"{s}.json" for s in sel] if sel else sorted((WORK / "answers").glob("KHM*.json"))
    flags = []
    for f in files:
        flags.extend(sweep(json.loads(f.read_text())))
    by_rule = defaultdict(list)
    for fl in flags:
        by_rule[fl["rule"]].append(fl["study_id"])
    out = {"studies_checked": len(files), "flags": len(flags),
           "by_rule": {k: sorted(set(v)) for k, v in sorted(by_rule.items())}, "details": flags}
    (WORK / "CONSISTENCY_SWEEP.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("studies_checked", "flags", "by_rule")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
