#!/usr/bin/env python3
"""Prompt 091: 0 of 120 headline, claim rule, Fig 8A grouping, figure fixes, S4 ML-adjacent list."""
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

EN = body((ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8"))
KO = body((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8"))
SYN = json.loads((ROOT / "results/derived/claim_evidence_synthesis.json").read_text(encoding="utf-8"))


def fig_text(stem):
    with fitz.open(ROOT / "figures/submission" / f"{stem}.pdf") as d:
        return " ".join(d[0].get_text().split())


class Prompt091(unittest.TestCase):
    def test_synthesis_headline(self):
        self.assertEqual(SYN["beyond_classification"], {"studies": 138, "all_claims_supported": 0})  # Prompt 106
        self.assertEqual(SYN["classification_only"], {"studies": 54, "all_claims_supported": 4})  # Prompt 106
        self.assertEqual(SYN["classification_met_studies"], {"n": 15, "with_further_claims": 11})  # Prompt 106
        self.assertEqual(SYN["sensitivity_every_ranking_is_a_claim"]["all_claims_supported"], 1)
        self.assertEqual(SYN["participant_flow_core"]["complete_cohort_traceability"], 140)  # Prompt 106
        self.assertEqual(SYN["association_estimates_health"], {"studies_with_estimate": 60, "survey_design_uncertainty": 4})  # Prompt 106
        self.assertEqual(SYN["causal_purpose"], {"health_focused": 4, "core": 0})
        groups = {k: v["n"] for k, v in SYN["claim_count_groups"].items()}
        self.assertEqual(groups, {"1": 54, "2": 76, "3": 50, "4": 11, "5": 1})  # Prompt 106

    def test_headline_in_text(self):
        abstract = EN[EN.index("\\abstract{"):EN.index("\\keywords")]
        # Prompt 093 (review v31 section 6) merged the two headline sentences into one; the finding is unchanged.
        # Prompt 094 (review v32): the 0-of-120 claim headline was replaced by the classification-to-explanation headline.
        self.assertIn("SHAP was used in 33 of these 53", " ".join(abstract.split()))  # Prompt 106
        self.assertIn("\\subsection{Variable Importance as the Main Product}", EN)  # Prompt 100: the headline is the section heading
        concl = EN[EN.index("\\section{Conclusions}"):]
        self.assertIn("rank the variables on which these classifications depend", " ".join(concl.split()))  # prompt 113
        self.assertIn("\\subsection{주된 산출물이 된 변수중요도}", KO)  # Prompt 100: section heading
        _, n = abstract_words(ROOT / "manuscript/bmc_main.pdf")
        self.assertLessEqual(n, 350)

    def test_claim_rule_consistent(self):
        # Prompt 093 replaced the Methods rule paragraph with the review's three-sentence version (same rule).
        # Prompt 094 (review v32): purposes and claims are no longer coded; Methods states that instead.
        self.assertIn("We did not code authors' aims or proposed uses.", EN)
        self.assertNotIn("and separately any produced\nimportance ranking, required", EN)
        self.assertNotIn("all required evidence", EN)

    def test_sentence_items(self):
        for gone in ("\\paragraph{Study selection.}", "AUROC was reported in 134", "Original author labels", "Two extraction records did not",
                     "The two extraction records that did not", "screening ledger", "Claim types not separately encoded",
                     "We defined four study-level analysis sets", "399/401", "Its STUDIES sheet",
                     "\\item[ALE]", "\\item[AUPRC]", "\\item[DNN]", "\\item[IQR]", "\\item[SVM]"):
            self.assertNotIn(gone, EN)
        # Prompt 093: the reporting/RoB subsection became the last Results paragraph, the 401/399/397 sentence moved to
        # the Figure S7 caption, and Table 1 became the three-column rule table in Methods (review v31 sections 4-6).
        flat = " ".join(EN.split())
        # Prompt 094 (review v32): association-claim, rule-table and stated-purpose sentences left with purpose coding.
        for present in ("unsupervised methods", "97 pooled several survey cycles"):  # Prompt 101: Figure 2E counts the 165 core studies  # Prompt 106  # Prompt 107  # Prompt 108
            self.assertIn(present, flat)
        # Prompt 095 (review v33) section 5: the 401/399/397 sentence concerned a report outside the core cohort and was removed from S5;
        # the retraction is still stated in Table S4.
        supp = " ".join(" ".join(p.get_text() for p in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split())
        self.assertNotIn("from 399 to 397", supp)
        self.assertIn("Included; retracted, so excluded from performance evidence", supp)

    def test_figure_details(self):
        # Prompt 093: Figure 8 is Figure 5; Figures 6-7 are panels B-D of Figure 4; Figure 3 is Figure 2B-C.
        f5 = fig_text("fig5_claim_evidence")
        for token in ("0 of 120", "45", "67", "41", "12"):
            self.assertIn(token, f5)
        self.assertNotIn("Not reported", f5)
        f4 = fig_text("fig4_further_claims")
        self.assertIn("association requirement", f4); self.assertIn("policy requirement", f4)
        self.assertIn("All three (requirement)", f4)
        f2 = fig_text("fig2_use_and_claims")
        self.assertNotIn("No specific use", f2)
        f1 = fig_text("fig1_prisma")
        for gone in ("KCI", "Entering merge", "non-candidate", "Metadata term", "false positive"):
            self.assertNotIn(gone, f1)

    def test_s4_lists_ml_adjacent(self):
        # Prompt 093: the 134-report list moved from the Table S4 PDF to the ML_ADJACENT sheet of the Table S5 workbook.
        from openpyxl import load_workbook
        wb = load_workbook(ROOT / "manuscript/bmc_supplementary_data1.xlsx", read_only=True)  # Prompt 097: Additional Data 1
        sheet = [n for n in wb.sheetnames if "ADJACENT" in n.upper()]
        self.assertEqual(len(sheet), 1)
        self.assertEqual(sum(1 for _ in wb[sheet[0]].iter_rows(min_row=2)), 101)  # Prompt 106
        with fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S04_Eligibility_boundary_and_study_family_decisions.pdf") as d:
            text = " ".join(" ".join(pg.get_text() for pg in d).split()).replace("\u2011", "-")
        self.assertNotIn("NR | kci", text)

if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
