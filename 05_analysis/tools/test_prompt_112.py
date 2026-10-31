#!/usr/bin/env python3
"""Prompt 112 (review v49 and supplement 2): new Figure 5 (what the rankings named), Figure 4 one panel, Figures 6-7
renumbered, Figure 3C outcome timing, one dot size in period plots, denominator and limitation sentences, harmonisation
sheets in Additional Data 1."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
MM = (ROOT / "tools/make_main_figures.py").read_text()
O = json.loads((ROOT / "results/derived/practice_trends_112.json").read_text())


def norm(t):
    return " ".join(t.split())


def fig_text(stem):
    import fitz
    with fitz.open(ROOT / f"figures/submission/{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


class Prompt112(unittest.TestCase):
    def test_figure_set(self):
        for tex, stems in ((EN, ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance",
                                 "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"]),
                           (KO, ["fig1_prisma_ko", "fig2_literature_map_ko", "fig3_analysis_workflow_ko", "fig4_variable_importance_ko",
                                 "fig5_rankings_named_ko", "fig6_maturing_practice_ko", "fig7_next_steps_ko"])):
            self.assertEqual(re.findall(r"\\includegraphics\[[^]]*\]\{figs/([^}.]+)\.pdf\}", tex), stems)
        self.assertIn("\\subsection{What the Rankings Named}", EN)
        self.assertIn("\\subsection{순위가 꼽은 변수}", KO)

    def test_values(self):
        r = O["rankings_named_112"]
        self.assertEqual(r["all"]["n"], 154)
        c = r["all"]["counts"]
        self.assertEqual((c["Age"], c["Sex"], c["Education, income or occupation"], c["BMI"]), (113, 62, 90, 61))
        rows = {(x["topic"], x["group"]): x for x in r["rows"]}
        su, cv, mu, dm = (rows[("MENTAL_HEALTH", "suicide")], rows[("CARDIOVASCULAR", "cardiovascular")],
                          rows[("MUSCULOSKELETAL", "muscle")], rows[("METABOLIC_ENDOCRINE", "diabetes")])
        self.assertEqual((su["n"], su["counts"]["Depression or mood"], su["counts"]["Stress"]), (12, 9, 8))
        self.assertEqual((cv["n"], cv["counts"]["Cholesterol or triglycerides"], cv["counts"]["Hypertension or blood pressure"]), (11, 8, 7))
        self.assertEqual((mu["n"], mu["counts"]["BMI"]), (8, 7))
        self.assertEqual((dm["n"], dm["counts"]["Age"], dm["counts"]["BMI"], dm["counts"]["Waist circumference or WHtR"],
                          dm["counts"]["Cholesterol or triglycerides"], dm["counts"]["Hypertension or blood pressure"]), (16, 11, 8, 8, 8, 7))
        st = O["diabetes_variable_panel_112"]["studies"]
        self.assertEqual((min(x["n_named"] for x in st), max(x["n_named"] for x in st)), (1, 31))
        self.assertEqual(sum(x["n"] for x in r["rows"] if x["level"] == "topic"), 154)
        n = O["named_variable_count_all_models"]
        self.assertEqual((n["strings"], n["strings_mapped"]), (2233, 2029))
        self.assertEqual(O["outcome_timing_192"], {"current_state_same_survey": 190, "timing_unclear": 2, "future_event": 0})
        # earlier JSON files stay unchanged supersets
        o110 = json.loads((ROOT / "results/derived/practice_trends_110.json").read_text())
        self.assertTrue(all(O[k] == v for k, v in o110.items()))

    def test_text(self):
        en, ko = norm(EN), norm(KO)
        self.assertNotIn("every denominator is 192", en)
        self.assertIn("so every partition sums to 192 (154 for the rankings in Figure~\\ref{fig:named})", en)
        self.assertIn("SHAP was the most common importance method (56 studies;", en)
        self.assertNotIn("22 core studies published in 2026", en)
        self.assertNotIn("22 core studies", en)
        self.assertIn("31 were published in 2025 and 22 in 2026", en)
        self.assertIn("Validation on a later survey period was reported by 23 core studies in all, 17 of them among the 97", en)
        self.assertNotIn("23 core studies already validated", en)
        self.assertIn("Fourth, coding: uses were described", en)
        lim = en.split("Third, the period comparisons are descriptive")[1].split("Fourth, coding")[0]
        self.assertNotIn("Practices were recorded as reported", lim)
        self.assertIn("Age, socioeconomic variables and body size were named across outcomes", en)
        self.assertIn("named in 9 and 8 of the 12 suicidality studies", en)
        self.assertIn("(2,029 of 2,233 matched)", en)
        self.assertIn("and otherwise followed the outcome.", en.split("\\textbf{Results:}")[1][:900])
        for tok in ("모든 분할의 합을 192편으로", "2025년, 22편은 2026년에", "이후 조사 시기로 모형을 검증한 핵심 연구는 모두 23편", "넷째, 코딩이다",
                    "나이, 사회경제 변수, 체격은 결과와 관계없이 꼽혔고", "자살 관련 연구 12편 중 9편과 8편", "그 밖의 변수는 분류한 결과에 따라 달랐다"):
            self.assertIn(tok, ko, tok)
        self.assertNotIn("모든 분모를 192편으로", ko)
        self.assertNotIn("2026년에 출판된 핵심 연구 22편", ko)

    def test_figures(self):
        t3 = fig_text("fig3_analysis_workflow")
        for tok in ("C. Outcome timing", "Current state", "190", "Timing unclear", "Future event"):
            self.assertIn(tok, t3, tok)
        t4 = fig_text("fig4_variable_importance")
        self.assertNotIn("B. Domains", t4); self.assertNotIn("C. Diabetes", t4)
        t5 = fig_text("fig5_rankings_named")
        for tok in ("A. Most important variables by outcome (N=154; %)", "B. Diabetes or prediabetes, study by study (N=16 of the 154)",
                    "All ranking studies (154)", "Suicidality (12)", "Person", "Behaviour", "Clinical and", "Choi 2024 (31)"):
            self.assertIn(tok, t5, tok)
        self.assertIn('s=30, color=TEAL, zorder=3', MM)
        self.assertNotIn("s=[42, 18, 18, 42]", MM)
        for stem, toks in (("fig6_maturing_practice", ("1/45", "8/53", "14/53", "17/53")), ("fig7_next_steps", ("2/45", "12/53"))):
            t = fig_text(stem)
            for tok in toks:
                self.assertIn(tok, t, tok)

    def test_supplement(self):
        import openpyxl
        wb = openpyxl.load_workbook(ROOT / "manuscript/supplementary/tables/Supplementary_Data_1_Study_level_dataset.xlsx", read_only=True)
        self.assertIn("VARIABLE_HARMONISATION", wb.sheetnames); self.assertIn("RANKING_VARIABLES", wb.sheetnames)
        wb.close()
        import fitz
        with fitz.open(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S07_Agreement_between_rankings.pdf") as d:
            t = " ".join(d[0].get_text().split())
        self.assertIn("B. Rows of Figure 5A clustered by their variable profiles alone", t)


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
