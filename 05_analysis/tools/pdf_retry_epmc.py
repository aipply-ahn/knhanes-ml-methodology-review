"""PDF 실패분 재시도 — DOI 로 Europe PMC 를 조회해 PMCID 를 얻고 render 로 받는다. refs 파일 제자리 갱신.

    python tools/pdf_retry_epmc.py references/benchmark_reviews.json
"""
import sys, time, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *
from fetch_pdf import try_url, PDFDIR

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def main():
    path = sys.argv[1]
    R = load(path); ok = 0
    for r in R:
        if r.get("pdf_file") or r["verdict"] == "EXCLUDE" or not r.get("doi"):
            continue
        try:
            d = get(f"{EPMC}?query={q('DOI:' + chr(34) + r['doi'] + chr(34))}&format=json&pageSize=1&resultType=lite")
            rs = d.get("resultList", {}).get("result", [])
        except Exception:
            rs = []
        pmc = rs[0].get("pmcid") if rs else None
        cands = []
        if pmc: cands.append(f"https://europepmc.org/articles/{pmc}?pdf=render")
        if r["doi"].startswith("10.3390/"):
            cands.append(f"https://doi.org/{r['doi']}")           # MDPI 랜딩 → citation_pdf_url
        for u in cands:
            b, info = try_url(u)
            if b:
                dst = os.path.join(PDFDIR, f"{r['key']}.pdf"); open(dst, "wb").write(b)
                r["pdf_file"], r["pdf_src"] = f"{r['key']}.pdf", u; ok += 1
                print(f"  OK {r['key']:36s} {len(b)//1024:6d}KB {u[:70]}"); break
        else:
            if pmc: print(f"  -- {r['key']:36s} pmc {pmc} 실패")
        time.sleep(0.5)
    dump(R, path); print(f"  재시도 성공 {ok}")


if __name__ == "__main__":
    main()
