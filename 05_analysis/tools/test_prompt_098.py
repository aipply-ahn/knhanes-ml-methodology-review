#!/usr/bin/env python3
"""Prompt 098 (review v36, 91/100): Figure 4 comparability (named-variable count, same-outcome pairs, overlap without
age, sex and body size), Figure 4B at variable level (diabetes and prediabetes studies), interpretation sentences,
survey-cycle definition, denominators, 15 domains plus other, Table S8 in the 10-column layout with top-ranked
variables, supplement clean-up (S1 locations, S2B removed, S3 continued, S5 abbreviations, S6 note), Figure 6C label."""
import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
PT = json.loads((ROOT / "results/derived/practice_trends_098.json").read_text())


def pdf_text(path):
    t = " ".join(" ".join(p.get_text() for p in fitz.open(path)).split())
    t = re.sub(r"(\w)[\u2011-] (\w)", r"\1\2", t)
    return t.replace("\u2011", "-")


SUPP = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")


def section(text, start, end):
    return text.split(start)[-1].split(end)[0]


class Prompt098(unittest.TestCase):
    def test_comparability_values_computed(self):
        c = PT["named_variable_count"]
        self.assertEqual((c["n"], c["median"], c["q1"], c["q3"]), (129, 10, 6.0, 12.5))
        g = PT["domain_agreement_098"]
        self.assertEqual(sum(v["pairs"] for v in g["all_domains"].values()), 129 * 128 // 2)
        self.assertEqual([g["all_domains"][k]["median"] for k in ("same_outcome", "same_topic_other_outcome", "different_topic")],
                         [0.3, 0.273, 0.25])
        self.assertEqual([g["without_age_sex_body_size"][k]["median"] for k in ("same_outcome", "different_topic")], [0.222, 0.167])
        for n in ("094", "095", "096", "097"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_diabetes_panel(self):
        p = PT["diabetes_variable_panel"]["studies"]
        self.assertEqual(len(p), 12)
        count = lambda lab: sum(lab in s["positions"] for s in p)
        self.assertEqual([count(x) for x in ("Age", "BMI", "Waist circumference or WHtR", "Cholesterol or triglycerides",
                                             "Hypertension or blood pressure", "Education, income or occupation",
                                             "Diet or nutrients", "HbA1c or fasting glucose")], [8, 5, 5, 5, 5, 5, 4, 3])
        self.assertIn("age was named in 11 of the 16 studies, body mass index, waist circumference and cholesterol or triglycerides "  # Prompt 101: same-core sentence  # Prompt 106  # prompt 112
                      "in 8 each and blood pressure in 7", " ".join(EN.split()))  # Prompt 101: diet and glycaemic counts in Figure 3C  # Prompt 106  # prompt 112
        self.assertIn("16편 중 나이는 11편, 체질량지수·허리둘레·콜레스테롤 또는 중성지방은 각각 8편", " ".join(KO.split()).replace("허리 둘레", "허리둘레"))  # Prompt 100: rewrapped  # Prompt 106  # prompt 112

    def test_interpretation_sentences(self):
        self.assertIn("The 154 rankings most often named\nage (113), socioeconomic position (93) and body size (87), and otherwise followed the outcome.", EN)  # Prompt 102: S8A wording  # Prompt 106  # prompt 111  # prompt 112
        self.assertNotIn("agreed little", EN)
        self.assertNotIn("little beyond them", EN)
        self.assertIn("0.25 and 0.17; \\suppfig{7}A)", " ".join(EN.split()))  # Prompt 102: agreement figure S8 cited in the Discussion  # prompt 109  # prompt 110
        self.assertIn("while the lists ranged from 1 to 31 variables", " ".join(EN.split()))  # Prompt 100: rewrapped  # Prompt 106  # prompt 112
        self.assertIn("reporting the full candidate set (Table~\\ref{tab:recommended-practice}) and assessing ranking stability would help readers interpret differences", " ".join(EN.split()))  # Prompt 101  # prompt 110
        self.assertIn("because the studies started from candidate sets of different sizes", EN)
        self.assertIn("TRIPOD+AI reporting and PROBAST+AI risk of bias were assessed.", EN)
        self.assertNotIn("sample-dependent ones", EN)
        self.assertIn("그 밖의 변수는 분류한 결과에 따라 달랐다", KO)  # Prompt 102: S8A wording  # prompt 112

    def test_definitions_and_denominators(self):
        self.assertIn("A survey cycle is one of the KNHANES phases of up\nto three years (for example, 2007--2009)", EN)
        self.assertIn("조사 주기(cycle)는 최대 3년으로 이루어진 KNHANES의 기수", KO)
        self.assertIn("most often addressed metabolic and endocrine health (49)", " ".join(EN.split()))  # Prompt 100: Figure 2C sentence  # Prompt 106  # Prompt 107
        self.assertIn("plus other), ranking stability", EN)
        self.assertIn("combined-year weights", EN)
        self.assertNotIn("combined-cycle weights", EN.split("\\section*{Declarations}")[0].replace("% ", "%"))
        self.assertNotIn("The rise was not a shift", EN)  # Prompt 100: rebuttal removed; the rise is stated positively
        self.assertEqual(" ".join(EN.split()).count("from 5 of 10 to 15 of 17"), 1)  # Prompt 100: positive sentence citing Supplementary Figure S3E  # Prompt 106
        self.assertIn("Additional file 1] KNHANES\\_ML\\_review\\_Supplementary.pdf (PDF). Supplementary Tables S1--S8", EN)
        self.assertNotIn("follows the reference list in this file", EN)

    def test_word_limits(self):
        import subprocess
        out = subprocess.run(["python3", str(ROOT / "prompts/implementation_records/prompt_098/word_counts.py")],
                             capture_output=True, text=True).stdout
        w = dict(line.split() for line in out.strip().splitlines())
        self.assertLessEqual(int(w["Abstract"]), 350)
        self.assertLessEqual(int(w["Discussion"]), 1300)

    def test_table_s8_layout(self):
        s8 = SUPP.split("Supplementary Table S8. Characteristics of ten illustrative included studies")[-1]  # Prompt 106  # prompt 113
        for h in ("ID Study DOI Outcome Survey years; n Algorithms Valid. Importance Top-ranked variables Design; code",
                  "Core health-focused classification studies (n=192)", "Cardiovascular (n=31)",  # Prompt 106
                  "Other health-focused studies (n=22)", "Method-focused studies (n=36)", "no DOI",  # Prompt 106
                  "Top-ranked variables are listed as reported, up to five, in the reported order"):
            self.assertIn(h, s8)
        self.assertIn("age, sex, hypertension, successful high school graduate status, drinking amount", s8)
        self.assertNotIn("Group; period", s8)
        self.assertNotIn("not used or not reported", s8)
        self.assertNotIn("not provided", s8)
        tex = (ROOT / "manuscript/supplementary/tex/Supplementary_Table_S08_Included_studies.tex").read_text()
        self.assertIn(r"\textbf{XGB}", tex)  # selected model in bold
        self.assertEqual(len(PT["top_variables"]), 129)

    def test_supplement_cleanup(self):
        self.assertNotIn("Supporting Assessments", SUPP.split("Supplementary Table S2")[0].split("Supplementary Table S1.")[-1])
        self.assertNotIn("model-based rankings are analysed in Figure 3", SUPP)
        self.assertNotIn("Final analytic sample size (N=184)", SUPP)
        self.assertIn("The final analytic sample is shown in Figure 3E", SUPP)  # Prompt 099: S2C  # Prompt 107  # Prompt 108  # prompt 110
        s3c = SUPP.split("Screening dispositions")[-1].split("Supplementary Table S4")[0]
        self.assertIn("full-text layer kept", s3c)
        self.assertIn("Includes one record (ART003346494", s3c)
        self.assertNotIn("Dataset not confirmed", s3c)
        s5 = SUPP.split("Supplementary Table S5. The 22 health-focused studies outside the core classification cohort")[-1].split("Supplementary Figure S1.")[0]  # Prompt 107
        self.assertNotIn("RMSE", s5)
        self.assertNotIn("beyond development", s5)
        self.assertNotIn("using machine learning methods", s5)
        self.assertIn("Abbreviations as in Table S8", s5)  # prompt 111
        s6 = SUPP.split("Verification protocol")[-1]
        self.assertIn("assigned to 15 domains plus other", s6)
        self.assertNotIn("PROTOCOL_ITEMS", s6)
        self.assertIn("The author checked the resulting study-level dataset against the full report and supplements.", s6)

    def test_figures(self):
        src = (ROOT / "tools/make_main_figures.py").read_text()
        self.assertIn('practice_trends_112.json', src)  # Prompt 104: superset JSON  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109  # prompt 110  # prompt 112
        self.assertNotIn("Filled: produced a ranking", src)  # Prompt 099: Figure 2A is bars; the ranking code left
        self.assertIn("All applied steps", src)  # Prompt 099: Figure 6C redesigned with a summary row
        self.assertIn("Combined-year weights", src)
        for f in ("fig5_rankings_named", "fig5_rankings_named_ko"):  # Prompt 100: diabetes panel is Figure 3C  # Prompt 107  # prompt 112
            t = " ".join(fitz.open(ROOT / f"manuscript/figs/{f}.pdf")[0].get_text().split())
            self.assertTrue("diabetes or prediabetes" in t.lower() or "당뇨·전당뇨" in t, f)  # prompt 109  # prompt 112


if __name__ == "__main__":
    unittest.main(verbosity=2)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
