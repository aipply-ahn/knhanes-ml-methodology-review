#!/usr/bin/env python3
"""Prompt 103 (review v41): Figure 2 grid A / B|C / D|E / F|G with D and E on one axis; abstract, Discussion subject,
What Matured bridge and Figure 3 method-list polish; 2F first label off the axis; S5E one label per line; S2D predictor set."""
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
FLAT = " ".join(EN.split())
FLATK = " ".join(KO.split())
MM = (ROOT / "tools/make_main_figures.py").read_text()


def words(path, page=0):
    """(text, x0, y0) for each word on a figure page."""
    with fitz.open(path) as d:
        return [(w[4], w[0], w[1]) for w in d[page].get_text("words")]


class Prompt103(unittest.TestCase):
    def test_figure2_grid(self):
        w = words(ROOT / "figures/submission/fig3_analysis_workflow.pdf")
        pos = {}
        for t, x, y in w:
            if len(t) == 2 and t[1] == "." and t[0] in "ABCDEFGHIJK" and t[0] not in pos:  # Prompt 104: A-K grid
                pos[t[0]] = (x, y)
        self.assertEqual(sorted(pos), list("ABCDEFGHIJ"))  # Prompt 104  # Prompt 108  # prompt 110
        rows = [("A", "B"), ("C", "D"), ("E", "F"), ("F", "G"), ("H", "I"), ("I", "J")]  # Prompt 104: D|E and H|I still pair  # Prompt 107  # Prompt 108  # prompt 110
        for l, r in rows:
            self.assertLess(abs(pos[l][1] - pos[r][1]), 30, (l, r))  # same row
            self.assertLess(pos[l][0], pos[r][0])  # left then right
        ys = [pos["A"][1], pos["E"][1], pos["H"][1]]  # Prompt 104  # Prompt 107  # Prompt 108  # prompt 110
        self.assertEqual(ys, sorted(ys))
        d = MM.split("def figure_analysis(")[1].split("# --------------------------------------------------------------------------- Figure 3")[0]
        self.assertIn("ax.set_xticks([0, 96, 192])", d)  # Prompt 104: D, E, H, J, K share lbars' axis
        self.assertGreaterEqual(d.count("fbars(ax"), 5)  # Prompt 104
        self.assertIn("nr_bar(", d)  # Prompt 104: 1/32 label off the axis  # Prompt 107

    def test_sentences(self):
        self.assertIn("Practices that make these explanations stable and representative were in early use: of the 192 studies, 25 checked", FLAT)  # Prompt 106  # Prompt 107  # prompt 110
        self.assertNotIn("already visible", EN)
        self.assertIn("PROBAST+AI rated 375 of the 378 model evaluations here at high risk, mainly in the analysis domain (\\suppfig{8})", FLAT)  # prompt 109  # prompt 113
        self.assertNotIn("Its high-risk ratings", EN)
        self.assertIn("repeated survey cycles could also be used to assess the temporal stability of variable-importance rankings.", FLAT)
        self.assertIn("SHAP was the most common importance method (56 studies; other methods in \\suppfig{6}E)", FLAT)  # Prompt 106  # Prompt 107  # prompt 112
        self.assertNotIn("model-native importance (43)", EN)
        res = EN.split("\\subsection{How Machine Learning Was Used}")[1].split("\\FloatBarrier")[0].split("\\end{figure}")[1]
        paras = [p for p in res.strip().split("\n\n") if p.strip()]
        self.assertTrue(paras[1].startswith("From here on, every figure follows the 192 core studies."))  # Prompt 107: bridge paragraph first  # Prompt 108
        self.assertIn("Figure~\\ref{fig:analysis}A", paras[1]); self.assertIn("Figure~\\ref{fig:analysis}B", paras[1]); self.assertIn("(\\suppfig{1})", paras[0])  # Prompt 104  # Prompt 107  # Prompt 108  # prompt 110
        for tok in ("안정적이고 대표성 있게 하는 실천은 초기 단계였다", "PROBAST+AI는 이 문헌의 모형평가 378개 중 375개를", "시기별 안정성을 평가하는 데에도", "흔한 중요도 방법은 SHAP이었다(56편"):  # Prompt 106  # Prompt 107  # prompt 110  # prompt 112
            self.assertIn(tok, FLATK, tok)
        for tex in (EN, KO):
            figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", tex)]
            self.assertEqual(list(dict.fromkeys(figs)), list(range(1, 9)))

    def test_supplement_panels(self):
        s2 = " ".join(fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf")[0].get_text().split())  # prompt 110
        self.assertIn("Predictor set", s2); self.assertIn("39 (20%)", s2)  # Prompt 106
        s5 = " ".join(fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Figure_S05_Differences_by_publication_period.pdf")[0].get_text().split())
        self.assertIn("Metabolic 5/10 → 15/17", s5)  # Prompt 106


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
