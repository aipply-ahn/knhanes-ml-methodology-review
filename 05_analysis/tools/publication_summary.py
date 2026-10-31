"""Crossref 검증 결과 정리 → data/PUBLICATION_CHECK.md

    python tools/publication_summary.py

우리 refs.json 의 journal 문자열이 아니라 Crossref 등록 메타데이터를 근거로 출판 유형을 확정한다.
프리프린트는 후속 출판본 후보를 함께 제시한다. 판정 변경은 사람이 확인한 뒤에 한다.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, DER, load

TYPE_KO = {"journal-article": "학술지 원저", "posted-content": "프리프린트",
           "proceedings-article": "학회 논문", "book-chapter": "단행본 장",
           "report": "보고서", None: "확인 불가"}


def main():
    C = load(os.path.join(DER, "publication_check.json"))
    R = {r["key"]: r for r in load(os.path.join(PROJ, "references", "refs.json"))}
    rows = []
    for k, v in C.items():
        m = v.get("crossref") or {}
        t = m.get("type")
        rows.append({
            "key": k, "year": v.get("year"), "doi": v.get("doi"),
            "crossref_type": t, "유형": TYPE_KO.get(t, t or "확인 불가"),
            "crossref_journal": m.get("container"), "our_journal": v.get("our_journal"),
            "issn": ";".join(m.get("issn") or []) if m.get("issn") else "",
            "publisher": m.get("publisher"),
            "권호쪽": " ".join(x for x in [m.get("volume"), m.get("issue"),
                                        m.get("page") or m.get("article_number")] if x),
            "error": m.get("error"),
            "published_rel": ";".join(v.get("published_doi_from_relation") or []),
            "cands": v.get("published_candidates") or [],
        })
    cnt = collections.Counter(r["유형"] for r in rows)
    L = ["# 포함 논문의 출판 실체 검증 (Crossref)", "",
         f"포함 {len(rows)}편의 DOI 를 Crossref 에 조회해 등록 유형·학술지·ISSN·권호쪽을 확인했다.",
         "우리 서지 문자열이 아니라 등록 메타데이터가 근거다.", "",
         "## 출판 유형", "", "| 유형 | 편수 |", "|---|---:|"]
    L += [f"| {t} | {n} |" for t, n in cnt.most_common()]

    bad = [r for r in rows if r["error"]]
    if bad:
        L += ["", "## DOI 조회 실패", "", "| 논문 | DOI | 사유 |", "|---|---|---|"]
        L += [f"| {r['key']} | {r['doi']} | {r['error']} |" for r in bad]

    pre = [r for r in rows if r["crossref_type"] == "posted-content"]
    if pre:
        L += ["", "## 프리프린트와 후속 출판 여부", "",
              "`is-preprint-of` 관계가 등록되어 있으면 그것을 쓰고, 없으면 제목으로 학술지 원저를 검색했다.", "",
              "| 논문 | 연도 | 프리프린트 DOI | 후속 출판 후보 |", "|---|---|---|---|"]
        for r in pre:
            if r["published_rel"]:
                c = f"**관계 등록됨** {r['published_rel']}"
            elif r["cands"]:
                c = "<br>".join(f"유사 {x['sim']} · {x['doi']} · {x['container']} ({x['year']})"
                                for x in r["cands"][:3])
            else:
                c = "찾지 못함"
            L.append(f"| {r['key']} | {r['year']} | {r['doi']} | {c} |")

    conf = [r for r in rows if r["crossref_type"] == "proceedings-article"]
    if conf:
        L += ["", "## 학회 논문", "", "| 논문 | 연도 | 학회 | DOI |", "|---|---|---|---|"]
        L += [f"| {r['key']} | {r['year']} | {r['crossref_journal']} | {r['doi']} |" for r in conf]

    mismatch = [r for r in rows if r["crossref_journal"] and r["our_journal"]
                and r["crossref_journal"].lower()[:18] != str(r["our_journal"]).lower()[:18]]
    if mismatch:
        L += ["", "## 우리 서지와 Crossref 학술지명이 다른 건", "",
              "| 논문 | 우리 기록 | Crossref |", "|---|---|---|"]
        L += [f"| {r['key']} | {r['our_journal']} | {r['crossref_journal']} |" for r in mismatch]

    noissn = [r for r in rows if r["crossref_type"] == "journal-article" and not r["issn"]]
    if noissn:
        L += ["", "## 학술지 원저이나 ISSN 미등록", "", "| 논문 | 학술지 | DOI |", "|---|---|---|"]
        L += [f"| {r['key']} | {r['crossref_journal']} | {r['doi']} |" for r in noissn]

    open(os.path.join(PROJ, "data", "PUBLICATION_CHECK.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("  data/PUBLICATION_CHECK.md")
    for t, n in cnt.most_common(): print(f"    {n:>4}  {t}")
    print(f"\n  프리프린트 {len(pre)} · 학회 논문 {len(conf)} · 조회 실패 {len(bad)} · 학술지명 불일치 {len(mismatch)}")
    return rows


if __name__ == "__main__":
    main()
