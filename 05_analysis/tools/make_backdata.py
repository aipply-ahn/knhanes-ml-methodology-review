"""백데이터 export — 모든 표·그림의 근거를 사람이 열어볼 수 있는 표로 뺀다.

    python tools/make_backdata.py

출력 data/backdata/*.tsv (엑셀에서 바로 열림) + README.md
"""
import sys, os, json, glob, csv, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, DER, load
OUT = os.path.join(PROJ, "data", "backdata")
os.makedirs(OUT, exist_ok=True)
R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
E = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/extraction/*.json")))}
P = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/probast/*.json")))}
A = load(os.path.join(DER, "analysis.json"))
T = load(os.path.join(DER, "tripod_stats.json"))
inc = sorted([k for k, r in R.items() if r["verdict"] == "INCLUDE"],
             key=lambda k: (-(R[k].get("year") or 0), k))


def w(name, header, rows):
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f, delimiter="\t")
        wr.writerow(header)
        for r in rows: wr.writerow(r)
    print(f"  {name}  ({len(rows)} 행)")


def s(v, n=400):
    if v is None: return ""
    if isinstance(v, list): v = "; ".join(str(x) for x in v)
    return re.sub(r"\s+", " ", str(v))[:n]


# 1. 연구별 추출 원자료 (본문 표 1 · 부록 6 의 근거)
F = ["problem","task","ml_usage","knhanes_waves","knhanes_role","other_datasets","sample_filtering",
     "n_final","variables","variable_selection","missing_handling","preprocessing","survey_weights",
     "models","best_model","hyperparameter_tuning","validation","metrics","interpretability",
     "findings","limitations","code_data_availability","notes","source"]
# knhanes_waves 에서 파생한 조사연도 범위 — 본문 §조사 기수와 영역, 그림 8 의 근거
from analyze_extraction import wave_scope, waves, cycle_of


def _span(k):
    v = E.get(k, {}).get("knhanes_waves")
    sc = wave_scope(v); wv = waves(v)
    if not wv: return ["", "", "", ""]
    cyc = sorted({cycle_of(y) for y in range(wv[0], wv[1] + 1)},
                 key=lambda c: int(re.sub(r"\D", "", c or "0") or 0))
    return [sc or "", f"{wv[0]}–{wv[1]}" if wv[0] != wv[1] else str(wv[0]),
            "·".join(c for c in cyc if c), str(len([c for c in cyc if c]))]


w("01_extraction_by_study.tsv",
  ["key","year","journal","title","doi","pmid","category","cited","publication_type"] + F
  + ["조사연도 범위(파생)", "연도 범위(파생)", "해당 기수(파생)", "기수 수(파생)"],
  [[k, R[k].get("year"), R[k].get("journal"), R[k].get("title"), R[k].get("doi"), R[k].get("pmid"),
    R[k].get("category"), R[k].get("cited"), R[k].get("publication_type_ko") or ""]
   + [s(E.get(k, {}).get(x)) for x in F] + _span(k)
   for k in inc])

# 2. PROBAST 신호질문 전체 (부록 7 · 그림 5A 의 근거)
DOMQ = {}
for k in inc:
    for d, qs in ((P.get(k) or {}).get("probast") or {}).items():
        DOMQ.setdefault(d, set()).update(q for q in qs if q not in ("judgment", "note"))
cols = [(d, q) for d in ("D1", "D2", "D3", "D4") for q in sorted(DOMQ.get(d, []))]
w("02_probast_signalling.tsv",
  ["key","year","source","overall_rob","applicability","D1_judgment","D2_judgment","D3_judgment","D4_judgment"]
  + [f"{d}.{q}" for d, q in cols] + ["D1_note","D2_note","D3_note","D4_note","notes"],
  [[k, R[k].get("year"), (P.get(k) or {}).get("source"), (P.get(k) or {}).get("overall_rob"),
    (P.get(k) or {}).get("applicability")]
   + [(((P.get(k) or {}).get("probast") or {}).get(d) or {}).get("judgment", "") for d in ("D1","D2","D3","D4")]
   + [(((P.get(k) or {}).get("probast") or {}).get(d) or {}).get(q, "") for d, q in cols]
   + [s((((P.get(k) or {}).get("probast") or {}).get(d) or {}).get("note"), 300) for d in ("D1","D2","D3","D4")]
   + [s((P.get(k) or {}).get("notes"), 400)] for k in inc])

# 3. TRIPOD 항목별 (그림 5B · TRIPOD_STATS 의 근거)
TI = sorted({i for k in inc for i in ((P.get(k) or {}).get("tripod") or {})})
w("03_tripod_items.tsv",
  ["key","year","n_yes","n_applicable","pct"] + TI,
  [[k, R[k].get("year"), (P.get(k) or {}).get("tripod_n_yes"), (P.get(k) or {}).get("tripod_n_applicable"),
    round(100 * (P.get(k) or {}).get("tripod_n_yes", 0) / max(1, (P.get(k) or {}).get("tripod_n_applicable", 1)), 1)]
   + [((P.get(k) or {}).get("tripod") or {}).get(i, "") for i in TI] for k in inc])

# 4. TRIPOD 일반 vs KNHANES 확장 (짝지은 검정의 원자료)
w("04_tripod_vs_extension.tsv",
  ["key","year","source","general_yes","general_applicable","general_pct",
   "extension_yes","extension_applicable","extension_pct","difference_pp"],
  [[r["key"], r["year"], r["source"], r["gen_yes"], r["gen_app"],
    round(r["gen_pct"],1) if r["gen_pct"] is not None else "",
    r["ext_yes"], r["ext_app"], round(r["ext_pct"],1) if r["ext_pct"] is not None else "",
    round(r["gen_pct"]-r["ext_pct"],1) if (r["gen_pct"] is not None and r["ext_pct"] is not None) else ""]
   for r in T["per_study"]])

# 5. 집계 (모든 그림의 막대값)
rows = []
for grp, d in (("연도별 출판", A["year"]), ("결과변수 영역", A["category"]), ("과제", A["task"]),
               ("KNHANES 역할", A["knhanes_role"]), ("자료층", A["data_layer"]),
               ("조사연차 사용", A["wave_year_usage"]), ("사용 연차 폭", A["wave_span"]),
               ("표본크기 구간", A["n_final"]["bins"]), ("가중치 처리", A["weights"]),
               ("결측 처리", A["missing"]), ("불균형 처리", A["imbalance"]), ("검증", A["validation"]),
               ("해석기법", A["interp"]), ("코드 공개", A["code"]),
               ("성능 보고 깊이", A["metric_depth"]), ("변수중요도 유형", A["importance_kind"]),
               ("사후 통계분석", A["posthoc"]), ("모형 비교 방식", A["model_comparison"]),
               ("비교 모델", A["models_compared"]), ("최고 모델", A["best_model"]),
               ("논문당 모델 수", A["n_models_per_paper"]), ("ML 인접 방법", A["adjacent_method"])):
    for k2, v in d.items(): rows.append([grp, k2, v])
w("05_aggregates.tsv", ["집계 축", "값", "편수"], rows)

# 6. 판정 이력 (포함·제외 전체)
V = load(os.path.join(DER, "verdicts.json"))
S = {x["uid"]: x for x in load(os.path.join(DER, "screen.json"))["rows"]}
w("06_screening_verdicts.tsv",
  ["uid","tier","verdict","reason","bench_category","ml_terms","year","journal","title","doi","pmid"],
  [[u, S.get(u, {}).get("tier"), v.get("verdict"), s(v.get("reason"), 200), v.get("category"),
    s(v.get("ml_methods")), S.get(u, {}).get("year"), s(S.get(u, {}).get("journal"), 60),
    s(S.get(u, {}).get("title"), 200), S.get(u, {}).get("doi"), S.get(u, {}).get("pmid")]
   for u, v in sorted(V.items(), key=lambda x: (x[1].get("verdict") or "", x[0]))])

open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("""# data/backdata/ — 백데이터

리뷰 본문의 **모든 표와 그림의 근거**를 사람이 열어볼 수 있는 형태로 뺀 것이다.
탭 구분(TSV), UTF-8 BOM 이므로 엑셀에서 바로 열린다. 전부 자동 생성이며 손으로 고치지 않는다.
재생성: `python tools/make_backdata.py`

| 파일 | 무엇 | 무엇의 근거 |
|---|---|---|
| `01_extraction_by_study.tsv` | 포함 {n_include}편 × 25개 추출 항목 | 본문 결과 전반, 부록 6 |
| `02_probast_signalling.tsv` | PROBAST 4영역 신호질문 전부 + 확장 S1–S3 + 판정 메모 | 그림 5A, 부록 7 |
| `03_tripod_items.tsv` | TRIPOD+AI 19항목 연구별 판정 | 그림 5B, 부록 7 |
| `04_tripod_vs_extension.tsv` | 일반 항목 대 확장 항목 준수율 (짝지은 검정 원자료) | `data/TRIPOD_STATS.md` |
| `05_aggregates.tsv` | 모든 그림의 막대값 | 그림 1–7 |
| `06_screening_verdicts.tsv` | 평가 대상 판정 전체 (포함·인접·제외·보류와 사유) | 그림 1 PRISMA |

## 확인하실 때

- `02` 의 `*_note` 열과 `notes` 열에 판정 근거가 적혀 있다. 이견이 있으면 그 셀을 보고 판단하시면 된다
- `06` 의 `reason` 열은 제외 사유 코드로 시작한다 (NOT_KNHANES / NO_ML / REVIEW / ABBREV_FP / OTHER)
- 판정을 바꾸려면 `results/derived/verdicts.json` 또는 `data/probast/<key>.json` 을 고치고
  `analyze_extraction.py` → `probast_merge.py` → `tripod_stats.py` → `make_backdata.py` 순으로 재실행한다
""".format(n_include=A["n_include"]))
print("  README.md")


if __name__ == "__main__":
    pass
