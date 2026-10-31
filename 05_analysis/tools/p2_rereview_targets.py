#!/usr/bin/env python3
"""Build the end-of-run re-review target list for blinded P2.

    python tools/p2_rereview_targets.py

Combines (1) judgement-type flags from P2_work/CONSISTENCY_SWEEP.json, (2) rule-change
re-review cases recorded by the coordinator during the run (MANUAL below, mirrored in
handoff/보고_20260914_P2_수정요청코멘트.md), and (3) SUR04/08/09 mention candidates from
P2_work/SUR_MENTION_SCAN.json. Writes P2_work/REREVIEW_TARGETS.json (study -> items + reasons).
Reads only P2 data.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/protocol_v1_2/P2_work"

# sweep rules that are informational only (legitimate values are common) -> not re-reviewed automatically
SKIP_RULES = {"check_conditional_item"}

MANUAL = {
    # rules added after these studies finished (see comments file)
    "KHM007": [("FINAL/units", "rule-sensitive items from pilot batch (FINAL, resampling applicability, POP09/12-14)")],
    "KHM016": [("FINAL/units", "early-batch rule-sensitive items")],
    "KHM018": [("FINAL/units", "early-batch rule-sensitive items")],
    "KHM022": [("performance_metrics", "MSE on class labels should be OTHER")],
    "KHM023": [("VI01-VI18", "non-FINAL model interpretation recorded on FINAL row")],
    "KHM024": [("VI09", "VI09 filled although VI01=NOT_USED")],
    "KHM026": [("VI01-VI18", "non-FINAL model interpretation recorded on FINAL row")],
    "KHM032": [("VAL02", "different KNHANES year coded EXTERNAL; should be TEMPORAL")],
    "KHM067": [("POP08-POP10", "summed three KNHANES samples; use development sample")],
    "KHM071": [("MOD05/ELG06", "FINAL chosen by accuracy (majority-class SVM); default L2 LR is not ELG06")],
    "KHM073": [("ELG02", "only unpenalised LR -> ELG02=UNC")],
    "KHM075": [("MOD17", "calculator without access route"), ("SUR14", "SUR12=NOT_REQUIRED -> SUR14=NA")],
    "KHM076": [("PD_A2/PE_A1", "sample-size adequacy judged by justification instead of actual counts")],
    "KHM077": [("PD_A2/PE_A1", "sample-size adequacy judged by justification instead of actual counts")],
    "KHM078": [("PD_A2/PE_A1", "sample-size adequacy judged by justification instead of actual counts")],
    "KHM079": [("PD_A2/PE_A1", "sample-size adequacy"), ("Outcome units", "secondary modelled target (lean/non-lean MASLD) needs Outcome unit"), ("VI11", "feature-selection-guided inference belongs to PRE11")],
    "KHM081": [("PD_A2/PE_A1", "sample-size adequacy judged by justification instead of actual counts")],
    "KHM083": [("VI11", "Boruta-selected inference belongs to PRE11")],
    "KHM084": [("PD_A2/PE_A1", "sample-size adequacy (borderline)")],
    "KHM085": [("MOD15", "third-party toolkit is not own code")],
    "KHM087": [("PE_A7", "best model chosen on temporal test -> PN")],
    "KHM088": [("Evaluation units", "uplift models evaluated by AUUC need Model/Evaluation units")],
    "KHM089": [("POP09", "development sample 2007-2010, not whole 2007-2012")],
    "KHM101": [("VAL11", "post-upsampling leaf counts recorded as events")],
    "KHM102": [("units", "sensitivity refits recorded as separate Dataset/Development/Evaluation units")],
    "KHM106": [("OUT18", "undefined outcome -> NAU")],
    "KHM109": [("FUN_PROCESS", "SMOTE is not ML processing")],
    "KHM117": [("units", "pooled model + 13 yearly refits all coded as units; refits are subgroup metrics"), ("DAT15", "yearly KOSIS aggregate comparison is not linkage")],
    "KHM126": [("POP09/POP14", "down-sampled counts recorded"), ("units", "whole-sample re-application coded as E02")],
    "KHM135": [("Outcome units", "metabolic-syndrome component models coded as Outcome units")],
    "KHM138": [("MOD12/MOD13", "early stopping -> MOD12=USED")],
    "KHM159": [("SUR08", "check against reporting-item rule (description counts)")],
    "KHM160": [("Outcome units", "15 parallel binary outcomes -> one MULTIBIN outcome"), ("SUR04", "coded NR under withdrawn 'used in analysis' guidance")],
    "KHM161": [("VAL02", "split used only for ANN input selection should not be in VAL02")],
    "KHM162": [("SUR08", "coded NR under withdrawn 'used in analysis' guidance")],
    "KHM163": [("SUR04/SUR08/SUR09", "coded NR under withdrawn 'used in analysis' guidance")],
    "KHM166": [("PD_A2/PE_A1", "NI although n and prevalence make adequacy obvious")],
    "KHM187": [("MOD12/MOD13", "early stopping -> MOD12=USED")],
    "KHM188": [("performance_metrics", "sex-specific refit AUCs omitted; record as 'subgroup refit'"), ("PRE11/PRE13", "feature-set choice by performance -> PRE11=USED")],
    "KHM192": [("MOD17", "calculator runs LR, not the FINAL XGBoost")],
    "KHM193": [("MOD11", "baselines with no reported results -> NOT_USED")],
    "KHM194": [("MOD05/best_model_selections", "author-proposed SHAP risk score should be FINAL")],
    "KHM200": [("FUN_PROCESS", "K-means binning preprocessing -> ABSENT")],
    "KHM203": [("TSK01/OUT09/metrics", "ordinal target modelled as regression, only MSE/R2 -> CONT/ORDINAL, regression metric codes")],
    "KHM212": [("performance_metrics", "calibration-line slope/intercept from grouped linear fit -> OTHER, not CALSLOPE/CALINT")],
    "KHM214": [("IMB03", "cost-sensitive CART refitted in CV -> WITHIN")],
    "KHM217": [("MOD15", "only trained weights released -> NOT_USED")],
    "KHM222": [("POP08-POP10", "day records coded instead of participants; POP items count survey participants")],
    "KHM031": [("TSK01", "Bayesian network without evaluation coded CLS; compare with KHM179 OTHER/CAUSAL rule")],
    "KHM098": [("TSK07/VAL", "check against later rules (MAE/RMSE on binary labels -> OTHER)")],
}


def main():
    targets = defaultdict(list)
    sweep = json.loads((WORK / "CONSISTENCY_SWEEP.json").read_text())
    for d in sweep["details"]:
        if d["rule"] in SKIP_RULES:
            continue
        targets[d["study_id"]].append({"item": d["item"], "unit": d["unit"], "source": "sweep", "reason": f'{d["rule"]}: {d["detail"]}'})
    for sid, items in MANUAL.items():
        for item, why in items:
            targets[sid].append({"item": item, "unit": None, "source": "coordinator_rule_change", "reason": why})
    scan = WORK / "SUR_MENTION_SCAN.json"
    if scan.exists():
        for d in json.loads(scan.read_text()):
            targets[d["study_id"]].append({"item": d["item"], "unit": None, "source": "sur_mention_scan",
                                           "reason": f'{d["item"]}={d["value"]} but source mentions design element: "{d["snippet"][:160]}"'})
    out = {"studies": len(targets), "items": sum(len(v) for v in targets.values()),
           "targets": {k: targets[k] for k in sorted(targets)}}
    (WORK / "REREVIEW_TARGETS.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"studies": out["studies"], "items": out["items"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
