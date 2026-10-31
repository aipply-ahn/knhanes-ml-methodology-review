#!/usr/bin/env python3
"""Prompt 095 (review v33): maturing-practice claims matched to the data, Figure 4 small multiples, denominators, supplement cleanup."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_prompt_087 import abstract_words  # noqa: E402
from test_prompt_088 import body  # noqa: E402
from test_prompt_093 import section, supp_text  # noqa: E402

EN = " ".join(body((ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8")).split())
KO = " ".join(body((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8")).split())
PT = json.loads((ROOT / "results/derived/practice_trends_095.json").read_text(encoding="utf-8"))


def pdf(path):
    with fitz.open(path) as d:
        return " ".join(" ".join(p.get_text() for p in d).split()).replace("\u2011", "-")


class Calculations(unittest.TestCase):
    """The [S5 calculation] items of review v33 section 8."""

    def test_094_values_unchanged(self):
        o94 = json.loads((ROOT / "results/derived/practice_trends_094.json").read_text(encoding="utf-8"))
        for k, v in o94.items():
            self.assertEqual(PT[k], v, k)

    def test_little_changed_and_latest_split(self):
        self.assertEqual(PT["little_changed"], {"tuning_kept_apart": [16, 10, 20, 26], "predictor_set_rebuildable": [6, 5, 6, 9],
                                                "final_model_fully_specified": [3, 0, 3, 5]})
        s = PT["latest_period_by_year"]
        self.assertEqual((s["2025"]["n"], s["2026"]["n"]), (27, 22))
        self.assertEqual([s["2025"][k] for k in ("validation_beyond_development", "calibration", "code_link")], [5, 2, 3])
        self.assertEqual([s["2026"][k] for k in ("validation_beyond_development", "calibration", "code_link")], [13, 12, 5])

    def test_denominators(self):
        self.assertEqual((PT["validation_beyond_development_184"], PT["validation_beyond_development_165"]), (41, 38))
        self.assertEqual(PT["later_use_among_ranking"], {"n": 129, "reduced_predictor_set": 24, "subsequent_statistical_analysis": 12})
        self.assertEqual((PT["core_year_scope"]["MULTI_CROSS"], PT["temporal_validation_165"], PT["temporal_validation_among_pooled"]), (93, 23, 17))
        self.assertEqual(PT["preprocessing_all_within"], [5, 0, 2, 8])
        self.assertEqual(PT["preprocessing_applied"], [31, 32, 52, 48])
        self.assertEqual(PT["weights_in_fitting_not_applicable"], ["KHM003", "KHM005"])


class MainText(unittest.TestCase):
    def test_overstatement_removed(self):
        for gone in ("steadily more robust", "has become steadily", "fell in every period", "moved from classification toward explanation",
                     "all rose across the four periods", "so the same next steps apply to them", "Meanwhile, tree-based boosting",
                     "No step before the split: 82/165", "the 121 studies that pooled several survey cycles"):
            self.assertNotIn(gone, EN, gone)
        for gone in ("꾸준히 견고해졌다", "모든 시기에서 줄어", "분류에서 설명으로 옮겨 왔다", "네 시기에 걸쳐 모두 늘었다", "121편은 이미"):
            self.assertNotIn(gone, KO, gone)

    def test_v33_sentences(self):
        # Prompt 096 (review v34): "latest period" wording split into two layers (every period / 2026); boosting left the abstract.
        for present in (
                "42 of 53 in 2025--2026",  # Prompt 096 (review v34): boosting stays in How ML Was Used  # Prompt 106
                "Code sharing and checks of ranking stability rose in every period",
                "validation beyond the development data have become more common, the last two mostly in the newest studies",  # prompt 111
                "In KNHANES, model-based variable importance has become a prominent output",  # prompt 113
                "The 12 validations in 2026 used a later survey period (3), external data (7) or both (2);",  # Prompt 102: pattern repetition removed  # Prompt 103: bridge clause follows  # Prompt 106
                "Validation on a later survey period was reported by 23 core studies in all",  # Prompt 102: moved into the stability step  # prompt 112
                "share these design features, so the same distinction is likely to apply.",  # prompt 113
                "Tree-based boosting was fitted in 92 of the 192 studies, rising from 1 of 45",  # Prompt 099: boosting is Figure 2C  # Prompt 106  # Prompt 107
                "Code sharing, calibration and validation beyond the development data became more common",  # Prompt 100: no-change lines in S3F  # prompt 109  # prompt 110
                "the timing of scaling and missing-value handling was often unreported (69 and 50 studies",  # Prompt 099: Figure 6C reference follows (EN is whitespace-joined)  # Prompt 106
                "the 190 that classified a current health state and two whose outcome timing was unclear",  # Prompt 106  # Prompt 107
                "38 (19.8)",  # Prompt 101: the 41 clause left; core count in Table 1  # Prompt 106  # Prompt 107  # prompt 109
                "All preprocessing within the training data"):  # Prompt 097 (review v35): bracket (8/48) removed  # Prompt 106  # Prompt 107  # prompt 109
            self.assertIn(present, EN, present)

    def test_boosting_not_in_maturing(self):
        mat = section(EN, "\\subsection{Practices That Became More Common}", "\\subsection{Ranking Stability")  # Prompt 100: renamed section  # prompt 109
        self.assertNotIn("boosting", mat.lower())
        self.assertIn("boosting", section(EN, "\\subsection{How Machine Learning Was Used}", "\\subsection{Variable Importance"))  # Prompt 100: renamed section

    def test_probast_moved_to_next_steps(self):
        self.assertNotIn("236 of 259", section(EN, "\\subsection{Practices That Became More Common}", "\\subsection{Ranking Stability"))  # Prompt 100: renamed section  # prompt 109
        self.assertNotIn("236 of 259", section(EN, "\\subsection{Ranking Stability, Survey Design and Preprocessing}", "\\section{Discussion}")); self.assertIn("PROBAST+AI rated 375 of the 378 model evaluations here at high risk", EN)  # prompt 113  # Prompt 102: in Next Steps  # Prompt 101: stated in Results after Figure 2G  # Prompt 100: PROBAST+AI only in the Discussion and S8  # Prompt 106  # prompt 109

    def test_abstract_length(self):
        _, n = abstract_words(ROOT / "build/submission/bmc_main.pdf")
        self.assertLessEqual(n, 350)  # Prompt 096 (review v34): message-revision abstract, about 345 words

    def test_period_facts_not_invented_rationale(self):
        self.assertIn("the periods hold 45, 35, 59 and 53 core studies, and SHAP first appeared in this literature in 2020", " ".join(EN.split()))  # Prompt 106
        self.assertNotIn("Periods were chosen", EN)

    def test_connector_sentence_kept(self):
        self.assertIn("Thin lines connect observations across the ordered publication periods", EN)
        self.assertIn("가는 선은 순서가 있는 출판 시기의 관측값을 시각적으로 연결", KO)


class Figures(unittest.TestCase):
    def test_fig4_small_multiples(self):
        t = pdf(ROOT / "figures/submission/fig6_maturing_practice.pdf")  # prompt 112
        for token in ("(N=192)", "17/53", "14/53", "8/53", "1/45"):  # Prompt 100: four small multiples; no-change lines in S3F  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109
            self.assertIn(token, t)
        self.assertNotIn("boosting", t.lower())
        self.assertNotIn("stability", t.lower())  # Prompt 100: ranking stability is panel B  # prompt 109

    def test_fig2_fig3_denominators(self):
        f2 = pdf(ROOT / "figures/submission/fig2_ml_use.pdf")
        self.assertIn("Classification or estimation", f2); self.assertIn("41 (22%)", f2)
        f3 = pdf(ROOT / "figures/submission/fig4_variable_importance.pdf")
        self.assertIn("(N=192)", f3); self.assertIn("25 used it to build a reduced predictor set", " ".join(EN.split())); self.assertIn("12 to guide a subsequent statistical analysis", " ".join(EN.split()))  # Prompt 100: later use after Figure 3C  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110  # prompt 112

    def test_fig6_panel_d(self):
        t = pdf(ROOT / "figures/submission/fig7_next_steps.pdf")  # Prompt 100: former Figure 6  # prompt 112
        # Prompt 096 (review v34): Figure 6 has A stability by period, B survey design, C preprocessing; the flat preprocessing line was removed.
        for token in ("104", "Step not applied", "A. Ranking stability checked, by period and approach (N=192)", "Across survey cycles"):  # Prompt 099: trend moved to Figure 5  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109
            self.assertIn(token, t)

    def test_fig1_table_s5(self):
        t = pdf(ROOT / "figures/submission/fig1_prisma.pdf")
        self.assertIn("No ML or prediction term", " ".join(t.split())); self.assertNotIn("ML-adjacent", t); self.assertNotIn("Table S4", t)  # Prompt 097 (review v35): Additional Data 1  # Prompt 106  # prompt 110

    def test_no_amber_in_fig6c_and_s6(self):
        src = (ROOT / "tools/make_main_figures.py").read_text(encoding="utf-8")
        # Prompt 096 (review v34): the reproducibility panel moved to Supplementary Figure S3E (navy bars).
        self.assertNotIn("C. Rebuildable", src)
        s6 = (ROOT / "tools/make_supplementary_figures.py").read_text(encoding="utf-8")
        s6 = s6[s6.index("def s8():"):s6.index("def main():")]
        self.assertNotIn("VERM", s6)  # Prompt 096 (review v34): amber now marks only "any preprocessing step before the split" (S6E), the next-step colour
        for fn in ("s2", "s3"):
            body_ = s6 = (ROOT / "tools/make_supplementary_figures.py").read_text(encoding="utf-8")
            part = body_[body_.index(f"def {fn}():"):body_.index("# ----", body_.index(f"def {fn}():"))]
            self.assertNotRegex(part, r"axvline\(med, color=(AMBER|VERM)")


class Supplement(unittest.TestCase):
    def test_wording(self):
        t = supp_text()
        for gone in ("Retain corpus", "Merge preprint into khm100", "interpret ations", "evidence requirements",
                     "grades questioned in earlier reviews", "399 to 397", "the red line", "classification requirements"):
            self.assertNotIn(gone, t, gone)
        for present in ("Verification protocol: AI-assisted extraction, author check and coding rules", "Targeted source checks of outcome and predictor grades",
                        "Included; retracted, so excluded from performance evidence", "Preprint counted with its jour"):  # prompt 109
            self.assertIn(present, t, present)

    def test_prisma_locations(self):
        t = pdf(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S01_PRISMA_2020_checklist.pdf")
        self.assertNotRegex(t, r"Supplementary Figure S9")  # Prompt 099: eight supplementary figures
        self.assertIn("Discussion; Supplementary Figure S8", t)  # Prompt 102: PROBAST+AI figure renumbered S7  # prompt 109
        self.assertIn("Supplementary Figure S5", t.replace("Sup- plementary", "Supplementary"))  # Prompt 102: period figure renumbered S5

    def test_s6_portrait_grid(self):
        with fitz.open(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S05_Differences_by_publication_period.pdf") as d:  # Prompt 102: renumbered S5
            r = d[0].rect
        self.assertGreater(r.width, r.height * .9)  # prompt 110
        t = pdf(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S05_Differences_by_publication_period.pdf")  # Prompt 102: renumbered S5
        # Prompt 097 (review v35): topic panel moved to main Figure 2B; five panels remain.
        for token in ("A. Algorithms by period", "B. Paired model comparison", "C. Rankings by topic",  # prompt 110
                      ):  # Prompt 099: algorithm families moved to Figure 2C  # prompt 110
            self.assertIn(token, t)
  # Prompt 107
    def test_logs(self):
        for name in ("bmc_main", "bmc_main_ko", "bmc_supplementary"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
