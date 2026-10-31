#!/usr/bin/env python3
"""Prompt 092: shorter Methods, supplement renumbered with verification tables, supplement appended, v30 details."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_prompt_087 import abstract_words  # noqa: E402
from test_prompt_088 import body  # noqa: E402

EN = body((ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8"))
KO = body((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8"))


def words(tex):
    tex = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", tex, flags=re.S)
    tex = re.sub(r"\\(cite|supptab|suppfig|ref|label)\{[^}]*\}", "X", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?", "", tex)
    return len(re.sub(r"[{}~]", " ", tex).split())


class Prompt092(unittest.TestCase):
    def test_methods_shorter_than_results(self):
        methods = EN[EN.index("\\section{Methods}"):EN.index("\\section{Results}")]
        results = EN[EN.index("\\section{Results}"):EN.index("\\section{Discussion}")]
        # Prompt 093 moved Table 1 (rule table) into Methods and set per-section targets (Methods ~1,250,
        # Results ~1,400 words; review v31 section 4); both are checked on prose only, and test_prompt_093 holds the caps.
        prose = lambda t: words(re.sub(r"\\begin\{table\}.*?\\end\{table\}", "", t, flags=re.S))
        self.assertLessEqual(prose(methods), 1250 * 1.05 + 40)  # prompt 115: AI-use disclosure in Verification and Synthesis (required)
        self.assertLessEqual(prose(results), 1400 * 1.05 + 120)  # prompt 112
        # Prompt 094 (review v32): claim coding and the evidence-requirement paragraph were removed from Methods.
        for head in ("Protocol and Reporting", "Search, Eligibility, and Study Selection", "Study Groups, Tasks, and Outputs",
                     "Practices Extracted", "Supporting Assessments", "Verification and Synthesis"):
            self.assertIn("\\subsection{" + head + "}", methods)
        self.assertNotIn("\\paragraph{Evidence required for each claim.}", methods)

    def test_supplement_citation_order(self):
        for tex in (EN, KO):
            b = tex[:tex.find("\\section*{Supplementary materials}") if "Supplementary materials" in tex else tex.find("\\section*{보충자료}")]
            seq = []
            for m in re.finditer(r"\\supp(tab|fig)\{(\d+)\}", b):
                k = ("T" if m.group(1) == "tab" else "F") + m.group(2)
                if k not in seq:
                    seq.append(k)
            tables = [int(k[1:]) for k in seq if k[0] == "T"]
            figures = [int(k[1:]) for k in seq if k[0] == "F"]
            self.assertEqual(tables, sorted(tables))
            self.assertEqual(tables[-2:], [7, 8])  # prompt 093: protocol and results are Tables S7 and S8
            self.assertEqual(figures, sorted(figures))

    def test_supplement_items_one_per_page(self):
        with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
            toc = [t[1] for t in d.get_toc()]
            starts = [(i, re.match(r"\s*Supplementary (Table|Figure) S(\d+)\.", p.get_text()[:200])) for i, p in enumerate(d)]
        names = [t.split(".")[0] for t in toc]
        # Prompt 093: Table S5 is the workbook (Additional file 2); eight figures; protocol/results are S7/S8.
        # Prompt 094 (review v32): six supplementary figures (panels moved into main Figures 2 and 6).
        expected = [f"Supplementary Table S{n}" for n in range(1, 6)] + [f"Supplementary Figure S{n}" for n in range(1, 9)] + ["Supplementary Table S6", "Supplementary Table S7", "Supplementary Table S8"]  # Prompt 097 (review v35): citation order; workbook is Additional Data 1
        self.assertEqual(names, expected)
        # Prompt 096 (review v34): Table S9 (study-level summary) follows the two verification tables.
        self.assertIn("Verification protocol", toc[-3]); self.assertIn("Recorded verification results", toc[-2])
        self.assertIn("included studies", toc[-1])  # Prompt 098: Table S8 "Characteristics of the 220 included studies"
        figure_pages = [i for i, m in starts if m and m.group(1) == "Figure"]
        self.assertEqual(len(figure_pages), 8)  # Prompt 099: eight supplementary figures
        self.assertEqual(len(set(figure_pages)), 8)  # Prompt 099: eight supplementary figures

    def test_supplement_appended_to_manuscripts(self):
        for name, sections in (("bmc_main.pdf", "Supplementary material"), ("bmc_main_ko.pdf", "보충자료 (영문)")):
            with fitz.open(ROOT / "manuscript" / name) as whole, fitz.open(ROOT / "build/submission" / name) as main, \
                    fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as supp:
                self.assertEqual(len(whole), len(main) + len(supp))
                self.assertIn(sections, [t[1] for t in whole.get_toc()])
                self.assertIn("Supplementary Table S1.", whole[len(main) + 1].get_text())

    def test_verification_results_table(self):
        with fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S07_Verification_results.pdf") as d:  # renumbered by prompts 093 and 097
            text = " ".join(" ".join(p.get_text() for p in d).split())
        for token in ("413 values changed", "236 confirmed", "140 flags",  # prompt 113
                       "not recorded", "2 confirmed ineligible", "103 values recoded"):
            self.assertIn(token, text)

    def test_sentence_items(self):
        abstract = EN[EN.index("\\abstract{"):EN.index("\\keywords")]
        # Prompt 094 (review v32): the v32 abstract states that 164 health-focused studies classified a current health state.
        self.assertIn("190", abstract)  # Prompt 106
        self.assertNotIn("external or later-period validation", abstract)
        _, n = abstract_words(ROOT / "build/submission/bmc_main.pdf")
        self.assertLessEqual(n, 350)
        # Prompt 094 (review v32): the claim-evidence sentences were removed; the rebuild and comparison facts remain.
        self.assertIn("15 (8%)", " ".join(fitz.open(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf")[0].get_text().split()))  # Prompt 102: rebuild count in Figure S2D  # Prompt 106  # prompt 110
        self.assertIn("Of the ten comparisons of existing methods, one reported uncertainty or a paired comparison", " ".join(" ".join(pg.get_text() for pg in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))  # Prompt 100: Figure S6 caption
        concl = EN[EN.index("\\section{Conclusions}"):EN.index("\\section*{Abbreviations}")]
        self.assertNotIn("38 of 165", concl)
        self.assertIn("whether their rankings are stable", " ".join(concl.split()))  # Prompt 096 (review v34): message-revision Conclusions
        self.assertNotIn("No trend model was fitted", EN[EN.index("\\section{Results}"):])
        self.assertNotIn("algorithmically", EN)
        self.assertNotIn("\\paragraph{Study selection.}", EN)
        self.assertEqual(len(re.findall(r"figs/fig7_next_steps", EN)), 1)  # Prompt 100: last main figure is Figure 5; Figure 6 since prompt 107  # Prompt 107  # prompt 112

    def test_figures(self):
        # Prompt 093: claim-evidence figure is Figure 5; the claims panel moved into Figure 2.
        with fitz.open(ROOT / "figures/submission/fig5_claim_evidence.pdf") as d:
            f8 = d[0].get_text()
        self.assertNotIn("C. Could", f8)
        with fitz.open(ROOT / "figures/submission/fig1_prisma.pdf") as d:
            self.assertIn("not retrieved,", d[0].get_text())


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
