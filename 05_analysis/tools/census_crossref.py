"""Crossref — 네 번째 검색원. Europe PMC·PubMed 밖(비의학지·학회지)을 건진다.

    python tools/census_crossref.py

Scopus·WoS 는 구독 키가 없어 접근 불가(401). Crossref 는 무료·무키이며 색인 규모가 크다.
다만 초록 보유율이 낮아 선별은 제목·키워드 중심이 된다. 결과: results/raw/crossref_<date>.json
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

API = "https://api.crossref.org/works"
QUERIES = ["KNHANES", "Korea National Health and Nutrition Examination Survey",
           "Korean National Health and Nutrition Examination Survey",
           "KNHANES machine learning", "KNHANES deep learning",
           "Korea National Health and Nutrition Examination Survey machine learning"]


def fetch_all(q, cap=2000):
    items, cur, total = [], "*", None
    while len(items) < cap:
        u = (f"{API}?query.bibliographic={quote(q)}&rows=200&cursor={quote(cur)}"
             f"&select=DOI,title,abstract,container-title,issued,author,type,subject,is-referenced-by-count"
             f"&mailto={MAILTO}")
        try:
            d = get(u, timeout=60)
        except Exception as e:
            print(f"    중단 {e}"); break
        m = d["message"]
        total = m["total-results"] if total is None else total
        rs = m.get("items", [])
        if not rs: break
        items += rs
        nxt = m.get("next-cursor")
        if not nxt or nxt == cur: break
        cur = nxt
        print(f"    {q[:26]:28s} {len(items)}/{min(total, cap)}", flush=True)
        time.sleep(0.3)
    return total, items[:cap]


def quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe="")


KN = re.compile(r"knhanes|korea(n)? national health and nutrition examination survey", re.I)


def main():
    pool, log = {}, []
    for q in QUERIES:
        tot, items = fetch_all(q)
        new = 0
        for v in items:
            doi = norm_doi(v.get("DOI"))
            if not doi or doi in pool: continue
            title = (v.get("title") or [""])[0]
            ab = re.sub(r"<[^>]+>", " ", v.get("abstract") or "").strip() or None
            # KNHANES 명칭이 제목·초록에 실제로 있는 것만 (Crossref 서지검색은 느슨하다)
            if not KN.search(title + " " + (ab or "")): continue
            yr = ((v.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            aus = [f"{a.get('given','')} {a.get('family','')}".strip() for a in v.get("author") or []]
            pool[doi] = dict(doi=doi, title=title, abstract=ab, year=yr,
                             journal=(v.get("container-title") or [None])[0],
                             authors=", ".join(aus), author_list=aus, type=v.get("type"),
                             cited=v.get("is-referenced-by-count"), keywords=v.get("subject") or [],
                             pmid=None, pmcid=None, oa_id=None, mesh=[], pub_type=[v.get("type")],
                             is_oa=None, pdf_url=None, landing=f"https://doi.org/{doi}",
                             fulltext_urls=[], epmc_layer=None, oa_type=v.get("type"), lang=None)
            new += 1
        log.append(dict(query=q, hits=tot, retrieved=len(items), new_after_name_filter=new))
        print(f"  {q[:44]:46s} hits {tot:7d} 수집 {len(items):5d} 명칭필터 통과 신규 {new:4d}", flush=True)
    recs = list(pool.values())
    out = dict(source="Crossref", api=API, searched_on=time.strftime("%Y-%m-%d"),
               note="Scopus·WoS 는 구독 키 없음(401). Crossref 로 대체 교차.",
               name_filter="제목/초록에 KNHANES 명칭 3변형 중 하나가 실제로 있는 것만",
               queries=log, n_unique=len(recs),
               n_with_abstract=sum(1 for r in recs if r["abstract"]), records=recs)
    dump(out, os.path.join(RAW, f"crossref_{TODAY}.json"))
    print(f"  고유 {len(recs)} · 초록 {out['n_with_abstract']}")


if __name__ == "__main__":
    main()
