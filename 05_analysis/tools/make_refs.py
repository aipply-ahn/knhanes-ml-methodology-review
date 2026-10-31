"""screen.json + corpus.json + verdicts.json + kdca 매칭 → references/refs.json · INDEX.md · refs.bib

    python tools/make_refs.py

refs.json 은 **선별 통과(T1·T2·T3 중 verdict != EXCLUDE) 논문의 기계용 원본**이다.
PDF 파일명 = bibkey. 판정은 results/derived/verdicts.json 에서만 고친다.
"""
import sys
from collections import Counter, defaultdict
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def main():
    C = {r["uid"]: r for r in load(os.path.join(DER, "corpus.json"))["records"]}
    S = load(os.path.join(DER, "screen.json"))
    vp = os.path.join(DER, "verdicts.json")
    V = load(vp) if os.path.exists(vp) else {}
    old = {r["uid"]: r for r in load(os.path.join(REF, "refs.json"))} if os.path.exists(os.path.join(REF, "refs.json")) else {}

    refs, keys = [], Counter()
    for s in S["rows"]:
        if s["tier"] == "--":
            continue
        v = V.get(s["uid"], {})
        if v.get("verdict") == "EXCLUDE" and s["tier"] != "T1":
            continue   # T2/T3 제외는 refs 에서 뺀다. T1 제외는 근거 보존을 위해 남긴다
        r = C[s["uid"]]
        first = (r.get("author_list") or [None])[0] or (r.get("authors") or "").split(",")[0]
        key = bibkey(first, r.get("year"), r.get("title"))
        keys[key] += 1
        if keys[key] > 1:
            key += "abcdefghijklmnop"[keys[key] - 2]
        o = old.get(s["uid"], {})
        expected_pdf = f"{key}.pdf"
        existing_pdf = o.get("pdf_file") if o.get("pdf_file") and os.path.exists(os.path.join(REF, "pdf", o["pdf_file"])) else None
        if not existing_pdf and os.path.exists(os.path.join(REF, "pdf", expected_pdf)):
            existing_pdf = expected_pdf
        refs.append(dict(
            key=key, uid=s["uid"], tier=s["tier"], verdict=v.get("verdict", "PENDING"),
            verdict_reason=v.get("reason"), category=v.get("category"),
            companion_of=v.get("companion_of"), study_family=v.get("study_family"),
            study_family_linkage_status=v.get("study_family_linkage_status"),
            study_family_linkage_basis=v.get("study_family_linkage_basis"),
            study_family_linkage_author_directed=v.get("study_family_linkage_author_directed"),
            ml_methods_reported=v.get("ml_methods") or [], task=v.get("task"),
            knhanes_role=v.get("knhanes_role"), outcome=v.get("outcome"),
            ml_terms=s["t1"] + s["t2"] + s["t3"],
            title=r.get("title"), year=r.get("year"), authors=r.get("authors"),
            author_list=r.get("author_list"), journal=r.get("journal"), doi=r.get("doi"),
            pmid=r.get("pmid"), pmcid=r.get("pmcid"), oa_id=r.get("oa_id"), cited=r.get("cited"),
            abstract=r.get("abstract"), keywords=r.get("keywords"), sources=r.get("sources"),
            kdca_no=r.get("kdca_no"), is_oa=r.get("is_oa"), pdf_url=r.get("pdf_url"),
            landing=r.get("landing"), fulltext_urls=r.get("fulltext_urls"),
            pdf_file=existing_pdf,
            pdf_src=o.get("pdf_src"), pdf_tried=o.get("pdf_tried", False),
        ))
    # 프리프린트/출판본 중복 — 정규화 제목이 같으면 출판본만 센다 (PROTOCOL D11)
    PRE = re.compile(r"research square|medrxiv|biorxiv|preprint|ssrn|arxiv", re.I)
    groups = {}
    for r in refs:
        if r["verdict"] in ("EXCLUDE",): continue
        groups.setdefault(norm_title(r.get("title"))[:70], []).append(r)
    for g in groups.values():
        if len(g) < 2: continue
        g.sort(key=lambda r: (bool(PRE.search(r.get("journal") or "")), not r.get("pmid"), -(r.get("cited") or 0)))
        for d in g[1:]:
            d["duplicate_of"] = g[0]["key"]; d["verdict_orig"] = d["verdict"]; d["verdict"] = "DUPLICATE"
    # 기존 pdf 파일명이 새 key 와 다르면 rename
    for r in refs:
        if r["pdf_file"] and r["pdf_file"] != f"{r['key']}.pdf":
            src, dst = os.path.join(REF, "pdf", r["pdf_file"]), os.path.join(REF, "pdf", f"{r['key']}.pdf")
            if os.path.exists(src) and not os.path.exists(dst):
                os.rename(src, dst)
            r["pdf_file"] = f"{r['key']}.pdf"
    dump(refs, os.path.join(REF, "refs.json"))
    write_index(refs)
    write_bib(refs)


def bibesc(s):
    return (s or "").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def write_bib(refs):
    L = []
    for r in refs:
        if r["verdict"] in ("EXCLUDE", "DUPLICATE", "LINKED_COMPANION"): continue
        au = " and ".join(a for a in (r.get("author_list") or []) if a) or (r.get("authors") or "")
        L.append(f"@article{{{r['key']},\n  title={{{bibesc(r['title'])}}},\n  author={{{bibesc(au)}}},\n"
                 f"  journal={{{bibesc(r.get('journal'))}}},\n  year={{{r.get('year') or ''}}},\n"
                 f"  doi={{{r.get('doi') or ''}}}\n}}\n")
    open(os.path.join(REF, "refs.bib"), "w", encoding="utf-8").write("\n".join(L))


def write_index(refs):
    inc = [r for r in refs if r["verdict"] == "INCLUDE"]
    unc = [r for r in refs if r["verdict"] in ("PENDING", "UNCERTAIN")]
    exc = [r for r in refs if r["verdict"] == "EXCLUDE"]
    dup = [r for r in refs if r["verdict"] == "DUPLICATE"]
    npdf = sum(1 for r in inc if r.get("pdf_file"))
    L = []; A = L.append
    A(f"# 참고문헌 — KNHANES × 머신러닝 전수조사 결과\n")
    A(f"생성 {time.strftime('%Y-%m-%d')} · `python tools/make_refs.py` 자동생성. 판정은 `results/derived/verdicts.json` 에서 고친다.\n")
    A("| 상태 | 건수 | 초록 | PDF |")
    A("|---|---:|---:|---:|")
    A(f"| ✅ 포함 (INCLUDE) | {len(inc)} | {sum(1 for r in inc if r.get('abstract'))} | {npdf} |")
    linked0 = [r for r in refs if r["verdict"] == "LINKED_COMPANION"]
    A(f"| 🔗 연결 보고서 (LINKED_COMPANION) | {len(linked0)} | {sum(1 for r in linked0 if r.get('abstract'))} | {sum(1 for r in linked0 if r.get('pdf_file'))} |")
    adj0 = [r for r in refs if r["verdict"] == "INCLUDE_ADJACENT"]
    A(f"| 🔷 포함 — ML 인접 (INCLUDE_ADJACENT) | {len(adj0)} | {sum(1 for r in adj0 if r.get('abstract'))} | {sum(1 for r in adj0 if r.get('pdf_file'))} |")
    A(f"| ❓ 보류 (UNCERTAIN/PENDING) | {len(unc)} | {sum(1 for r in unc if r.get('abstract'))} | {sum(1 for r in unc if r.get('pdf_file'))} |")
    A(f"| ❌ 제외 (T1 이었으나 제외) | {len(exc)} | | |")
    A(f"| ♻ 중복 (프리프린트 등, 출판본에 합침) | {len(dup)} | | |")
    A("")
    A("PDF 는 전부 `pdf/<key>.pdf`. 기계용 원본은 `refs.json`, BibTeX 는 `refs.bib`. 로그는 `_logs/`.\n")
    cats = Counter(r.get("category") or "미분류" for r in inc)
    if cats:
        A("## 포함 논문 — 범주별\n")
        A("| 범주 | 건수 |"); A("|---|---:|")
        for c, n in cats.most_common(): A(f"| {c} | {n} |")
        A("")
    yrs = Counter(r.get("year") for r in inc)
    A("## 포함 논문 — 연도별\n")
    A("| " + " | ".join(str(y) for y in sorted(yrs)) + " |")
    A("|" + "---:|" * len(yrs))
    A("| " + " | ".join(str(yrs[y]) for y in sorted(yrs)) + " |")
    A("")

    def block(r):
        st = {"INCLUDE": "✅", "INCLUDE_ADJACENT": "🔷", "LINKED_COMPANION": "🔗", "UNCERTAIN": "❓", "PENDING": "❓", "EXCLUDE": "❌", "DUPLICATE": "♻"}[r["verdict"]]
        pdf = f"[PDF](pdf/{r['pdf_file']})" if r.get("pdf_file") else "_PDF 없음_"
        doi = f"[doi](https://doi.org/{r['doi']})" if r.get("doi") else ""
        pm = f"[PMID {r['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/)" if r.get("pmid") else ""
        kd = f"KDCA #{r['kdca_no']}" if r.get("kdca_no") else ""
        au = re.sub(r"\s+and\s+", ", ", r.get("authors") or "")
        au = (au[:80] + "…") if len(au) > 80 else au
        A(f"### `{r['key']}` ({r.get('year') or '?'}) {st} {r['tier']}")
        A(f"**{r.get('title') or ''}**  ")
        if au: A(f"{au}  ")
        A(f"{r.get('journal') or ''}{' · 피인용 ' + str(r['cited']) if r.get('cited') else ''}  ")
        A(" · ".join(x for x in (doi, pm, pdf, kd) if x) + "  ")
        A(f"ML 용어: {', '.join(r['ml_terms'])}  ")
        if r.get("category"): A(f"범주: {r['category']} · 과제: {r.get('task') or '?'} · KNHANES 역할: {r.get('knhanes_role') or '?'} · 결과변수: {r.get('outcome') or '?'}  ")
        if r.get("ml_methods_reported"): A(f"알고리즘(초록/전문 기재): {', '.join(str(m) for m in r['ml_methods_reported'])}  ")
        if r.get("verdict_reason"): A(f"판정 근거: {r['verdict_reason']}  ")
        ab = re.sub(r"<[^>]+>", " ", r.get("abstract") or ""); ab = re.sub(r"\s+", " ", ab).strip()
        A("")
        A("> " + (ab[:900].rsplit(" ", 1)[0] + " …" if len(ab) > 900 else ab) if ab else "> _초록 미확보_")
        A("")

    adj = [r for r in refs if r["verdict"] == "INCLUDE_ADJACENT"]
    linked = [r for r in refs if r["verdict"] == "LINKED_COMPANION"]
    for title, rows in (("✅ 포함 — ML 적용", inc), ("🔗 연결된 추가·동반 보고서", linked), ("🔷 포함 — ML 인접 (LASSO·군집·PCA·LCA 등)", adj),
                        ("❓ 보류 — 전문 확인 필요", unc), ("♻ 중복", dup),
                        ("❌ 제외 (T1 규칙선별 통과했으나 검토 후 제외)", exc)):
        A(f"## {title} — {len(rows)}건\n")
        for r in sorted(rows, key=lambda x: (-(x.get("year") or 0), -(x.get("cited") or 0))):
            block(r)
    open(os.path.join(REF, "INDEX.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  INDEX.md — 포함 {len(inc)} · 보류 {len(unc)} · 제외 {len(exc)} · PDF {npdf}")


if __name__ == "__main__":
    main()
