#!/usr/bin/env python3
"""Prompt 100 (review v38, straight storyline): Figure 2 follows the analysis workflow (A-G, purpose/task and
predictor/data panels added, no reversal panel); Figure 3 = rankings/SHAP, domains (four topics with >=10 ranking
studies), diabetes variables; Figure 4 = four practices that became more common as small multiples; Figure 5 = next
steps; rebuttal material (topic slopes, importance methods, no-change lines, pairwise overlap, preprocessing trend,
PROBAST+AI) lives in the supplement or Discussion. Results headings move forward."""
import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
ENB = EN.split("\\section*{Declarations}")[0]
KOB = KO.split("\\section*{선언}")[0]
RES_EN = EN.split("\\section{Results}")[1].split("\\section{Discussion}")[0]
RES_KO = KO.split("\\section{결과}")[1].split("\\section{고찰}")[0]
PT = json.loads((ROOT / "results/derived/practice_trends_100.json").read_text())
FIG = ROOT / "figures/submission"


def text(stem):
    with fitz.open(FIG / f"{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


def supp():
    with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
        t = " ".join(" ".join(p.get_text() for p in d).split())
    return re.sub(r"(\w)[\u2011-] (\w)", r"\1\2", t).replace("\u2011", "-")


class Prompt100(unittest.TestCase):
    def test_values(self):
        self.assertEqual(PT["task_composition"], {"health": {"classification": 165, "continuous_or_ordered": 10, "other": 9},
                                                  "method": {"develop_or_improve": 26, "compare_existing": 10}})
        self.assertEqual(PT["outcome_structure"], {"BINARY": 130, "MULTIBIN": 25, "MULTICLASS": 6, "MIXED": 4})
        self.assertEqual(PT["candidate_predictors"]["reported"], 61); self.assertEqual(PT["candidate_predictors"]["median"], 23.0)
        for n in ("094", "095", "096", "097", "098", "099"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_results_structure(self):
        self.assertEqual(re.findall(r"\\subsection\{([^}]*)\}", RES_EN),
                         ["Study Selection", "How Machine Learning Was Used", "Variable Importance as the Main Product",
                          "What the Rankings Named", "Practices That Became More Common", "Ranking Stability, Survey Design and Preprocessing"])  # prompt 109  # prompt 112
        self.assertEqual(len(re.findall(r"\\subsection\{", RES_KO)), 6)  # prompt 112
        self.assertEqual(re.findall(r"figs/(fig\d_[a-z_]+)\.pdf", ENB),
                         ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"])  # prompt 112
        self.assertEqual(re.findall(r"figs/(fig\d_[a-z_]+)_ko\.pdf", KOB),  # Prompt 107
                         ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"])  # prompt 112
  # Prompt 107
    def test_no_reversal_devices(self):
        for gone in ("On the surface", "What they classified, however", "The rise was not a shift", "At the level of individual studies, rankings varied more",
                     "overlapped only slightly more", "spread\nleast, although", "but the difference moved into unclear", "PROBAST+AI rated 236",
                     "adopted least; their absence", "whereas complete predictor sets"):
            self.assertNotIn(gone, RES_EN, gone)
        for gone in ("겉으로 보면", "그러나 이 모형들이", "주제 구성의 변화 때문이 아니었다", "순위가 더 다양했다", "조금 클 뿐", "가장 덜 퍼졌지만", "PROBAST+AI로 평가하면"):  # Prompt 102: PROBAST+AI now in Next Steps
            self.assertNotIn(gone, RES_KO, gone)
        self.assertNotIn("PROBAST+AI, whose analysis domain covers such steps", " ".join(EN.split()))  # Prompt 102: in Next Steps  # Prompt 106  # prompt 109

    def test_new_sentences(self):
        flat = " ".join(RES_EN.split())
        for s in ("192 classified a health outcome, 22 analysed health with another task (14 estimated a continuous or ordered value and eight performed other analyses",  # Prompt 106  # Prompt 107
                  "and outcomes were usually binary (151)", "97 pooled several survey cycles", "started from a median of 22.5 predictors",  # Prompt 101: 165 core  # Prompt 106  # Prompt 107  # Prompt 108
                  "Of the 192 core studies, 154 produced a variable-importance ranking",  # Prompt 101: opens from Figure 2G
                  "The rise occurred in each of the four largest topics", "Within diabetes or prediabetes, the core recurred alongside study-specific variables",  # Prompt 101  # prompt 109  # prompt 112
                  "Three further practices bear directly on how",  # prompt 109
                  "none yet compared survey cycles", "mostly in studies published in 2026"):  # Prompt 107  # prompt 109  # prompt 110  # prompt 112
            self.assertIn(s, flat, s)
        self.assertNotIn("5 and 2 of 27", flat)  # 2025 values only as points in the figure

    def test_figures(self):
        f2 = text("fig2_literature_map")
        for tok in ("A. Studies per publication year", "B. Task", "Health analysis (classification) (n=192)",  # Prompt 101: B renamed  # Prompt 106  # Prompt 108
                    "Health analysis (other ML) (n=22)", "Method-focused (n=36)", "2025"):  # Prompt 104: A-K grid  # Prompt 106  # Prompt 107  # Prompt 108
            self.assertIn(tok, f2, tok)
        self.assertNotIn("But what they classified", f2); self.assertNotIn("like a prediction model", f2)
        f3 = text("fig4_variable_importance")  # Prompt 107
        self.assertIn("A. Most important variables by outcome", text("fig5_rankings_named")); self.assertIn("B. Diabetes or prediabetes, study by study", text("fig5_rankings_named"))  # Prompt 101: 3C message  # prompt 109  # prompt 112
        self.assertNotIn("Oral", f3); self.assertNotIn("Respiratory", f3); self.assertNotIn("Importance methods", f3)
        f4 = text("fig6_maturing_practice")  # prompt 112
        for tok in ("A. Analysis code shared (N=192)", "B. Calibration reported (N=192)", "C. Validation beyond the", "14/53", "17/53"):  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109
            self.assertIn(tok, f4, tok)
        self.assertNotIn("No consistent change", f4)
        self.assertIn("Across survey cycles", text("fig7_next_steps"))  # prompt 112
        for stale in ("fig4_ranking_content", "fig3_classification_to_explanation", "fig4_maturing_practice", "fig5_next_steps"):  # Prompt 107
            self.assertFalse((FIG / f"{stale}.pdf").exists(), stale)
        self.assertIn("Thin lines connect observations across the ordered publication periods as visual guides only; they do not represent fitted trends.", EN)
        self.assertIn("가는 선은 순서가 있는 출판 시기의 관측값을 시각적으로 연결할 뿐 적합한 추세를 뜻하지 않는다.", KO)

    def test_supplement(self):
        t = supp()
        for tok in ("C. Rankings by topic", "Other practices by period are given in Table 1", "(n/N of the core studies", "E. Importance methods",  # Prompt 106  # prompt 110  # prompt 110
                    "B. Rows of Figure 5A clustered by their variable profiles alone", "summarised in Figure 3J",  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110  # prompt 112
                    "(n/N of the core studies in the topic and period)", "Results: Practices That Became More Common; Figure 6"):  # Prompt 107  # prompt 109  # prompt 110  # prompt 112
            self.assertIn(tok, t, tok)
        figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", ENB)]
        self.assertEqual(list(dict.fromkeys(figs)), list(range(1, 9)))
        self.assertEqual(list(dict.fromkeys(int(x) for x in re.findall(r"\\suppfig\{(\d)\}", KOB))), list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
