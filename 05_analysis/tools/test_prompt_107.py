#!/usr/bin/env python3
"""Prompt 107 (review v44, fixed denominators and the Figure 2/3 split)."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
PT = json.loads((ROOT / "results/derived/practice_trends_107.json").read_text())


def body(tex):
    return tex[tex.index("\\begin{document}"):]


def pdf_text(p):
    raw = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout
    return " ".join(re.sub(r"(?m)^\s*\d+\s*$", "", raw).split()).replace("\u2011", "-")


class Prompt107(unittest.TestCase):
    def test_six_main_figures_in_order(self):
        for tex, stems in ((EN, ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance",
                                 "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"]),  # prompt 112
                           (KO, ["fig1_prisma_ko", "fig2_literature_map_ko", "fig3_analysis_workflow_ko", "fig4_variable_importance_ko",
                                 "fig5_rankings_named_ko", "fig6_maturing_practice_ko", "fig7_next_steps_ko"])):  # prompt 112
            figs = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{figs/([^}.]+)\.pdf\}", body(tex))
            self.assertEqual(figs, stems)
            for st in stems:
                self.assertTrue((ROOT / "figures/submission" / f"{st}.pdf").exists(), st)
        for old in ("fig3_classification_to_explanation", "fig4_maturing_practice.", "fig5_next_steps"):
            self.assertNotIn(old, body(EN)); self.assertNotIn(old, body(KO))

    def test_fixed_denominators_in_derived_values(self):
        n = PT["classified_outcome"]["n"]
        self.assertEqual(n, 192)
        self.assertEqual(sum(PT["core_topics"].values()), n)
        sm = PT["selected_model_family_192"]
        self.assertEqual(sum(v for k, v in sm.items() if k != "n"), n)
        self.assertEqual(sm["single_algorithm"], 52)
        for v in PT["survey_design_192"].values():
            self.assertEqual(sum(v.values()), n)
        for v in PT["preprocessing_192"].values():
            self.assertEqual(sum(v.values()), n)
        self.assertEqual(PT["preprocessing_192"]["all_applied_steps"], {"WITHIN": 17, "BEFORE": 96, "UNCLEAR": 72, "NA": 7})
        self.assertEqual(PT["core_topics"]["METABOLIC_ENDOCRINE"], 49); self.assertEqual(PT["core_topics"]["MENTAL_HEALTH"], 42)
        tc = PT["task_composition"]
        self.assertEqual((tc["health"]["classification"], tc["health"]["continuous_or_ordered"] + tc["health"]["other"], sum(tc["method"].values())), (192, 22, 36))

    def test_partial_denominators_removed_from_text(self):
        pdf = pdf_text(ROOT / "build/submission/bmc_main.pdf")
        for stale in ("9 of 190", "7 of 191", "17 of 185", "Among the 185 studies", "214 analysed a health question",
                      "214 were health-focused", "health-focused studies (214)", "2 of 29 to 12 of 49 studies", "(12 of 22 each)",
                      "/190", "/191", "/185", "154/192", "the 140 studies comparing"):
            self.assertNotIn(stale, pdf, stale)
        for fresh in ("192 classified a health state, 22 analysed health with other tasks and 36", "every partition sums to 192",  # prompt 112
                      "From here on, every figure follows the 192 core studies", "All (N=192)", "31 were published in 2025 and 22 in 2026"):  # prompt 109  # prompt 111  # prompt 112
            self.assertIn(fresh, pdf.replace("ﬁ", "fi"), fresh)
        ko = " ".join(body(KO).split())
        for stale in ("190편 중 9편", "191편 중 7편", "185편 중 17편", "건강 중심 214편"):
            self.assertNotIn(stale, ko, stale)
        self.assertIn("모든 분할의 합을 192편으로", ko)  # prompt 112

    def test_table_s5_counts_22(self):
        a = json.loads((ROOT / "manuscript/supplementary/data/Supplementary_Table_S06_noncore_health_reaudit.json").read_text()) \
            if (ROOT / "manuscript/supplementary/data/Supplementary_Table_S06_noncore_health_reaudit.json").exists() else None
        supp = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")
        self.assertIn("The 22 health-focused studies outside the core classification cohort", supp)
        self.assertNotIn("The 19 health-focused studies outside the core classification cohort", supp)
        if a:
            self.assertEqual(a["n"], 22)

    def test_supplement_duplicates_removed(self):
        supp = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")
        self.assertNotIn("Analyses performed (N=214", supp)
        self.assertNotIn("Final analytic sample by publication year", supp)
        self.assertIn("Role of KNHANES", supp)

    def test_abstract_limit(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from test_prompt_087 import abstract_words
        self.assertLessEqual(abstract_words(ROOT / "build/submission/bmc_main.pdf")[1], 350)


if __name__ == "__main__":
    unittest.main()
