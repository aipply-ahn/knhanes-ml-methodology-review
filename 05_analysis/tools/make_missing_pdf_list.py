"""원문(PDF) 미확보 논문 목록 — 사용자가 직접 확인할 수 있게 링크와 시도 이력을 담는다.

    python tools/make_missing_pdf_list.py

출력 data/PDF_MISSING.tsv (엑셀) · data/PDF_MISSING.md (사람용, 클릭 링크)
"""
import sys, os, json, glob, csv, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, load
E = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/extraction/*.json")))}
P = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/probast/*.json")))}

SETS = [("본 리뷰 포함 논문", os.path.join(REF, "refs.json"), ("INCLUDE", "INCLUDE_ADJACENT", "UNCERTAIN")),
        ("본보기 리뷰", os.path.join(REF, "benchmark_reviews.json"), ("INCLUDE", "UNCERTAIN"))]



# DOI 접두사 → (플랫폼, 직접 URL 패턴, 사용자가 받을 수 있는가)
PLATFORM = [
 ("10.1016/",  "ScienceDirect",      "https://www.sciencedirect.com/science/article/pii/{PII}", "예 — 기관 구독"),
 ("10.1007/",  "SpringerLink",       "https://link.springer.com/article/{DOI}",                 "예 — 기관 구독"),
 ("10.1140/",  "SpringerLink",       "https://link.springer.com/article/{DOI}",                 "예 — 기관 구독"),
 ("10.1186/",  "BMC (오픈액세스)",    "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.1111/",  "Wiley Online Library","https://onlinelibrary.wiley.com/doi/{DOI}",              "예 — 기관 구독"),
 ("10.1002/",  "Wiley Online Library","https://onlinelibrary.wiley.com/doi/{DOI}",              "예 — 기관 구독"),
 ("10.1097/",  "LWW (Wolters Kluwer)","https://journals.lww.com/ (DOI 검색)",                   "예 — 기관 구독"),
 ("10.1109/",  "IEEE Xplore",        "https://ieeexplore.ieee.org/document/ (DOI 검색)",        "예 — 기관 구독"),
 ("10.1177/",  "SAGE Journals",      "https://journals.sagepub.com/doi/{DOI}",                  "예 — 기관 구독"),
 ("10.1093/",  "Oxford Academic",    "https://academic.oup.com/ (DOI 검색)",                    "예 — 기관 구독"),
 ("10.3390/",  "MDPI (오픈액세스)",   "https://doi.org/{DOI}",                                   "예 — 무료, 서버만 차단됨"),
 ("10.2196/",  "JMIR (오픈액세스)",   "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.1371/",  "PLOS (오픈액세스)",   "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.1038/",  "Nature Portfolio",   "https://www.nature.com/articles/{SUFFIX}",                "예 — 기관 구독"),
 ("10.3346/",  "JKMS (오픈액세스)",   "https://jkms.org/ (DOI 검색)",                            "예 — 무료"),
 ("10.4178/",  "역학과 건강 (오픈액세스)", "https://e-epih.org/ (DOI 검색)",                      "예 — 무료"),
 ("10.7762/",  "CNR 한국영양학회",     "https://e-cnr.org/ (DOI 검색)",                           "예 — 무료"),
 ("10.3349/",  "Yonsei Medical Journal", "https://eymj.org/ (DOI 검색)",                        "예 — 무료"),
 ("10.4162/",  "Nutrition Research and Practice", "https://e-nrp.org/ (DOI 검색)",              "예 — 무료"),
 ("10.5009/",  "Gut and Liver",      "https://www.gutnliver.org/ (DOI 검색)",                    "예 — 무료"),
 ("10.21203/", "Research Square 프리프린트", "https://doi.org/{DOI}",                            "예 — 무료"),
 ("10.1101/",  "medRxiv/bioRxiv 프리프린트", "https://doi.org/{DOI}",                            "예 — 무료"),
 ("10.31222/", "OSF 프리프린트",       "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.20944/", "Preprints.org",      "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.1080/",  "Taylor & Francis",   "https://www.tandfonline.com/doi/{DOI}",                    "예 — 기관 구독"),
 ("10.1136/",  "BMJ Journals",       "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1001/",  "JAMA Network",       "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1227/",  "Wolters Kluwer",     "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.3389/",  "Frontiers (오픈액세스)", "https://doi.org/{DOI}",                                "예 — 무료"),
 ("10.7759/",  "Cureus (오픈액세스)",  "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.1123/",  "Human Kinetics",     "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1210/",  "Endocrine Society",  "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1167/",  "ARVO Journals",      "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.21037/", "AME Publishing",     "https://doi.org/{DOI}",                                    "예 — 무료"),
 ("10.1159/",  "Karger",             "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1089/",  "Mary Ann Liebert",   "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1017/",  "Cambridge Core",     "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.1155/",  "Hindawi/Wiley",      "https://doi.org/{DOI}",                                    "예 — 무료"),
 ("10.1200/",  "ASCO Journals",      "https://doi.org/{DOI}",                                    "예 — 기관 구독"),
 ("10.32388/", "Qeios 프리프린트",     "https://doi.org/{DOI}",                                   "예 — 무료"),
 ("10.21480/", "위험관리연구 (KCI)",   "KCI 또는 학회 홈페이지",                                   "확인 필요 — 국내 학회지"),
]


def platform_of(doi, journal, pmcid):
    d = (doi or "").lower()
    if pmcid:
        return ("PubMed Central", f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/", "예 — 무료")
    for pre, name, url, avail in PLATFORM:
        if d.startswith(pre):
            suffix = doi.split("/", 1)[1] if doi and "/" in doi else ""
            target = url.replace("{DOI}", doi or "").replace("{SUFFIX}", suffix)
            if "{PII}" in target or "(DOI 검색)" in target: target = f"https://doi.org/{doi}"
            return (name, target, avail)
    if not doi:
        return ("DOI 없음 — 학술지 홈페이지에서 직접", "", "확인 필요")
    return (f"기타 (DOI 접두 {d.split('/')[0]})", f"https://doi.org/{doi}", "확인 필요")

def pub_hint(doi, journal):
    d = (doi or "").lower(); j = (journal or "").lower()
    if d.startswith("10.1016/"): return "Elsevier — ScienceDirect. 기관 로그인 필요"
    if d.startswith(("10.1007/", "10.1140/")): return "Springer — link.springer.com"
    if d.startswith("10.1111/"): return "Wiley — onlinelibrary.wiley.com"
    if d.startswith("10.1097/"): return "LWW/Wolters Kluwer"
    if d.startswith("10.1109/"): return "IEEE Xplore"
    if d.startswith("10.1177/"): return "SAGE"
    if d.startswith("10.1093/"): return "Oxford University Press"
    if d.startswith("10.3390/"): return "MDPI — 오픈액세스이나 서버에서 봇 차단(403). 브라우저로 받으면 됨"
    if d.startswith("10.2196/"): return "JMIR — 오픈액세스"
    if d.startswith("10.1002/"): return "Wiley"
    if d.startswith("10.7762/"): return "한국영양학회 e-cnr.org"
    if d.startswith("10.3346/"): return "대한의학회 jkms.org — 오픈액세스"
    if d.startswith("10.4178/"): return "역학과 건강 e-epih.org — 오픈액세스"
    if "koreamed" in j or "korean" in j: return "KoreaMed / KMbase 확인"
    return ""


def main():
    rows = []
    for label, path, want in SETS:
        if not os.path.exists(path): continue
        for r in load(path):
            if r.get("verdict") not in want: continue
            if r.get("pdf_file") and os.path.isfile(os.path.join(REF, "pdf", r["pdf_file"])): continue
            k = r["key"]
            e = E.get(k, {}); p = P.get(k, {})
            doi = r.get("doi")
            plat, plat_url, avail = platform_of(doi, r.get("journal"), r.get("pmcid"))
            rows.append(dict(
                platform=plat, platform_url=plat_url, obtainable=avail,
                set=label, key=k, verdict=r.get("verdict"), year=r.get("year"),
                journal=r.get("journal") or "", title=r.get("title") or "",
                doi=doi or "", doi_link=f"https://doi.org/{doi}" if doi else "",
                pubmed=f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/" if r.get("pmid") else "",
                pmc=f"https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/" if r.get("pmcid") else "",
                landing=r.get("landing") or "",
                is_oa="예" if r.get("is_oa") else ("아니오" if r.get("is_oa") is False else "불명"),
                publisher_hint=pub_hint(doi, r.get("journal")),
                tried="시도함" if r.get("pdf_tried") else "미시도",
                impact="추출·평가가 초록 기준" if (e.get("source") == "abstract_only" or p.get("source") == "abstract_only") else "",
                save_as=f"references/pdf/{k}.pdf"))
    rows.sort(key=lambda r: (r["platform"], r["set"], -(r["year"] or 0)))
    cols = ["platform","obtainable","set","key","verdict","year","journal","title","doi",
            "platform_url","doi_link","pubmed","pmc","landing","is_oa","tried","impact","save_as"]
    KO = {"platform":"플랫폼","obtainable":"직접 확보 가능?","platform_url":"플랫폼 URL",
          "set":"구분","key":"인용키","verdict":"판정","year":"연도","journal":"학술지","title":"제목",
          "doi":"DOI","doi_link":"DOI 링크","pubmed":"PubMed","pmc":"PMC","landing":"랜딩페이지",
          "is_oa":"오픈액세스","tried":"자동수집 시도","impact":"영향",
          "save_as":"저장할 경로"}
    with open(os.path.join(PROJ, "data", "PDF_MISSING.tsv"), "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f, delimiter="\t"); wr.writerow([KO[c] for c in cols])
        for r in rows: wr.writerow([r[c] for c in cols])

    from collections import Counter
    if not rows:
        text = "# 원문(PDF) 미확보 논문 — 총 0건\n\n현재 수집 대상인 본 리뷰 포함·인접·보류 및 본보기 리뷰의 PDF 미확보 항목은 없다. 서지와 실제 파일 경로를 대조한 결과다. 제외된 문헌은 다운로드 대상으로 집계하지 않는다.\n\nPDF 확보 완료는 구조화 추출·평가의 전문 재검토 완료를 뜻하지 않는다.\n\n[서지 및 판정](../references/INDEX.md) · [엑셀용 목록](PDF_MISSING.tsv)\n"
        open(os.path.join(PROJ, "data", "PDF_MISSING.md"), "w", encoding="utf-8").write(text)
        print("  PDF_MISSING.tsv · PDF_MISSING.md — 총 0건")
        return
    byplat = Counter(r["platform"] for r in rows)
    n_direct = sum(1 for r in rows if r["obtainable"].startswith("예"))
    L = [f"# 원문(PDF) 미확보 논문 — 총 {len(rows)}건\n",
         "현재 서지와 실제 파일을 대조한 PDF 미확보 목록이다. 접근 차단·구독 필요·공개 원문 미발견 등이 포함된다.\n",
         f"**{n_direct}건은 기관 구독 또는 공개 원문 경로를 우선 확인할 수 있다.** 실제 다운로드 가능 여부는 접속 환경에 따라 다르다. "
         "플랫폼별로 묶었으니 한 사이트에서 여러 편을 이어서 받으시면 된다.\n",
         "## 플랫폼별 건수\n", "| 플랫폼 | 건수 | 직접 확보 |", "|---|---:|---|"]
    seen = {}
    for r in rows: seen.setdefault(r["platform"], r["obtainable"])
    for pl, n in byplat.most_common():
        L.append(f"| {pl} | {n} | {seen[pl]} |")
    L += ["", "## 넣는 방법 — 파일명은 그대로 두셔도 된다\n",
          "받으신 파일을 `references/inbox/` 에 넣고 아래를 실행하면 DOI·PII·제목으로 자동 매칭한다.\n",
          "```bash\ncd /data2/project/ahnbi_c2/paper_KNHANES_ML_reivew\n"
          "python tools/ingest_pdf.py            # 매칭 미리보기\n"
          "python tools/ingest_pdf.py --apply    # 반영\n"
          "python tools/make_paper_md.py         # 전문 md 생성\n"
          "python tools/make_missing_pdf_list.py # 이 목록 갱신\n```\n",
          "엑셀본은 `data/PDF_MISSING.tsv` (플랫폼·직접확보가능·플랫폼URL 열 포함).\n",
          "`영향` 열이 채워진 논문은 현재 초록만으로 추출·평가된 것이라 "
          "원문 확보 후 별도의 전문 기반 재추출·평가가 필요하다. PDF 등록만으로 기존 평가가 자동 변경되지는 않는다.\n"]
    for pl, n in byplat.most_common():
        g = [r for r in rows if r["platform"] == pl]
        L.append(f"## {pl} — {n}건 ({seen[pl]})\n")
        L.append("| 인용키 | 구분 | 판정 | 연도 | 학술지 | 제목 | 링크 | 영향 |")
        L.append("|---|---|---|---:|---|---|---|---|")
        for r in sorted(g, key=lambda r: (r["set"], -(r["year"] or 0))):
            link = f"[열기]({r['platform_url']})" if r["platform_url"].startswith("http") else r["platform_url"]
            extra = " · ".join(x for x in (
                f"[PubMed]({r['pubmed']})" if r["pubmed"] else "",
                f"[PMC]({r['pmc']})" if r["pmc"] else "") if x)
            L.append(f"| `{r['key']}` | {'포함' if '포함' in r['set'] else '본보기'} | {r['verdict']} | "
                     f"{r['year']} | {r['journal'].replace('|', '/')} | {r['title'].replace('|', '/')} | "
                     f"{link}{(' · ' + extra) if extra else ''} | {r['impact']} |")
        L.append("")
    open(os.path.join(PROJ, "data", "PDF_MISSING.md"), "w", encoding="utf-8").write("\n".join(L))
    from collections import Counter
    print(f"  PDF_MISSING.tsv · PDF_MISSING.md — 총 {len(rows)}건")
    print("  구분별:", dict(Counter(r['set'] for r in rows)))
    print("  출판사별:", dict(Counter(r['publisher_hint'].split(' —')[0] or '기타' for r in rows).most_common(8)))


if __name__ == "__main__":
    main()
