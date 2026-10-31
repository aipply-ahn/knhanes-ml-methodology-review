"""수집원 3종(Europe PMC · OpenAlex · PubMed) 을 DOI → PMID → 정규화 제목 순으로 병합한다.

    python tools/census_merge.py

결과: results/derived/corpus.json   (한 행 = 한 논문, 출처 표시)
"""
import glob, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def latest(pat):
    fs = sorted(glob.glob(os.path.join(RAW, pat)))
    return load(fs[-1]) if fs else None


def main():
    ep, oa, pm = latest("epmc_*.json"), latest("openalex_*.json"), latest("pubmed_*.json")
    recs, by_doi, by_pmid, by_title = [], {}, {}, {}

    def find(r):
        d, p, t = norm_doi(r.get("doi")), r.get("pmid"), norm_title(r.get("title"))
        if d and d in by_doi: return by_doi[d]
        if p and p in by_pmid: return by_pmid[p]
        if t and len(t) > 25 and t in by_title: return by_title[t]
        return None

    def register(m):
        if m.get("doi"): by_doi[m["doi"]] = m
        if m.get("pmid"): by_pmid[str(m["pmid"])] = m
        t = norm_title(m.get("title"))
        if t and len(t) > 25: by_title[t] = m

    def add(r, src):
        m = find(r)
        if m is None:
            m = dict(uid=None, doi=norm_doi(r.get("doi")), pmid=r.get("pmid"), pmcid=r.get("pmcid"),
                     oa_id=r.get("oa_id"), title=r.get("title"), year=r.get("year"),
                     journal=r.get("journal"), authors=r.get("authors"),
                     author_list=r.get("author_list") or [], abstract=r.get("abstract"),
                     keywords=list(r.get("keywords") or []), mesh=list(r.get("mesh") or []),
                     pub_type=list(r.get("pub_type") or []), cited=r.get("cited"),
                     is_oa=r.get("is_oa"), pmc_pdf=r.get("in_pmc") or r.get("has_pdf"),
                     pdf_url=r.get("pdf_url"), landing=r.get("landing"),
                     fulltext_urls=list(r.get("fulltext_urls") or []),
                     epmc_layer=r.get("epmc_layer"), oa_type=r.get("type"), lang=r.get("lang"),
                     sources=[src])
            recs.append(m)
        else:
            if src not in m["sources"]: m["sources"].append(src)
            for k in ("doi", "pmid", "pmcid", "oa_id", "abstract", "journal", "authors", "year",
                      "pdf_url", "landing", "epmc_layer", "oa_type", "lang", "is_oa"):
                if not m.get(k) and r.get(k): m[k] = r[k]
            if not m["author_list"] and r.get("author_list"): m["author_list"] = r["author_list"]
            for k in ("keywords", "mesh", "fulltext_urls"):
                for x in r.get(k) or []:
                    if x and x not in m[k]: m[k].append(x)
            if (r.get("cited") or 0) > (m.get("cited") or 0): m["cited"] = r["cited"]
            if r.get("in_pmc") or r.get("has_pdf"): m["pmc_pdf"] = True
        register(m)

    stats = {}
    for name, d in (("EPMC", ep), ("OpenAlex", oa), ("PubMed", pm)):
        if not d: continue
        n0 = len(recs)
        for r in d["records"]: add(r, name)
        stats[name] = dict(input=len(d["records"]), new=len(recs) - n0)
        print(f"  {name:9s} 입력 {len(d['records']):6d} → 신규 {len(recs) - n0:6d}")

    for i, m in enumerate(recs):
        m["uid"] = m["doi"] or (f"pmid:{m['pmid']}" if m.get("pmid") else m.get("oa_id") or f"rec{i}")
        m["knhanes_in_ta"] = bool(re.search(r"knhanes|korea(n)? national health and nutrition examination survey",
                                            ((m.get("title") or "") + " " + (m.get("abstract") or "")).lower()))
    out = dict(merged_on=time.strftime("%Y-%m-%d"), inputs=stats, n=len(recs),
               n_with_abstract=sum(1 for r in recs if r.get("abstract")),
               n_knhanes_in_ta=sum(1 for r in recs if r["knhanes_in_ta"]), records=recs)
    dump(out, os.path.join(DER, "corpus.json"))
    print(f"  병합 {len(recs)} · 초록 {out['n_with_abstract']} · KNHANES 제목/초록 명시 {out['n_knhanes_in_ta']}")


if __name__ == "__main__":
    main()
