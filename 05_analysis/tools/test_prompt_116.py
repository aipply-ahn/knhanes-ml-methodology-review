#!/usr/bin/env python3
"""Prompt 116 (review v52): verification wording matches the records (P1 migration by Codex, blinded P2 re-extraction by
Claude Opus 5, P2 kept where they differ); Table S7 defines the comparison unit; Additional Data 1 carries the evidence
links and is described as the public dataset, with the internal logs named; four sentences made direct."""
import json
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
EN = " ".join((ROOT / "manuscript/bmc_main.tex").read_text().split())
KO = " ".join((ROOT / "manuscript/bmc_main_ko.tex").read_text().split())
F = ROOT / "paper/KNHANES_ML_review_Additional_Data_1.xlsx"


def tex(n):
    return " ".join((ROOT / "manuscript/supplementary/tex" / n).read_text().replace("\\allowbreak{}", "").replace("\\-", "").split())


class Prompt116(unittest.TestCase):
    def test_records_behind_the_wording(self):
        a = json.loads((ROOT / "data/protocol_v1_2/ADJUDICATION_SUMMARY.json").read_text())
        self.assertEqual(a["reviewers"]["P1"], "codex_primary_evidence_review")
        p1 = json.loads((ROOT / "data/protocol_v1_2/P1/KHM001_P1.json").read_text())
        self.assertEqual(p1["review_mode"], "migration_validation")
        self.assertIn('"decision": "P2"', (ROOT / "tools/adjudicate_protocol_v1_2.py").read_text())

    def test_methods_and_limitations(self):
        for tok in ("OpenAI Codex compiled the records of the 217 studies retained from the first round from an earlier extraction and checked them against the source reports",
                    "Anthropic Claude Opus 5 then extracted every item again without access to these records, and its values were kept where the two differed",
                    "the author verified the resulting study-level dataset against the source reports before analysis",
                    "the first-round comparison was between a re-extraction and migrated records, not two independent extractions",
                    "Additional Data~1 gives one row per study, with the coded values, their evidence locations and column definitions",
                    "is the public study-level dataset", "the source locations of the extracted evidence",
                    "The internal extraction records (both AI extractions, their item-level comparison and the source extracts)"):
            self.assertIn(tok, EN, tok)
        for gone in ("OpenAI Codex extracted the 217", "prespecified rules that favoured", "Variable importance is central to this use",
                     "Once fitted and evaluated", "Stability is the first step.", "the questions that matter extend beyond",
                     "each column tied to its figure or table", "The full protocol has not been publicly deposited"):
            self.assertNotIn(gone, EN, gone)
        for tok in ("OpenAI Codex가 이전 추출에서 기록을 옮겨 정리하고", "둘이 다르면 둘째 값을 남겼다", "옮겨 온 기록과 재추출 사이의 비교", "공개용 연구별 자료", "추출 근거의 원문 위치"):
            self.assertIn(tok, KO, tok)

    def test_tables(self):
        s7 = tex("Supplementary_Table_S07_Verification_results.tex")
        for tok in ("65,268 item comparisons: 12,286 identical, 52,982 different", "re-extracted value kept for the 52,982 differences",
                    "An item comparison is one protocol item in one study record", "not extraction accuracy"):
            self.assertIn(tok, s7, tok)
        self.assertNotIn("resolved by rule", s7)
        s6 = tex("Supplementary_Table_S06_Human_verification_protocol.tex")
        self.assertIn("OpenAI Codex compiled the first-round records from an earlier extraction", s6)

    def test_additional_data(self):
        wb = load_workbook(F, read_only=True)  # prompt 117: evidence is a column of the single sheet
        rows = list(wb.active.iter_rows(values_only=True)); h = rows[0]
        core = [r for r in rows[1:] if r[h.index("Study group")] == "Core classification"]
        ev = [r[h.index("Evidence locations")] for r in core]
        self.assertGreaterEqual(sum(v not in (None, "None linked") for v in ev), 190)
        self.assertTrue(all("p." in v for v in ev if v not in (None, "None linked")))
        wb.close()
        full = load_workbook(ROOT / "manuscript/bmc_supplementary_data1.xlsx", read_only=True)
        readme = list(full["README"].iter_rows(values_only=True))
        self.assertTrue(any(r[0] == "Workbook role" and str(r[1]).startswith("INTERNAL full coding log, not submitted") for r in readme))
        full.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
