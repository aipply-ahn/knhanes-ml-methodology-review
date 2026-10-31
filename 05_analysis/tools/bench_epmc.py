"""벤치마크 리뷰 전수조사 — "특정 바이오헬스 데이터셋/자료유형에 ML 을 적용한 연구들을 리뷰한 논문" 을 모은다.

    python tools/bench_epmc.py

층
  A  ML(제목) ∧ 리뷰(제목) ∧ 자료원 용어(제목/초록: EHR·claims·biobank·cohort·survey·registry·real-world·tabular …)
  B  명명 데이터셋별 — (데이터셋명 제목/초록) ∧ ML(제목/초록) ∧ (리뷰 제목 또는 PUB_TYPE Review)
  C  방법론·보고품질 리뷰 — (TRIPOD·PROBAST·reporting quality·risk of bias·methodological) ∧ ML(제목) ∧ 리뷰
결과: results/raw/bench_epmc_<date>.json  (Europe PMC · 초록 포함 · 층 표시 · 적중 데이터셋명)
"""
import sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *
from census_epmc import epmc_all, pubmed_count, slim

ML_T = '(TITLE:"machine learning" OR TITLE:"deep learning" OR TITLE:"artificial intelligence" OR TITLE:"predictive model*" OR TITLE:"prediction model*" OR TITLE:"data mining" OR TITLE:"neural network*")'
ML_TA = '(TITLE_ABS:"machine learning" OR TITLE_ABS:"deep learning" OR TITLE_ABS:"artificial intelligence" OR TITLE_ABS:"data mining" OR TITLE_ABS:"prediction model*")'
REV_T = '(TITLE:review OR TITLE:survey OR TITLE:scoping OR TITLE:systematic OR TITLE:overview OR TITLE:bibliometric OR TITLE:"state of the art" OR TITLE:landscape OR TITLE:"meta-analysis" OR TITLE:"meta-research" OR TITLE:"umbrella")'
REV_ANY = f'({REV_T} OR PUB_TYPE:"Review" OR PUB_TYPE:"Systematic Review")'

SOURCE_TERMS = ["electronic health record*", "EHR", "electronic medical record*", "claims data", "administrative data",
                "insurance data", "biobank", "cohort stud*", "population-based", "national survey", "health survey",
                "survey data", "complex survey", "registry", "registries", "real-world data", "real-world evidence",
                "tabular data", "structured data", "routinely collected", "public health", "epidemiolog*",
                "longitudinal data", "panel data", "wearable*", "big data"]
DATASETS = ["NHANES", "KNHANES", "UK Biobank", "MIMIC", "eICU", "PhysioNet", "KoGES", "CHARLS", "ELSA",
            "Health and Retirement Study", "SHARE", "Framingham", "SEER", "TCGA", "ADNI", "All of Us",
            "Million Veteran Program", "NHIRD", "CPRD", "China Kadoorie Biobank", "Taiwan Biobank",
            "Estonian Biobank", "FinnGen", "BioBank Japan", "HUNT", "Rotterdam Study", "Whitehall", "NHATS",
            "MESA", "ARIC", "Optum", "MarketScan", "Medicare", "Veterans Affairs", "Kaiser Permanente", "N3C",
            "PCORnet", "OMOP", "OHDSI", "TriNetX", "Flatiron", "Korea Community Health Survey", "KCHS",
            "National Health Insurance Service", "NHIS-NSC", "HIRA", "Korea Health Panel", "KLoSA", "CHNS",
            "Demographic and Health Survey*", "BRFSS", "National Health Interview Survey", "MEPS", "JAGES", "CLHLS",
            "Global Burden of Disease", "Nurses' Health Study", "Women's Health Initiative", "Danish registers",
            "Nordic registers", "JMDC", "Intensive care", "ICU", "emergency department", "primary care"]
METHOD_TERMS = ["TRIPOD", "PROBAST", "reporting quality", "risk of bias", "methodological quality",
                "reporting guideline*", "external validation", "calibration", "fairness", "bias",
                "explainab*", "interpretab*", "class imbalance", "missing data", "survey weight*", "sampling weight*"]


def main():
    out = dict(source="Europe PMC", searched_on=time.strftime("%Y-%m-%d"), layers=[], records={})
    pool = out["records"]

    def add(items, layer, tag):
        n = 0
        for v in items:
            k = v.get("id") or v.get("doi")
            if k in pool:
                pool[k]["bench_layers"].append(f"{layer}:{tag}")
            else:
                r = slim(v, layer); r["bench_layers"] = [f"{layer}:{tag}"]; pool[k] = r; n += 1
        return n

    print("A. 자료원 용어")
    src = "(" + " OR ".join(f'TITLE_ABS:"{t}"' for t in SOURCE_TERMS) + ")"
    qa = f"{ML_T} AND {REV_T} AND {src}"
    tot, items = epmc_all(qa, label="A")
    out["layers"].append(dict(layer="A", tag="source_terms", query=qa, hits=tot, retrieved=len(items), new=add(items, "A", "source")))
    print("B. 명명 데이터셋별")
    for d in DATASETS:
        qd = f'TITLE_ABS:"{d}" AND {ML_TA} AND {REV_ANY}'
        tot, items = epmc_all(qd, cap=2000, label=d[:14])
        new = add(items, "B", d)
        out["layers"].append(dict(layer="B", tag=d, query=qd, hits=tot, retrieved=len(items), new=new))
        print(f"    {d:34s} hits {tot:5d} 신규 {new:4d}", flush=True)
        time.sleep(0.3)
    print("C. 방법론·보고품질")
    mt = "(" + " OR ".join(f'TITLE_ABS:"{t}"' for t in METHOD_TERMS) + ")"
    qc = f"{ML_T} AND {REV_T} AND {mt} AND (TITLE_ABS:\"prediction model*\" OR TITLE_ABS:\"prognostic\" OR TITLE_ABS:\"diagnostic\" OR TITLE_ABS:\"clinical\" OR TITLE_ABS:\"health\")"
    tot, items = epmc_all(qc, cap=3000, label="C")
    out["layers"].append(dict(layer="C", tag="method_quality", query=qc, hits=tot, retrieved=len(items), new=add(items, "C", "method")))
    out["records"] = list(pool.values())
    out["n_unique"] = len(out["records"]); out["n_with_abstract"] = sum(1 for r in out["records"] if r["abstract"])
    dump(out, os.path.join(RAW, f"bench_epmc_{TODAY}.json"))
    print(f"  고유 {out['n_unique']} · 초록 {out['n_with_abstract']}")


if __name__ == "__main__":
    main()
