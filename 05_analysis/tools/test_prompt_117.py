#!/usr/bin/env python3
"""Prompt 117: Additional Data 1 is a single sheet (author): one row per included study plus the 97 reports not included,
every result as a column, column definitions as header notes; text follows it; review v53 sentences 5.1-5.3."""
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
EN = " ".join((ROOT / "manuscript/bmc_main.tex").read_text().split())
KO = " ".join((ROOT / "manuscript/bmc_main_ko.tex").read_text().split())
F = ROOT / "paper/KNHANES_ML_review_Additional_Data_1.xlsx"


class Prompt117(unittest.TestCase):
    def test_single_sheet(self):
        wb = load_workbook(F)
        self.assertEqual(wb.sheetnames, ["Additional Data 1"])
        ws = wb.active
        h = [c.value for c in ws[1]]
        self.assertEqual(len(h), len(set(h)))
        self.assertTrue(all(c.comment is not None for c in ws[1]))
        self.assertEqual(ws.max_row - 1, 347)
        for col in ("Task", "Reason not included", "Evidence locations", "Variable names and harmonised labels",
                    "PROBAST+AI evaluation units, overall", "Reporting 19: Registration and data/code availability", "Method evaluation design"):
            self.assertIn(col, h)
        wb.close()

    def test_text(self):
        for tok in ("Bibliographic details and the coded values underlying the figures and tables are given for all 250 included studies in Additional Data~1",
                    "reporting the full candidate set (Table~\\ref{tab:recommended-practice}) and assessing ranking stability would help readers interpret differences in variable importance across studies",
                    "their stability should therefore be assessed before substantive conclusions are drawn from them",
                    "a single table with one row for each of the 250 included studies (and for the 97 reports excluded",
                    "each column defined in its header note", "Its coding rules are summarised with the verification procedure below."):
            self.assertIn(tok, EN, tok)
        for gone in ("Every included study is listed with its DOI", "would make rankings comparable", "which is why stability is checked first",
                     "Sensitivity sheet", "Protocol_items", "Columns sheet", "sheet showing"):
            self.assertNotIn(gone, EN, gone)
        for tok in ("한 행씩 담은 하나의 표", "연구 간 변수중요도 차이를 해석하는 데 도움이 된다", "실질적 결론을 내리기 전에"):
            self.assertIn(tok, KO, tok)
        rules = (ROOT / "tools/verification_protocol_rules.py").read_text()
        self.assertNotIn("Protocol_items sheet", rules)
        self.assertIn("defined in its header note", rules)


if __name__ == "__main__":
    unittest.main(verbosity=1)
