#!/usr/bin/env python3
"""Prompt 110 (review v47): Figure 3 ten panels (survey years in Supplementary Figure S2B), Figure 4 at text width with
first-author-and-year labels, Figure 6B legend, Figure 1 wording, Supplementary Figures S2/S3 swapped, S5 three panels,
Table S5 one value per cell, Results/abstract/Discussion text (KNHANES role, Jaccard, topic-mix test, Fig 5 counts)."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
O = json.loads((ROOT / "results/derived/practice_trends_110.json").read_text())


def fig_text(stem):
    import fitz
    return " ".join(fitz.open(ROOT / f"figures/submission/{stem}.pdf")[0].get_text().split())


def norm(t):
    return " ".join(t.split())


class Prompt110(unittest.TestCase):
    def test_json_superset(self):
        o109 = json.loads((ROOT / "results/derived/practice_trends_109.json").read_text())
        for k in o109:
            if k != "diabetes_variable_panel":
                self.assertEqual(O[k], o109[k], k)
        labs = [s["label"] for s in O["diabetes_variable_panel"]["studies"]]
        self.assertEqual(len(set(labs)), 16)
        self.assertEqual(round(O["topic_mix_test"]["monte_carlo_chi_square_p"], 2), 0.52)

    def test_abstract_and_results_text(self):
        en = norm(EN); ko = norm(KO)
        self.assertNotIn("Three next steps", en)
        self.assertIn("Practices that make these explanations stable and representative were in early use", en)
        self.assertNotIn("163 of all 250", en)
        i = en.index("beyond a single KNHANES application"); self.assertIn("163 of the 250 studies", en[i:i + 200])
        self.assertIn("Monte Carlo chi-square p = 0.52", en)
        self.assertIn("median Jaccard index 0.25 and 0.17", en)
        self.assertLess(en.index("median Jaccard index 0.25"), en.index("\\section{Discussion}"))
        self.assertNotIn("0.30 for the same outcome", en)
        self.assertIn("Calibration rose from 3 of 59 in 2023--2024 to 14 of 53", en)
        self.assertIn("validation beyond the development data from 10 of 59 to 17 of 53", en)
        self.assertIn("\\cite{berk2013posi}", en); self.assertIn("\\cite{berk2013posi}", ko)
        self.assertIn("Of the 44 studies reporting a decision threshold, 21 chose it", en)  # prompt 111
        self.assertIn("다음 단계 셋" not in ko and "초기 단계였다" or "", ko)
        self.assertIn("Monte Carlo 카이제곱 p = 0.52", ko)
        self.assertIn("Jaccard 지수 중앙값 0.25 대 0.17", ko)
        for tex in (en, ko):
            self.assertNotIn("Figure~\\ref{fig:analysis}K", tex); self.assertNotIn("fig:analysis-ko}K", tex)

    def test_supplement_order(self):
        for tex in (EN, KO):
            first = list(dict.fromkeys(re.findall(r"\\suppfig\{(\d)\}", tex)))
            self.assertEqual(first, [str(k) for k in range(1, 9)])
        figs = sorted(p.name for p in (ROOT / "manuscript/supplementary/figures").glob("Supplementary_Figure_S0[23]_*.pdf"))
        self.assertEqual(figs, ["Supplementary_Figure_S02_Study_characteristics.pdf",
                                "Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf"])
        bss = (ROOT / "tools/build_standalone_supplements.py").read_text()
        self.assertNotIn("A decision threshold was reported in 44 core studies", bss)
        self.assertIn('"Internal evaluation",\n                      "Beyond development data"', bss)

    def test_figures(self):
        t3 = fig_text("fig3_analysis_workflow")
        self.assertIn("J. Evaluation steps", t3); self.assertNotIn("K. ", t3); self.assertNotIn("Several compared", t3)
        t4 = fig_text("fig4_variable_importance")
        self.assertIn("Importance ranking and SHAP by publication period", t4)  # prompt 112
        self.assertIn("Kim 2026", fig_text("fig5_rankings_named"))  # prompt 112
        self.assertIn("Yes", fig_text("fig7_next_steps"))  # prompt 112
        t1 = fig_text("fig1_prisma")
        self.assertNotIn("one dictionary rule", t1); self.assertNotIn("additional records", t1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
