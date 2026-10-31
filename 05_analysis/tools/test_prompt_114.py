#!/usr/bin/env python3
"""Prompt 114: Additional Data 1 is the coded-data workbook in the form of the EHR review's Additional File 1
(Columns dictionary, one row per study, unit-level sheets, selection flow, Reproduce). The published counts are re-added
here from the submitted file itself, independently of tools/build_data1_workbook.py."""
import json
import unittest
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "paper/KNHANES_ML_review_Additional_Data_1.xlsx"  # prompt 115: renamed
EN = " ".join((ROOT / "manuscript/bmc_main.tex").read_text().split())
KO = " ".join((ROOT / "manuscript/bmc_main_ko.tex").read_text().split())
SHEETS = ["Additional Data 1"]  # prompt 117: one sheet (author); was 17 sheets


def table(wb, name, skip=0):
    rows = list(wb[name].iter_rows(values_only=True))[skip:]
    return rows[0], rows[1:]


class Prompt114(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb = load_workbook(F, read_only=True)
        h, allrows = table(cls.wb, "Additional Data 1")
        cls.h, cls.all = h, allrows
        cls.rows = [r for r in allrows if not str(r[h.index("Study group")]).startswith("Not included")]
        cls.core = [r for r in cls.rows if r[cls.h.index("Study group")] == "Core classification"]

    def col(self, name, rows=None):
        return [r[self.h.index(name)] for r in (rows or self.core)]

    def test_structure(self):
        self.assertEqual(self.wb.sheetnames, SHEETS)
        self.assertLess(F.stat().st_size, 2_000_000)
        self.assertEqual(len(self.rows), 250)
        self.assertEqual(Counter(self.col("Study group", self.rows)), {"Core classification": 192, "Other health analysis": 22, "Method-focused": 36})
        self.assertEqual(len({r[0] for r in self.all}), 347)
        full = load_workbook(F)  # header notes define every column
        self.assertTrue(all(c.comment is not None and c.comment.text.strip() for c in full.active[1]))
        full.close()

    def test_published_counts(self):
        yes = lambda c: sum(v == "Yes" for v in self.col(c))
        self.assertEqual((yes("Importance ranking produced"), yes("SHAP used"), yes("Ranking stability checked")), (154, 56, 25))
        self.assertEqual((yes("Sampling weights mentioned"), self.col("Weights in model fitting").count("Yes"),
                          self.col("Weights in performance evaluation").count("Yes"), self.col("Strata or PSUs in variance estimation").count("Yes")), (50, 9, 7, 28))
        self.assertEqual((yes("Analysis code shared"), yes("Calibration reported"), yes("AUROC reported")), (17, 20, 138))
        beyond = sum(a == "Yes" or b == "Yes" for a, b in zip(self.col("Validation on a later survey period"), self.col("Validation on external data")))
        self.assertEqual((beyond, yes("Validation on a later survey period")), (38, 23))
        pre = Counter(self.col("Preprocessing over all applied steps"))
        self.assertEqual((pre["All within the training data"], pre["At least one step before the split"], pre["Timing unclear"], pre["No data-dependent step"]), (17, 96, 72, 7))
        self.assertEqual(Counter(self.col("Outcome timing"))["Current state measured in the same survey"], 190)
        self.assertEqual(Counter(self.col("Missing-value handling"))["Complete-case analysis"], 113)
        self.assertEqual(sum("Boosting" in v.split("; ") for v in self.col("Algorithm families fitted")), 92)
        self.assertEqual(Counter(self.col("Family of the selected model"))["Boosting"], 50)
        self.assertEqual(yes("Decision threshold reported"), 44)
        self.assertEqual(self.col("Threshold chosen without the final evaluation data").count("Yes"), 21)
        rk = [r for r in self.core if r[self.h.index("Importance ranking produced")] == "Yes"]
        hv = [v.split("; ") for v in self.col("Harmonised variables (Figure 5)", rk)]
        self.assertEqual((sum("Age" in v for v in hv), sum("BMI" in v for v in hv)), (113, 61))
        per = Counter((r[self.h.index("Publication period")], r[self.h.index("Importance ranking produced")]) for r in self.core)
        self.assertEqual([per[(p, "Yes")] for p in ("≤2019", "2020–2022", "2023–2024", "2025–2026")], [29, 25, 51, 49])
        added = [r for r in self.core if r[self.h.index("Added under the final eligibility criterion")] == "Yes"]
        self.assertEqual(len(added), 27)
        self.assertEqual(sum(r[self.h.index("Strata or PSUs in variance estimation")] == "Yes" for r in added), 14)

    def test_former_sheets_as_columns(self):  # prompt 117
        import re
        n = lambda txt: sum(int(x) for x in re.findall(r"HIGH (\d+)", str(txt)))
        tot = lambda col: sum(int(x) for v in self.col(col) for x in re.findall(r"(?:LOW|HIGH|UNCLEAR) (\d+)", str(v)))
        self.assertEqual((tot("PROBAST+AI development units, overall"), tot("PROBAST+AI evaluation units, overall"),
                          sum(n(v) for v in self.col("PROBAST+AI evaluation units, overall"))), (297, 378, 375))
        self.assertEqual(sum(str(r[self.h.index("Study group")]).startswith("Not included") for r in self.all), 97)
        other = [r for r in self.rows if r[self.h.index("Study group")] == "Other health analysis"]
        self.assertEqual(Counter(self.col("Task", other)), {"Continuous or ordered outcome": 14, "Other analysis": 8})
        self.assertFalse(any(v in ("NA", "NR", None) for v in self.col("Outcome", other)))
        method = [r for r in self.rows if r[self.h.index("Study group")] == "Method-focused"]
        self.assertEqual(Counter(self.col("Task", method))["Develops or improves a method"], 26)
        self.assertEqual(sum(c.startswith("Reporting ") for c in self.h), 19)
        pairs = [x for v in self.col("Variable names and harmonised labels") if v not in (None, "\u2013") for x in v.split("; ")]
        self.assertEqual((len(pairs), sum(not x.endswith("= not matched") for x in pairs)), (2233, 2029))

    def test_text(self):
        for tok in ("Additional Data~1 gives one row per study, with the coded values, their evidence locations and column definitions;",
                    "Bibliographic details and the coded values underlying the figures and tables are given for all 250 included studies in Additional Data~1;",
                    "(column on the final criterion in Additional Data~1)", "is the public study-level dataset, a single table",
                    "The internal extraction records (both AI extractions, their item-level comparison and the source extracts)"):
            self.assertIn(tok, EN, tok)
        for gone in ("SENSITIVITY\\_ANALYSES", "linked sheets for models, evaluations, and source locations", "Sensitivity sheet",
                     "a sheet showing how each result is reproduced", "Studies sheet"):
            self.assertNotIn(gone, EN, gone)
        for tok in ("한 행씩 담은 하나의 표", "추가자료~1의 최종 기준 열", "공개용 연구별 자료"):
            self.assertIn(tok, KO, tok)
        mk = (ROOT / "manuscript/Makefile").read_text()
        self.assertIn("python ../tools/build_data1_workbook.py", mk)
        dl = (ROOT / "tools/build_review_delivery.py").read_text()
        self.assertIn("KNHANES_ML_review_Additional_Data_1.xlsx", dl)  # prompt 115
        self.assertNotIn("Studies sheet", (ROOT / "manuscript/supplementary/tex/Supplementary_Table_S08_Included_studies.tex").read_text().replace("\\allowbreak{}", ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
