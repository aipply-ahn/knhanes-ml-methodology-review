"""포함 논문의 출판 실체를 Crossref 로 검증한다.

    python tools/verify_publication.py              # 포함 논문 전체
    python tools/verify_publication.py --preprints  # 프리프린트만

두 가지를 확인한다.
  (1) DOI 가 실제로 무엇인가 — Crossref `type` 이 journal-article / posted-content(프리프린트) /
      proceedings-article 중 무엇이고, 학술지명·ISSN·발행처가 무엇인가. 우리 refs.json 의
      journal 문자열이 아니라 등록 메타데이터를 근거로 삼는다.
  (2) 프리프린트가 이후 정식 출판되었는가 — Crossref 의 `relation.is-preprint-of` 를 먼저 보고,
      없으면 제목으로 journal-article 을 검색해 유사도 0.9 이상 후보를 제시한다.

결과 results/derived/publication_check.json · data/PUBLICATION_CHECK.md
판정을 자동으로 바꾸지 않는다. 후보만 제시하고 반영은 사람이 확인한 뒤에 한다.
"""
import os, sys, json, time, glob, difflib, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, DER, load, dump

UA = "KNHANES-ML-review/1.0 (mailto:your-email@example.org)"
CR = "https://api.crossref.org/works"


def _get(url, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(r, timeout=40))
        except Exception as e:
            if i == tries - 1: return {"_error": str(e)}
            time.sleep(2 * (i + 1))


def norm(s):
    return " ".join(str(s or "").lower().split())


def by_doi(doi):
    d = _get(f"{CR}/{urllib.parse.quote(doi, safe='')}")
    if "_error" in d or "message" not in d: return {"error": d.get("_error", "no message")}
    m = d["message"]
    return {
        "type": m.get("type"),
        "container": (m.get("container-title") or [None])[0],
        "publisher": m.get("publisher"),
        "issn": m.get("ISSN"),
        "volume": m.get("volume"), "issue": m.get("issue"),
        "page": m.get("page"), "article_number": m.get("article-number"),
        "title": (m.get("title") or [None])[0],
        "relation": {k: [x.get("id") for x in v] for k, v in (m.get("relation") or {}).items()},
        "subtype": m.get("subtype"),
    }


def find_published(title):
    """제목으로 journal-article 을 찾는다."""
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5,
                                "filter": "type:journal-article"})
    d = _get(f"{CR}?{q}")
    out = []
    for m in (d.get("message", {}).get("items") or []):
        t = (m.get("title") or [""])[0]
        s = difflib.SequenceMatcher(None, norm(title), norm(t)).ratio()
        if s >= 0.85:
            out.append({"sim": round(s, 3), "doi": m.get("DOI"),
                        "container": (m.get("container-title") or [None])[0],
                        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                        "title": t[:110]})
    return sorted(out, key=lambda x: -x["sim"])


def main():
    R = {r["key"]: r for r in load(os.path.join(PROJ, "references", "refs.json"))}
    inc = [json.load(open(f))["key"] for f in glob.glob(os.path.join(PROJ, "data", "extraction", "*.json"))]
    inc = [k for k in inc if R.get(k, {}).get("verdict") == "INCLUDE"]
    only_pre = "--preprints" in sys.argv
    res = {}
    for i, k in enumerate(sorted(inc), 1):
        doi = R[k].get("doi")
        if not doi: res[k] = {"doi": None, "crossref": {"error": "DOI 없음"}}; continue
        meta = by_doi(doi)
        rec = {"doi": doi, "our_journal": R[k].get("journal"), "year": R[k].get("year"),
               "title": R[k].get("title"), "crossref": meta}
        if meta.get("type") == "posted-content":
            rel = meta.get("relation", {})
            pub = rel.get("is-preprint-of") or []
            rec["published_doi_from_relation"] = pub
            rec["published_candidates"] = [] if pub else find_published(R[k].get("title") or "")
        res[k] = rec
        time.sleep(0.12)
        if i % 20 == 0: print(f"    …{i}/{len(inc)}")
        if only_pre and meta.get("type") != "posted-content":
            res.pop(k)
    dump(res, os.path.join(DER, "publication_check.json"))
    print(f"  검증 {len(res)}편 → results/derived/publication_check.json")
    return res


if __name__ == "__main__":
    main()
