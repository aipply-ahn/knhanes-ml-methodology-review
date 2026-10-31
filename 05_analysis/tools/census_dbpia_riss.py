"""Direct DBpia and RISS census for KNHANES x machine learning.

Run:
    python tools/census_dbpia_riss.py search
    python tools/census_dbpia_riss.py detail
    python tools/census_dbpia_riss.py report

Searches use the same dataset and method grid as the native KCI census. Raw
responses are retained so that counts and screening decisions are auditable.
This script does not alter the main review corpus automatically.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import sys
import time
import unicodedata
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/dbpia_riss_20260906"
RAW.mkdir(parents=True, exist_ok=True)
DBPIA = "https://www.dbpia.co.kr"
RISS = "https://www.riss.kr"

DATASETS = [
    "국민건강영양조사", "KNHANES", "국민건강 영양조사",
    "National Health and Nutrition Examination Survey", "국건영",
    "국민건강·영양조사", "KNHNAES",
]
METHODS = [
    "머신러닝", "기계학습", "기계 학습", "machine learning", "딥러닝",
    "deep learning", "데이터마이닝", "data mining", "신경망",
    "neural network", "인공지능", "artificial intelligence",
    "랜덤 포레스트", "random forest", "XGBoost", "부스팅",
    "서포트 벡터", "support vector", "의사결정나무", "의사결정트리",
    "decision tree", "군집", "clustering", "잠재계층", "잠재프로파일",
    "LASSO", "elastic net", "AutoML", "SHAP", "머신 러닝", "딥 러닝",
    "인공 신경망", "SVM", "LightGBM", "AdaBoost", "CatBoost", "k-means",
    "KNN", "CHAID", "CART", "다층 퍼셉트론", "연관규칙", "association rule",
]
RISS_COLLECTIONS = ["re_a_kor", "bib_t"]  # domestic papers, theses

ML_CORE = re.compile(
    r"머신\s*러닝|기계\s*학습|딥\s*러닝|데이터\s*마이닝|인공\s*지능|"
    r"신경망|랜덤\s*포레스트|서포트\s*벡터|의사\s*결정\s*(?:나무|트리)|"
    r"machine[ -]learning|deep[ -]learning|data[ -]mining|neural[ -]network|"
    r"random[ -]forest|boost|support[ -]vector|decision[ -]tree|AutoML|SHAP|"
    r"CatBoost|XGBoost|LightGBM|AdaBoost|\b(?:SVM|KNN)\b|다층\s*퍼셉트론|"
    r"association[ -]rules?|연관\s*규칙", re.I,
)
ML_ADJ = re.compile(
    r"군집|clustering|잠재\s*(?:계층|프로파일)|latent[ -](?:class|profile)|"
    r"LASSO|elastic[ -]net|k[ -]means|\b(?:CART|CHAID)\b", re.I,
)
KNHANES = re.compile(
    r"국민[\s·⋅]*건강[\s·⋅]*영양[\s·⋅]*조사|국건영|KNHA?NES|"
    r"Korea[n]? National Health and Nutrition Examination Survey", re.I,
)


def dump(obj, path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def clean(text):
    if isinstance(text, list):
        if text and isinstance(text[0], dict):
            text = "; ".join(str(x.get("autrNm") or x.get("name") or "") for x in text)
        else:
            text = "; ".join(map(str, text))
    elif isinstance(text, dict):
        text = json.dumps(text, ensure_ascii=False)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<!H[SE]>", "", text or ""))).strip()


def norm(text):
    return "".join(c for c in unicodedata.normalize("NFKC", clean(text)).lower() if c.isalnum())


def slug(source, dataset, method, collection=""):
    return hashlib.sha256("|".join([source, dataset, method, collection]).encode()).hexdigest()[:18]


def get(session, url, **kwargs):
    for attempt in range(3):
        try:
            r = session.get(url, timeout=45, **kwargs)
            r.raise_for_status()
            return r
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def dbpia_search():
    out = RAW / "dbpia"
    out.mkdir(exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    landing = DBPIA + "/search/topSearch?searchOption=all&query=" + quote("국민건강영양조사 머신러닝")
    page = get(s, landing).text
    key = re.search(r"const searchResultKey = '([^']+)'", page).group(1)
    req = {
        "query": "", "page": 1, "pageSize": 100, "subjectCodes": [],
        "pbshYears": [], "plctNames": [], "dataTypes": [],
        "publicationInfos": [], "sort": "RANK", "collection": "ALL",
        "includeAr": False, "collectionQuery": [], "collectionQueryStr": "",
        "filter": [], "prefix": [], "realQuery": "", "startDate": "1970.01.01",
        "endDate": "", "originText": False, "subjectCategory": "",
    }
    records, queries, failures = {}, [], []
    headers = {"X-JSP-KEY": key, "Origin": DBPIA, "Referer": landing}
    for i, (dataset, method) in enumerate(((d, m) for d in DATASETS for m in METHODS), 1):
        q = f"{dataset} {method}"
        fp = out / f"query_{slug('dbpia', dataset, method)}.json"
        try:
            if fp.exists():
                data = json.loads(fp.read_text())
            else:
                req["query"] = q
                r = s.post(DBPIA + "/api/search/list", headers=headers, json=req, timeout=45)
                r.raise_for_status()
                data = r.json()
                dump(data, fp)
                time.sleep(0.05)
            total = int((data.get("pageInfo") or {}).get("totalCount", 0))
            rows = list(data.get("list") or [])
            for page_no in range(2, (total + 99) // 100 + 1):
                page_fp = out / f"query_{slug('dbpia', dataset, method)}_page{page_no}.json"
                if page_fp.exists():
                    page_data = json.loads(page_fp.read_text())
                else:
                    req["query"], req["page"] = q, page_no
                    response = s.post(DBPIA + "/api/search/list", headers=headers, json=req, timeout=45)
                    response.raise_for_status()
                    page_data = response.json()
                    dump(page_data, page_fp)
                    time.sleep(0.05)
                rows.extend(page_data.get("list") or [])
            req["page"] = 1
            queries.append({"dataset": dataset, "method": method, "total": total, "n": len(rows)})
            for z in rows:
                rid = z["nodeId"]
                r = records.setdefault(rid, {
                    "source": "DBpia", "id": rid, "title": clean(z.get("nodeTitle")),
                    "abstract": clean(z.get("abstractText")),
                    "publication_type": (z.get("labels") or {}).get("nodeType"),
                    "year": clean(z.get("publishYymm"))[:4] or None,
                    "authors": clean(z.get("authors")), "publisher": clean(z.get("iprdNm")),
                    "journal": clean(z.get("plctNm")),
                    "url": DBPIA + "/journal/articleDetail?nodeId=" + rid,
                    "search_matches": [],
                })
                r["search_matches"].append({"dataset": dataset, "method": method})
        except Exception as exc:
            failures.append({"dataset": dataset, "method": method, "error": str(exc)})
        if i % 50 == 0:
            print("DBpia", i, "/", len(DATASETS) * len(METHODS), "unique", len(records), flush=True)
    dump({"searched_on": dt.datetime.now().isoformat(), "endpoint": DBPIA + "/api/search/list",
          "datasets": DATASETS, "methods": METHODS, "query_count": len(queries),
          "failed_queries": failures, "n_unique": len(records), "queries": queries,
          "records": list(records.values())}, RAW / "dbpia_census.json")


def parse_riss_search(text, collection):
    soup = BeautifulSoup(text, "html.parser")
    count = soup.select_one(".searchBox .num") or soup.select_one(".searchResult .num")
    # The category result header is the last '(검색결과 N건)' before the list.
    nums = [int(x.get_text(strip=True).replace(",", "")) for x in soup.select("span.num")
            if x.get_text(strip=True).replace(",", "").isdigit()]
    rows = []
    for box in soup.select("div.srchResultListW > ul > li"):
        a = box.select_one('p.title a[href*="DetailView.do"][href*="control_no"]')
        hidden = box.select_one('input[name="p_control_no"]')
        if not a or not hidden:
            continue
        control, mat = hidden.get("value", "|").split("|", 1)
        etc = box.select_one("p.etc")
        spans = [clean(x.get_text(" ", strip=True)) for x in etc.find_all("span", recursive=False)] if etc else []
        year = next((x for x in spans if re.fullmatch(r"(?:19|20)\d{2}", x)), None)
        rows.append({"source": "RISS", "id": control, "mat_type": mat,
                     "collection": collection, "title": clean(a.get_text(" ", strip=True)),
                     "year": year, "list_metadata": spans,
                     "url": urljoin(RISS, a.get("href")), "search_matches": []})
    return (max(nums) if nums else len(rows)), rows


def riss_search():
    out = RAW / "riss"
    out.mkdir(exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    records, queries, failures = {}, [], []
    jobs = [(d, m, c) for d in DATASETS for m in METHODS for c in RISS_COLLECTIONS]
    for i, (dataset, method, collection) in enumerate(jobs, 1):
        q = f"{dataset} {method}"
        fp = out / f"query_{slug('riss', dataset, method, collection)}.html"
        params = {"isDetailSearch": "N", "searchGubun": "true", "viewYn": "OP",
                  "query": q, "colName": collection, "iStartCount": "0", "pageScale": "100"}
        try:
            if fp.exists():
                text = fp.read_text(errors="ignore")
            else:
                text = get(s, RISS + "/search/Search.do", params=params).text
                fp.write_text(text)
                time.sleep(0.08)
            total, rows = parse_riss_search(text, collection)
            for start in range(100, total, 100):
                page_fp = out / f"query_{slug('riss', dataset, method, collection)}_start{start}.html"
                page_params = dict(params, iStartCount=str(start))
                if page_fp.exists():
                    page_text = page_fp.read_text(errors="ignore")
                else:
                    page_text = get(s, RISS + "/search/Search.do", params=page_params).text
                    page_fp.write_text(page_text)
                    time.sleep(0.08)
                _, page_rows = parse_riss_search(page_text, collection)
                rows.extend(page_rows)
            queries.append({"dataset": dataset, "method": method, "collection": collection,
                            "total": total, "n": len(rows)})
            for z in rows:
                rid = z["id"]
                if rid not in records:
                    records[rid] = z
                records[rid]["search_matches"].append({"dataset": dataset, "method": method,
                                                        "collection": collection})
        except Exception as exc:
            failures.append({"dataset": dataset, "method": method,
                             "collection": collection, "error": str(exc)})
        if i % 50 == 0:
            print("RISS", i, "/", len(jobs), "unique", len(records), flush=True)
    dump({"searched_on": dt.datetime.now().isoformat(), "endpoint": RISS + "/search/Search.do",
          "collections": RISS_COLLECTIONS, "datasets": DATASETS, "methods": METHODS,
          "query_count": len(queries), "failed_queries": failures, "n_unique": len(records),
          "queries": queries, "records": list(records.values())}, RAW / "riss_census.json")


def search():
    dbpia_search()
    riss_search()


def riss_detail():
    census = json.loads((RAW / "riss_census.json").read_text())
    out = RAW / "riss_detail"
    out.mkdir(exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    enriched = []
    for i, row in enumerate(census["records"], 1):
        fp = out / f"{row['id']}.html"
        try:
            if fp.exists():
                text = fp.read_text(errors="ignore")
            else:
                text = get(s, row["url"]).text
                fp.write_text(text)
                time.sleep(0.1)
            soup = BeautifulSoup(text, "html.parser")
            metas = {m.get("name"): clean(m.get("content")) for m in soup.find_all("meta", attrs={"name": True})}
            # RISS layouts use several ids/classes; select the longest abstract-like block.
            candidates = []
            for x in soup.select("#abs1, #abs2, #abstract, .abstract, .abstractTxt, .contentAbstract"):
                t = clean(x.get_text(" ", strip=True))
                if len(t) > 80:
                    candidates.append(t)
            for key in ["citation_abstract", "DC.Description", "description"]:
                if len(metas.get(key, "")) > 80:
                    candidates.append(metas[key])
            r = dict(row)
            r.update(abstract=max(candidates, key=len) if candidates else "",
                     doi=metas.get("citation_doi") or metas.get("DC.Identifier"),
                     detail_title=metas.get("citation_title") or row["title"],
                     authors=[clean(x.get("content")) for x in soup.find_all("meta", {"name": "citation_author"})])
            enriched.append(r)
        except Exception as exc:
            r = dict(row); r["detail_error"] = str(exc); enriched.append(r)
        if i % 50 == 0:
            print("RISS detail", i, "/", len(census["records"]), flush=True)
    dump(enriched, RAW / "riss_records_detailed.json")


def detail():
    riss_detail()


def classify(text):
    if not KNHANES.search(text):
        return "EXCLUDE_DATASET_NOT_CONFIRMED"
    if ML_CORE.search(text):
        return "CORE_ML_TITLE_ABSTRACT"
    if ML_ADJ.search(text):
        return "ADJACENT_ML_TITLE_ABSTRACT"
    return "FULL_TEXT_NEEDED_ML_NOT_CONFIRMED"


def match_existing(row, refs):
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", row.get("doi") or "", flags=re.I).lower()
    if doi:
        hit = next((r for r in refs if (r.get("doi") or "").lower() == doi), None)
        if hit:
            return hit["key"], "doi"
    a = norm(row.get("title")); b = norm(row.get("detail_title"))
    for r in refs:
        t = norm(r.get("title"))
        if len(t) >= 20 and (t == a or t == b):
            return r["key"], "title"
    return None, None


def report():
    import csv
    refs = json.loads((ROOT / "references/refs.json").read_text())
    # Korean and English titles in KCI provide a deterministic bridge to records whose
    # canonical reference title is in the other language.
    alias_refs = list(refs)
    kci_path = ROOT / "data/KCI_CENSUS.tsv"
    if kci_path.exists():
        with kci_path.open(encoding="utf-8-sig") as handle:
            for kci in csv.DictReader(handle, delimiter="\t"):
                titles = [kci.get("title"), kci.get("title_en")]
                hit = next((r for r in refs if any(norm(t) and norm(t) == norm(r.get("title")) for t in titles)), None)
                if hit:
                    for title in titles:
                        if title:
                            alias_refs.append({"key": hit["key"], "title": title, "doi": hit.get("doi")})
    db = json.loads((RAW / "dbpia_census.json").read_text())["records"]
    rp = RAW / "riss_records_detailed.json"
    ri = json.loads(rp.read_text()) if rp.exists() else json.loads((RAW / "riss_census.json").read_text())["records"]
    rows = []
    for source_rows in [db, ri]:
        for row in source_rows:
            text = " ".join(clean(row.get(k)) for k in ["title", "detail_title", "abstract"])
            key, basis = match_existing(row, alias_refs)
            rows.append(dict(row, screening=classify(text), existing_key=key, match_basis=basis,
                             abstract_available=bool(clean(row.get("abstract")))))
    # Cross-database title clusters, retained at report level rather than deleting records.
    clusters = {}
    for row in rows:
        clusters.setdefault(norm(row.get("title")), []).append(row)
    for group in clusters.values():
        label = ";".join(sorted(f"{x['source']}:{x['id']}" for x in group))
        for row in group:
            row["cross_db_cluster"] = label
    dump(rows, RAW / "screening_candidates.json")

    cols = ["source", "id", "publication_type", "collection", "year", "title",
            "screening", "abstract_available", "existing_key", "match_basis", "url"]
    with (ROOT / "data/DBPIA_RISS_CENSUS.tsv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    counts = {}
    for row in rows:
        k = (row["source"], row["screening"], bool(row["existing_key"]))
        counts[k] = counts.get(k, 0) + 1
    md = ["# DBpia and RISS direct-search census", "",
          f"Search date: {dt.date.today().isoformat()}", "",
          f"Grid: {len(DATASETS)} dataset expressions × {len(METHODS)} method expressions. "
          f"RISS searched domestic journal papers and theses separately.", "",
          "| Source | Abstract screening | Existing corpus match | Records |",
          "|---|---|---:|---:|"]
    for (source, status, matched), n in sorted(counts.items()):
        md.append(f"| {source} | {status} | {'yes' if matched else 'no'} | {n} |")
    md += ["", "`CORE_ML_TITLE_ABSTRACT` and `ADJACENT_ML_TITLE_ABSTRACT` mean that both "
           "KNHANES use and an eligible method were explicit in the title/abstract. Records marked "
           "`FULL_TEXT_NEEDED_ML_NOT_CONFIRMED` require full-text adjudication. Matching to the existing "
           "corpus is a deduplication aid, not a final eligibility decision.", ""]
    (ROOT / "data/DBPIA_RISS_CENSUS.md").write_text("\n".join(md))
    print("records", len(rows), "unmatched core/adjacent",
          sum(not r["existing_key"] and r["screening"].startswith(("CORE", "ADJACENT")) for r in rows))


if __name__ == "__main__":
    {"search": search, "detail": detail, "report": report}[sys.argv[1]]()
