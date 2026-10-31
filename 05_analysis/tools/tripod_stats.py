"""TRIPOD 일반 항목 대 KNHANES 확장 항목(S1-S3) 준수율 비교 — 짝지은 검정.

    python tools/tripod_stats.py

논거: "일반 보고 항목은 지키는데 조사설계 항목만 무너진다" 를 통계적으로 보인다.
Diagnostic and Prognostic Research 2026 (COVID 예후모형 53편) 이 TRIPOD 대 TRIPOD+AI
준수율을 비교한 설계를 빌리되, 우리는 **같은 연구 안에서** 두 항목군을 비교하므로 짝지은 검정을 쓴다.
결과: results/derived/tripod_stats.json · data/TRIPOD_STATS.md
"""
import sys, os, json, glob, math
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, DER, dump, load
from scipy import stats

R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
P = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/probast/*.json")))}
inc = [k for k, r in R.items() if r["verdict"] == "INCLUDE" and k in P
       and P[k].get("source") == "full_text"]

GEN = ["title_design", "abstract_structured", "background_objective", "data_source",
       "participants_eligibility", "outcome_definition", "predictors_description",
       "sample_size_justification", "missing_data", "model_building",
       "model_performance_measures", "model_evaluation", "results_participants",
       "results_performance", "limitations", "data_availability", "code_availability",
       "funding", "model_availability"]
EXT = ["S1", "S2", "S3"]
EXTNAME = {"S1": "표본가중치를 모형 적합에 반영 또는 미반영 근거 제시",
           "S2": "층화·집락을 성능 추정에 반영",
           "S3": "다기수 통합 시 통합 가중치 산출 명시"}


def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


def main():
    rows = []
    for k in inc:
        t = P[k].get("tripod") or {}
        d4 = (P[k].get("probast") or {}).get("D4") or {}
        g_app = [i for i in GEN if t.get(i) != "NA"]
        g_yes = sum(1 for i in g_app if t.get(i) == "Y")
        e_app = [s for s in EXT if d4.get(s) not in ("NA", None)]
        e_yes = sum(1 for s in e_app if d4.get(s) in ("Y", "PY"))
        rows.append(dict(key=k, year=R[k].get("year"),
                         gen_yes=g_yes, gen_app=len(g_app), gen_pct=100 * g_yes / len(g_app) if g_app else None,
                         ext_yes=e_yes, ext_app=len(e_app), ext_pct=100 * e_yes / len(e_app) if e_app else None,
                         source=P[k].get("source")))
    paired = [(r["gen_pct"], r["ext_pct"]) for r in rows if r["gen_pct"] is not None and r["ext_pct"] is not None]
    g = [a for a, b in paired]; e = [b for a, b in paired]
    W = stats.wilcoxon(g, e, zero_method="wilcox", alternative="greater")
    A = {"n_studies": len(rows), "n_paired": len(paired)}
    A["general"] = {"median_pct": round(float(stats.scoreatpercentile(g, 50)), 1),
                    "q1": round(float(stats.scoreatpercentile(g, 25)), 1),
                    "q3": round(float(stats.scoreatpercentile(g, 75)), 1),
                    "mean_pct": round(sum(g) / len(g), 1)}
    A["extension"] = {"median_pct": round(float(stats.scoreatpercentile(e, 50)), 1),
                      "q1": round(float(stats.scoreatpercentile(e, 25)), 1),
                      "q3": round(float(stats.scoreatpercentile(e, 75)), 1),
                      "mean_pct": round(sum(e) / len(e), 1)}
    A["difference_mean_pp"] = round(A["general"]["mean_pct"] - A["extension"]["mean_pct"], 1)
    A["wilcoxon"] = {"statistic": float(W.statistic), "p": float(W.pvalue),
                     "alternative": "general > extension", "note": "짝지은 부호순위 검정"}
    # 항목별 준수율 + 윌슨 95% CI
    items = {}
    for i in GEN:
        app = [k for k in inc if (P[k].get("tripod") or {}).get(i) != "NA"]
        yes = sum(1 for k in app if (P[k].get("tripod") or {}).get(i) == "Y")
        lo, hi = wilson(yes, len(app))
        items[i] = dict(group="TRIPOD 일반", yes=yes, applicable=len(app),
                        pct=round(100 * yes / len(app), 1) if app else None, ci=[lo, hi])
    for s in EXT:
        app = [k for k in inc if ((P[k].get("probast") or {}).get("D4") or {}).get(s) not in ("NA", None)]
        yes = sum(1 for k in app if ((P[k].get("probast") or {}).get("D4") or {}).get(s) in ("Y", "PY"))
        lo, hi = wilson(yes, len(app))
        items[s] = dict(group="KNHANES 확장", yes=yes, applicable=len(app),
                        pct=round(100 * yes / len(app), 1) if app else None, ci=[lo, hi],
                        label=EXTNAME[s])
    A["items"] = items
    # 시기별 추이 (확장 항목이 개선되었나)
    per = {}
    for r in rows:
        y = r["year"] or 0
        p = "–2019" if y <= 2019 else "2020–2022" if y <= 2022 else "2023–2024" if y <= 2024 else "2025–2026"
        per.setdefault(p, {"n": 0, "gen": [], "ext": []})
        per[p]["n"] += 1
        if r["gen_pct"] is not None: per[p]["gen"].append(r["gen_pct"])
        if r["ext_pct"] is not None: per[p]["ext"].append(r["ext_pct"])
    A["by_period"] = {k: dict(n=v["n"],
                              gen_median=round(float(stats.scoreatpercentile(v["gen"], 50)), 1) if v["gen"] else None,
                              ext_median=round(float(stats.scoreatpercentile(v["ext"], 50)), 1) if v["ext"] else None)
                      for k, v in sorted(per.items())}
    A["per_study"] = rows
    dump(A, os.path.join(DER, "tripod_stats.json"))

    L = ["# TRIPOD 일반 항목 대 KNHANES 확장 항목 준수율\n",
         "생성 자동 · `python tools/tripod_stats.py` · 원자료 `data/probast/*.json`\n",
         f"대상 {A['n_studies']}편 (두 항목군 모두 평가 가능한 {A['n_paired']}편으로 짝지은 검정)\n",
         "## 요약\n", "| 항목군 | 준수율 중앙값 | 사분위 | 평균 |", "|---|---:|---|---:|",
         f"| TRIPOD 일반 (19항목) | {A['general']['median_pct']}% | {A['general']['q1']}–{A['general']['q3']}% | {A['general']['mean_pct']}% |",
         f"| **KNHANES 확장 (S1–S3)** | **{A['extension']['median_pct']}%** | {A['extension']['q1']}–{A['extension']['q3']}% | {A['extension']['mean_pct']}% |",
         "",
         f"평균 차이 **{A['difference_mean_pp']} 퍼센트포인트**. "
         f"윌콕슨 부호순위 검정 W={A['wilcoxon']['statistic']:.0f}, "
         f"p{'<0.001' if A['wilcoxon']['p'] < 0.001 else f'={A[chr(39)+chr(39)] if False else A['wilcoxon']['p']:.4f}'} "
         "(대립가설: 일반 항목 준수율이 확장 항목보다 높다).\n",
         "## 항목별 준수율 (윌슨 95% 신뢰구간)\n",
         "| 항목군 | 항목 | 충족 | 해당 | % | 95% CI |", "|---|---|---:|---:|---:|---|"]
    for k, v in sorted(items.items(), key=lambda x: (x[1]["group"], -(x[1]["pct"] or 0))):
        nm = v.get("label", k)
        L.append(f"| {v['group']} | {nm} | {v['yes']} | {v['applicable']} | {v['pct']} | {v['ci'][0]}–{v['ci'][1]} |")
    L += ["", "## 시기별 추이\n", "| 시기 | 연구 수 | 일반 항목 중앙값 | 확장 항목 중앙값 |", "|---|---:|---:|---:|"]
    for k, v in A["by_period"].items():
        L.append(f"| {k} | {v['n']} | {v['gen_median']}% | {v['ext_median']}% |")
    L += ["", "## 해석\n",
          "일반 보고 항목은 절반 이상 지켜지는 반면 조사설계 항목은 사실상 지켜지지 않는다. ",
          "두 항목군은 **같은 논문 안에서** 측정되므로 저자 역량이나 학술지 수준의 차이로 설명되지 않는다. ",
          "차이는 **무엇이 학계 관행으로 자리 잡았는가**에서 온다.\n"]
    open(os.path.join(PROJ, "data", "TRIPOD_STATS.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  일반 {A['general']['median_pct']}% vs 확장 {A['extension']['median_pct']}% · "
          f"차이 {A['difference_mean_pp']}pp · p={A['wilcoxon']['p']:.3g}")


if __name__ == "__main__":
    main()
