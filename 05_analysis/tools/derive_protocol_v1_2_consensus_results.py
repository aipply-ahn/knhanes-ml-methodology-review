#!/usr/bin/env python3
"""Derive consensus manuscript summaries from protocol-v1.2 final JSON."""
import json
from study_reporting import categorical_methods, reduce_reporting, records, reporting_summary
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/"data/protocol_v1_2"; OUT=ROOT/"results/derived/protocol_v1_2_consensus_results.json"
def val(r,i): return [x["value"] for x in r["protocol_items"][i]]
def one(r,i):
    x=val(r,i); return x[0] if len(x)==1 else x
allr=[json.loads(p.read_text()) for p in sorted((BASE/"final").glob("KHM*_final.json"))]
R=[r for r in allr if r.get("corpus_status",{}).get("include",one(r,"ELG04")=="Y")]
P=[r for r in R if one(r,"TSK01") in ("CLS","CONT")]
C=[r for r in R if one(r,"TSK01")=="CLS"]
def count_rows(records,i,drop_na=False):
    c=Counter(str(x) for r in records for x in val(r,i));
    if drop_na: c.pop("NA",None)
    return dict(c)
reporting={i:count_rows(R,i) for i in [f"REP{n:02d}" for n in range(1,20)]}
survey={i:count_rows(R,i) for i in ["SUR04","SUR05","SUR06","SUR07","SUR08","SUR09","SUR10","SUR11","SUR12","SUR14"]}
probast={"development":{"n_units":sum(len(r["units"]["developments"]) for r in P),
                         "overall":count_rows(P,"PD_OVERALL",True),
                         "domains":{f"D{n}":count_rows(P,f"PD_D{n}",True) for n in range(1,5)}},
         "evaluation":{"n_units":sum(len(r["units"]["evaluations"]) for r in P),
                       "overall":count_rows(P,"PE_OVERALL",True),
                       "domains":{f"D{n}":count_rows(P,f"PE_D{n}",True) for n in range(1,5)}}}
def first_applicable(r,i):
    xs=[x for x in val(r,i) if x!="NA"]
    return xs[0] if xs else "NA"
def study_any(r,i,code):
    return any(x==code or isinstance(x,list) and code in x for x in val(r,i))
def worst_study_value(r,i):
    """Collapse multiple semantic units only for study-level display summaries."""
    xs=val(r,i)
    if all(x=="NAU" for x in xs): return "NAU"
    for code in ("HIGH","LIMITED","ROBUST"):
        if code in xs: return code
    return xs[0]
classification={
 "missing_primary":dict(Counter(categorical_methods(r,"PRE01") for r in C)),
 "imbalance_primary":dict(Counter(categorical_methods(r,"IMB01") for r in C)),
 "class_recoverability":dict(Counter(("R" if (state:=reduce_reporting(records(r,"IMB05"), {"R"}, {"P"}))=="Y" else state) for r in C)),
 "threshold_primary":dict(Counter(v for r in C for v in set(val(r,"THR01")))),
 "aggregation_policy":"Cycle083: legacy *_primary key names are compatibility aliases, not primary-unit designation. Categorical methods use MULTIPLE for distinct observed strategies; class recovery uses at least one sample; threshold methods count study-presence of each code and can overlap. This historical full classification cohort differs from the current 165-study health core.",
 "reporting_prevalence":reporting_summary(C),
 "validation":{code:sum(study_any(r,"VAL02",code) for r in C) for code in ("APPARENT","SPLIT","CV","BOOT","TEMPORAL","EXTERNAL","NONE_NR","OTHER")},
 "metrics":{code:sum(any(m.get("metric")==code for m in r["performance_metrics"]) for r in C) for code in ("ACC","BACC","AUROC","AUPRC","SENS","SPEC","PPV","NPV","F1","MCC","KAPPA","BRIER","LOGLOSS","CALSLOPE","CALINT","CALPLOT","DCA")},
 "metric_reporting":{i:sum(study_any(r,i,"Y") for r in C) for i in ("MET_CI","MET_SD","MET_PAIR","MET_APPROPRIATE")},
 "importance":{i:sum(study_any(r,i,"USED") for r in C) for i in ("VI01","VI10","VI11","VI14","VI16","VI17","VI18","VI19")},
 "outcome_timing":dict(Counter(first_applicable(r,"OUT10") for r in C)),
 "outcome_adequacy":dict(Counter(worst_study_value(r,"OUT18") for r in C)),
 "predictor_adequacy":dict(Counter(worst_study_value(r,"PRD15") for r in C)),
}
content={i:sum(study_any(r,i,"PRESENT") for r in R) for i in
 ["RAT_PERF","RAT_SCREEN","RAT_COMPLEX","RAT_FACTOR","RAT_METHOD","RAT_DEPLOY","RAT_NONE","FUN_PRED","FUN_COMPARE","FUN_INTERP","FUN_PROCESS","FUN_TRANSPORT","FUN_PATTERN","FUN_TOOL","CLM_BETTER","CLM_FACTOR","CLM_SCREEN","CLM_NONCAUSAL","CLM_EXTVAL","CLM_SURVEY","CLM_IMPLEMENT"]}
out={"status":"PASS","date":"2026-09-15","source":"data/protocol_v1_2/final/*.json","review_status":"blinded LLM P2 and prespecified rule-based reconciliation complete",
     "denominators":{"reports":len(allr),"studies":len(R),"prediction":len(P),"classification":sum(one(r,"TSK01")=="CLS" for r in R),"continuous":sum(one(r,"TSK01")=="CONT" for r in R),"other":sum(one(r,"TSK01")=="OTHER" for r in R)},
     "knhanes_role":dict(Counter(one(r,"TSK06") for r in R)),"reporting":reporting,"survey":survey,"probast_ai":probast,
     "classification":classification,"content":content,
     "integrity_flags":sum(one(r,"ADM09")=="Y" for r in R),"retracted_history":sum(r.get("corpus_status",{}).get("exclude_from_valid_evidence") is True for r in R)}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n"); print(json.dumps(out,ensure_ascii=False,indent=2))
