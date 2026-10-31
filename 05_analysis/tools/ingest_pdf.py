"""references/inbox/ 에 넣어둔 PDF 를 자동으로 인용키에 매칭해 references/pdf/ 로 넣는다.

    python tools/ingest_pdf.py            # 매칭 결과만 보여준다 (dry run)
    python tools/ingest_pdf.py --apply    # 실제로 이동

매칭 순서
  1. 파일명의 DOI 조각      s12877-026-07852-6_reference.pdf → 10.1186/s12877-026-07852-6
  2. 파일명의 Elsevier PII  1-s2.0-S0165178126004488-main.pdf → Crossref PII 조회 → DOI
  3. PDF 첫 2쪽 본문의 DOI
  4. PDF 첫 쪽 제목과 refs.json 제목의 유사도 (0.85 이상)

넣은 뒤에는 아래를 이어서 돌린다.
  python tools/make_paper_md.py          # 전문 md
  python tools/extract_batches.py --tag extN   /  probast 배치 재생성
"""
import sys, os, re, json, glob, difflib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, get, norm_doi, norm_title, MAILTO, q

INBOX = os.path.join(REF, "inbox")
PDFDIR = os.path.join(REF, "pdf")
SETS = ["refs.json", "benchmark_reviews.json"]


def pdf_text(path, pages=2):
    try:
        return subprocess.run(["pdftotext", "-f", "1", "-l", str(pages), path, "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def doi_from_pii(pii):
    try:
        d = get(f"https://api.crossref.org/works?filter=alternative-id:{pii}&rows=1&mailto={MAILTO}")
        it = d["message"].get("items") or []
        return norm_doi(it[0]["DOI"]) if it else None
    except Exception:
        return None


def guess_doi(fn, txt):
    base = os.path.basename(fn)
    # 1. 파일명 안의 DOI 조각 (BMC/Springer 패턴)
    m = re.search(r"(s\d{5}-\d{3}-\d{5}-[\dxX])", base)
    if m: return f"10.1186/{m.group(1)}"
    m = re.search(r"(10\.\d{4,9})[_/]([\w.\-]+)", base)
    if m: return norm_doi(f"{m.group(1)}/{m.group(2)}")
    # 2. Elsevier PII
    m = re.search(r"1-s2\.0-(S\w+?)-", base)
    if m:
        d = doi_from_pii(m.group(1))
        if d: return d
    # 3. 본문 DOI
    m = re.search(r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s,;)\]]+)", txt, re.I)
    if m: return norm_doi(m.group(1).rstrip(".")), 
    return None


def main():
    apply = "--apply" in sys.argv
    os.makedirs(INBOX, exist_ok=True)
    entries = []
    for s in SETS:
        p = os.path.join(REF, s)
        if os.path.exists(p):
            for r in json.load(open(p)):
                entries.append((s, r))
    by_doi = {norm_doi(r.get("doi")): (s, r) for s, r in entries if r.get("doi")}
    files = sorted(glob.glob(os.path.join(INBOX, "*.pdf")))
    if not files:
        print(f"  {os.path.relpath(INBOX, PROJ)}/ 가 비어 있다. PDF 를 넣고 다시 실행한다.")
        return
    print(f"  inbox {len(files)} 건\n")
    plan = []
    for f in files:
        txt = pdf_text(f)
        d = guess_doi(f, txt)
        if isinstance(d, tuple): d = d[0]
        hit = by_doi.get(d) if d else None
        how = "DOI" if hit else ""
        if not hit:  # 제목 유사도
            head = " ".join(txt.split("\n")[:14])
            best, score = None, 0
            for s, r in entries:
                if not r.get("title"): continue
                sc = difflib.SequenceMatcher(None, norm_title(r["title"])[:80], norm_title(head)[:200]).ratio()
                if sc > score: best, score = (s, r), sc
            if score >= 0.55: hit, how = best, f"제목 유사도 {score:.2f}"
        base = os.path.basename(f)
        if hit:
            s, r = hit
            dst = os.path.join(PDFDIR, f"{r['key']}.pdf")
            state = "이미 있음" if os.path.exists(dst) and os.path.getsize(dst) > 20000 else "이동"
            print(f"  ✓ {base[:44]:46s} → {r['key']:26s} [{how}] {state}")
            print(f"      {r.get('verdict')} · {(r.get('title') or '')[:78]}")
            plan.append((f, dst, r, state))
        else:
            print(f"  ✗ {base[:44]:46s} → 매칭 실패 (DOI {d})")
    if apply:
        n = 0
        for f, dst, r, state in plan:
            if state == "이동" or not os.path.exists(dst):
                os.replace(f, dst); n += 1
        # refs 갱신
        keys = {r["key"] for _, _, r, _ in plan}
        for s in SETS:
            p = os.path.join(REF, s)
            if not os.path.exists(p): continue
            R = json.load(open(p)); ch = 0
            for r in R:
                if r["key"] in keys:
                    dst = os.path.join(PDFDIR, f"{r['key']}.pdf")
                    if os.path.exists(dst) and os.path.getsize(dst) > 20000 and not r.get("pdf_file"):
                        r["pdf_file"] = f"{r['key']}.pdf"
                        r["pdf_src"] = "수동 확보 (inbox 경유)"; ch += 1
            if ch: json.dump(R, open(p, "w"), ensure_ascii=False, indent=1); print(f"  {s} 갱신 {ch}건")
        print(f"\n  이동 {n}건. 이어서 실행:\n"
              f"    python tools/make_paper_md.py\n"
              f"    python tools/make_missing_pdf_list.py")
    else:
        print(f"\n  (미리보기) 실제로 넣으려면 --apply")


if __name__ == "__main__":
    main()
