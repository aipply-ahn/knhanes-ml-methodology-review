"""Europe PMC — 주 검색원. KNHANES 말뭉치 **전체**를 받는다 (질의당 상한 없음).

    python tools/census_epmc.py

세 층을 받는다.
  A  TITLE_ABS 에 KNHANES(변형 3종)가 있는 논문 전부          → 핵심 말뭉치
  B  전문(any field) 에 KNHANES AND ML 용어가 있는 논문 전부    → 확장 말뭉치
     (초록에는 ML 단어를 안 쓰고 방법에만 쓴 논문을 건진다)
  C  ML 용어별 건수 — EPMC(TITLE_ABS) · PubMed · Crossref 교차 (건수만)

결과: results/raw/epmc_<date>.json
"""
import sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
CROSSREF = "https://api.crossref.org/works"

ML_TERMS = [
    "machine learning", "deep learning", "artificial intelligence", "neural network",
    "random forest", "gradient boosting", "XGBoost", "LightGBM", "CatBoost",
    "support vector machine", "decision tree", "k-nearest neighbor", "naive Bayes",
    "ensemble learning", "explainable", "SHAP", "multilayer perceptron",
    "convolutional neural network", "LSTM", "autoencoder", "clustering",
    "k-means", "LASSO", "elastic net", "prediction model", "risk prediction",
    "large language model", "AutoML", "TabPFN",
]

KN_TA = "(" + " OR ".join(f'TITLE_ABS:"{t}"' for t in KNHANES_TERMS) + ")"
KN_ANY = "(" + " OR ".join(f'"{t}"' for t in KNHANES_TERMS) + ")"
ML_ANY = "(" + " OR ".join(f'"{t}"' for t in ML_TERMS) + ")"


def epmc_all(query, cap=20000, label=""):
    items, cur, total = [], "*", None
    while len(items) < cap:
        u = (f"{EPMC}?query={q(query)}&format=json&pageSize=1000&resultType=core"
             f"&cursorMark={q(cur)}")
        d = get(u)
        total = d["hitCount"] if total is None else total
        rs = d.get("resultList", {}).get("result", [])
        if not rs:
            break
        items += rs
        print(f"    {label} {len(items)}/{total}", flush=True)
        nxt = d.get("nextCursorMark")
        if not nxt or nxt == cur:
            break
        cur = nxt
        time.sleep(0.3)
    return total, items


def pubmed_count(term):
    try:
        return int(get(f"{PUBMED}?db=pubmed&term={q(term)}&retmode=json&retmax=0")
                   ["esearchresult"]["count"])
    except Exception:
        return None


def crossref_count(term):
    try:
        return get(f"{CROSSREF}?query.bibliographic={q(term)}&rows=0&mailto={MAILTO}")["message"]["total-results"]
    except Exception:
        return None


def slim(v, layer):
    ft = [x.get("url") for x in (v.get("fullTextUrlList") or {}).get("fullTextUrl", []) if x.get("url")]
    return dict(
        epmc_id=v.get("id"), source=v.get("source"), pmid=v.get("pmid"), pmcid=v.get("pmcid"),
        doi=norm_doi(v.get("doi")), title=v.get("title"),
        authors=v.get("authorString"),
        author_list=[a.get("fullName") for a in (v.get("authorList") or {}).get("author", [])],
        journal=(v.get("journalInfo") or {}).get("journal", {}).get("title") or v.get("journalTitle"),
        year=int(v["pubYear"]) if str(v.get("pubYear", "")).isdigit() else None,
        pub_type=[x for x in (v.get("pubTypeList") or {}).get("pubType", [])],
        abstract=v.get("abstractText") or None,
        keywords=[k for k in (v.get("keywordList") or {}).get("keyword", [])],
        mesh=[m.get("descriptorName") for m in (v.get("meshHeadingList") or {}).get("meshHeading", [])],
        cited=v.get("citedByCount"), is_oa=v.get("isOpenAccess") == "Y",
        in_pmc=v.get("inPMC") == "Y", has_pdf=v.get("hasPDF") == "Y",
        fulltext_urls=ft, epmc_layer=layer, lang=v.get("language"),
    )


def main():
    out = dict(source="Europe PMC", api=EPMC, searched_on=time.strftime("%Y-%m-%d"),
               knhanes_terms=KNHANES_TERMS, ml_terms=ML_TERMS, layers={}, term_counts=[])

    print("A. 핵심 말뭉치 — TITLE_ABS KNHANES")
    totA, itemsA = epmc_all(KN_TA, label="A")
    print("B. 확장 말뭉치 — any-field KNHANES AND ML")
    totB, itemsB = epmc_all(f"{KN_ANY} AND {ML_ANY}", label="B")

    pool = {}
    for layer, items in (("A", itemsA), ("B", itemsB)):
        for v in items:
            k = v.get("id") or v.get("doi")
            if k in pool:
                pool[k]["epmc_layer"] = "AB" if pool[k]["epmc_layer"] != layer else layer
            else:
                pool[k] = slim(v, layer)
    out["layers"] = dict(A=dict(query=KN_TA, hits=totA, retrieved=len(itemsA)),
                         B=dict(query=f"{KN_ANY} AND {ML_ANY}", hits=totB, retrieved=len(itemsB)))

    print("C. ML 용어별 교차 건수")
    for t in ML_TERMS:
        ep = get(f"{EPMC}?query={q(KN_TA + ' AND TITLE_ABS:' + chr(34) + t + chr(34))}&format=json&pageSize=1")["hitCount"]
        pm_term = f'(KNHANES[tiab] OR "Korea National Health and Nutrition Examination Survey"[tiab] OR "Korean National Health and Nutrition Examination Survey"[tiab]) AND "{t}"[tiab]'
        pm = pubmed_count(pm_term)
        cr = crossref_count(f"KNHANES {t}")
        out["term_counts"].append(dict(term=t, epmc_title_abs=ep, pubmed_tiab=pm, crossref_bibliographic=cr))
        print(f"    {t:32s} EPMC {ep:5d} | PubMed {pm if pm is not None else '-':>5} | Crossref {cr if cr is not None else '-':>8}", flush=True)
        time.sleep(0.4)

    recs = list(pool.values())
    out.update(n_unique=len(recs), n_with_abstract=sum(1 for r in recs if r["abstract"]),
               records=recs)
    dump(out, os.path.join(RAW, f"epmc_{TODAY}.json"))
    print(f"  A {totA} · B {totB} · 고유 {len(recs)} · 초록 {out['n_with_abstract']}")


if __name__ == "__main__":
    main()
