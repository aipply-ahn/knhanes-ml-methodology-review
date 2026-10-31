#!/usr/bin/env python3
"""Prompt 104 (review v42): Figure 2 grows to eleven panels in a 3 x 4 grid (question A-C, data D-G, analysis H-K):
new F final analytic sample, G candidate predictors, H missing-value handling, J model the authors selected (132
comparing several; boosting 50; criterion not coded); no AUROC distribution. Supplementary Figure S2 keeps outcome
structure and rebuildability only. Results, Methods and Discussion sentences follow the new panels."""
import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
FLAT, FLATK = " ".join(EN.split()), " ".join(KO.split())
PT = json.loads((ROOT / "results/derived/practice_trends_104.json").read_text())


DOCS = {}


def fig(stem):
    DOCS[stem] = fitz.open(ROOT / f"figures/submission/{stem}.pdf")  # kept open while the page is used
    return DOCS[stem][0]


class Prompt104(unittest.TestCase):
    def test_values(self):
        self.assertEqual(PT["missing_handling_165"], {"complete_case": 97, "single_imputation": 27, "multiple_imputation": 6,
                                                      "model_native": 1, "other_or_several": 10, "not_reported": 24})
        sf = PT["selected_model_family"]
        self.assertEqual(sf["n"], 132); self.assertEqual(sf["Boosting"], 50)
        self.assertEqual(sum(v for k, v in sf.items() if k != "n"), 132)
        self.assertEqual(PT["core_sample"]["reported"], 162); self.assertEqual(round(PT["core_sample"]["median"]), 7262)
        self.assertEqual(len(PT["candidate_predictor_values"]), 61)
        for n in ("094", "095", "096", "097", "098", "099", "100", "101"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_figure2_grid(self):
        page = fig("fig3_analysis_workflow")
        pos = {}
        for w in page.get_text("words"):
            t = w[4]
            if len(t) == 2 and t[1] == "." and t[0] in "ABCDEFGHIJK" and t[0] not in pos:
                pos[t[0]] = (w[0], w[1])
        self.assertEqual(sorted(pos), list("ABCDEFGHIJ"))  # Prompt 108  # prompt 110
        for row in ("ABCD", "EFG", "HIJ"):  # Prompt 107  # Prompt 108  # prompt 110
            ys = [pos[c][1] for c in row]
            self.assertLess(max(ys) - min(ys), 25, row)
            xs = [pos[c][0] for c in row]
            self.assertEqual(xs, sorted(xs), row)
        self.assertLess(pos["A"][1], pos["E"][1])  # Prompt 107  # Prompt 108  # prompt 110
        t = " ".join(page.get_text().split())
        for tok in ("E. Final analytic sample", "F. Candidate predictors", "G. Missing values", "I. Model the authors",  # Prompt 108  # prompt 110
                    "Complete case", "Boosting", "50", "median 5,607", "median 22.5", "Topic and data", "Analysis"):  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110  # prompt 111
            self.assertIn(tok, t, tok)
        for gone in ("AUROC distribution", "best", "Best"):
            self.assertNotIn(gone, t, gone)

    def test_text(self):
        for tok in ("184 of the 192 used the health interview, 167 the examination and 111 laboratory data",  # Prompt 106
                    "Analytic samples had a median of 5,607 participants", "118 did not report it (Figure~\\ref{fig:analysis}F)",  # Prompt 106  # Prompt 108  # prompt 110
                    "Missing values were most often handled by complete-case analysis (113 of 192) or single imputation (27), and 31",  # Prompt 106
                    "The model the authors selected was most often a boosting model (50 of 192)",
                    "(Figure~\\ref{fig:analysis}J; \\suppfig{6})", "the model the authors selected when several were compared",  # Prompt 108  # prompt 110
                    "the selection criterion was not coded", "started from a median of 22.5 predictors; 118 did not report it"):  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110
            self.assertIn(tok, FLAT, tok)
        self.assertNotIn("7,176", EN)
        for tok in ("184편이 건강설문을", "5,607명", "완전사례 분석(192편 중 113편)", "저자가 고른 모형은 부스팅이 가장 많았고(192편 중 50편)",  # Prompt 106
                    "(그림~\\ref{fig:analysis-ko}J, \\suppfig{6})", "여러 모형을 비교한 경우 저자가 고른 모형"):  # Prompt 107  # Prompt 108  # prompt 110
            self.assertIn(tok, FLATK, tok)
        for tex in (EN, KO):
            self.assertEqual(list(dict.fromkeys(int(x) for x in re.findall(r"\\suppfig\{(\d)\}", tex))), list(range(1, 9)))

    def test_supplement_s2(self):
        t = " ".join(fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf")[0].get_text().split())  # prompt 110
        self.assertIn("A. Outcome structure", t); self.assertIn("B. Rebuildable from the report", t)
        panels = t.split("Both panels use")[0]
        self.assertNotIn("Missing-data handling", panels); self.assertNotIn("candidate predictors", panels.lower())
        self.assertIn("are shown in Figure 3C, 3G and 3F", t)  # Prompt 107  # Prompt 108  # prompt 110
        self.assertIn("\\suppfig{2}", EN); self.assertIn("\\suppfig{2}", KO)  # prompt 109


if __name__ == "__main__":
    unittest.main()
