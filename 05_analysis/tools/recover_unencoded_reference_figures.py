#!/usr/bin/env python3
"""Recover figures whose captions are visible but not text-addressable in PDF.

These page-relative clips complement ``extract_reference_figures.py``.  They are
kept explicit so that the exceptional cases remain reviewable and reproducible.
"""

from pathlib import Path
import csv

import fitz
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "pdf"
OUTPUT = ROOT / "reference_figure_audit" / "manual_recovery"

# paper, figure, one-indexed PDF page, (x0, y0, x1, y1) as page fractions, caption
OVERRIDES = [
    ("choi2026association", "1", 7, (.50, .03, .98, .47), "Decision tree for final systolic blood pressure"),
    ("choi2026association", "2", 8, (.38, .49, .98, .96), "Decision tree for final diastolic blood pressure"),
    ("kim2023improving", "1", 5, (.13, .38, .87, .91), "Flowchart of this study"),
    ("kim2023improving", "2", 8, (.12, .05, .88, .57), "Sensitivity-based multi-sampling algorithm"),
    ("kim2023improving", "3", 10, (.10, .35, .90, .72), "Training-set structure after sensitivity-based multi-sampling"),
    ("shin2023nomogram", "1", 8, (.15, .09, .85, .91), "Nomogram for metabolic syndrome using a naive Bayesian classifier"),
    ("shin2023nomogram", "2", 9, (.15, .08, .85, .84), "ROC curve of the Bayesian nomogram with complex sampling"),
    ("shin2023nomogram", "3", 11, (.15, .08, .85, .83), "Calibration plot of the Bayesian nomogram with complex sampling"),
    ("shin2023nomogram", "4", 12, (.15, .07, .85, .83), "Comparison of logistic-regression and Bayesian nomograms"),
]

UNAVAILABLE = [
    ("bench_critelli2024systematic", "1--2", "captions only in this manuscript version; figures recovered from the 2025 published version"),
    ("lin2026association", "S3", "caption cites a supplementary figure that is not embedded in the available PDF"),
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    docs = {}
    for paper, number, page_number, frac, caption in OVERRIDES:
        doc = docs.setdefault(paper, fitz.open(SOURCE / f"{paper}.pdf"))
        page = doc[page_number - 1]
        w, h = page.rect.width, page.rect.height
        clip = fitz.Rect(frac[0] * w, frac[1] * h, frac[2] * w, frac[3] * h)
        pix = page.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72), clip=clip,
                              colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image = ImageOps.expand(image, border=2, fill="white")
        path = OUTPUT / f"{paper}_fig{number}_p{page_number}.jpg"
        image.save(path, quality=92, optimize=True, progressive=True)
        rows.append([paper, number, page_number, caption, str(path.relative_to(ROOT)), "manual page-relative recovery"])
    for doc in docs.values():
        doc.close()
    with (OUTPUT / "index.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["manuscript", "figure", "pdf_page", "caption_or_status", "image_path", "method"])
        writer.writerows(rows)
        for paper, number, status in UNAVAILABLE:
            writer.writerow([paper, number, "", status, "", "unavailable in local PDF"])
    print(f"recovered {len(rows)} exceptional figures -> {OUTPUT}")


if __name__ == "__main__":
    main()
