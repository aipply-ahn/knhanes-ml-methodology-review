"""Run the October 2026 database search (tools/oct_search/query.py) in every source, deduplicate, apply the
publication-type rule and check which analysed studies are retrieved. Deterministic; no AI.
    python3 tools/oct_search/run_search.py
Outputs: results/oct_search/{raw_*.json, records.json, flow.json}"""
import csv, hashlib, json, math, os, re, sys, time, unicodedata, urllib.parse as up
import requests
from bs4 import BeautifulSoup
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "tools/oct_search"))
import common, query as Q
OUT = os.path.join(ROOT, "results/oct_search"); os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "knhanes-ml-review/1.0"


def cached(name, fn):
    p = os.path.join(OUT, f"raw_{name}.json")
    if os.path.exists(p):
        return json.load(open(p))
    d = fn(); json.dump(d, open(p, "w"), ensure_ascii=False); return d


def europepmc():
    out, cur = [], "*"
    while True:
        d = S.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params=dict(query=Q.europepmc(), format="json", pageSize=1000,
                  cursorMark=cur, resultType="core"), timeout=120).json()
        for r in d["resultList"]["result"]:
            out.append(dict(source="Europe PMC", id=r.get("id"), doi=r.get("doi"), pmid=r.get("pmid"), title=r.get("title"), year=r.get("pubYear"),
                            ptype=";".join((r.get("pubTypeList") or {}).get("pubType", [])), journal=(r.get("journalInfo") or {}).get("journal", {}).get("title")))
        nxt = d.get("nextCursorMark")
        if not nxt or nxt == cur or not d["resultList"]["result"]:
            return dict(query=Q.europepmc(), searched=time.strftime("%Y-%m-%d"), hits=d["hitCount"], records=out)
        cur = nxt


def pubmed():
    import xml.etree.ElementTree as ET
    r = S.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", data=dict(db="pubmed", retmode="json", retmax=10000, term=Q.pubmed()), timeout=120).json()
    ids = r["esearchresult"]["idlist"]; out = []
    for i in range(0, len(ids), 200):
        for n in range(5):
            try:
                root = ET.fromstring(S.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", data=dict(db="pubmed", id=",".join(ids[i:i + 200]), retmode="xml"), timeout=120).content)
                break
            except ET.ParseError:
                time.sleep(5 * (n + 1))
        for art in root.findall(".//PubmedArticle"):
            a = art.find("MedlineCitation/Article"); own = art.find("PubmedData/ArticleIdList")
            doi = next((x.text for x in (list(own) if own is not None else []) if x.get("IdType") == "doi"), None)
            out.append(dict(source="PubMed", id=art.findtext("MedlineCitation/PMID"), pmid=art.findtext("MedlineCitation/PMID"), doi=doi,
                            title="".join(a.find("ArticleTitle").itertext()) if a.find("ArticleTitle") is not None else None,
                            year=a.findtext("Journal/JournalIssue/PubDate/Year"), ptype=";".join(p.text or "" for p in a.findall("PublicationTypeList/PublicationType")),
                            journal=a.findtext("Journal/Title")))
        time.sleep(0.4)
    return dict(query=Q.pubmed(), searched=time.strftime("%Y-%m-%d"), hits=int(r["esearchresult"]["count"]), records=out)


def openalex():
    key = common._openalex_keys()[0]; out, cur = [], "*"
    while cur:
        # the two term groups go in as two filters (ANDed by OpenAlex); one boolean "(A) AND (B)" string drops records
        # that match both groups (checked 2026-11-01 on known records)
        flt = Q.openalex_filter()
        d = S.get("https://api.openalex.org/works", params={"filter": flt, "per-page": 200, "cursor": cur,
                  "select": "id,doi,display_name,publication_year,type,ids,primary_location", "api_key": key}, timeout=120).json()
        for w in d["results"]:
            if any(x["id"] == w["id"] for x in out):  # cursor paging can return a work twice
                continue
            out.append(dict(source="OpenAlex", id=w["id"], doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
                            pmid=((w.get("ids") or {}).get("pmid") or "").rsplit("/", 1)[-1] or None, title=w.get("display_name"),
                            year=w.get("publication_year"), ptype=w.get("type"), journal=((w.get("primary_location") or {}).get("source") or {}).get("display_name")))
        cur = d["meta"].get("next_cursor") if d["results"] else None
    return dict(query=Q.openalex_filter(), searched=time.strftime("%Y-%m-%d"), hits=d["meta"]["count"], records=out)


def kci():
    SEARCH = "https://www.kci.go.kr/kciportal/po/search/poArtiSearList.kci"; cache = os.path.join(OUT, "kci_pages"); os.makedirs(cache, exist_ok=True)
    recs, log = {}, []
    for ds in Q.SURVEY_KO:
        for term in [t.rstrip("*") for t in Q.ML] + Q.ML_KO:
            p = {"poSearchBean.conditionList": "KEYALL", "poSearchBean.keywordList": ds, "poSearchBean.refineOperationList": "AND",
                 "poSearchBean.refineConditionList": "KEYALL", "poSearchBean.refineKeywordList": term, "poSearchBean.docsCount": "50"}
            slug = hashlib.sha256((ds + "|" + term).encode()).hexdigest()[:14]; page, total = 1, None
            while total is None or page <= math.ceil(total / 50):
                f = os.path.join(cache, f"{slug}_{page}.html")
                if os.path.exists(f):
                    html = open(f).read()
                else:
                    p["poSearchBean.startPg"] = str(page); html = S.get(SEARCH, params=p, timeout=60).text; open(f, "w").write(html); time.sleep(0.3)
                soup = BeautifulSoup(html, "html.parser"); c = soup.find("input", {"name": "allCnt"}); total = int(c["value"]) if c else 0
                for a in soup.select("a.subject"):
                    tr = a.find_parent("tr"); fl = {x.get("name"): x.get("value", "") for x in tr.find_all("input")}
                    k = re.search(r"ART\d+", a["href"]).group()
                    recs.setdefault(k, dict(source="KCI", id=k, kci_id=k, title=fl.get("R_INDE_TITL") or a.get_text(" ", strip=True),
                                            journal=fl.get("R_SERE_NM"), year=(fl.get("R_PUBI_DT") or "")[:4], ptype="", doi=None, pmid=None))
                page += 1
            log.append(dict(survey=ds, term=term, hits=total))
    return dict(query="KEYALL: survey name AND term, for every survey name x term", searched=time.strftime("%Y-%m-%d"),
                queries=log, hits=len(recs), records=list(recs.values()))


def kdca():
    import glob
    kf = sorted(glob.glob(os.path.join(ROOT, "results/rerun_20261031/raw/kdca_2*.json")))[-1]  # latest download of the list
    K = json.load(open(kf))["records"]
    rx = re.compile("|".join([re.escape(t.rstrip("*")) for t in Q.ML] + [r"\s?".join(map(re.escape, t)) for t in Q.ML_KO]), re.I)
    out = [dict(source="KDCA", id=f"kdca:{k['kdca_no']}", doi=None, pmid=None, title=k.get("title_en") or k.get("title"), title_ko=k.get("title_ko"),
                year=k.get("year"), ptype=k.get("paper_type"), journal=k.get("journal"))
           for k in K if rx.search(" ".join(str(k.get(f) or "") for f in ("title", "title_ko", "title_en", "keywords_ko", "keywords_en")))]
    return dict(query="complete KDCA KNHANES publication list, the same terms applied to titles and keywords", list_file=os.path.basename(kf), searched=time.strftime("%Y-%m-%d"), hits=len(out), records=out)


def nt(t):
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFKC", t or "").lower())


if __name__ == "__main__":
    raw = {n: cached(n, f) for n, f in (("europepmc", europepmc), ("pubmed", pubmed), ("openalex", openalex), ("kci", kci), ("kdca", kdca))}
    # KCI result lists give the Korean title only; add English title and DOI from the KCI article page (bibliographic
    # completion, cached in results/rerun_20261031/raw/kci_all_20261101/pages; fetched for ids not yet cached)
    sys.path.insert(0, os.path.join(ROOT, "tools/rerun_20261031")); import kci_enrich
    for r in raw["kci"]["records"]:
        e = kci_enrich.parse(r["kci_id"])
        r.update(title_ko=e.get("title_ko") or r["title"], title=e.get("title_en") or r["title"], doi=e.get("doi"),
                 _text=" ".join(filter(None, [e.get("title_ko"), e.get("title_en"), e.get("abstract_ko"), e.get("abstract_en"), e.get("keywords")])))
    # KCI search returns records whose title, abstract and keywords do not contain the query terms (term splitting or
    # expansion; checked 2026-11-02: 171 of 171 records returned for 딥러닝 lacked the term), so the same query is applied
    # to the KCI title, abstract and keywords: a survey name AND a term, exact (Korean terms spacing-insensitive)
    def trx(t):
        t = t.rstrip("*")
        if re.search(r"[가-힣]", t):
            return r"\s?".join(map(re.escape, t.replace(" ", "")))
        return r"\b" + r"[\s-]".join(map(re.escape, re.split(r"[\s-]", t)))
    SVX = re.compile("|".join(trx(t) for t in Q.SURVEY + Q.SURVEY_KO), re.I)
    MLX = re.compile("|".join(trx(t) for t in Q.ML + Q.ML_KO), re.I)
    raw["kci"]["returned_by_kci"] = len(raw["kci"]["records"])
    raw["kci"]["records"] = [r for r in raw["kci"]["records"] if SVX.search(r["_text"]) and MLX.search(r["_text"])]
    raw["kci"]["hits"] = len(raw["kci"]["records"])
    flow = {"identified": {n: d["hits"] for n, d in raw.items()}, "kci_returned_before_term_check": raw["kci"].get("returned_by_kci")}
    flow["identified_total"] = sum(len(d["records"]) for d in raw.values())
    # deduplicate: DOI, PMID, normalised title (English or Korean)
    groups, idx = [], {}
    for n, d in raw.items():
        for r in d["records"]:
            ks = [k for k in (("d:" + common.norm_doi(r["doi"])) if r.get("doi") else None, ("p:" + str(r["pmid"])) if r.get("pmid") else None,
                              *[("t:" + nt(t)) for t in (r.get("title"), r.get("title_ko")) if t and len(nt(t)) > 12]) if k]
            g = next((idx[k] for k in ks if k in idx), None)
            if g is None:
                g = dict(members=[], keys=set()); groups.append(g)
            g["members"].append(r); g["keys"].update(ks)
            for k in ks: idx[k] = g
    # a record without DOI or PMID whose title is a truncated form of another record's title (same year +-1) is the same
    # report: KDCA and KCI lists and some OpenAlex entries cut titles before the subtitle (checked 2026-11-02)
    full = [(g, nt(m.get("title")), m.get("year")) for g in groups for m in g["members"] if m.get("title")]
    for g in list(groups):
        if any(m.get("doi") or m.get("pmid") for m in g["members"]):
            continue
        cand = [(nt(m.get("title")), m.get("year")) for m in g["members"] if m.get("title") and len(nt(m.get("title"))) >= 40]
        import difflib
        h = next((h for t, y in cand for h, u, yy in full if h is not g and u != t and (not y or not yy or abs(int(y) - int(yy)) <= 1)
                  and (u.startswith(t) or (abs(len(u) - len(t)) < 6 and difflib.SequenceMatcher(None, t, u).ratio() >= 0.97))), None)
        if h is not None:
            h["members"] += g["members"]; h["keys"] |= g["keys"]; groups.remove(g)
            for k in g["keys"]: idx[k] = h
            full = [(h if x is g else x, u, y) for x, u, y in full]
    # metadata errors that no rule can match, identified during abstract retrieval (same abstract and source page):
    # OpenAlex W7224723616 has the author list as its title and no DOI; it is the article 10.1111/jphd.12293
    # W2525892710: second OpenAlex entry of the IJACSA 2015 article (title with its subtitle, no DOI; found at full-text
    # retrieval, 2026-11-05)
    # W2945993365, W2898230957, W2171107267: OpenAlex entries with only the Korean title and no DOI of three KCI articles
    # (same PDF or same first page; found at full-text assessment, 2026-11-05)
    for wid, doi in (("https://openalex.org/W7224723616", "10.1111/jphd.12293"), ("https://openalex.org/W2525892710", "10.14569/ijacsa.2015.061213"),
                     ("https://openalex.org/W2945993365", "10.7586/jkbns.2019.21.1.85"), ("https://openalex.org/W2898230957", "10.7586/jkbns.2018.20.2.103"),
                     ("https://openalex.org/W2171107267", "10.5762/kais.2013.14.7.3368")):
        g = next((g for g in groups if any(m.get("id") == wid for m in g["members"])), None); h = idx.get("d:" + common.norm_doi(doi))
        if g is not None and h is not None and g is not h:
            h["members"] += g["members"]; h["keys"] |= g["keys"]; groups.remove(g)
    flow["after_deduplication"] = len(groups)
    NONREPORT = {"software", "dataset", "supplementary-materials", "conference-abstract", "abstract", "peer-review", "paratext"}
    # conference abstracts whose metadata type is "journal-article": candidates found from supplement issue or page
    # numbering (e.g. "Supplement_1", "S1", "10S", "A141") and each confirmed on the publisher page (2026-11-05)
    VERIFIED_ABSTRACTS = {
        "10.1093/eurpub/ckaf161.042": "EUPHA conference abstract (Eur J Public Health supplement)",
        "10.1096/fasebj.27.1_supplement.635.5": "Experimental Biology meeting abstract (FASEB J supplement)",
        "10.1111/aos.17042": "congress abstract (Acta Ophthalmologica supplement)",
        "10.1186/1687-9856-2013-s1-p171": "poster presentation abstract (Int J Pediatr Endocrinol supplement)",
        "10.1681/asn.20213210s1686c": "Kidney Week poster abstract (J Am Soc Nephrol supplement)",
        "10.1681/asn.2024rggdf78f": "Kidney Week poster abstract TH-PO971 (J Am Soc Nephrol supplement)",
        "10.1136/oemed-2016-103951.383": "conference poster abstract P060 (Occup Environ Med supplement, page A141)",
        "10.1016/j.atherosclerosis.2024.118188": "EAS 2024 congress abstract (Atherosclerosis supplement 'EAS Abstracts 2024')",
        "10.1093/eurheartj/ehag785.3003": "ESC congress abstract (Eur Heart J Supplement_1)",
        "10.1093/ndt/gfaf116.1930": "ERA Congress abstract #2083 (Nephrol Dial Transplant 'Congress Abstracts' supplement)",
        "10.1210/jendso/bvae163.1510": "ENDO 2024 abstract 7190 (J Endocr Soc 'ENDO 2024 Abstracts' supplement)",
        "10.1210/jendso/bvaf149.1694": "ENDO 2025 poster abstract MON-220 (J Endocr Soc supplement)",
        "10.1210/jendso/bvaf149.553": "ENDO 2025 poster abstract MON-811 (J Endocr Soc supplement)",
        "10.2337/db25-1581-p": "ADA Scientific Sessions abstract 1581-P (Diabetes Supplement_1)",
        "10.14309/00000434-201710001-00964": "ACG 2017 accepted abstract 963 (Am J Gastroenterol supplement, page S541)",
    }
    REPOSITORY = ("10.5281/", "10.6084/", "10.17605/", "10.5061/", "10.7910/", "10.17632/")  # Zenodo, figshare, OSF, Dryad, Dataverse, Mendeley Data
    TYPE = re.compile(r"\b(review|editorial|erratum|corrigendum|retraction|news|paratext|dissertation|thesis)\b|학위", re.I)
    TITLE = re.compile(r"systematic review|scoping review|meta-analysis|narrative review|umbrella review|literature review|\breview of\b|"
                       r"study protocol|protocol for|erratum|corrigendum|correction to|retraction", re.I)
    for g in groups:
        types = " ".join(str(m.get("ptype") or "") for m in g["members"])
        journal_src = any(m["source"] == "KCI" or re.search(r"journal article|research-article|^article$|학술지", str(m.get("ptype") or ""), re.I) for m in g["members"])
        thesis = bool(re.search(r"dissertation|thesis|학위", types, re.I)) and not journal_src
        other = bool(re.search(r"\b(review|editorial|erratum|corrigendum|retraction|news|paratext)\b", types, re.I) and not re.search(r"research-article", types, re.I))
        # not a research report: every member is typed as a code/data/supplement deposit, a repository project or a
        # conference abstract (OpenAlex/Crossref types; Europe PMC "Abstract"); added 2026-11-04 after such records were
        # found among the screened records
        nonreport = any(common.norm_doi(m["doi"]) in VERIFIED_ABSTRACTS for m in g["members"] if m.get("doi")) or all(str(m.get("ptype") or "").lower() in NONREPORT or (str(m.get("ptype") or "").lower() == "other" and
                        str(m.get("doi") or "").lower().startswith(REPOSITORY)) for m in g["members"])
        g["excluded_type"] = "thesis" if thesis else ("type" if other or any(TITLE.search(m.get("title") or "") for m in g["members"])
                                                      else ("nonreport" if nonreport else ""))
    flow["excluded_thesis"] = sum(g["excluded_type"] == "thesis" for g in groups)
    flow["excluded_other_type"] = sum(g["excluded_type"] == "type" for g in groups)
    flow["excluded_not_research_report"] = sum(g["excluded_type"] == "nonreport" for g in groups)
    flow["records_for_full_text"] = sum(not g["excluded_type"] for g in groups)
    json.dump(flow, open(os.path.join(OUT, "flow.json"), "w"), indent=1, ensure_ascii=False)
    json.dump([dict(members=g["members"], excluded_type=g["excluded_type"]) for g in groups], open(os.path.join(OUT, "records.json"), "w"), ensure_ascii=False)
    print(json.dumps(flow, indent=1, ensure_ascii=False))
