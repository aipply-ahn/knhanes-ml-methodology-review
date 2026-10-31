#!/usr/bin/env python3
"""Prompt 3 audits for classification metrics, imbalance, and target--predictor construction.

All prose-derived judgements are evidence-assisted primary-review codes.  Raw excerpts are
retained and second-reviewer/consensus columns are deliberately blank.
"""
from __future__ import annotations

import csv
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from canonical_data import included_extraction_index

from analyze_extraction import validation

ROOT = Path(__file__).resolve().parents[1]


def txt(d, *fields):
    return " ".join(str(d.get(k) or "") for k in fields)


def flag(s, pattern):
    return bool(re.search(pattern, s, re.I))


def clean(s, n=700):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n] + ("…" if len(s) > n else "")


METRICS = {
    "Accuracy": r"\baccuracy\b|\bacc\b|정확도",
    "Balanced accuracy": r"balanced[- ]?accuracy|균형정확도",
    "AUROC": r"\bauroc\b|roc[- ]?auc|area under (?:the )?(?:roc|receiver)|(?<!pr[- ])\bauc\b",
    "AUPRC/average precision": r"\bauprc\b|pr[- ]?auc|precision[- ]recall(?:\s+(?:auc|curve))|average precision",
    "Sensitivity/recall": r"sensitivity|\brecall\b|true positive rate|\btpr\b|민감도|재현율",
    "Specificity/TNR": r"specificity|true negative rate|\btnr\b|특이도",
    "Precision/PPV": r"\bprecision\b|positive predictive value|\bppv\b|정밀도|양성예측",
    "NPV": r"negative predictive value|\bnpv\b|음성예측",
    "F1": r"\bf1(?:[- ]?(?:score|measure))?\b",
    "MCC": r"matthews correlation|\bmcc\b",
    "Cohen kappa": r"cohen.?s? kappa|cohen.?s? κ|카파",
    "Brier score": r"brier",
    "Log loss": r"log[- ]?loss|cross[- ]entropy loss|로그손실",
    "Calibration": r"calibration (?:plot|curve|slope|intercept)|brier|hosmer|lemeshow|보정 ?(?:곡선|기울기|절편|평가)",
    "Decision curve/net benefit": r"decision curve|\bdca\b|net benefit|결정 ?곡선|순편익",
    "Confidence interval": r"95\s*%?\s*ci|confidence interval|신뢰구간|\(0\.\d+[–-]0\.\d+\)",
    "SD/resampling distribution": r"mean\s*[±\+]\s*(?:sd|0\.)|standard deviation|\bsd\b|반복.{0,20}(?:분포|평균)|repeated .{0,20}(?:resampl|cross)",
    "Paired model comparison": r"delong|mcnemar|paired (?:test|t[- ]?test)|paired bootstrap|bootstrap difference|대응.*검정",
}


def metric_flags(d):
    s = txt(d, "metrics", "validation", "findings")
    return {k: flag(s, p) for k, p in METRICS.items()}


def best_sentence(d):
    s = clean(txt(d, "best_model", "findings"), 2500)
    parts = re.split(r"(?<=[.!?。])\s+|[;\n]", s)
    hit = [x for x in parts if flag(x, r"best|highest|outperform|superior|최고|가장 높|우수")]
    return clean(" ".join(hit[:2]) or d.get("best_model"), 700)


def selection_metric(d):
    # Prefer an explicitly adjudicated structured field over prose heuristics. This is
    # essential when a figure has several metric leaders (e.g., CatBoost best by F1 but
    # random forest highest by sensitivity in ahn2025discovering).
    explicit = d.get("best_model_selection_metric")
    if explicit in {"AUPRC", "F1", "AUROC", "Accuracy", "Balanced accuracy", "Clinical utility", "Multiple metrics"}:
        return explicit
    s = best_sentence(d)
    found=[]
    for name,pat in [("AUPRC",METRICS["AUPRC/average precision"]),("F1",METRICS["F1"]),
                     ("AUROC",METRICS["AUROC"]),("Accuracy",METRICS["Accuracy"]),
                     ("Balanced accuracy",METRICS["Balanced accuracy"]),
                     ("Clinical utility",METRICS["Decision curve/net benefit"])]:
        if flag(s,pat): found.append(name)
    if len(found)>1: return "Multiple metrics"
    if found: return found[0]
    if flag(s,r"best|highest|outperform|superior|최고|가장 높|우수"): return "Author-selected; criterion not reported"
    return "Not recoverable"


def best_value(d, criterion):
    if criterion in ("Multiple metrics", "Author-selected; criterion not reported", "Not recoverable"):
        return "", ""
    explicit_metric = d.get("best_model_selection_metric")
    explicit_value = d.get("best_model_selection_value")
    if explicit_metric == criterion and explicit_value not in (None, ""):
        return f"{float(explicit_value):g}", "proportion_or_reported_scale"
    aliases={"AUPRC":METRICS["AUPRC/average precision"],"F1":METRICS["F1"],
             "AUROC":METRICS["AUROC"],"Accuracy":METRICS["Accuracy"],
             "Balanced accuracy":METRICS["Balanced accuracy"],
             "Clinical utility":METRICS["Decision curve/net benefit"]}
    # Keep only a value immediately attached to the named metric.  A wider window
    # incorrectly captures outcome cut-offs (e.g., eGFR45) or nearby P values.
    s=txt(d,"best_model")+" "+best_sentence(d)
    m=re.search(rf"(?:{aliases[criterion]})(?:\s+(?:score|value))?\s*(?:of\s*)?[=:]?\s*((?:0?\.\d+)|(?:\d{{2,3}}(?:\.\d+)?))\s*(%)?",s,re.I)
    if not m: return "", ""
    raw=m.group(1); v=float("0"+raw if raw.startswith(".") else raw)
    if criterion in ("AUROC","Accuracy","Balanced accuracy","F1") and v < .2:
        return "", ""
    unit="%" if m.group(2) else "proportion_or_reported_scale"
    if not m.group(2) and v>1 and v<=100: unit="%_inferred"
    return f"{v:g}",unit


def evaluation_dataset(d):
    v=validation(d.get("validation")); s=txt(d,"validation","other_datasets","knhanes_waves")
    if "외부검증" in v: return "external_or_temporal",clean(s,500)
    if "단일 분할" in v or "교차검증" in v: return "internal",clean(s,500)
    return "apparent_or_unclear",clean(s,500)


def imbalance_strategy(d):
    s=txt(d,"preprocessing","notes")
    found=[]
    if flag(s,r"smote|adasyn"): found.append("SMOTE/ADASYN")
    if flag(s,r"class weight|scale_pos_weight|cost[- ]sensitive|비용민감|클래스 가중"): found.append("Class weighting/cost-sensitive")
    if flag(s,r"random oversampl|random undersampl|under[- ]?sampl|over[- ]?sampl|언더샘플|오버샘플"): found.append("Random over/undersampling")
    if flag(s,r"balanced random forest|focal loss|easyensemble|rusboost|speciali[sz]ed ensemble"): found.append("Algorithm-specific")
    if len(found)>1: return "Multiple methods"
    if found: return found[0]
    if flag(s,r"no (?:class )?imbalance|without (?:resampl|balanc)|처리 안 함|미사용"): return "No handling stated"
    return "Not reported"


def imbalance_order(d, strategy):
    if strategy in ("No handling stated","Not reported"): return "NA" if strategy.startswith("No") else "Not reported"
    s=txt(d,"preprocessing","validation","notes","supplementary_materials")
    if flag(s,r"before (?:the )?(?:train|split)|prior to (?:train|split)|전체.{0,15}(?:smote|샘플).{0,15}분할|(?:smote|리샘플링).{0,35}분할 (?:전|이전)|smote 적용 데이터셋.{0,30}분할|smote.{0,30}(?:data|dataset).{0,30}(?:train|test).{0,15}split"):
        return "Before split (leakage concern)"
    if flag(s,r"within (?:each )?(?:fold|training partition)|each training fold|학습.{0,12}fold|fold.{0,12}학습"):
        return "Within each resampling training partition"
    if flag(s,r"x_train|training (?:data|set) only|train(?:ing)?[- ]only|학습 ?(?:자료|세트).{0,15}(?:smote|적용)|(?:smote|adasyn).{0,15}(?:train|학습|훈련).{0,8}(?:only|만)|(?:학습|훈련)셋에만"):
        return "Training data only"
    return "Order not reported"


def test_distribution(d, strategy):
    if strategy in ("No handling stated","Not reported"): return "Not applicable/unclear"
    s=txt(d,"preprocessing","validation","notes")
    if flag(s,r"test.{0,35}(?:original|natural|untouched|unmodified|원래|원분포|변경하지)"):
        return "Original prevalence retained"
    if imbalance_order(d,strategy)=="Before split (leakage concern)" or flag(s,r"test (?:set|data).{0,20}(?:balanced|resampled|smote)|검정.{0,15}(?:균형화|재표집)"):
        return "Balanced/altered test distribution"
    return "Not reported"


def threshold_method(d):
    s=txt(d,"metrics","validation","preprocessing","findings")
    if flag(s,r"test.{0,60}(?:threshold|cutoff).{0,30}(?:optim|maximi|youden|f1)|(?:threshold|cutoff).{0,40}test.{0,20}(?:optim|maximi)"):
        return "Test-selected (bias concern)"
    if flag(s,r"youden"): return "Youden index"
    if flag(s,r"threshold.{0,30}(?:f1|maximi.{0,10}f1)|f1.{0,20}threshold"): return "F1 optimised"
    if flag(s,r"validation|out[- ]of[- ]fold|\boof\b") and flag(s,r"threshold|cutoff|임계"):
        return "Validation/OOF selected"
    if flag(s,r"threshold.{0,12}0\.5|0\.5.{0,12}threshold|임계.{0,12}0\.5"): return "Fixed 0.5"
    if flag(s,r"threshold|decision cutoff|분류 임계|판정기준"): return "Other/unclear reported method"
    return "Not reported"


def class_distribution(d):
    s=txt(d,"sample_filtering","problem","findings","metrics")
    has_count=flag(s,r"(?:case|positive|negative|class|group|환자|양성|음성|군)\D{0,18}n?\s*[=:]?\s*\d{2,}")
    has_rate=flag(s,r"(?:prevalence|positive rate|class proportion|유병률|양성률|비율).{0,20}\d+(?:\.\d+)?\s*%")
    return "Partial" if has_count or has_rate else "No"


def outcome_grades(target):
    recover=target.get("definition_status")=="Recoverable"
    construction=target.get("outcome_construction","")
    basis=target.get("cutoff_basis","")
    if not recover: r="R0"
    elif target.get("cutoff_reported")=="Reported" or construction=="Existing categorical response/diagnosis": r="R2"
    else: r="R1"
    if basis in ("Clinical guideline/diagnostic standard","Validated scale or instrument convention"): c="C2"
    elif basis in ("Reference population or prior literature","Data-driven distribution or optimisation"): c="C1"
    elif basis in ("Numeric rule reported; rationale not stated","Basis not recoverable") or not basis: c="CU"
    else: c="C1"
    overall="Robust" if r=="R2" and c=="C2" else "Not assessable" if r=="R0" or c=="CU" else "Limited"
    return r,c,overall


def overlap_type(d):
    s=txt(d,"problem","variables","notes")
    patterns=[
      (r"hypertension|고혈압",r"systolic|diastolic|blood pressure|수축기|이완기|혈압"),
      (r"diabet|당뇨",r"fasting glucose|hba1c|blood sugar|공복혈당|당화혈색소"),
      (r"metabolic syndrome|대사증후군",r"waist|triglycer|hdl|blood pressure|glucose|허리|중성지방|혈압|혈당"),
      (r"obes|비만",r"\bbmi\b|waist|body mass|height|weight|체질량|허리둘레|신장|체중"),
      (r"osteopor|bone mineral|골다공|골밀도",r"t[- ]?score|bone mineral density|\bbmd\b|골밀도"),
      (r"depress|우울",r"phq[- ]?9|우울.{0,8}(?:문항|점수)|depression treatment"),
      (r"kidney|\bckd\b|콩팥|신장질환",r"egfr|creatinine|albumin.?creatinine|크레아티닌|알부민"),
    ]
    return "Direct component or deterministic proxy" if any(flag(s,a) and flag(s,b) for a,b in patterns) else "No direct overlap identified"


def predictor_grades(d, overlap, order):
    variables=str(d.get("variables") or ""); select=str(d.get("variable_selection") or "")
    v_ok=bool(variables and not flag(variables,r"미기재|not reported|unclear"))
    s_ok=bool(select and not flag(select,r"미기재|not reported|unclear"))
    if not v_ok: r="R0"
    elif s_ok and flag(select,r"\d+|lasso|rfe|recursive|literature|expert|임상|선행|전체|all available|후보"): r="R2"
    else: r="R1"
    explicit_control=flag(txt(d,"variables","variable_selection","notes"),r"exclud.{0,45}(?:outcome|target|component|diagnos)|결과.{0,20}제외|구성요소.{0,20}제외")
    if overlap.startswith("Direct"): c="C0"
    elif not v_ok: c="CU"
    elif explicit_control and order not in ("Before split (leakage concern)",): c="C2"
    else: c="C1"
    overall="High concern" if c=="C0" else "Not assessable" if r=="R0" or c=="CU" else "Robust" if r=="R2" and c=="C2" else "Limited"
    return r,c,overall


def write_tsv(path, rows):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t"); w.writeheader(); w.writerows(rows)


def main():
    refs={r["key"]:r for r in json.load(open(ROOT/"references/refs.json"))}
    ext=included_extraction_index()
    cls=[d for d in ext.values() if refs.get(d["key"],{}).get("verdict")=="INCLUDE" and
         d.get("task")=="classification"]
    targets={r["key"]:r for r in csv.DictReader(open(ROOT/"data/TARGET_DEFINITION_AUDIT.tsv",encoding="utf-8-sig"),delimiter="\t")}
    metric_rows=[]; imbalance_rows=[]; align_rows=[]
    metric_counts=Counter(); selection_counts=Counter(); strategy_counts=Counter(); order_counts=Counter(); threshold_counts=Counter()
    cross=defaultdict(Counter)
    for d in sorted(cls,key=lambda x:x["key"]):
        mf=metric_flags(d)
        for k,v in mf.items(): metric_counts[k]+=v
        criterion=selection_metric(d); value,unit=best_value(d,criterion); edata,eev=evaluation_dataset(d)
        selection_counts[criterion]+=1
        metric_rows.append({"key":d["key"],**{k:"Y" if v else "N" for k,v in mf.items()},
            "best_model_selection_metric":criterion,"best_metric_name":criterion if criterion not in ("Multiple metrics","Author-selected; criterion not reported","Not recoverable") else "",
            "best_metric_value":value,"best_metric_value_unit":unit,"evaluation_dataset":edata,
            "internal_or_external":edata,
            "selection_evidence":clean(d.get("best_model_selection_source") or best_sentence(d), 700),
            "evaluation_evidence":eev,
            "primary_review_verification_required":"Y","second_reviewer":"","consensus":""})
        strategy=imbalance_strategy(d); order=imbalance_order(d,strategy); test=test_distribution(d,strategy); threshold=threshold_method(d)
        strategy_counts[strategy]+=1; order_counts[order]+=1; threshold_counts[threshold]+=1
        for m in ("Accuracy","AUROC","AUPRC/average precision","F1","Calibration"):
            cross[strategy][m]+=mf[m]
        imbalance_rows.append({"key":d["key"],"class_structure":targets.get(d["key"],{}).get("classification_scheme","Not recoverable"),
            "n_classes":targets.get(d["key"],{}).get("n_classes",""),"class_distribution_recoverable":class_distribution(d),
            "imbalance_strategy":strategy,"application_order":order,"test_distribution":test,"threshold_method":threshold,
            "evidence":clean(txt(d,"preprocessing","validation","metrics","notes")),"primary_review_verification_required":"Y","second_reviewer":"","consensus":""})
        t=targets.get(d["key"],{}); orr,oc,oo=outcome_grades(t); overlap=overlap_type(d); pr,pc,po=predictor_grades(d,overlap,order)
        align_rows.append({"key":d["key"],"outcome_reproducibility":orr,"outcome_credibility":oc,"outcome_overall":oo,
            "predictor_reconstructability":pr,"target_predictor_alignment":pc,"predictor_overall":po,"overlap_signal":overlap,
            "outcome_evidence":clean(t.get("outcome_definition")),"predictor_evidence":clean(txt(d,"variables","variable_selection","notes")),
            "primary_review_verification_required":"Y","second_reviewer":"","consensus":""})
    # Fail the rebuild if a human-adjudicated criterion/value is silently lost in
    # prose parsing. This closes the failure mode exposed by ahn2025discovering.
    by_key = {d["key"]: d for d in cls}
    for row in metric_rows:
        d = by_key[row["key"]]
        explicit = d.get("best_model_selection_metric")
        if explicit and row["best_model_selection_metric"] != explicit:
            raise ValueError(f"{row['key']}: explicit best criterion did not propagate")
        explicit_value = d.get("best_model_selection_value")
        if explicit_value not in (None, "") and float(row["best_metric_value"]) != float(explicit_value):
            raise ValueError(f"{row['key']}: explicit best value did not propagate")
    write_tsv(ROOT/"data/PROMPT3_CLASSIFICATION_METRICS.tsv",metric_rows)
    write_tsv(ROOT/"data/PROMPT3_IMBALANCE_AUDIT.tsv",imbalance_rows)
    write_tsv(ROOT/"data/PROMPT3_TARGET_PREDICTOR_AUDIT.tsv",align_rows)
    result={"n_classification":len(cls),"metric_counts":dict(metric_counts),"selection_metric":dict(selection_counts),
            "imbalance_strategy":dict(strategy_counts),"imbalance_application_order":dict(order_counts),"threshold_method":dict(threshold_counts),
            "class_distribution_recoverability":dict(Counter(r["class_distribution_recoverable"] for r in imbalance_rows)),
            "test_distribution":dict(Counter(r["test_distribution"] for r in imbalance_rows)),
            "outcome_reproducibility":dict(Counter(r["outcome_reproducibility"] for r in align_rows)),
            "outcome_credibility":dict(Counter(r["outcome_credibility"] for r in align_rows)),
            "outcome_overall":dict(Counter(r["outcome_overall"] for r in align_rows)),
            "predictor_reconstructability":dict(Counter(r["predictor_reconstructability"] for r in align_rows)),
            "target_predictor_alignment":dict(Counter(r["target_predictor_alignment"] for r in align_rows)),
            "predictor_overall":dict(Counter(r["predictor_overall"] for r in align_rows)),
            "strategy_by_metric":{s:dict(v) for s,v in cross.items()},
            "definitions":{"primary_review":"Evidence-assisted prose coding; independent second review and consensus pending.",
             "performance_values":"Retained study by study only; no pooling across outcomes, prevalences, splits, or evaluation datasets."}}
    (ROOT/"results/derived/prompt3_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    def display(value):
        """Human-readable appendix label; underlying TSV/JSON codes remain unchanged."""
        return str(value).replace("_or_", "/").replace("_", " ").replace("|", "/")

    def display_key(value):
        """Add a legal wrap point after the four-digit year in long study identifiers."""
        return re.sub(r"(\d{4})(?=[A-Za-z])", r"\1 ", str(value))

    def table(counter, heading):
        out=[f"## {heading}","","| Category | n | % |","|---|---:|---:|"]
        out += [f"| {display(k)} | {v} | {100*v/len(cls):.1f} |" for k,v in counter.items()]
        return out+[""]
    lines=["# Additional file 13. Classification-performance, imbalance, and target--predictor audits","",
      "All prose-derived codes are evidence-assisted primary-review judgements. Independent second review and consensus are pending. Metric indicators are non-mutually exclusive. Reported best values are retained study by study and are not pooled across outcomes, prevalences, splits, or evaluation datasets.",""]
    lines+=table(metric_counts,"Reported classification-performance metrics")
    lines+=table(selection_counts,"Criterion used to designate the best model")
    lines+=table(strategy_counts,"Class-imbalance strategy")
    lines+=table(order_counts,"Timing of imbalance handling")
    lines+=table(Counter(r["test_distribution"] for r in imbalance_rows),"Evaluation/test distribution")
    lines+=table(Counter(r["class_distribution_recoverable"] for r in imbalance_rows),"Class-distribution recoverability")
    lines+=table(threshold_counts,"Decision-threshold selection")
    lines += ["## Imbalance strategy by reported metric","",
              "| Strategy | Accuracy | AUROC | AUPRC | F1 | Calibration |","|---|---:|---:|---:|---:|---:|"]
    for strategy,c in cross.items():
        lines.append(f"| {strategy} | {c['Accuracy']} | {c['AUROC']} | {c['AUPRC/average precision']} | {c['F1']} | {c['Calibration']} |")
    lines += [""]+table(Counter(r["outcome_reproducibility"] for r in align_rows),"Outcome-definition reproducibility")
    lines += table(Counter(r["outcome_credibility"] for r in align_rows),"Outcome-definition credibility")
    lines += table(Counter(r["outcome_overall"] for r in align_rows),"Outcome-definition overall construction adequacy")
    lines += table(Counter(r["predictor_reconstructability"] for r in align_rows),"Predictor-set reconstructability")
    lines += table(Counter(r["target_predictor_alignment"] for r in align_rows),"Target--predictor alignment")
    lines += table(Counter(r["predictor_overall"] for r in align_rows),"Predictor construction/alignment: overall adequacy")
    lines += ["## Study-level audit","",
      "| Study | Best criterion | Best value | Evaluation | Imbalance strategy | Application order | Threshold | Outcome R/C/overall | Predictor R/C/overall |",
      "|---|---|---:|---|---|---|---|---|---|"]
    by_i={r['key']:r for r in imbalance_rows}; by_a={r['key']:r for r in align_rows}
    for r in metric_rows:
        i=by_i[r['key']]; a=by_a[r['key']]
        val=(r['best_metric_value']+("%" if r['best_metric_value_unit'] in ('%','%_inferred') else '')) or "NR"
        lines.append(f"| {display_key(r['key'])} | {display(r['best_model_selection_metric'])} | {val} | {display(r['evaluation_dataset'])} | {display(i['imbalance_strategy'])} | {display(i['application_order'])} | {display(i['threshold_method'])} | {a['outcome_reproducibility']}/{a['outcome_credibility']}/{a['outcome_overall']} | {a['predictor_reconstructability']}/{a['target_predictor_alignment']}/{a['predictor_overall']} |")
    (ROOT/"manuscript/submission/appendices/appendix13_prompt3_audits.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
