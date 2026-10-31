#!/usr/bin/env python3
"""Prompt 115 (review v51 and author instructions): verification described as two AI systems plus the author's check,
no two-human or kappa wording; Additional Data 1 label and the three submission files; review text items."""
import hashlib
import re
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
EN_RAW = (ROOT / "manuscript/bmc_main.tex").read_text()
EN = " ".join(EN_RAW.split())
KO = " ".join((ROOT / "manuscript/bmc_main_ko.tex").read_text().split())
SUB = ROOT / "paper"  # prompt 119: final files alone in paper/
NAMES = ["KNHANES_ML_review_Main.pdf", "KNHANES_ML_review_Supplementary.pdf", "KNHANES_ML_review_Additional_Data_1.xlsx"]


def pdf_text(p):
    import fitz
    with fitz.open(p) as d:
        return " ".join(" ".join(pg.get_text() for pg in d).split())


class Prompt115(unittest.TestCase):
    def test_verification_wording(self):
        for tok in ("The author made all screening and eligibility decisions.",
                    "OpenAI Codex compiled the records of the 217 studies retained from the first round from an earlier extraction",
                    "its values were kept where the two differed",
                    "were extracted once by Claude Opus 5", "the author verified the resulting study-level dataset against the source reports",
                    "Extraction and appraisal were done by two AI systems and checked by one author", "with no second human reviewer",
                    "directed and checked the AI-assisted data extraction and appraisal"):
            self.assertIn(tok, EN, tok)
        for tok in ("OpenAI Codex가 이전 추출에서 기록을 옮겨 정리하고", "저자가 완성된 연구별 자료를 원문과 대조해 검수", "검토자는 없었으며"):
            self.assertIn(tok, KO, tok)
        tex = lambda n: " ".join((ROOT / "manuscript/supplementary/tex" / n).read_text().replace("\\allowbreak{}", "").replace("\\-", "").split())
        s67 = tex("Supplementary_Table_S06_Human_verification_protocol.tex") + " " + tex("Supplementary_Table_S07_Verification_results.tex")
        for tok in ("Verification protocol: AI-assisted extraction, author check and coding rules", "Extraction (two AI systems)",
                    "12,286 identical", "Author check (all studies)", "Single extraction of the 33 added studies by Claude Opus 5",
                    "OpenAI Codex compiled the first-round records from an earlier extraction"):
            self.assertIn(tok, s67, tok)
        supp = pdf_text(SUB / "KNHANES_ML_review_Supplementary.pdf")
        for text in (EN, KO, supp, s67):
            for bad in (r"[Kk]appa", r"inter-?rater", r"two (independent )?(human )?reviewers", r"second reviewer\b(?! )",
                        r"One reviewer \(the author\)", r"independently and\s+reconciled", "Human verification protocol"):
                self.assertIsNone(re.search(bad, text), bad)

    def test_review_items(self):
        for tok in ("In repeated cross-sectional surveys, outcomes and predictors are measured at the same time",
                    "Age, socioeconomic variables and body size were named across outcomes",
                    "these shares partly reflect how many variables each study reported",
                    "These changes concerned model evaluation and transparency.",
                    "These findings point to three steps for interpreting variable importance from survey data",
                    "repeated survey cycles could also be used to assess the temporal stability of variable-importance rankings",
                    "The ratings are counted in model evaluations, so a study evaluating several models contributes several",
                    "search sensitivity was not tested against a reference set of known eligible studies",
                    "including studies to which a practice did not apply"):
            self.assertIn(tok, EN, tok)
        for gone in ("0.33 and 0.20", "Survey data invite a different use", "common core and otherwise followed the outcome. Among",
                     "The next steps are those", "which leads to the first next step", "every coded value"):
            self.assertNotIn(gone, EN, gone)
        self.assertNotIn("0.33 대 0.20", KO)
        supp = pdf_text(SUB / "KNHANES_ML_review_Supplementary.pdf")
        self.assertIn("Pairs share studies and are not independent", supp)
        self.assertIn("prediction-model risk of bias, counted in model units", supp.replace("‑", "-"))

    def test_label_and_files(self):
        for t in (EN_RAW, (ROOT / "manuscript/bmc_main_ko.tex").read_text()):
            self.assertNotIn("Supplementary Data", t)
            self.assertNotIn("보충자료~1", t)
        self.assertIn("Additional file 2] KNHANES\\_ML\\_review\\_Additional\\_Data\\_1.xlsx (XLSX). Additional Data 1", EN_RAW)
        self.assertEqual(sorted(p.name for p in SUB.iterdir()), sorted(NAMES))  # prompt 119: paper/ holds only the final files
        rows = [l.split("\t") for l in (ROOT / "manuscript/submission_MANIFEST.tsv").read_text().splitlines()[1:]]
        self.assertEqual([r[0] for r in rows], NAMES)
        for r in rows:
            self.assertEqual(hashlib.sha256((SUB / r[0]).read_bytes()).hexdigest(), r[4], r[0])
        main = pdf_text(SUB / "KNHANES_ML_review_Main.pdf")
        self.assertNotIn("Supplementary contents", main)
        self.assertIn("A Systematic Methodological Review of Supervised Machine Learning", main)
        self.assertEqual((SUB / "KNHANES_ML_review_Supplementary.pdf").read_bytes(), (ROOT / "manuscript/bmc_supplementary.pdf").read_bytes())
        self.assertFalse((ROOT / "manuscript/Additional_File_2_Supplementary_Data_1.xlsx").exists())
        wb = load_workbook(SUB / "KNHANES_ML_review_Additional_Data_1.xlsx", read_only=True)
        self.assertEqual(wb.sheetnames, ["Additional Data 1"])  # prompt 117: one sheet
        rows = list(wb["Additional Data 1"].iter_rows(values_only=True)); h = rows[0]
        self.assertNotIn("Largest AUROC", h)
        for keep in ("Study ID", "Study", "Title", "Journal", "Year", "DOI or PMID", "Outcome group (Figure S7A)"):
            self.assertIn(keep, h)
        i = h.index("Variable names and harmonised labels")
        pairs = [x for r in rows[1:] if r[i] not in (None, "", "\u2013") for x in str(r[i]).split("; ")]
        self.assertEqual((len(pairs), sum(not x.endswith("= not matched") for x in pairs)), (2233, 2029))
        wb.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
