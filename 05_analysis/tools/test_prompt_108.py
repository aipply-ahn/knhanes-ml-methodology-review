#!/usr/bin/env python3
"""Prompt 108 (review v45): one denominator per figure (Fig 2 = 250, Fig 3 = 192 with A-K, Fig 4 192 -> 154,
Fig 5 = 192 in every title, Fig 6 = 192 including 6A), and the three caption reconciliations from the records."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
O = json.loads((ROOT / "results/derived/practice_trends_108.json").read_text())


def fig_text(stem):
    import fitz
    return " ".join(fitz.open(ROOT / f"figures/submission/{stem}.pdf")[0].get_text().split())


def norm(t):
    return " ".join(t.split())


class Prompt108(unittest.TestCase):
    def test_values(self):
        self.assertEqual(O["stability_192"], {"checked": 25, "not_checked": 129, "no_ranking": 38})
        self.assertEqual(O["combined_weights_na_by_scope"], {"ONE_YEAR": 41, "MULTI_SAME": 4, "MULTI_CROSS": 1, "UNC": 0})
        self.assertEqual(O["survey_years_vs_scope"]["years_not_named_scope_known"], {"MULTI_CROSS": 1})
        self.assertEqual(O["missing_step_not_applied"], {"complete_case": 101, "other_methods": 3, "complete_case_with_timing": 12})

    def test_figure2_only_250(self):
        t = fig_text("fig2_literature_map")
        for tok in ("A. Studies per publication year (N=250)", "B. Task (N=250)"):
            self.assertIn(tok, t)
        for gone in ("C. Health topic", "Survey years analysed", "Years pooled"):
            self.assertNotIn(gone, t)

    def test_figure3_eleven_panels(self):
        t = fig_text("fig3_analysis_workflow")
        for tok in ("A. Health topic", "B. Survey years", "C. Outcome timing", "D. Predictor data", "E. Final analytic sample",  # prompt 111  # prompt 112
                    "F. Candidate predictors", "G. Missing values", "H. Algorithms fitted",  # prompt 111
                    "I. Model the authors", "J. Evaluation steps", "not reported 118"):  # prompt 111
            self.assertIn(tok, t)
        self.assertNotIn("1/45 → 42/53", t)  # author request: no family singled out in 3I
        af = O["algorithms_fitted_192"]
        self.assertGreater(af["random_forest"], af["logistic_regression"])  # I is in count order: random forest first
        self.assertIn('order = sorted(names, key=lambda k: -af[k]) + ["other"]', (ROOT / "tools/make_main_figures.py").read_text())

    def test_figure3_full_width(self):
        # Author request: Figure 3 spans the text width on the page (EN and KO).
        import fitz
        for pdf, needle in (("build/submission/bmc_main.pdf", "J. Evaluation steps"), ("build/submission/bmc_main_ko.pdf", "J. 보고한 평가 단계")):  # prompt 111
            d = fitz.open(ROOT / pdf)
            pg = next(p for p in d if needle in p.get_text() and len(p.get_drawings()) > 200)  # the 11-panel page
            tb = [b for b in pg.get_text("blocks") if len(b[4].strip()) > 40 and not b[4].replace("\n", "").strip().isdigit()]  # prompt 111
            left, right = min(b[0] for b in tb), max(b[2] for b in tb)
            dr = [x["rect"] for x in pg.get_drawings()]
            self.assertGreater(max(r.x1 for r in dr) - min(r.x0 for r in dr), 0.93 * (right - left), pdf)

    def test_figure4_5_6_titles(self):
        t4 = fig_text("fig4_variable_importance")
        self.assertIn("(N=154; %)", fig_text("fig5_rankings_named")); self.assertIn("(N=16 of the 154", fig_text("fig5_rankings_named"))  # prompt 112
        t5 = fig_text("fig6_maturing_practice")  # prompt 112
        self.assertNotIn("Rose in", t5)
        self.assertEqual(len(re.findall(r"\(N=192\)", t5)), 3)  # prompt 109
        t6 = fig_text("fig7_next_steps")  # prompt 112
        self.assertIn("A. Ranking stability checked, by period and approach (N=192)", t6)  # prompt 109
        for tok in ("2/45", "12/53", "Approach not described"):  # prompt 109
            self.assertIn(tok, t6)

    def test_text(self):
        en = norm(EN); ko = norm(KO)
        self.assertIn("From here on, every figure follows the 192 core studies. They most often addressed", en)
        self.assertIn("25 of the 192 studies checked their ranking in all (the 38 without a ranking were not applicable)", en)  # prompt 109
        self.assertIn("the 41 studies using one survey year and 5 that analysed their survey years separately", en)
        self.assertIn("(101 of the 113 complete-case studies; with 3 other studies, 104 not applied)", en)
        self.assertIn("Six studies did not name their survey years.", " ".join((R_SUPP := __import__("pathlib").Path(ROOT / "tools/build_standalone_supplements.py").read_text()).split()))  # prompt 111
        self.assertIn("Code sharing, calibration and validation beyond the development data make results easier to reuse and", en)  # prompt 109  # prompt 113
        self.assertNotIn("the 46 studies using one survey year", en)
        self.assertIsNone(re.search(r"\\ref\{fig:ml-use\}[C-E]", EN))
        self.assertIn("started from a median of 22.5 predictors; 118 did not report it (Figure~\\ref{fig:analysis}F)", en)  # prompt 111
        self.assertIn("전체로는 192편 중 25편이 순위를 점검했다(순위가 없는 38편은 비해당)", ko)  # prompt 109
        self.assertIn("한 해의 조사만 쓴 41편과 조사연도를 따로 분석한 5편", ko)
        self.assertIn("코드 공개, 보정, 개발자료 밖 검증은 결과를 다시 쓰고 비교하기 쉽게 만든다.", ko)  # prompt 109
        self.assertIsNone(re.search(r"\\ref\{fig:ml-use-ko\}[C-E]", KO))

    def test_pdf_and_logs(self):
        for n in ("bmc_main", "bmc_main_ko"):
            log = (ROOT / f"build/submission/{n}.log").read_text(errors="ignore")
            self.assertNotIn("Float too large", log, n)
            self.assertNotIn("Missing character", log, n)
        raw = subprocess.run(["pdftotext", str(ROOT / "build/submission/bmc_main.pdf"), "-"], capture_output=True, text=True).stdout
        t = norm(raw).replace("\u2011", "-")
        self.assertIn("How the 192 core studies were analysed", t)  # prompt 112
        self.assertNotIn("Rose in every period", t)


if __name__ == "__main__":
    unittest.main()
