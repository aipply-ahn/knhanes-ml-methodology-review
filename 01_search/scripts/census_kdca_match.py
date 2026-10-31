"""KDCA 등록목록을 corpus 에 연결한다. 병합 뒤, 선별 앞에 돈다.

    python tools/census_kdca_match.py

  ① URL 의 DOI → corpus DOI 매칭
  ② 영문 제목 정규화 → corpus 제목 매칭
  ③ 미매칭 영문 제목 → Crossref 서지 검색 (유사도 ≥ 0.92) → DOI → corpus 매칭 또는 Europe PMC/Crossref 로 초록 보강
  ④ 그래도 미매칭 (한국어 논문·학위논문 등) → uid `kdca:<no>` 로 corpus 에 추가 (초록 없음)

corpus.json 을 제자리 갱신하고 results/derived/kdca_match.json 에 매칭 기록을 남긴다.
"""
import difflib, glob, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

CROSSREF = "https://api.crossref.org/works"
OA = "https://api.openalex.org/works"


def inv2text(inv):
    if not inv: return None
    pos = {}
    for w, idxs in inv.items():
        for i in idxs: pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def doi_from_url(u):
    if not u: return None
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>?#]+", u)
    return norm_doi(m.group(0).rstrip(".)/")) if m else None


def crossref_title(title):
    try:
        d = get(f"{CROSSREF}?query.bibliographic={q(title)}&rows=3&select=DOI,title,abstract,container-title,issued,author&mailto={MAILTO}")
    except Exception:
        return None
    best = None
    for it in d["message"]["items"]:
        t = (it.get("title") or [""])[0]
        r = difflib.SequenceMatcher(None, norm_title(t), norm_title(title)).ratio()
        if r >= 0.92 and (best is None or r > best[0]):
            best = (r, it)
    return best[1] if best else None


EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def enrich_doi(doi, cr_item=None):
    """DOI → 서지·초록. Europe PMC (예산 없음) 우선, 없으면 Crossref 항목의 초록."""
    try:
        d = get(f"{EPMC}?query={q('DOI:' + chr(34) + doi + chr(34))}&format=json&pageSize=1&resultType=core")
        rs = d.get("resultList", {}).get("result", [])
    except Exception:
        rs = []
    if rs:
        v = rs[0]
        return dict(doi=doi, title=v.get("title"), year=int(v["pubYear"]) if str(v.get("pubYear", "")).isdigit() else None,
                    cited=v.get("citedByCount"), journal=(v.get("journalInfo") or {}).get("journal", {}).get("title"),
                    pmid=v.get("pmid"), pmcid=v.get("pmcid"), is_oa=v.get("isOpenAccess") == "Y",
                    author_list=[a.get("fullName") for a in (v.get("authorList") or {}).get("author", [])],
                    authors=v.get("authorString"), abstract=v.get("abstractText"), lang=v.get("language"),
                    src="EPMC")
    if cr_item:
        ab = re.sub(r"<[^>]+>", " ", cr_item.get("abstract") or "").strip() or None
        aus = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in cr_item.get("author") or []]
        yr = ((cr_item.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        return dict(doi=doi, title=(cr_item.get("title") or [None])[0], year=yr, cited=None,
                    journal=(cr_item.get("container-title") or [None])[0], pmid=None, pmcid=None, is_oa=None,
                    author_list=aus, authors=", ".join(aus), abstract=ab, lang=None, src="Crossref")
    return None


def main():
    K = load(sorted(glob.glob(os.path.join(RAW, "kdca_*.json")))[-1])
    Cj = load(os.path.join(DER, "corpus.json")); C = Cj["records"]
    by_doi = {r["doi"]: r for r in C if r.get("doi")}
    by_title = {norm_title(r["title"]): r for r in C if r.get("title") and len(norm_title(r["title"])) > 25}
    cache_p = os.path.join(DER, "_kdca_lookup_cache.json")
    cache = load(cache_p) if os.path.exists(cache_p) else {}
    log, stat = [], {"doi": 0, "title": 0, "crossref": 0, "crossref_new": 0, "unmatched": 0}

    def attach(r, k, how):
        r["kdca_no"] = k["kdca_no"]; r["kdca_fields"] = k["fields"]; r["kdca_type"] = k["paper_type"]
        r["kdca_title_ko"] = k.get("title_ko")
        if "KDCA" not in r["sources"]: r["sources"].append("KDCA")
        log.append(dict(kdca_no=k["kdca_no"], how=how, uid=r["uid"]))

    for i, k in enumerate(K["records"], 1):
        d = doi_from_url(k.get("url"))
        if d and d in by_doi:
            attach(by_doi[d], k, "doi"); stat["doi"] += 1; continue
        t = norm_title(k.get("title_en") or "")
        if t and len(t) > 25 and t in by_title:
            attach(by_title[t], k, "title"); stat["title"] += 1; continue
        if k.get("title_en") and len(k["title_en"]) > 20:
            key = str(k["kdca_no"])
            if key not in cache:
                it = crossref_title(k["title_en"])
                cache[key] = (it.get("DOI") if it else None)
                if it: cache["cr:" + norm_doi(it["DOI"])] = it
                json.dump(cache, open(cache_p, "w"))
                time.sleep(0.6)
            cd = norm_doi(cache[key])
            if cd:
                if cd in by_doi:
                    attach(by_doi[cd], k, "crossref→doi"); stat["crossref"] += 1; continue
                nk = f"oa:{cd}"
                if nk not in cache:
                    cache[nk] = enrich_doi(cd, cache.get("cr:" + cd)) or {}
                    json.dump(cache, open(cache_p, "w")); time.sleep(0.3)
                o = cache[nk] or {}
                r = dict(uid=cd, doi=cd, pmid=o.get("pmid"), pmcid=o.get("pmcid"), oa_id=o.get("oa_id"),
                         title=o.get("title") or k["title_en"], year=o.get("year") or k.get("year"),
                         journal=o.get("journal") or k.get("journal"), authors=o.get("authors") or k.get("author_en"),
                         author_list=o.get("author_list") or [k.get("author_en")], abstract=o.get("abstract"),
                         keywords=[x for x in [k.get("keywords_en")] if x], mesh=[], pub_type=[],
                         cited=o.get("cited"), is_oa=o.get("is_oa"), pmc_pdf=None, pdf_url=o.get("pdf_url"),
                         landing=o.get("landing") or k.get("url"), fulltext_urls=[], epmc_layer=None,
                         oa_type=o.get("oa_type"), lang=o.get("lang"), sources=["KDCA+Crossref"] + ([o["src"]] if o.get("src") else []),
                         knhanes_in_ta=True)
                C.append(r); by_doi[cd] = r; attach(r, k, "crossref→new"); stat["crossref_new"] += 1; continue
        # 미매칭 → KDCA 단독 레코드
        r = dict(uid=f"kdca:{k['kdca_no']}", doi=d, pmid=None, pmcid=None, oa_id=None,
                 title=k.get("title_en") or k.get("title_ko"), title_ko=k.get("title_ko"),
                 year=k.get("year"), journal=k.get("journal"),
                 authors=k.get("author_en") or k.get("author_ko"), author_list=[k.get("author_en") or k.get("author_ko")],
                 abstract=None, keywords=[x for x in [k.get("keywords_en"), k.get("keywords_ko")] if x],
                 mesh=[], pub_type=[k.get("paper_type")], cited=None, is_oa=None, pmc_pdf=None, pdf_url=None,
                 landing=k.get("url"), fulltext_urls=[], epmc_layer=None, oa_type=None,
                 lang=("ko" if k.get("lang") == "KOR" else "en"), sources=[], knhanes_in_ta=True)
        C.append(r); attach(r, k, "kdca-only"); stat["unmatched"] += 1
        if i % 200 == 0: print(f"    {i}/{len(K['records'])} {stat}", flush=True)

    Cj.update(n=len(C), n_with_abstract=sum(1 for r in C if r.get("abstract")),
              n_knhanes_in_ta=sum(1 for r in C if r.get("knhanes_in_ta")),
              kdca=dict(n=len(K["records"]), **stat))
    dump(Cj, os.path.join(DER, "corpus.json"))
    dump(dict(matched_on=time.strftime("%Y-%m-%d"), stat=stat, log=log), os.path.join(DER, "kdca_match.json"))
    print(f"  KDCA {len(K['records'])} → {stat}")


if __name__ == "__main__":
    main()
