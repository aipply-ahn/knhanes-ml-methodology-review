#!/usr/bin/env python3
"""Append the combined supplement after the reference list of the main manuscripts (prompt 092).

The locked LaTeX preamble cannot load pdfpages, so the built manuscript PDF and the combined
supplement PDF are joined after compilation. Each supplementary table and figure already starts on
its own page in bmc_supplementary.pdf. Bookmarks for the supplement are added under one parent entry.
Usage: python tools/append_supplement.py [en|ko ...]
"""
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/submission"
SUPP = ROOT / "manuscript/bmc_supplementary.pdf"
TARGETS = {"en": ("bmc_main.pdf", "Supplementary material"), "ko": ("bmc_main_ko.pdf", "보충자료 (영문)")}


def append(lang):
    name, label = TARGETS[lang]
    main = fitz.open(BUILD / name)
    main_pages = len(main)
    supp = fitz.open(SUPP)
    toc = main.get_toc(simple=True)
    main.insert_pdf(supp)
    toc.append([1, label, main_pages + 1])
    for level, title, page in supp.get_toc(simple=True):
        toc.append([level + 1, title, page + main_pages])
    main.set_toc(toc)
    out = ROOT / "manuscript" / name
    main.save(out, garbage=3, deflate=True)
    print(f"{name}: {main_pages} manuscript pages + {len(supp)} supplementary pages")


if __name__ == "__main__":
    for lang in sys.argv[1:] or ["en", "ko"]:
        append(lang)
