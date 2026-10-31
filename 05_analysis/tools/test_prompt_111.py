#!/usr/bin/env python3
"""Prompt 111 (review v48): abstract/conclusion/Principal Findings wording, threshold sentence, Figure 3 caption (G, H),
Discussion subheadings, Figure 3 left-axis bar labels with one bar thickness, n/N at every period point in Figures 5
and 6A, Figure 4A/4C labels, Table S5 learners and design codes."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
MM = (ROOT / "tools/make_main_figures.py").read_text()
BSS = (ROOT / "tools/build_standalone_supplements.py").read_text()


def norm(t):
    return " ".join(t.split())


def fig_text(stem):
    import fitz
    with fitz.open(ROOT / f"figures/submission/{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


class Prompt111(unittest.TestCase):
    def test_text(self):
        en, ko = norm(EN), norm(KO)
        self.assertNotIn("practices that make results reusable", en)
        self.assertIn("code sharing, calibration and validation beyond the development data have become more common, the last two mostly in the newest studies", en)
        self.assertIn("rose in 2025--2026 (14 and 17 of 53), mostly among studies published in 2026", en)
        self.assertNotIn("12 of the 22 each", en)
        self.assertIn("The 154 rankings most often named age (113)", en)
        self.assertIn("three steps for interpreting variable importance from survey data", en)
        self.assertIn("Of the 44 studies reporting a decision threshold, 21 chose it without using the final evaluation data.", en)
        self.assertIn("logistic regression was fitted alongside at least one eligible learner", en)
        self.assertIn("model-native, handled within the learning algorithm", en)
        self.assertIn("\\subsection{Reuse and Comparison of Results}", EN)
        self.assertIn("\\subsection{Stable and Representative Explanations}", EN)
        self.assertNotIn("Three Next Steps", EN)
        self.assertEqual(EN.count("\\subsection{Practices That Became More Common}"), 1)
        for tok in ("뒤의 둘은 대부분 최신 연구에서 늘었다", "53편 중 14편, 17편", "순위 154개 중 나이(113개)", "변수중요도를 해석하기 위한 세 단계",
                    "결정 임계값을 보고한 44편 중 21편", "로지스틱 회귀는 적격 학습기 하나 이상과 함께", "\\subsection{결과의 재사용과 비교}",
                    "\\subsection{안정적이고 대표성 있는 설명}"):
            self.assertIn(tok, ko, tok)
        self.assertNotIn("결과를 다시 쓸 수 있게", ko)

    def test_figure3_bars(self):
        d = MM.split('def figure_analysis(')[1].split('def domain_heatmap(')[0]
        self.assertIn("ax.set_yticklabels([r[0] for r in rows]", d)  # names on the left axis
        self.assertEqual(len(set(re.findall(r"height=\.(\d+), zorder=[12]", d))), 1)  # one bar thickness
        t = fig_text("fig3_analysis_workflow")
        self.assertIn("CI for performance", t); self.assertIn("J. Evaluation steps", t)

    def test_period_labels(self):
        t5 = fig_text("fig6_maturing_practice")  # prompt 112
        for tok in ("1/45", "2/35", "6/59", "8/53", "3/59", "14/53", "10/59", "17/53"):
            self.assertIn(tok, t5, tok)
        t6 = fig_text("fig7_next_steps")  # prompt 112
        for tok in ("2/45", "3/35", "8/59", "12/53"):
            self.assertIn(tok, t6, tok)

    def test_figure4(self):
        self.assertIn('color="white", weight="bold")  # prompt 111', MM)
        self.assertNotIn("axCb", MM)  # prompt 112

    def test_table_s5(self):
        self.assertIn('"KHM229": "DT (CHAID)", "KHM239": "DT (CRT)", "KHM254": "DT (CHAID)"', BSS)
        self.assertIn('["Study (first author, year)", "Task"', BSS)
        self.assertNotIn('"Task-specific checks"],', BSS)
        self.assertIn("Studies added under the final eligibility criterion (n=33)", BSS)
        self.assertNotIn('["Criterion-A additions"', BSS)


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
