"""Full-text eligibility input: one line per report selected for full text that has a retrieved PDF, with the text of
each PDF page (pdftotext; every page with fewer than 300 characters, e.g. scanned pages or figure-only pages, is also
read with Tesseract OCR, kor+eng, 300 dpi, and the OCR text appended with a marker).
Output: results/oct_search/eligibility/eligibility_input.jsonl (private: contains full texts) and
eligibility_input_public.jsonl (identifiers, PDF and text SHA256, page count and text method; no text).
Usage: eligibility_input.py [--ids FILE]   (default: every full-text target with a retrieved PDF)"""
import argparse, csv, hashlib, json, os, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results/oct_search/eligibility")
OCR = "<work_dir_outside_project>/ocr_env/bin/tesseract"
LOW = 300  # characters
sha = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def ocr_page(pdf, k):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-f", str(k), "-l", str(k), "-r", "300", "-png", pdf, os.path.join(d, "p")], check=True)
        f = sorted(os.listdir(d))[0]
        return subprocess.run([OCR, os.path.join(d, f), "-", "-l", "kor+eng"], capture_output=True, text=True, check=True).stdout


def pages_text(pdf):
    """Text of each PDF page: pdftotext; a page with fewer than LOW characters (image-only pages such as flow charts,
    decision trees or scanned pages) is also read by OCR and the OCR text is appended, marked as such."""
    t = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = t.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    methods = []
    for k, p in enumerate(pages, 1):
        if len(p.strip()) < LOW:
            o = ocr_page(pdf, k).strip()
            if o:
                pages[k - 1] = (p.rstrip() + "\n" if p.strip() else "") + "[OCR of the page image]\n" + o
                methods.append("pdftotext+ocr" if p.strip() else "ocr")
                continue
        methods.append("pdftotext")
    return pages, methods


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ids"); a = ap.parse_args()
    targets = set(open(a.ids or os.path.join(ROOT, "results/oct_search/screening/run/fulltext_targets.txt")).read().split())
    L = [r for r in csv.DictReader(open(os.path.join(ROOT, "results/oct_search/candidates_ledger.tsv")), delimiter="\t")
         if r["record_id"] in targets and r["fulltext_status"] != "NOT_RETRIEVED"]
    os.makedirs(OUT, exist_ok=True)
    priv, publ = os.path.join(OUT, "eligibility_input.jsonl"), os.path.join(OUT, "eligibility_input_public.jsonl")
    with open(priv + ".tmp", "w") as f, open(publ + ".tmp", "w") as g:  # written to temporary files, then replaced
        for r in sorted(L, key=lambda r: r["record_id"]):
            pdf = os.path.join(ROOT, r["fulltext_path"]); pages, methods = pages_text(pdf)
            method = "pdftotext" if set(methods) == {"pdftotext"} else ("tesseract OCR (kor+eng, 300 dpi)" if set(methods) == {"ocr"} else "pdftotext; OCR (kor+eng, 300 dpi) for pages with < %d characters" % LOW)
            row = dict(record_id=r["record_id"], title=r["title"], doi=r["doi"] or None, pmid=r["pmid"] or None, kci_id=r["kci_id"] or None,
                       pdf_sha256=sha(open(pdf, "rb").read()), n_pages=len(pages), text_method=method, page_methods=methods, pages=pages,
                       text_sha256=sha("\f".join(pages)))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            pub = {k: v for k, v in row.items() if k != "pages"}; pub["fulltext_source"] = r["fulltext_source"]
            g.write(json.dumps(pub, ensure_ascii=False) + "\n")
            print(r["record_id"], len(pages), method, flush=True)
    os.replace(publ + ".tmp", publ); os.replace(priv + ".tmp", priv)  # public first, private input last


if __name__ == "__main__":
    main()
