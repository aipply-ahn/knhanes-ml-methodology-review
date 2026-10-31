#!/usr/bin/env python3
"""Prompt 096 (review v34 + message revision): explanation-tool message, two-layer maturing claims, Figure 6
redesign, supplement cleanup and the Table S9 study-level summary preview."""
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
PT = json.loads((ROOT / "results/derived/practice_trends_096.json").read_text(encoding="utf-8"))


def pdf(path):
    with fitz.open(path) as d:
        return " ".join(" ".join(p.get_text() for p in d).split()).replace("\u2011", "-")


class Calculations(unittest.TestCase):
    """[S5 calculation] items of review v34 section 8."""

    def test_095_values_unchanged(self):
        o95 = json.loads((ROOT / "results/derived/practice_trends_095.json").read_text(encoding="utf-8"))
        for k, v in o95.items():
            self.assertEqual(PT[k], v, k)

    def test_tuning_definitions(self):
        self.assertEqual(PT["tuning_definitions"], {"separated_or_no_tuning": [16, 10, 20, 26], "separated_only": [11, 6, 18, 22]})

    def test_rise_2026(self):
        r = PT["rise_2026"]
        self.assertEqual((r["n"], r["validation"], r["calibration"], r["validation_and_calibration"], r["journals"]), (22, 13, 12, 9, 12))
        self.assertEqual(r["validation_kind"], {"external_data": 7, "later_survey_period": 4, "both": 2})
        self.assertEqual(r["max_validation_studies_per_author_name"], 2)

    def test_preprocessing_states_and_stability_methods(self):
        self.assertEqual([p["UNCLEAR_NO_BEFORE"] for p in PT["preprocessing_states"]], [8, 15, 23, 19])
        s = PT["stability_methods"]
        self.assertEqual((s["n"], s["method_identified"], s["SUBGROUP_CONSISTENCY"], s["RESAMPLING_STABILITY"],
                          s["EXTERNAL_DATA_REPLICATION"], s["UNCERTAINTY_INTERVAL"]), (25, 11, 6, 3, 2, 1))

    def test_every_period_claims(self):
        for k in ("code_link", "stability_among_ranking"):
            v = PT["shares"][k]
            self.assertTrue(all(a < b for a, b in zip(v, v[1:])), k)


class MainText(unittest.TestCase):
    def test_latest_period_wording_gone(self):
        for gone in ("latest period", "mostly in 2025--2026", "fell from 18 of 32", "Toward Reporting Guidance",
                     "works mostly as an analysis tool instead", "natural companion of a ranking", "Figure~\\ref{fig:next-steps}D",
                     "5 of 31 through 2019", "Three practices suited to survey data spread least"):
            self.assertNotIn(gone, EN, gone)
        for gone in ("주로 최근 시기", "보고 지침을 향해", "31편 중 5편", "주로 2025--2026년에 늘었다"):
            self.assertNotIn(gone, KO, gone)

    def test_message_revision(self):
        for present in (
                "Standards for ML in health research are built around models that predict outcomes in new individuals.",
                "Code sharing and checks of ranking stability rose in every period, and calibration and validation beyond the development data rose in 2025--2026 (14 and 17 of 53), mostly among studies published in 2026.",  # Prompt 106  # Prompt 107  # prompt 111
                "In KNHANES research, supervised ML has increasingly been used not only to classify contemporaneously measured health states",  # prompt 113
                "In repeated cross-sectional surveys, outcomes and predictors are measured at the same time",
                "And how far have the practices that make an explanation from survey data stable and representative been adopted?",
                "In KNHANES, model-based variable importance has become a prominent output alongside classification.",  # prompt 113
                "\\subsection{Prediction Standards and Explanation Standards}",  # Prompt 101: renamed with the reorder
                "their stability should therefore be assessed before substantive conclusions are drawn",  # Prompt 102: Three Next Steps
                "The 12 validations in 2026 used a later survey period",  # Prompt 102: pattern repetition removed  # Prompt 106
                "the rise coincides with the publication of TRIPOD+AI in 2024, whose citation was not recorded",  # Prompt 102: moved to Limitations
                "The second step, representativeness, is specific to survey data.",  # Prompt 102
                "the last two mostly in the newest studies",  # prompt 111
                "Studies published in 2026 were retrieved within months of publication",
                "uses were described from the outputs each study produced, not from the authors' stated aims",  # prompt 112
                "mostly in studies published in 2026 (12 each, against 2 and 5 of the 31 published in 2025".lower(),  # Prompt 100: 2025 values only in Figure 4  # Prompt 106  # Prompt 107  # prompt 109  # prompt 110  # prompt 110  # prompt 112
                "not applicable); where the approach was described",  # Prompt 099: the rise is stated in Maturing Practice  # Prompt 106  # Prompt 107  # Prompt 108
                "The timing of scaling and missing-value handling".lower()):
            self.assertIn(present, EN if not present.islower() else EN.lower(), present)
        self.assertIn("\\subsection{Ranking Stability, Survey Design and Preprocessing}", EN)  # prompt 109
        self.assertEqual(EN.count("\\subsection{"), 19)  # Prompt 100: five Results subsections  # prompt 112

    def test_table1_checklist(self):
        t = section(EN, "\\begin{table}", "\\end{table}")
        self.assertIn("Methodological practices reported in the 192 core classification studies", t)  # prompt 109
        order = [t.index(x) for x in ("Outcome and predictors", "Data preparation", "Model development and evaluation", "Variable importance",  # prompt 109
                                      "Survey design", "Transparency", "Analysis code shared",  # prompt 109
                                      "Final model fully specified")]  # prompt 109
        self.assertEqual(order, sorted(order))

    def test_ko_parity(self):
        for present in ("두드러진 산출물이 되었다", "\\subsection{예측 기준과 설명 기준}",  # Prompt 101: renamed with the reorder "안정성은 설명의 첫째 요건이다", "변화는 두 가지 양상을 보였다",
                        "둘째 단계인 대표성", "\\subsection{순위 안정성, 조사설계, 전처리}",  # Prompt 102: three steps "설명과 조사자료", "예측 기준과 공통",  # prompt 109
                        "2026년 출판 연구는 출판 후", "대부분 2026년 출판 연구에서 나왔다"):  # Prompt 100: 2025 values only in Figure 4  # prompt 109  # prompt 110  # prompt 112
            self.assertIn(present, KO, present)

    def test_abstract_length(self):
        _, n = abstract_words(ROOT / "build/submission/bmc_main.pdf")
        self.assertLessEqual(n, 350)

    def test_title_kept(self):
        self.assertIn("From Classification to Explanation: A Systematic Methodological Review of Supervised Machine Learning in a National Health Survey", " ".join(  # Prompt 106
            (ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8").split()))


class Figures(unittest.TestCase):
    def test_fig4_titles(self):
        t = pdf(ROOT / "figures/submission/fig6_maturing_practice.pdf")  # prompt 112
        self.assertNotIn("Rose in every period", t)  # Prompt 100: two patterns as row headings  # Prompt 107  # Prompt 108
        self.assertNotIn("No consistent change", t)  # Prompt 100: moved to Supplementary Figure S3F
        self.assertNotIn("latest period", t)

    def test_fig6_redesign(self):
        t = pdf(ROOT / "figures/submission/fig7_next_steps.pdf")  # Prompt 100: former Figure 6  # prompt 112
        for token in ("A. Ranking stability checked, by period and approach", "Across survey cycles", "B. Survey design",  # Prompt 101: not-identifiable bar moved to the caption  # Prompt 107  # Prompt 108  # prompt 109
                      "C. When data-dependent preprocessing"):
            self.assertIn(token, t)
        for gone in ("Rebuildable from report", "5/31", "8/48", "D. "):
            self.assertNotIn(gone, t)


class Supplement(unittest.TestCase):
    def test_s6_panels(self):
        t = pdf(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S05_Differences_by_publication_period.pdf")  # Prompt 102: renumbered S5
        for token in ("A. Algorithms by period", "B. Paired model comparison", "C. Rankings by topic",  # prompt 110
                      ):  # Prompt 099: algorithm families moved to Figure 2C  # prompt 110
            self.assertIn(token, t)
        for gone in ("Calibration", "Model-based importance", "Reproducibility"):  # Prompt 100: panel F shows tuning kept apart (former Figure 5B)  # Prompt 107
            self.assertNotIn(gone, t)

    def test_s3e_and_s5_colour(self):
        t = pdf(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf")  # Prompt 102: renumbered S2  # prompt 110
        self.assertIn("B. Rebuildable from the report", t); self.assertIn("97 (51%)", t); self.assertIn("15 (8%)", t)  # Prompt 104: panel B  # Prompt 106
        src = (ROOT / "tools/make_supplementary_figures.py").read_text(encoding="utf-8")
        s5 = src[src.index("def s7():"):src.index("def s8():")]
        self.assertIn('Patch(color=LIGHT_TEAL, label="Partial")', s5)
        self.assertNotIn('Patch(color=AMBER, label="Partial")', s5)

    def test_portrait_pages(self):
        with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
            for p in d:
                head = p.get_text()[:200]
                if "Supplementary Figure S5." in head or "Supplementary Figure S6." in head:
                    self.assertGreater(p.rect.height, p.rect.width)

    def test_wording(self):
        t = re.sub(r"(\w)[\u2011-] (\w)", r"\1\2", supp_text())  # join words hyphenated at a line break
        for gone in ("Alevlenme", "KNHANES NR", "none/not reported unresolved", "Mi-Hyun Jin", "Retracted—excluded", "DAE_OE_XGB",
                     "ML_ADJACENT_REPORTS sheet", "11 records plus 1 encountered error", "5128 retrieved", "Records screened 11077",
                     "repeated pagination row", "Results: Maturing Practice; Supplementary Figure S5", "Toward Reporting Guidance"):
            self.assertNotIn(gone, t, gone)
        for present in ("Discussion; Supplementary Figure S8"  # Prompt 102: renumbered  # prompt 109
                       , "5,128 retrieved", "Records screened 11,077", "cursor pagination",
                        "the same XGBoost analysis", "KHM, report identifier used in Additional Data 1",  # Prompt 097: S4 header paragraph -> footnote
                       
                        "Retracted; excluded from performance evidence", "evaluation not reported", "years not reported", "Jin MH et al.",
                        "12 records"):
            self.assertIn(present, t, present)

    def test_s3_duplicate_row_wording(self):
        src = (ROOT / "tools/build_standalone_supplements.py").read_text(encoding="utf-8")
        self.assertIn("layer hits; one duplicated row removed before union.", src)  # PDF text hyphenates "du- plicated"

    def test_table_s2_no_self_reference(self):
        t = pdf(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S02_PRISMA_S_checklist.pdf")
        self.assertNotIn("Table S2 Not", t); self.assertNotIn("Table S2 No", t)

    def test_table_s9_preview(self):
        # Prompt 097 (review v35): the study table is Table S8 "Included studies" (DOI column; still 10 of 220).
        t = pdf(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S08_Included_studies.pdf")
        self.assertIn("Ten of the 250 included studies are shown", t)  # Prompt 106  # prompt 113
        self.assertEqual(len(set(__import__("re").findall(r"KHM\d{3}", t))), 10)  # Prompt 098: ID is its own column
        with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
            toc = [x[1] for x in d.get_toc()]
        self.assertEqual(len(toc), 16)  # Prompt 099: eight supplementary figures
        self.assertTrue(toc[-1].startswith("Supplementary Table S8."))

    def test_logs(self):
        for name in ("bmc_main", "bmc_main_ko", "bmc_supplementary"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
