"""references/pdf/<key>.pdf → references/md/<key>.md  (PyMuPDF 텍스트 추출, 페이지 구분 포함)
PDF 가 없는 포함 논문은 초록만으로 md 를 만든다 (헤더에 `full_text: false`).

    python tools/make_paper_md.py [--force]
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *
import fitz

MD = os.path.join(REF, "md")


def header(r, full):
    au = r.get("authors") or ""
    return (f"---\nkey: {r['key']}\ntitle: \"{(r.get('title') or '').replace(chr(34), chr(39))}\"\nauthors: \"{au[:300].replace(chr(34), chr(39))}\"\n"
            f"journal: \"{(r.get('journal') or '').replace(chr(34), chr(39))}\"\nyear: {r.get('year')}\ndoi: {r.get('doi')}\npmid: {r.get('pmid')}\n"
            f"verdict: {r['verdict']}\ncategory: {r.get('category')}\nfull_text: {str(full).lower()}\n---\n\n"
            f"# {r.get('title')}\n\n**{au[:300]}** · {r.get('journal')} · {r.get('year')}\n\n")


def main():
    force = "--force" in sys.argv
    os.makedirs(MD, exist_ok=True)
    R = load(os.path.join(REF, "refs.json"))
    n_full = n_abs = 0
    for r in R:
        if r["verdict"] not in ("INCLUDE", "INCLUDE_ADJACENT", "UNCERTAIN"):
            continue
        dst = os.path.join(MD, f"{r['key']}.md")
        if os.path.exists(dst) and not force:
            # 기존 md 가 초록만인데 PDF 가 새로 생겼으면 다시 만든다
            head = open(dst, encoding="utf-8").read(600)
            pdf = os.path.join(REF, "pdf", r.get("pdf_file") or "")
            if not ("full_text: false" in head and r.get("pdf_file") and os.path.exists(pdf)):
                continue
        ab = re.sub(r"<[^>]+>", " ", r.get("abstract") or ""); ab = re.sub(r"\s+", " ", ab).strip()
        body = f"## Abstract (from index)\n\n{ab or '_초록 없음_'}\n\n"
        full = False
        if r.get("pdf_file") and os.path.exists(os.path.join(REF, "pdf", r["pdf_file"])):
            try:
                doc = fitz.open(os.path.join(REF, "pdf", r["pdf_file"]))
                pages = []
                for i, pg in enumerate(doc, 1):
                    t = pg.get_text("text")
                    t = re.sub(r"[ \t]+\n", "\n", t)
                    pages.append(f"\n\n<!-- page {i} -->\n\n{t}")
                txt = "".join(pages)
                if len(txt.strip()) > 500:
                    body += "## Full text (PyMuPDF extraction)\n" + txt
                    full = True
            except Exception as e:
                body += f"\n_PDF 추출 실패: {e}_\n"
        open(dst, "w", encoding="utf-8").write(header(r, full) + body)
        n_full += full; n_abs += (not full)
    print(f"  md 생성 — 전문 {n_full} · 초록만 {n_abs} → references/md/")


if __name__ == "__main__":
    main()
