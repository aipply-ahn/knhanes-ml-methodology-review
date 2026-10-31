"""OpenAlex — 교차 검색원. PubMed 밖(IEEE·MDPI 비의학지·학회·arXiv·KCI 일부)을 건진다.
OA PDF URL(best_oa_location) 도 여기서 얻는다.

    python tools/census_openalex.py

결과: results/raw/openalex_<date>.json
"""
import sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

API = "https://api.openalex.org/works"
SELECT = ("id,doi,display_name,publication_year,cited_by_count,type,language,"
          "primary_location,best_oa_location,open_access,ids,authorships,"
          "abstract_inverted_index,keywords")


def inv2text(inv):
    if not inv:
        return None
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


CACHE = os.path.join(RAW, "_oacache")


def get_backoff(u):
    """429 는 최대 5 분까지 기다린다. 일일 예산 소진이면 결국 raise."""
    for i in range(8):
        try:
            return get(u, tries=1)
        except Exception as e:
            if getattr(e, "code", None) == 429 and i < 7:
                time.sleep(min(300, 20 * 2 ** i)); continue
            if i < 7 and getattr(e, "code", None) in (500, 502, 503, 504):
                time.sleep(10 * (i + 1)); continue
            raise


def search_all(term, label):
    """용어별 체크포인트 — 커서와 누적 결과를 디스크에 남겨 중단 후 이어 받는다."""
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, re.sub(r"[^a-z]", "_", term.lower()) + ".json")
    st = load(cf) if os.path.exists(cf) else dict(cursor="*", total=None, items=[], done=False)
    if st["done"]:
        return st["total"], st["items"]
    items, cur, total = st["items"], st["cursor"], st["total"]
    while True:
        u = (f"{API}?filter=title_and_abstract.search:{q(term)}&per-page=200"
             f"&cursor={q(cur)}&select={SELECT}&mailto={MAILTO}")
        d = get_backoff(u)
        total = d["meta"]["count"] if total is None else total
        rs = d.get("results", [])
        if not rs:
            break
        items += rs
        cur = d["meta"].get("next_cursor")
        print(f"    {label} {len(items)}/{total}", flush=True)
        json.dump(dict(cursor=cur, total=total, items=items, done=not cur), open(cf, "w"))
        if not cur:
            break
        time.sleep(0.5)
    json.dump(dict(cursor=cur, total=total, items=items, done=True), open(cf, "w"))
    return total, items


def slim(v, hit_terms):
    pl = v.get("primary_location") or {}
    bo = v.get("best_oa_location") or {}
    ids = v.get("ids") or {}
    aus = [(a.get("author") or {}).get("display_name") for a in v.get("authorships") or []]
    return dict(
        oa_id=v["id"], doi=norm_doi(v.get("doi")), title=v.get("display_name"),
        year=v.get("publication_year"), cited=v.get("cited_by_count"), type=v.get("type"),
        lang=v.get("language"),
        journal=(pl.get("source") or {}).get("display_name"),
        landing=pl.get("landing_page_url"), pdf_url=bo.get("pdf_url") or pl.get("pdf_url"),
        oa_status=(v.get("open_access") or {}).get("oa_status"),
        is_oa=(v.get("open_access") or {}).get("is_oa"),
        pmid=(ids.get("pmid") or "").rsplit("/", 1)[-1] or None,
        pmcid=(ids.get("pmcid") or "").rsplit("/", 1)[-1] or None,
        author_list=aus, authors=", ".join(a for a in aus if a),
        abstract=inv2text(v.get("abstract_inverted_index")),
        keywords=[k.get("display_name") for k in v.get("keywords") or []],
        hit_terms=hit_terms,
    )


def main():
    pool, log = {}, []
    # "Korean National …" 은 OpenAlex 어간처리로 "Korea National …" 과 동일 집합(9,418) 이라 뺀다.
    # 일일 예산 1,000 credit = 100 요청. 200건/페이지 → 약 68 요청.
    for t in KNHANES_TERMS[:2]:
        total, items = search_all(f'"{t}"', t[:20])
        new = 0
        for v in items:
            if v["id"] in pool:
                pool[v["id"]]["hit_terms"].append(t)
            else:
                pool[v["id"]] = slim(v, [t]); new += 1
        log.append(dict(term=t, hits=total, retrieved=len(items), new_unique=new))
        print(f"  {t:52s} hits {total:6d} 신규 {new:5d}", flush=True)
    recs = list(pool.values())
    out = dict(source="OpenAlex", api=API, searched_on=time.strftime("%Y-%m-%d"),
               filter="title_and_abstract.search (phrase) · 연도 제한 없음 · type 제한 없음",
               queries=log, n_unique=len(recs),
               n_with_abstract=sum(1 for r in recs if r["abstract"]), records=recs)
    dump(out, os.path.join(RAW, f"openalex_{TODAY}.json"))
    print(f"  고유 {len(recs)} · 초록 {out['n_with_abstract']}")


if __name__ == "__main__":
    main()
