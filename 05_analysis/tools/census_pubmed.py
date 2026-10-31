"""PubMed — 완전성 교차. E-utilities 로 PMID 전체를 받아 Europe PMC 와 대조하고,
EPMC 에 없는 PMID 는 efetch 로 서지·초록을 채운다.

    python tools/census_pubmed.py

결과: results/raw/pubmed_<date>.json
"""
import sys, time, xml.etree.ElementTree as ET
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TERM = ('KNHANES[tiab] OR "Korea National Health and Nutrition Examination Survey"[tiab] '
        'OR "Korean National Health and Nutrition Examination Survey"[tiab] '
        'OR "Korea National Health and Nutrition Examination Survey"[mh]')


def esearch_all(term):
    d = get(f"{EU}/esearch.fcgi?db=pubmed&term={q(term)}&retmode=json&retmax=0&usehistory=y")
    r = d["esearchresult"]
    total, we, qk = int(r["count"]), r["webenv"], r["querykey"]
    ids = []
    for start in range(0, total, 10000):
        d = get(f"{EU}/esearch.fcgi?db=pubmed&term={q(term)}&retmode=json&retmax=10000&retstart={start}")
        ids += d["esearchresult"]["idlist"]
        time.sleep(0.4)
    return total, ids


def efetch(pmids):
    recs = []
    for i in range(0, len(pmids), 200):
        chunk = pmids[i:i + 200]
        xml = get(f"{EU}/efetch.fcgi?db=pubmed&id={','.join(chunk)}&retmode=xml", raw=True)
        root = ET.fromstring(xml)
        for art in root.findall(".//PubmedArticle"):
            mc = art.find(".//MedlineCitation")
            a = mc.find("Article")
            pmid = mc.findtext("PMID")
            title = "".join(a.find("ArticleTitle").itertext()) if a.find("ArticleTitle") is not None else None
            abst = " ".join("".join(x.itertext()) for x in a.findall(".//AbstractText")) or None
            year = a.findtext(".//Journal/JournalIssue/PubDate/Year") or a.findtext(".//ArticleDate/Year")
            doi = next((x.text for x in art.findall(".//ArticleId") if x.get("IdType") == "doi"), None)
            pmc = next((x.text for x in art.findall(".//ArticleId") if x.get("IdType") == "pmc"), None)
            aus = [f"{au.findtext('LastName') or ''} {au.findtext('Initials') or ''}".strip()
                   for au in a.findall(".//Author")]
            recs.append(dict(pmid=pmid, doi=norm_doi(doi), pmcid=pmc, title=title, abstract=abst,
                             year=int(year) if year and year.isdigit() else None,
                             journal=a.findtext(".//Journal/Title"), authors=", ".join(aus),
                             author_list=aus,
                             mesh=[m.findtext("DescriptorName") for m in mc.findall(".//MeshHeading")],
                             keywords=[k.text for k in mc.findall(".//Keyword")],
                             pub_type=[p.text for p in a.findall(".//PublicationType")]))
        print(f"    efetch {min(i + 200, len(pmids))}/{len(pmids)}", flush=True)
        time.sleep(0.4)
    return recs


def main():
    total, ids = esearch_all(TERM)
    print(f"  PubMed esearch {total} · 받음 {len(ids)}")
    # EPMC 에 있는 PMID 와 대조
    import glob
    ep = sorted(glob.glob(os.path.join(RAW, "epmc_*.json")))
    have = set()
    if ep:
        have = {r["pmid"] for r in load(ep[-1])["records"] if r.get("pmid")}
    missing = [p for p in ids if p not in have]
    print(f"  EPMC 에 없는 PMID {len(missing)} → efetch")
    recs = efetch(missing) if missing else []
    out = dict(source="PubMed", api=EU, searched_on=time.strftime("%Y-%m-%d"), term=TERM,
               hits=total, pmids=ids, n_missing_from_epmc=len(missing), records=recs)
    dump(out, os.path.join(RAW, f"pubmed_{TODAY}.json"))


if __name__ == "__main__":
    main()
