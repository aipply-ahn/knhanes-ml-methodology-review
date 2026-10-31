#!/usr/bin/env python3
"""Prompt 102 (review v40): remaining bends straightened and small figure fixes.
PROBAST+AI sentence in Next Steps after preprocessing; method-focused sentence after Figure 2B; supplement pointers on
the panel sentences with the supplementary figures renumbered in citation order (S1 methods testbed, S2 outcome and
predictor, S3 characteristics, S4 participants, S5 period, S6 algorithms, S7 reporting and PROBAST+AI, S8 agreement);
What Matured without the rebuttal sentences (moved to Limitations); Three Next Steps section; S8A result sentence and
"varied with the health topic"; Figure 2A hatched 2026, 2B one-line labels, 2D component labels, 2E ticks, 3C row totals
with one dot size, 5A denominator in the title."""
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
FLAT = " ".join(EN.split())
FLATK = " ".join(KO.split())
RES = " ".join(EN.split("\\section{Results}")[1].split("\\section{Discussion}")[0].split())
DIS = EN.split("\\section{Discussion}")[1].split("\\section{Conclusions}")[0]
MM = (ROOT / "tools/make_main_figures.py").read_text()
SUPDIR = ROOT / "manuscript/supplementary/pdf"


def fig(stem):
    with fitz.open(ROOT / f"figures/submission/{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


def supp_text():
    with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
        return " ".join(" ".join(p.get_text() for p in d).split())


class Prompt102(unittest.TestCase):
    def test_probast_position(self):
        i = DIS.index("PROBAST+AI rated 375 of the 378 model evaluations here at high risk")  # Prompt 106  # prompt 109  # prompt 113
        self.assertNotIn("PROBAST", RES)  # prompt 109
        self.assertTrue(RES.rstrip().endswith("\\FloatBarrier") or "(69 and 50 studies;" in RES)  # Prompt 106  # prompt 109
        self.assertNotIn("Reporting the outcome, the predictor set", RES)  # prompt 109
        self.assertNotIn("Appraised with PROBAST+AI", EN)
        self.assertNotIn("분석 영역이 이런 단계를 다루는 PROBAST+AI는", KO)  # prompt 109

    def test_method_sentence_and_pointers(self):
        b = RES.index("(Figure~\\ref{fig:ml-use}B). Of the 36 method-focused studies")  # Prompt 107
        self.assertLess(b, RES.index("(Figure~\\ref{fig:analysis}A)"))  # Prompt 108
        for tok in ("(Figure~\\ref{fig:analysis}C; \\suppfig{3})", "primary dataset in 163 of the 250 studies (\\suppfig{2}A)", "Figure~\\ref{fig:analysis}E; \\suppfig{4})",  # Prompt 104: core sample in 2F  # Prompt 108  # Prompt 108  # prompt 110  # prompt 110
                    "other differences by period in \\suppfig{5}", "(Figure~\\ref{fig:analysis}J; \\suppfig{6})"):  # Prompt 104: evaluation is 2K  # Prompt 107  # Prompt 108  # prompt 110
            self.assertIn(tok, RES, tok)
        self.assertNotIn("The analyses and survey data of all 220 studies are summarised in", EN)
        for tex in (EN, KO):
            figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", tex.split("\\section*{Declarations}")[0])]
            self.assertEqual(list(dict.fromkeys(figs)), list(range(1, 9)))

    def test_supplement_renumbered(self):
        names = sorted(p.name for p in SUPDIR.glob("Supplementary_Figure_S*.pdf"))
        self.assertEqual(names, ["Supplementary_Figure_S01_Methods_testbed.pdf", "Supplementary_Figure_S02_Study_characteristics.pdf",  # prompt 110
                                 "Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf", "Supplementary_Figure_S04_Participants_and_sample_size.pdf",  # prompt 110
                                 "Supplementary_Figure_S05_Differences_by_publication_period.pdf", "Supplementary_Figure_S06_Algorithms_tuning_evaluation_and_measures.pdf",
                                 "Supplementary_Figure_S07_Agreement_between_rankings.pdf", "Supplementary_Figure_S08_Reporting_completeness_and_PROBAST_AI.pdf"])  # prompt 109
        t = supp_text()
        order = [t.index(f"Supplementary Figure S{n}. {ttl}") for n, ttl in (
            (1, "KNHANES as a methods testbed"), (2, "Role of KNHANES"), (3, "Outcome and predictor construction"),  # Prompt 107  # prompt 110
            (4, "Participants and sample size"), (5, "Differences by publication period"), (6, "Algorithms, tuning"),
            (7, "Agreement between pairs of rankings"), (8, "Reporting completeness and PROBAST+AI"))]  # prompt 109
        self.assertEqual(order, sorted(order))
        self.assertIn("not whether it can be rebuilt (Supplementary Figure S3B)", t)  # Prompt 104: rebuildability is S2B  # prompt 110
        self.assertIn("Discussion; Supplementary Figure S8; Additional Data 1", t)  # prompt 109
        self.assertIn("Discussion: Stable and Representative Explanations; Table 1; Conclusions", t)  # prompt 111
        self.assertIn("≤19", " ".join(fitz.open(SUPDIR / "Supplementary_Figure_S05_Differences_by_publication_period.pdf")[0].get_text().split()))

    def test_discussion(self):
        dis = re.findall(r"\\subsection\{([^}]*)\}", DIS)
        self.assertEqual(dis[:5], ["Principal Findings", "Explanation as the Main Product", "Reuse and Comparison of Results",  # prompt 109  # prompt 111
                                   "Stable and Representative Explanations", "Prediction Standards and Explanation Standards"])  # prompt 111
        mat = DIS.split("\\subsection{Reuse and Comparison of Results}")[1].split("\\subsection{")[0]  # prompt 109  # prompt 111
        for gone in ("two patterns", "12 journals", "TRIPOD+AI"):
            self.assertNotIn(gone, mat, gone)
        lim = " ".join(DIS.split("\\subsection{Strengths and Limitations}")[1].split())
        self.assertIn("The 12 validations in 2026 appeared in 11 journals, and no author name recurred in more than two of them", lim)  # Prompt 106
        three = " ".join(DIS.split("\\subsection{Stable and Representative Explanations}")[1].split("\\subsection{")[0].split())  # prompt 111
        self.assertIn("their stability should therefore be assessed before substantive conclusions are drawn", three)
        self.assertIn("the 23 studies that validated a model on a later survey period already", " ".join(three.split()))  # Prompt 106  # prompt 112
        self.assertIn("The second step, representativeness", three)
        self.assertIn("The third step is to keep missing-value handling", three)
        self.assertNotIn("not yet followed", three)
        self.assertEqual(three.lower().count("pooled"), 1)  # pooled cycles only in the stability paragraph  # prompt 112
        self.assertIn("candidates for survey-specific items in future reporting guidance", " ".join(DIS.split()))  # prompt 109
        self.assertIn("\\subsection{안정적이고 대표성 있는 설명}", KO)  # prompt 111

    def test_jaccard_and_topic_wording(self):
        self.assertIn("median Jaccard index 0.25 and 0.17; \\suppfig{7}A", FLAT)  # prompt 109  # prompt 110
        self.assertEqual(FLAT.count("differed by outcome"), 2); self.assertEqual(FLAT.count("otherwise followed the outcome"), 1)  # Prompt 106  # prompt 110  # prompt 112
        self.assertNotIn("followed the health topic", EN)
        self.assertNotIn("건강주제를 따랐다", KO)
        self.assertIn("Jaccard 지수 중앙값 0.25 대 0.17", FLATK)  # prompt 110

    def test_figures(self):
        # Author request 2026-09-28: panel B shows one bar per task under group headings with n=.
        t2 = fig("fig2_literature_map")
        for tok in ("to Sep", "Health analysis (classification) (192) Classify a health state 192", "Method-focused (36) Develop or improve a method 26", "Health analysis (other ML) (22)",  # Prompt 104: one-column labels  # Prompt 106
                    "Continuous or ordered value 14", "Other analyses 8", "Compare existing methods 10"):  # Prompt 104  # Prompt 107
            self.assertIn(tok, t2, tok)
        self.assertNotIn("Laboratory value", t2)
        e = MM.split("def figure2(")[1].split("# --------------------------------------------------------------------------- Figure 3")[0]  # Prompt 104
        self.assertIn("ax.set_xticks([0, 96, 192])", MM)  # Prompt 104: shared axis in lbars  # Prompt 107
        t3 = fig("fig4_variable_importance")
        self.assertIn("First author and year", fig("fig5_rankings_named")); self.assertNotIn("Named 1st-3rd", t3)  # Prompt 107  # prompt 112
        t5 = fig("fig7_next_steps")  # prompt 112
        self.assertIn("Approach not described", t5)  # Prompt 107
        self.assertNotIn("(n=25 of 129)", t5)


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
