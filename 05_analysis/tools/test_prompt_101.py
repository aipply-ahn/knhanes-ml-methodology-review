#!/usr/bin/env python3
"""Prompt 101 (review v39): remaining back-and-forth removed and five subfigures refined.
Figure 2B task labels, 2D source only (form in S4C), 2E on the 165 core studies (navy, all components, note in the
panel), 2G analysis order; Figure 3 opens from 2G, domains follow the health topic, 3C is the same core within one
outcome (rows in the domain order of 3B); Figure 4B states its denominator; Figure 5A shows only described approaches;
PROBAST+AI result stated in Results; Discussion follows the Results order; forward next-steps sentences."""
import json
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
PT = json.loads((ROOT / "results/derived/practice_trends_101.json").read_text())
MM = (ROOT / "tools/make_main_figures.py").read_text()


def fig(stem):
    with fitz.open(ROOT / f"figures/submission/{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


class Prompt101(unittest.TestCase):
    def test_values(self):
        self.assertEqual(PT["survey_components_165"], {"HEALTH_INTERVIEW": 159, "EXAMINATION": 144, "LABORATORY": 99, "ORAL_HEALTH": 12, "NUTRITION": 48})
        self.assertEqual(PT["core_year_scope"]["MULTI_CROSS"], 93)
        for n in ("094", "095", "096", "097", "098", "099", "100"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_figure2(self):
        t = fig("fig3_analysis_workflow")
        for tok in ("C. Outcome timing", "D. Predictor data", "Interview", "184", "Examination", "167", "Laboratory", "111",  # Prompt 104: title wraps  # Prompt 106  # Prompt 108  # prompt 110  # prompt 111  # prompt 111  # prompt 112
                    "F. Candidate predictors", "median 22.5", "not reported 118"):  # Prompt 104: candidate predictors are panel G  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110
            self.assertIn(tok, t, tok)
        for gone in ("Binary", "Several binary", "N=220) E", "191 (87%)"):  # Prompt 107
            self.assertNotIn(gone, t, gone)
        self.assertIn("J. Evaluation steps", t)  # Prompt 104: evaluation is panel K  # Prompt 107  # Prompt 108  # prompt 110
        order = [t.index(x) for x in ("Tuning search", "Train-test split", "Cross-validation", "AUROC reported", "CI for performance")]  # Prompt 108  # prompt 110  # prompt 111
        self.assertEqual(order, sorted(order))
        body = MM.split("def figure2(")[1].split("def figure_analysis(")[0]  # Prompt 108
        self.assertNotIn("TEAL", body)

    def test_figures_3_to_5(self):
        t3 = fig("fig4_variable_importance")
        self.assertIn("B. Diabetes or prediabetes, study by study", fig("fig5_rankings_named"))  # Prompt 107  # prompt 109  # prompt 112
        self.assertIn("≤19", t3); self.assertNotIn("≤2019", t3)
        t4 = fig("fig6_maturing_practice")  # prompt 112
        self.assertIn("B. Calibration reported", t4)  # Prompt 107  # prompt 109
        t5 = fig("fig7_next_steps")  # prompt 112
        self.assertNotIn("Not identifiable", t5); self.assertIn("Approach not described", t5); self.assertIn("14", t5)  # Prompt 107  # Prompt 107
        self.assertNotIn('axA.get_yticklabels()[4].set_weight("bold")', MM)

    def test_results_sentences(self):
        self.assertNotIn("Besides classification", EN)
        self.assertNotIn("interpreted variables (151)", RES)
        self.assertIn("Of the 192 core studies, 154 produced a variable-importance ranking;", RES)  # prompt 110
        self.assertIn("Below the topics, the remaining variables differed by outcome", RES)  # Prompt 102: S8A wording  # prompt 112
        self.assertIn("Within diabetes or prediabetes, the core recurred alongside study-specific variables", RES)  # prompt 109  # prompt 112
        self.assertNotIn("own candidate sets", RES); self.assertNotIn("median of 10 variables", RES)
        self.assertNotIn("PROBAST", RES)  # Prompt 102: in Next Steps  # Prompt 106  # prompt 109
        self.assertIn("184 of the 192 used the health interview, 167 the examination and 111 laboratory data", RES)  # Prompt 104  # Prompt 106  # Prompt 107
        self.assertNotIn("18 of the 41", RES); self.assertNotIn("Reporting that lets an analysis be rebuilt", RES)
        self.assertNotIn("would also let an analysis be rebuilt", RES)  # prompt 109
        self.assertIn("Of the 44 studies reporting a decision threshold, 21 chose it without", " ".join(EN.split())); (" ".join(  # Prompt 106  # prompt 110  # prompt 111
            " ".join(p.get_text() for p in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))

    def test_discussion_order(self):
        dis = re.findall(r"\\subsection\{([^}]*)\}", EN.split("\\section{Discussion}")[1].split("\\section{Conclusions}")[0])
        self.assertEqual(dis, ["Principal Findings", "Explanation as the Main Product", "Reuse and Comparison of Results",  # prompt 109  # prompt 111
                               "Stable and Representative Explanations", "Prediction Standards and Explanation Standards",  # Prompt 102  # prompt 111
                               "Comparison With Prior Work", "Strengths and Limitations"])
        two = EN.split("\\subsection{Stable and Representative Explanations}")[1].split("\\subsection{")[0]  # Prompt 102  # prompt 111
        self.assertIn("their stability should therefore be", two)  # Prompt 102
        self.assertIn("The second step, representativeness", two)  # Prompt 102
        self.assertIn("as\nsingle variables, education, income or occupation was named in 90", EN)  # Prompt 104: 2G cited  # Prompt 106  # prompt 110  # prompt 112
        kdis = re.findall(r"\\subsection\{([^}]*)\}", KO.split("\\section{고찰}")[1].split("\\section{결론}")[0])
        self.assertEqual(kdis[:5], ["주요 결과", "주된 산출물로서의 설명", "결과의 재사용과 비교", "안정적이고 대표성 있는 설명", "예측 기준과 설명 기준"])  # Prompt 102  # prompt 109  # prompt 111
        self.assertNotIn("not yet followed.\n\n\\subsection{Two", EN)

    def test_forward_headlines(self):
        self.assertIn("Practices that make these explanations stable and representative were in early use", FLAT)  # Prompt 103: abstract wording  # prompt 110
        self.assertIn("These findings point to three steps for interpreting variable importance from survey data", FLAT)  # prompt 111
        self.assertNotIn("adopted least", EN.split("\\section*{Declarations}")[0].split("\\begin{table}")[0])
        self.assertIn("안정적이고 대표성 있게 하는 실천은 초기 단계였다", FLATK)  # Prompt 103: abstract wording  # prompt 110
        self.assertIn("그 밖의 변수는 분류한 결과에 따라 달랐다", FLATK)  # Prompt 102: S8A wording  # prompt 112
        figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", EN.split("\\section*{Declarations}")[0])]
        self.assertEqual(list(dict.fromkeys(figs)), list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
