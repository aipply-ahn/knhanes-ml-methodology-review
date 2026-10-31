"""복합표본설계 × ML 방법론 문헌 수집 — 초고 B·C 의 근거.

    python tools/collect_survey_ml.py

"KNHANES 연구가 가중치를 안 쓴다" 는 비판은 **쓸 방법이 이미 문헌에 있다** 는 근거가 있어야 성립한다.
결과: references/survey_ml_methods.json · SURVEY_ML_METHODS.md
"""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from census_epmc import epmc_all, slim

W = ('(TITLE_ABS:"survey weight*" OR TITLE_ABS:"sampling weight*" OR TITLE_ABS:"complex survey" '
     'OR TITLE_ABS:"complex sampling" OR TITLE_ABS:"survey-weighted" OR TITLE_ABS:"design-based inference" '
     'OR TITLE_ABS:"weighted machine learning" OR TITLE_ABS:"pseudo-population" OR TITLE_ABS:"stratified multistage")')
ML = ('(TITLE_ABS:"machine learning" OR TITLE_ABS:"deep learning" OR TITLE_ABS:"random forest" '
      'OR TITLE_ABS:"gradient boosting" OR TITLE_ABS:"neural network*" OR TITLE_ABS:"prediction model*" '
      'OR TITLE_ABS:"XGBoost" OR TITLE_ABS:"ensemble learning" OR TITLE_ABS:"super learner")')
HEALTH = ('(TITLE_ABS:health OR TITLE_ABS:epidemiolog* OR TITLE_ABS:NHANES OR TITLE_ABS:prevalence '
          'OR TITLE_ABS:"public health" OR TITLE_ABS:survey OR TITLE_ABS:population OR TITLE_ABS:cohort '
          'OR TITLE_ABS:disease OR TITLE_ABS:mortality OR TITLE_ABS:risk)')
QUERIES = [("A", f"{W} AND {ML} AND {HEALTH}"),
           ("B", f'(TITLE:"survey weight*" OR TITLE:"sampling weight*" OR TITLE:"complex survey" OR TITLE:"survey-weighted" OR TITLE:"complex sampling") AND {ML}'),
           ("C", f'{W} AND (TITLE_ABS:imputation OR TITLE_ABS:"missing data" OR TITLE_ABS:"cross-validation" OR TITLE_ABS:"model performance" OR TITLE_ABS:calibration OR TITLE_ABS:"variance estimation")')]

# 명백한 비보건 오탐 (design-based/weighted 가 공학·화학 맥락)
NOISE = re.compile(r"quantum|peptide|protein design|optical|defect detect|chromatograph|lipolytica|"
                   r"bird sound|audiometric system|inventory|housing price|photodynamic|nanoparticle|"
                   r"fermentation|3d geometry|electronic nose|transformer and|plateau lake|"
                   r"higher education|anthropomorph|physical education|crispr|manufacturing", re.I)


def main():
    pool = {}
    for tag, qq in QUERIES:
        tot, items = epmc_all(qq, cap=3000, label=tag)
        for v in items:
            k = v.get("id") or v.get("doi")
            if k in pool:
                pool[k]["query_layers"].append(tag)
            else:
                r = slim(v, tag); r["query_layers"] = [tag]; pool[k] = r
        print(f"  {tag}: hits {tot} · 수집 {len(items)} · 누적 {len(pool)}", flush=True)
    recs = [r for r in pool.values() if not NOISE.search((r.get("title") or "") + " " + (r.get("journal") or ""))]
    for r in recs:
        t = ((r.get("title") or "") + " " + (r.get("abstract") or "")).lower()
        tags = []
        if re.search(r"nhanes|national health and nutrition", t): tags.append("NHANES")
        if re.search(r"demographic and health survey|\bdhs\b", t): tags.append("DHS")
        if re.search(r"charls|china health and retirement", t): tags.append("CHARLS")
        if re.search(r"knhanes|korea national health", t): tags.append("KNHANES")
        if re.search(r"brfss|nsch|nhis|meps|nsduh|yrbs", t): tags.append("기타 미국조사")
        r["datasets"] = tags
        kind = []
        if re.search(r"lesson|impact of (survey )?weight|should we|whether to|comparison of|compar\w+ (survey-)?weighted|methodolog|framework|guidance|recommend|tutorial|primer", t): kind.append("방법론·비교")
        if re.search(r"imputation|missing data", t): kind.append("결측")
        if re.search(r"cross-?validation|model performance|variance estimation|calibration|covariate shift|inference", t): kind.append("성능추정·추론")
        if re.search(r"\breview\b|systematic|scoping", t): kind.append("리뷰")
        r["kind"] = kind or ["응용"]
    # 핵심(core) 판정 — 제목이 '방법 자체'를 다루는 것만. 단순 응용은 부록으로 밀어낸다
    CORE_T = re.compile(r"complex (survey|sampl)|survey[- ]weight|sampling weight|design-based|weighted machine|"
                        r"accounting (for )?(sampl|survey|design)|impact of (survey |sampling )?weight|"
                        r"lessons learned|methodolog|framework|guidance|tutorial|primer|"
                        r"systematic review|scoping review|comparison of|comparing|evaluat\w+ (imputation|method)|"
                        r"variance estimation|standard error|inference|pseudo-population|super learner|"
                        r"cross-?validation|model performance|covariate shift|calibration", re.I)
    for r in recs:
        t = r.get("title") or ""
        r["core"] = bool(CORE_T.search(t)) and bool(re.search(r"survey|sampl|weight|design-based|complex", t, re.I))
    recs.sort(key=lambda r: (not r["core"], -(r.get("cited") or 0), -(r.get("year") or 0)))
    out = dict(searched_on=time.strftime("%Y-%m-%d"), queries=[q for _, q in QUERIES],
               n=len(recs), records=recs)
    dump(out, os.path.join(REF, "survey_ml_methods.json"))

    L = []; A = L.append
    A("# 복합표본설계 × 머신러닝 — 방법론 문헌\n")
    A(f"생성 {time.strftime('%Y-%m-%d')} · `python tools/collect_survey_ml.py` · 기계용 `survey_ml_methods.json`\n")
    A("**용도.** 초고 B·C 의 논증 근거. \"KNHANES 연구가 가중치를 안 쓴다\" 는 비판은 "
      "**쓸 방법이 이미 문헌에 있는데도 안 쓴다** 를 보여야 성립한다. 아래가 그 방법론 문헌이다.\n")
    from collections import Counter
    core = [r for r in recs if r["core"]]
    A(f"수집 {len(recs)}건 · **핵심(방법 자체를 다룬 것) {len(core)}건** · 나머지는 응용 사례로 부록에 목록만 둔다\n")
    A("## 핵심 문헌\n")
    for kind in ("방법론·비교", "성능추정·추론", "결측", "리뷰", "응용"):
        g = [r for r in core if kind in r["kind"]]
        if not g: continue
        A(f"### {kind} — {len(g)}건\n")
        for r in g[:40]:
            ds = ("[" + "·".join(r["datasets"]) + "] ") if r["datasets"] else ""
            A(f"#### {r.get('year')} · 피인용 {r.get('cited') or 0} · {ds}{(r.get('journal') or '')[:45]}")
            A(f"**{r.get('title')}**  ")
            A((f"[doi](https://doi.org/{r['doi']})  " if r.get("doi") else "") )
            ab = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.get("abstract") or "")).strip()
            A("> " + (ab[:550].rsplit(" ", 1)[0] + " …" if len(ab) > 550 else ab) if ab else "> _초록 없음_")
            A("")
    rest = [r for r in recs if not r["core"]]
    A(f"## 부록 — 가중치를 실제로 쓴 응용 사례 {len(rest)}건 (목록만)\n")
    A("| 연도 | 피인용 | 자료 | 제목 |"); A("|---:|---:|---|---|")
    for r in rest[:120]:
        A(f"| {r.get('year')} | {r.get('cited') or 0} | {'·'.join(r['datasets']) or '-'} | {(r.get('title') or '')[:95]} |")
    A("")
    open(os.path.join(REF, "SURVEY_ML_METHODS.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  SURVEY_ML_METHODS.md — {len(recs)}건")


if __name__ == "__main__":
    main()
