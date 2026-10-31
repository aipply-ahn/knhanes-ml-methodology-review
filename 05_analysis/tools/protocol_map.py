"""분석 프로토콜 전수 지도화 — 포함 130편의 프로토콜을 13개 영역으로 구조화한다.

    python tools/protocol_map.py

두 층으로 나눈다.
  (1) 프로토콜 표 — 논문별 13개 영역. `data/PROTOCOL_MAP.md` (부록용) · 백데이터 TSV
  (2) 이질성 지표 — 성능을 좌우하는 분석 결정이 얼마나 보고되었는지의 비율

**(2)는 아직 발표용 수치가 아니다.** 전문 정규식 판정의 정확도를 사람이 읽은 8편으로 검증한
결과 일치율이 73%에 그쳤다(`tools/validate_protocol_map.py`). 규칙을 8편에 더 맞추면 과적합이
되므로, 이 지표는 **1차 추출과 같은 방식의 구조화 2차 추출**로 확정해야 한다. 지금 값은
자릿수를 가늠하는 예비 추정으로만 쓴다. 반면 (1)의 프로토콜 표와 아래 분포표는 1차 구조화
추출에서 나오므로 그대로 쓸 수 있고, 연차 통합 가중치(S3)는 사람이 정의한 규칙의 PROBAST
판정이라 확정값이다.

**근거의 층위를 구분한다.** 전문을 확보한 논문은 원문 마크다운(`references/md/<key>.md`)을 직접
검색하고, 초록만 있는 논문은 판정 대상에서 빼고 분모에 넣지 않는다. 우리 추출문에 없다는 것과
논문에 없다는 것은 다르므로, 원문에서 확인 가능한 항목만 원문으로 판정한다.
"""
import os, sys, re, json, glob, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, DER, load, dump
import analyze_extraction as ae

REF = os.path.join(PROJ, "references")
R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
E = {}
for f in sorted(glob.glob(os.path.join(PROJ, "data", "extraction", "*.json"))):
    d = load(f)
    if R.get(d["key"], {}).get("verdict") == "INCLUDE":
        E[d["key"]] = d
P = {k: load(os.path.join(PROJ, "data", "probast", k + ".json"))
     for k in E if os.path.exists(os.path.join(PROJ, "data", "probast", k + ".json"))}


def _norm(t):
    """PDF 추출 텍스트의 줄바꿈을 공백으로 편다."""
    return re.sub(r"\s+", " ", t)


def fulltext(k):
    """전문 마크다운. 초록만 확보한 논문은 None."""
    p = os.path.join(REF, "md", k + ".md")
    if not os.path.exists(p): return None
    s = open(p, encoding="utf-8").read()
    return s if "full_text: true" in s[:600] else None


FT = {k: (_norm(v) if v else None) for k, v in ((k, fulltext(k)) for k in E)}
HAS_FT = [k for k, v in FT.items() if v]


# ── 이질성 지표 ───────────────────────────────────────────────────────────────
# 각 지표는 (이름, 설명, 판정함수). 판정함수는 전문 문자열을 받아 True/False/None(판단불가).
def _any(t, pat): return bool(re.search(pat, t, re.I))


def m_cascade(t, k):
    """표본 선정을 단계별 인원과 함께 제시했는가.

    참여자 흐름도라는 말만으로는 인정하지 않는다 — lee2019predictive 의 'flowchart' 는
    대상자 흐름도가 아니라 분석 절차도였다. 제외 사유와 인원이 함께 나와야 한다.
    """
    return _any(t, r"exclud\w*[^.]{0,100}?[\[\(]?\s*n\s*=\s*[\d,]{3,}|"
                   r"[\d,]{3,}\s+(?:participants|subjects|individuals|people|persons|women|men)"
                   r"\s+(?:were\s+)?(?:excluded|removed)|"
                   r"(?:excluded|removed)\s+[\d,]{3,}\s+(?:participants|subjects|individuals)")


def m_outcome(t, k):
    """결과변수 정의에 절단값 또는 표준 진단기준이 명시되어 있는가."""
    return _any(t, r"(?:defined|classified|categori[sz]ed|considered)\s+as[^.]{0,150}?"
                   r"(?:[<>≥≤]\s*=?\s*-?\d|cut-?off|T-?score|score\s+(?:of|≥|>=)\s*\d|"
                   r"\d+\s*(?:mg/dL|mmHg|kg/m))|"
                   r"cut-?off\s+(?:point|value|score)[^.]{0,60}?\d|"
                   r"T-?score\s*[≤<]\s*-?\s*2\.5")


def m_misscode(t, k):
    """결측 처리에서 대상 변수 또는 무응답 코드를 구체적으로 밝혔는가.

    'missing values were excluded' 같은 일반 서술은 인정하지 않는다.
    """
    return _any(t, r"missing\s+(?:data|values?)\s+(?:for|in|on)\s+(?:the\s+)?"
                   r"(?:following|variables?|[A-Z][\w\-]{2,})|"
                   r"(?:don'?t know|do not know|unknown|not applicable|refused to answer|no response)"
                   r"[^.]{0,60}?(?:treated|coded|considered|regarded)\s+as\s+missing|"
                   r"coded\s+as\s+(?:8|9|99|999)\b|"
                   r"missing\s+(?:values?|data)[^.]{0,80}?(?:imputed|replaced)\s+"
                   r"(?:with|by|using)\s+(?:the\s+)?[a-z]{3,}")


def m_leak(t, k):
    """전처리·변수선택을 학습자료 안에서만 수행했다고 밝혔는가."""
    act = r"(?:select\w*|impute\w*|imputation|scal\w+|normali\w+|standardi\w+|"
    act += r"variables?|features?|predictors?)"
    return _any(t, act + r"[^.]{0,100}?(?:within|inside|only\s+(?:on|in)|using|with|on|in)\s+"
                       r"(?:the\s+)?training\s+(?:set|data|dataset|sample|fold)|"
                r"(?:within|inside|on|using|with|in)\s+(?:the\s+)?training\s+"
                r"(?:set|data|dataset|sample|fold)[^.]{0,100}?" + act + r"|"
                r"nested\s+cross-?validation|"
                r"(?:avoid|prevent)\w*\s+(?:data\s+)?leakage")


def m_hyper(t, k):
    """초매개변수 선택 절차(탐색 방법 또는 범위)를 보고했는가."""
    return _any(t, r"grid\s*-?\s*search|random(?:i[sz]ed)?\s*-?\s*search|bayesian\s+optimi|"
                   r"optuna|hyperopt|"
                   r"hyper-?parameters?[^.]{0,80}?(?:search|tun\w+|optimi\w+|select\w+|determin\w+)|"
                   r"(?:tun\w+|optimi[sz]\w+)[^.]{0,60}?hyper-?parameters?")


def m_valsep(t, k):
    """독립 검정 평가와 내부 교차검증을 구분해 보고했는가."""
    cv = _any(t, r"cross-?validat|\b\d{1,2}-?fold\b")
    ho = _any(t, r"(?:test|hold-?out|validation|training)\s+(?:set|data|dataset|cohort|sample)|"
                 r"split[^.]{0,60}?(?:train|test)|"
                 r"\b\d{1,2}\s*[:/]\s*\d{1,2}\s*(?:split|ratio|=)|"
                 r"\b(?:70|75|80|60)\s*%[^.]{0,40}?(?:train|test)")
    return cv and ho


def m_ci(t, k):
    """성능 추정치에 신뢰구간이나 반복 간 변동을 제시했는가."""
    return _any(t, r"95\s*%\s*(?:CI|confidence)|confidence\s+intervals?|"
                   r"(?:standard deviations?|SD|IQR)\s+(?:of|across|over|between)\s+"
                   r"(?:the\s+)?(?:folds?|repetitions?|iterations?|runs?)|"
                   r"(?:AUC|AUROC|accuracy)[^.]{0,30}?\d?\.\d+\s*±\s*0?\.\d+")


METRICS = [
    ("표본 선정 단계별 인원 제시", m_cascade),
    ("결과변수 절단값·기준 명시", m_outcome),
    ("결측 대상 변수·코드 구체화", m_misscode),
    ("전처리·변수선택을 학습자료 내에서 수행 명시", m_leak),
    ("초매개변수 선택 절차 보고", m_hyper),
    ("독립 검정과 교차검증을 구분", m_valsep),
    ("성능에 신뢰구간·변동 제시", m_ci),
]


def per_study():
    rows = []
    for k, d in sorted(E.items(), key=lambda x: -(R[x[0]].get("year") or 0)):
        p = (P.get(k) or {}).get("probast", {}).get("D4", {})
        w = ae.waves(d.get("knhanes_waves"))
        rows.append({
            "key": k, "year": R[k].get("year"), "journal": R[k].get("journal"),
            "출판유형": R[k].get("publication_type_ko") or "확인 안 됨",
            "결과영역": R[k].get("category"),
            "조사연차": f"{w[0]}–{w[1]}" if w and w[0] != w[1] else (str(w[0]) if w else ""),
            "연차범위": ae.wave_scope(d.get("knhanes_waves")) or "불명",
            "최종 n": d.get("n_final"),
            "과제": d.get("task"),
            "결측처리": ae.missing(d.get("missing_handling")),
            "불균형": ae.imbalance(d.get("imbalance_handling") or d.get("preprocessing")),
            "검증": "·".join(ae.validation(d.get("validation"))),
            "성능보고깊이": ae.metric_depth(d.get("metrics")),
            "변수중요도": "·".join(ae.importance_kind(d.get("interpretability"))),
            "사후분석": "·".join(ae.posthoc(" ".join(str(d.get(x) or "") for x in
                                  ("metrics", "validation", "findings", "interpretability", "notes")))) or "없음",
            "가중치": ae.weights(d.get("survey_weights")),
            "S1 가중치": p.get("S1", ""), "S2 층화집락": p.get("S2", ""), "S3 통합가중치": p.get("S3", ""),
            "최고모형": re.sub(r"\s+", " ", str(d.get("best_model") or ""))[:90],
            "코드·자료공개": ae.interp(d.get("code_data_availability")) if hasattr(ae, "interp") else
                            (d.get("code_data_availability") or "")[:40],
            "근거": d.get("source"),
        })
    return rows


def main():
    rows = per_study()
    # 이질성 지표 — 전문 확보분만
    res = {}
    for name, fn in METRICS:
        yes = sum(1 for k in HAS_FT if fn(FT[k], k))
        res[name] = {"yes": yes, "n": len(HAS_FT), "pct": round(100 * yes / len(HAS_FT), 1)}
    # 조사설계는 PROBAST 판정을 그대로 쓴다(이미 사람이 정의한 규칙으로 판정됨)
    s3 = [P[k]["probast"]["D4"].get("S3") for k in P]
    pooled = [x for x in s3 if x != "NA"]
    res["연차 통합 가중치 산출 기술"] = {"yes": sum(1 for x in pooled if x == "Y"),
                                  "n": len(pooled), "pct": round(100*sum(1 for x in pooled if x=="Y")/max(1,len(pooled)), 1)}
    # 완전한 프로토콜 복원 가능 — 위 7개를 모두 충족
    full = sum(1 for k in HAS_FT if all(fn(FT[k], k) for _, fn in METRICS))
    res["분석 프로토콜 전체 복원 가능(7개 모두 충족)"] = {"yes": full, "n": len(HAS_FT),
                                                "pct": round(100 * full / len(HAS_FT), 1)}
    dump({"per_study": rows, "heterogeneity_provisional": res,
          "heterogeneity_status": "예비 추정 — 정규식 판정 정확도 73%(8편 검증). 2차 구조화 추출 필요",
          "n_include": len(E), "n_fulltext": len(HAS_FT)},
         os.path.join(DER, "protocol_map.json"))

    L = ["# 분석 프로토콜 전수 지도", "",
         f"포함 {len(E)}편. 이질성 지표는 전문을 확보한 {len(HAS_FT)}편의 **원문을 직접 검색**해 판정했다.",
         "우리 추출문이 아니라 논문 원문을 근거로 삼았으므로, '추출에 없음'과 '논문에 없음'이 섞이지 않는다.",
         "초록만 확보한 논문은 원리적으로 확인이 불가능하므로 분모에서 제외했다.", "",
         "## 성능을 좌우하는 분석 결정의 보고율 (예비 추정)", "",
         "> **주의.** 아래 비율은 전문 정규식 판정이며, 사람이 읽은 8편과 대조한 일치율이 73%다.",
         "> 발표 수치로 쓰려면 1차 추출과 같은 방식의 구조화 2차 추출이 필요하다.",
         "> 단 '연차 통합 가중치 산출 기술' 은 PROBAST S3 판정이므로 확정값이다.", "",
         "| 항목 | 보고 | 분모 | 비율 |", "|---|---:|---:|---:|"]
    for name, v in res.items():
        L.append(f"| {name} | {v['yes']} | {v['n']} | {v['pct']}% |")
    L += ["", "## 프로토콜 요소별 분포", ""]
    for col in ("연차범위", "결측처리", "불균형", "검증", "성능보고깊이", "가중치"):
        c = {}
        for r in rows: c[r[col]] = c.get(r[col], 0) + 1
        L += [f"### {col}", "", "| 값 | 편수 |", "|---|---:|"]
        L += [f"| {k} | {v} |" for k, v in sorted(c.items(), key=lambda x: -x[1])]
        L.append("")
    L += ["## 논문별 상세", "",
          "전체 표는 `data/backdata/07_protocol_map.tsv` 에 있다(본문에는 요약만 두고 부록으로 보낸다).", ""]
    open(os.path.join(PROJ, "data", "PROTOCOL_MAP.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    bd = os.path.join(PROJ, "data", "backdata"); os.makedirs(bd, exist_ok=True)
    with open(os.path.join(bd, "07_protocol_map.tsv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(rows)

    print(f"  data/PROTOCOL_MAP.md · data/backdata/07_protocol_map.tsv ({len(rows)}편)")
    print(f"  이질성 지표 — 전문 {len(HAS_FT)}편 기준")
    for name, v in res.items():
        print(f"    {name:<34} {v['yes']:>3}/{v['n']:<4} {v['pct']:>5.1f}%")


if __name__ == "__main__":
    main()
