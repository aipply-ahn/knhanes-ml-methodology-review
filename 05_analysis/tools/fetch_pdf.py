"""포함 판정 논문의 PDF 를 받아 references/pdf/<bibkey>.pdf 로 저장한다.

    python tools/fetch_pdf.py [--only-missing] [--verdicts INCLUDE,INCLUDE_ADJACENT,UNCERTAIN] [--refs references/benchmark_reviews.json]

후보 URL 순서
  1. OpenAlex best_oa_location.pdf_url (corpus.pdf_url)
  2. Europe PMC render  (PMCID 가 있을 때)  https://europepmc.org/articles/PMC…?pdf=render
  3. Unpaywall  best_oa_location.url_for_pdf
  4. 출판사 패턴 (MDPI · PLOS · Nature/SciRep · Springer/BMC · Frontiers · JMIR · Elsevier OA · KoreaMed 계열)
  5. 랜딩 페이지에서 citation_pdf_url 메타태그

성공 판정: 응답 본문이 %PDF 로 시작하고 20KB 이상.
로그: references/_logs/pdf_<date>.log · 결과 필드는 references/refs.json 의 pdf_file / pdf_src
"""
import sys, time, urllib.request, urllib.error
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

PDFDIR = os.path.join(REF, "pdf")
BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
           "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=BROWSER)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


def is_pdf(b):
    return b[:5] == b"%PDF-" and len(b) > 20000


def unpaywall(doi):
    try:
        d = get(f"https://api.unpaywall.org/v2/{doi}?email={MAILTO}", tries=2, timeout=25)
    except Exception:
        return []
    out = []
    for loc in [d.get("best_oa_location")] + (d.get("oa_locations") or []):
        if loc and loc.get("url_for_pdf") and loc["url_for_pdf"] not in out:
            out.append(loc["url_for_pdf"])
    return out


def publisher_patterns(doi, landing):
    c = []
    if not doi: return c
    if doi.startswith("10.3390/"):          # MDPI
        c.append(f"https://www.mdpi.com/{doi.split('10.3390/')[1]}/pdf")
    if doi.startswith("10.1371/"):          # PLOS
        c.append(f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable")
    if doi.startswith("10.1038/"):          # Nature/Sci Rep
        c.append(f"https://www.nature.com/articles/{doi.split('/', 1)[1]}.pdf")
    if doi.startswith(("10.1186/", "10.1007/", "10.1140/")):  # BMC/Springer
        c.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if doi.startswith("10.3389/"):          # Frontiers
        c.append(f"https://www.frontiersin.org/articles/{doi}/pdf")
    if doi.startswith("10.2196/"):          # JMIR
        c.append(f"https://www.jmir.org/{doi.split('10.2196/')[1]}/PDF")
    if doi.startswith("10.1016/"):          # Elsevier
        c.append(f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1].replace('.', '').replace('-', '').upper()}/pdfft")
    if doi.startswith("10.3346/"):          # JKMS
        c.append(f"https://jkms.org/pdf/{doi}")
    if doi.startswith("10.4178/"):          # Epidemiol Health
        c.append(f"https://www.e-epih.org/upload/pdf/{doi.split('/')[-1]}.pdf")
    if doi.startswith("10.1097/"):          # LWW (Medicine) — landing 가 대체로 OA
        pass
    c.append(f"https://doi.org/{doi}")     # 랜딩 → citation_pdf_url
    return c


def meta_pdf(html):
    m = re.search(r'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"', html, re.I) or \
        re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="citation_pdf_url"', html, re.I)
    return m.group(1) if m else None


def try_url(u, depth=0):
    try:
        b, ct, final = fetch(u)
    except Exception as e:
        return None, f"{type(e).__name__}"
    if is_pdf(b):
        return b, final
    if depth == 0 and b"<html" in b[:2000].lower():
        pu = meta_pdf(b.decode("utf-8", "ignore"))
        if pu:
            if pu.startswith("/"):
                from urllib.parse import urljoin
                pu = urljoin(final, pu)
            return try_url(pu, 1)
    return None, f"not-pdf({ct[:20]})"


def candidates(r):
    cands = []
    if r.get("pdf_url"): cands.append(r["pdf_url"])
    if r.get("pmcid"):
        pmc = r["pmcid"] if str(r["pmcid"]).startswith("PMC") else f"PMC{r['pmcid']}"
        cands += [f"https://europepmc.org/articles/{pmc}?pdf=render",
                  f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}/pdf/"]
    if r.get("doi"):
        cands += unpaywall(r["doi"])
        cands += publisher_patterns(r["doi"], r.get("landing"))
    for u in r.get("fulltext_urls") or []:
        if u not in cands: cands.append(u)
    return cands


def work(r):
    dst = os.path.join(PDFDIR, f"{r['key']}.pdf")
    seen, why = set(), []
    for u in candidates(r):
        if not u or u in seen: continue
        seen.add(u)
        b, info = try_url(u)
        if b:
            open(dst, "wb").write(b)
            return r, u, len(b), why
        why.append(f"{u[:70]} {info}")
        time.sleep(0.3)
    return r, None, 0, why


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    only_missing = "--only-missing" in sys.argv
    want = set((sys.argv[sys.argv.index("--verdicts") + 1] if "--verdicts" in sys.argv
                else "INCLUDE,INCLUDE_ADJACENT,UNCERTAIN").split(","))
    refs_path = sys.argv[sys.argv.index("--refs") + 1] if "--refs" in sys.argv else os.path.join(REF, "refs.json")
    refs = load(refs_path)
    os.makedirs(PDFDIR, exist_ok=True)
    logf = open(os.path.join(REF, "_logs", f"pdf_{TODAY}.log"), "a")
    ok = fail = skip = 0
    todo = []
    for r in refs:
        if r.get("verdict") not in want:
            continue
        dst = os.path.join(PDFDIR, f"{r['key']}.pdf")
        if os.path.exists(dst) and os.path.getsize(dst) > 20000:
            r["pdf_file"] = f"{r['key']}.pdf"; skip += 1; continue
        if only_missing and r.get("pdf_tried"):
            continue
        todo.append(r)
    print(f"  대상 {len(todo)} · 기존 {skip}", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for i, f in enumerate(as_completed(futs), 1):
            r, got, n, why = f.result()
            r["pdf_tried"] = True
            if got:
                r["pdf_file"], r["pdf_src"] = f"{r['key']}.pdf", got; ok += 1
                line = f"{i:4d} OK   {r['key']:34s} {n//1024:6d}KB  {got[:80]}"
            else:
                r["pdf_file"] = None; fail += 1
                line = f"{i:4d} --   {r['key']:34s} (후보 {len(why)}개 실패) " + " | ".join(why)[:300]
            print(line, flush=True); logf.write(line + "\n"); logf.flush()
            if i % 25 == 0:
                dump(refs, refs_path)
    dump(refs, refs_path)
    print(f"\n  PDF 성공 {ok} · 실패 {fail} · 기존 {skip}")


if __name__ == "__main__":
    main()
