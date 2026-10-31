#!/usr/bin/env python3
"""Prompt 109 (review v46): Table 1 as practices by publication period (no recommendation column), Figure 5 three
panels (code, calibration, validation), ranking stability once in Figure 6A, open before-the-split bar, Figure 4B/4C
order and title, PROBAST+AI and rebuildability sentences out of Results, Supplementary Figures S7 and S8 swapped."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
O = json.loads((ROOT / "results/derived/practice_trends_109.json").read_text())
T = O["table1_by_period"]


def fig_text(stem):
    import fitz
    return " ".join(fitz.open(ROOT / f"figures/submission/{stem}.pdf")[0].get_text().split())


def norm(t):
    return " ".join(t.split())


def section(tex, start, end):
    i = tex.index(start)
    return tex[i:tex.index(end, i)]


class Prompt109(unittest.TestCase):
    def test_table1_values(self):
        self.assertEqual(T["period_n"], [45, 35, 59, 53])
        for k, v in T.items():
            if isinstance(v, list) and k != "period_n":
                self.assertTrue(all(0 <= a <= b for a, b in zip(v, T["period_n"])), k)
        # values already in the manuscript (review v46 section 2)
        exp = {"outcome_rebuildable": 97, "predictor_set_rebuildable": 39, "candidate_predictors_reported": 74,
               "preprocessing_all_within": 17, "preprocessing_any_before": 96, "algorithms_compared": 140,
               "tuning_kept_apart": 84, "auroc": 138, "calibration": 20, "validation_beyond_development": 38,
               "importance_ranking": 154, "shap": 56, "stability": 25, "weights_mentioned": 50, "weights_in_fitting": 9,
               "weights_in_evaluation": 7, "strata_or_psu": 28, "combined_year_weights": 13, "code_shared": 17,
               "final_model_fully_specified": 13}
        self.assertEqual({k: sum(T[k]) for k in exp}, exp)
        for k, first, last in (("predictor_set_rebuildable", 14, 10), ("tuning_kept_apart", 20, 30), ("calibration", 1, 14),
                               ("validation_beyond_development", 6, 17), ("importance_ranking", 29, 49), ("shap", 0, 33),
                               ("stability", 2, 12), ("code_shared", 1, 8), ("final_model_fully_specified", 4, 5)):
            self.assertEqual((T[k][0], T[k][-1]), (first, last), k)
        self.assertEqual(T["importance_ranking"], [29, 25, 51, 49])
        self.assertEqual(T["shap"], [0, 6, 17, 33])

    def test_table1_is_results_table(self):
        for tex, lab in ((EN, "tab:recommended-practice"), (KO, "tab:recommended-practice-ko")):
            tab = section(tex, "\\label{" + lab + "}", "\\end{table}")
            for gone in ("Recommended practice", "권고 실천", "Specify the candidate", "Adopted (of 192)"):
                self.assertNotIn(gone, tab)
            self.assertIn("(n=45)", tab); self.assertIn("(N=192)", tab)
            self.assertEqual(tab.count("\\\\") - 1, 20 + 6)  # 20 practice rows + 6 group rows (+1 header)
        tab = norm(section(EN, "\\label{tab:recommended-practice}", "\\end{table}"))
        self.assertIn("Importance ranking produced & 29 (64.4) & 25 (71.4) & 51 (86.4) & 49 (92.5) & 154 (80.2)", tab)
        self.assertIn("SHAP used & 0 (0.0) & 6 (17.1) & 17 (28.8) & 33 (62.3) & 56 (29.2)", tab)  # prompt 110
        self.assertIn("Calibration reported & 1 (2.2) & 2 (5.7) & 3 (5.1) & 14 (26.4) & 20 (10.4)", tab)
        cap = norm(section(EN, "\\begin{table}", "\\label{tab:recommended-practice}"))
        self.assertIn("Methodological practices reported in the 192 core classification studies, by publication period", cap)
        # first cited in Results "Practices That Became More Common", placed there
        res = section(EN, "\\section{Results}", "\\section{Discussion}")
        self.assertIn("\\label{tab:recommended-practice}", res)
        self.assertIn("all recorded practices by period in Table~\\ref{tab:recommended-practice}", norm(res))  # prompt 110

    def test_results_text(self):
        f = norm(EN)
        for gone in ("PROBAST+AI, whose analysis domain covers such", "would also let an analysis be rebuilt",
                     "Four practices that make results reusable", "Building on these gains", "The same core appeared within one outcome",
                     "organises the explanation requirements", "basis for a consensus guideline", "What Matured and Why It Matters",
                     "Next Steps: Stable and Representative Explanations"):
            self.assertNotIn(gone, f)
        for tok in ("against 2 and 5 of the 31 published in 2025; Figure~\\ref{fig:maturing}B--C).",  # prompt 110  # prompt 112
                    "Checks of ranking stability rose in every period, from 2 of 45 through 2019 to 12 of 53 in 2025--2026",
                    "while the lists ranged from 1 to 31 variables (Figure~\\ref{fig:named}B)",  # prompt 112
                    "\\subsection{Ranking Stability, Survey Design and Preprocessing}", "\\subsection{Practices That Became More Common}",
                    "Code sharing, calibration and validation beyond the development data make results easier to reuse and",  # prompt 113
                    "candidates for survey-specific items in future reporting guidance",
                    "Ranking stability, survey design and preprocessing timing in the 192 core studies."):
            self.assertIn(tok, f)
        res = section(EN, "\\section{Results}", "\\section{Discussion}")
        self.assertNotIn("PROBAST", res)
        fk = norm(KO)
        for tok in ("\\subsection{순위 안정성, 조사설계, 전처리}", "1개에서 31개까지였다", "코드 공개, 보정, 개발자료 밖 검증은 결과를 다시 쓰고 비교하기 쉽게 만든다."):  # prompt 112
            self.assertIn(tok, fk)
        self.assertNotIn("PROBAST", section(KO, "\\section{결과}", "\\section{고찰}"))

    def test_supplementary_order(self):
        # S7 (agreement) is now cited before S8 (PROBAST+AI)
        f = norm(EN)
        self.assertLess(f.index("\\suppfig{7}A"), f.index("\\suppfig{8}"))
        figs = ROOT / "manuscript/supplementary/figures"
        self.assertTrue((figs / "Supplementary_Figure_S07_Agreement_between_rankings.pdf").exists())
        self.assertTrue((figs / "Supplementary_Figure_S08_Reporting_completeness_and_PROBAST_AI.pdf").exists())
        self.assertFalse((figs / "Supplementary_Figure_S07_Reporting_completeness_and_PROBAST_AI.pdf").exists())
        self.assertFalse((figs / "Supplementary_Figure_S08_Agreement_between_rankings.pdf").exists())

    def test_figures(self):
        t5 = fig_text("fig6_maturing_practice")  # prompt 112
        for tok in ("A. Analysis code shared", "B. Calibration reported", "C. Validation beyond the"):
            self.assertIn(tok, t5)
        for gone in ("Ranking stability", "2026 alone", "D."):
            self.assertNotIn(gone, t5)
        t6 = fig_text("fig7_next_steps")  # prompt 112
        self.assertIn("A. Ranking stability checked, by period and approach (N=192)", t6)
        self.assertIn("2/45", t6); self.assertIn("12/53", t6)
        for gone in ("Not checked 129", "No ranking", "D. When"):
            self.assertNotIn(gone, t6)
        t4 = fig_text("fig4_variable_importance")
        self.assertIn("B. Diabetes or prediabetes, study by study (N=16 of the 154)", fig_text("fig5_rankings_named"))  # prompt 112
        self.assertNotIn("The same core", t4)
        src = (ROOT / "tools/make_main_figures.py").read_text()
        self.assertIn('"BEFORE": "white"', src)
        self.assertIn('topics = [t for t in o["core_topics"] if t not in ("KIDNEY_UROLOGIC", "OTHER_OR_CROSS_CUTTING")][:7]', (ROOT / "tools/practice_trends.py").read_text())  # prompt 112


if __name__ == "__main__":
    unittest.main()
