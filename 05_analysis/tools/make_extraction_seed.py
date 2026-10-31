"""refs.json 의 판정 필드로 data/extraction_seed.tsv 를 만든다 — 추출표의 출발점.

    python tools/make_extraction_seed.py

authoritative 추출표는 data/extraction.tsv (손으로 채움). 이 seed 는 언제든 재생성한다.
"""
import csv, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

COLS = ["key", "verdict", "year", "journal", "title", "category", "outcome", "task", "knhanes_role",
        "ml_methods_reported", "knhanes_years", "n_sample", "features", "models", "best_model", "metric",
        "validation", "survey_weight", "imbalance", "interpretability", "code_available", "pdf", "doi", "pmid", "kdca_no"]


def main():
    R = load(os.path.join(REF, "refs.json"))
    rows = [r for r in R if r["verdict"] in ("INCLUDE", "INCLUDE_ADJACENT")]
    rows.sort(key=lambda r: (r["verdict"], -(r.get("year") or 0), r["key"]))
    with open(os.path.join(PROJ, "data", "extraction_seed.tsv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, ml_methods_reported="; ".join(str(m) for m in r.get("ml_methods_reported") or []),
                            pdf=r.get("pdf_file") or "", title=(r.get("title") or "").replace("\t", " ")))
    print(f"  data/extraction_seed.tsv — {len(rows)} 행")


if __name__ == "__main__":
    main()
