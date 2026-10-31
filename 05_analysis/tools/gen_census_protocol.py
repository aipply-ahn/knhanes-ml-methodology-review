"""planning/CENSUS.md 의 AUTOGEN 블록을 raw/derived 실측으로 다시 쓴다.

    python tools/gen_census_protocol.py
"""
import glob, sys
from collections import Counter
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def latest(pat):
    fs = sorted(glob.glob(os.path.join(RAW, pat)))
    return load(fs[-1]) if fs else None


def main():
    ep, oa, pm, kd = latest("epmc_*.json"), latest("openalex_*.json"), latest("pubmed_*.json"), latest("kdca_*.json")
    C = load(os.path.join(DER, "corpus.json"))
    S = load(os.path.join(DER, "screen.json"))
    vp = os.path.join(DER, "verdicts.json")
    V = load(vp) if os.path.exists(vp) else {}
    SF = load(os.path.join(DER, "final_selection_flow.json"))
    L = []; A = L.append
    A(f"*생성 {time.strftime('%Y-%m-%d')} — `tools/gen_census_protocol.py` 실측. 손으로 고치지 않는다.*\n")
    A("## §3 실측 — 검색원별 건수\n")
    A("| 층 | 검색원 | 검색일 | 검색식 | hits | 수집 | 초록 |")
    A("|---|---|---|---|---:|---:|---:|")
    if ep:
        for k, v in ep["layers"].items():
            A(f"| {k} | Europe PMC | {ep['searched_on']} | `{v['query'][:90]}…` | {v['hits']:,} | {v['retrieved']:,} | |")
        A(f"| A+B | Europe PMC 고유 | | | | {ep['n_unique']:,} | {ep['n_with_abstract']:,} |")
    if oa:
        for x in oa["queries"]:
            A(f"| C | OpenAlex | {oa['searched_on']} | `\"{x['term']}\"` | {x['hits']:,} | {x['retrieved']:,} | |")
        A(f"| C | OpenAlex 고유 | | | | {oa['n_unique']:,} | {oa['n_with_abstract']:,} |")
    if pm:
        A(f"| D | PubMed | {pm['searched_on']} | `{pm['term'][:90]}…` | {pm['hits']:,} | {len(pm['pmids']):,} | EPMC 누락 {pm['n_missing_from_epmc']} |")
    if kd:
        A(f"| E | KDCA 논문목록 | {kd['fetched_on']} | 전건 | {kd['count_reported']:,} | {kd['n_unique']:,} | (초록 없음) |")
    kp = os.path.join(REF, "kci_refs.json")
    if os.path.exists(kp):
        kr = load(kp)
        A(f"| F | KCI 보완검색 | 2026-09-05 | KNHANES 명칭 × ML/AI 용어 301개 조합 | {len(kr):,} | {len(kr):,} | {sum(bool(r.get('abstract_ko') or r.get('abstract_en')) for r in kr):,} |")
    A("")
    if ep:
        A("### ML 용어별 교차 건수 (KNHANES ∧ 용어, 제목/초록)\n")
        A("| 용어 | Europe PMC | PubMed | Crossref(참고) |"); A("|---|---:|---:|---:|")
        for t in ep["term_counts"]:
            A(f"| {t['term']} | {t['epmc_title_abs']} | {t['pubmed_tiab'] if t['pubmed_tiab'] is not None else '-'} | {t['crossref_bibliographic'] if t['crossref_bibliographic'] is not None else '-'} |")
        A("")
    if kd:
        A("### KDCA 목록 구성\n")
        ct = Counter(r["paper_type"] for r in kd["records"]); cl = Counter(r["lang"] for r in kd["records"])
        A("| 유형 | 건수 |"); A("|---|---:|")
        for k, v in ct.most_common(): A(f"| {k} | {v} |")
        A(f"| (언어) ENG | {cl.get('ENG', 0)} |"); A(f"| (언어) KOR | {cl.get('KOR', 0)} |")
        yrs = Counter(r["year"] for r in kd["records"] if r.get("year"))
        A(""); A("연도: " + " · ".join(f"{y} {yrs[y]}" for y in sorted(yrs)) + "\n")
        if C.get("kdca"):
            k = C["kdca"]
            A(f"corpus 연결: DOI {k['doi']} · 제목 {k['title']} · Crossref→기존 {k['crossref']} · Crossref→신규 {k['crossref_new']} · **미연결(KDCA 단독) {k['unmatched']}**\n")
    A("### 문헌 흐름\n")
    A("```")
    f = SF["flow"]
    A(f"수집원 합계 (중복 포함)         {SF['sources']['total_before_cross_source_deduplication']:>7,}")
    A(f"  → 중복 제거                    {f['duplicates_removed']:>7,}")
    A(f"  → 고유 레코드 선별             {f['unique_records_screened']:>7,}")
    A(f"       선별 후 미진입             {f['terminology_exclusions']:>7,}")
    A(f"  → 후보 적격성 판정                  {f['records_assessed_against_eligibility']:>7,}")
    A(f"       부적격 보고                {f['ineligible_reports']:>7,}")
    A(f"       ML 인접 별도목록           {f['ml_adjacent_reports_catalogued']:>7,}")
    A(f"  → 연구군 연결 대상 적격 보고    {f['eligible_reports_entering_family_linkage']:>7,}")
    A(f"       추가·동반 연결 보고         {f['additional_or_companion_reports_linked']:>7,}")
    A("       전문 확보 시도·미확보·실제 평가: 전체 건수 불명 (적격군 0으로 추정하지 않음)")
    A(f"  → 고유 완전보고 연구 포함        {f['unique_full_report_studies_included']:>7,}")
    if V:
        cats = Counter(v.get("category") for v in V.values() if v.get("verdict") == "INCLUDE")
    refs = load(os.path.join(REF, "refs.json")) if os.path.exists(os.path.join(REF, "refs.json")) else []
    if refs:
        inc = [r for r in refs if r["verdict"] == "INCLUDE"]
        A(f"  → PDF 확보 (INCLUDE 중)      {sum(1 for r in inc if r.get('pdf_file')):>7,} / {len(inc):,}")
    A("```\n")
    if S:
        A("### T1 적중 용어 분포\n")
        c = Counter(t for x in S["rows"] if x["tier"] == "T1" for t in x["t1"])
        A("| 용어 | 논문 수 |"); A("|---|---:|")
        for k, v in c.most_common(): A(f"| {k} | {v} |")
        A("")
        A("### 선별 통과 논문의 출처 (T1)\n")
        c = Counter(",".join(sorted(x["sources"] or [])) for x in S["rows"] if x["tier"] == "T1")
        A("| 출처 조합 | 건수 |"); A("|---|---:|")
        for k, v in c.most_common(): A(f"| {k} | {v} |")
        A("")
    if V:
        A("### 판정 사유 분포\n")
        c = Counter((v.get("verdict"), v.get("reason", "")[:40]) for v in V.values() if v.get("verdict") == "EXCLUDE")
        A("| 제외 사유 | 건수 |"); A("|---|---:|")
        for (vd, k), n in c.most_common(20): A(f"| {k} | {n} |")
        A("")
        # Included-study topics are derived only after final eligibility and
        # family linkage.  They therefore belong in Additional file 5, not in
        # this report-level search-strategy appendix.
    A("### 재현\n")
    A("```bash\nPY=/home/ahnbi/.conda/envs/myclaude/bin/python\n$PY tools/census_epmc.py && $PY tools/census_openalex.py && $PY tools/census_pubmed.py && $PY tools/census_kdca.py\n"
      "$PY tools/census_merge.py && $PY tools/census_kdca_match.py && $PY tools/census_screen.py\n"
      "# verdicts.json 수동 판정\n$PY tools/make_refs.py && $PY tools/fetch_pdf.py && $PY tools/make_refs.py && $PY tools/gen_census_protocol.py\n```")
    body = "\n".join(L)
    for p in (os.path.join(PROJ, "planning", "CENSUS.md"),
              os.path.join(PROJ, "manuscript", "submission", "appendices", "appendix4_search_strategy.md")):
        s = open(p, encoding="utf-8").read()
        replacement = "<!-- AUTOGEN:census -->\n" + body + "\n<!-- /AUTOGEN:census -->"
        if "<!-- /AUTOGEN:census -->" in s:
            s = re.sub(r"<!-- AUTOGEN:census -->.*?<!-- /AUTOGEN:census -->", replacement, s, flags=re.S)
        else:
            # Older Additional file 3 snapshots lost the closing sentinel;
            # replace the stale generated tail rather than silently doing nothing.
            s = re.sub(r"<!-- AUTOGEN:census -->.*\Z", replacement, s, flags=re.S)
        open(p, "w", encoding="utf-8").write(s)
        print("  " + os.path.relpath(p, PROJ) + " AUTOGEN 갱신")


if __name__ == "__main__":
    main()
