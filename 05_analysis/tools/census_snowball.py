"""인용망 스노볼링 — 키워드 검색이 놓친 논문을 참고문헌·피인용으로 건진다.

    python tools/census_snowball.py --seeds 40

키워드 검색은 저자가 제목·초록에 그 단어를 쓴 논문만 잡는다. KNHANES 를 쓰고도
자료명을 방법 절에만 적은 논문은 놓친다. 스노볼링이 그 그물 밖을 건진다.

씨앗: 포함 129편 중 피인용 상위 N편
  forward  Europe PMC citations 엔드포인트 (200 확인, references 는 503 이라 미사용)
  both     Semantic Scholar Graph API (references + citations)
결과: results/derived/snowball.json + 신규 후보를 판정 배치로
"""
import sys, os, time, hashlib
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
S2 = "https://api.semanticscholar.org/graph/v1"
S2F = "title,year,citationCount,venue,abstract,externalIds"
CACHE = os.path.join(DER, "_snowball_cache")

KN = re.compile(r"knhanes|korea(n)? national health and nutrition examination survey", re.I)
ML = re.compile(r"machine learning|deep learning|artificial intelligence|data mining|neural network|"
                r"random forest|xgboost|gradient boost|support vector|decision tree|naive bayes|"
                r"\bSHAP\b|ensemble|lightgbm|catboost|k-nearest", re.I)


def cached(tag, fn):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, hashlib.md5(tag.encode()).hexdigest() + ".json")
    if os.path.exists(p): return load(p)
    v = fn()
    json.dump(v, open(p, "w"))
    return v


def epmc_citations(pmid, cap=600):
    def go():
        out, page = [], 1
        while len(out) < cap:
            try:
                d = get(f"{EPMC}/MED/{pmid}/citations?format=json&pageSize=200&page={page}", tries=3)
            except Exception:
                break
            cs = d.get("citationList", {}).get("citation", [])
            if not cs: break
            out += cs
            if len(cs) < 200: break
            page += 1
            time.sleep(0.3)
        return out
    return cached(f"epmc_cit:{pmid}", go)


def s2_edges(doi, direction):
    def go():
        out, off = [], 0
        while off < 600:
            try:
                d = get(f"{S2}/manuscript/DOI:{doi}/{direction}?fields={S2F}&limit=100&offset={off}", tries=3)
            except Exception:
                break
            data = d.get("data") or []
            if not data: break
            key = "citedPaper" if direction == "references" else "citingPaper"
            out += [x[key] for x in data if x.get(key)]
            if len(data) < 100: break
            off += 100
            time.sleep(1.2)
        return out
    return cached(f"s2:{doi}:{direction}", go)


def main():
    n_seed = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else 40
    R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
    C = load(os.path.join(DER, "corpus.json"))["records"]
    known_doi = {norm_doi(r.get("doi")) for r in C if r.get("doi")}
    known_pmid = {str(r["pmid"]) for r in C if r.get("pmid")}
    known_title = {norm_title(r.get("title"))[:70] for r in C if r.get("title")}
    seeds = sorted([r for r in R.values() if r["verdict"] == "INCLUDE"],
                   key=lambda r: -(r.get("cited") or 0))[:n_seed]
    print(f"  씨앗 {len(seeds)}편 (피인용 {seeds[0].get('cited')}–{seeds[-1].get('cited')})")

    cand, stat = {}, Counter()

    def consider(rec, via):
        t = (rec.get("title") or "")
        ab = rec.get("abstract") or ""
        doi = norm_doi(rec.get("doi")); pmid = str(rec.get("pmid") or "")
        if (doi and doi in known_doi) or (pmid and pmid in known_pmid) or norm_title(t)[:70] in known_title:
            stat["기존"] += 1; return
        key = doi or f"pmid:{pmid}" or norm_title(t)[:70]
        if not key or key in cand:
            if key in cand: cand[key]["n_via"] += 1
            return
        if not KN.search(t + " " + ab):
            stat["KNHANES 무관"] += 1; return
        if not ML.search(t + " " + ab):
            stat["ML 무관"] += 1; return
        stat["신규 후보"] += 1
        cand[key] = dict(uid=key, doi=doi, pmid=pmid or None, title=t, abstract=ab[:3000],
                         year=rec.get("year"), journal=rec.get("journal"), cited=rec.get("cited"),
                         via=via, n_via=1)

    for i, s in enumerate(seeds, 1):
        if s.get("pmid"):
            for c in epmc_citations(s["pmid"]):
                consider(dict(title=c.get("title"), abstract=None, doi=norm_doi(c.get("doi")),
                              pmid=c.get("id") if c.get("source") == "MED" else None,
                              year=c.get("pubYear"), journal=c.get("journalAbbreviation"),
                              cited=c.get("citedByCount")), f"epmc-cit:{s['key']}")
        if s.get("doi"):
            for direction in ("references", "citations"):
                for p in s2_edges(s["doi"], direction):
                    ext = p.get("externalIds") or {}
                    consider(dict(title=p.get("title"), abstract=p.get("abstract"),
                                  doi=norm_doi(ext.get("DOI")), pmid=ext.get("PubMed"),
                                  year=p.get("year"), journal=p.get("venue"),
                                  cited=p.get("citationCount")), f"s2-{direction[:3]}:{s['key']}")
        if i % 10 == 0 or i == len(seeds):
            print(f"    씨앗 {i:3d}/{len(seeds)} · 신규후보 {len(cand)} · {dict(stat)}", flush=True)

    recs = sorted(cand.values(), key=lambda r: (-(r["n_via"]), -(r.get("cited") or 0)))
    dump(dict(searched_on=time.strftime("%Y-%m-%d"), n_seeds=len(seeds), stat=dict(stat),
              n_candidates=len(recs), records=recs), os.path.join(DER, "snowball.json"))
    if recs:
        out = os.path.join(DER, "review")
        for i in range(0, len(recs), 40):
            json.dump([dict(uid=r["uid"], tier="SNOW", terms=[], year=r.get("year"),
                            journal=r.get("journal"), title=r.get("title"), title_ko=None,
                            abstract=r.get("abstract"), keywords=[], lang=None,
                            sources=["snowball"], epmc_layer=None) for r in recs[i:i + 40]],
                      open(os.path.join(out, f"batch_snow_{i // 40 + 1:02d}.json"), "w"),
                      ensure_ascii=False, indent=1)
    print(f"  신규 후보 {len(recs)} · 판정 배치 {(len(recs) + 39) // 40}")


if __name__ == "__main__":
    main()
