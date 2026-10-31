#!/usr/bin/env python3
"""Prompt 113 (external publishability review): Table S7 re-read steps with their units, Table S8 as ten illustrative
studies with the full list in Additional Data 1, Figure 1 retrieval statement, single-tree sensitivity analysis,
ranking x survey design, 2025/2026, length-matched agreement, PROBAST+AI count, and the revised claims (4.1, 4.2, 7.1-7.3)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
O = json.loads((ROOT / "results/derived/practice_trends_113.json").read_text())


def norm(t):
    return " ".join(t.split())


def pdf_text(path):
    import fitz
    with fitz.open(path) as d:
        return norm(" ".join(pg.get_text() for pg in d))


class Prompt113(unittest.TestCase):
    def test_values(self):
        s = O["sensitivity_without_added_113"]
        self.assertEqual((s["added_studies"], s["added_core"]), (32, 27))
        w = s["without_added"]
        self.assertEqual((w["n"], w["stability"], w["weights_in_fitting"], w["weights_in_evaluation"], w["strata_or_psu"],
                          w["preprocessing_all_within"]), (165, 25, 6, 5, 14, 15))
        self.assertEqual(s["added_only"]["strata_or_psu"], 14)
        self.assertEqual((s["by_period_without_added"]["period_n"][0], s["by_period_without_added"]["ranking"][0],
                          s["by_period_without_added"]["period_n"][3], s["by_period_without_added"]["ranking"][3]), (33, 18, 48, 45))
        r = O["ranking_by_design_113"]
        self.assertEqual((r["ranking"]["stability"], r["ranking"]["weights_in_fitting"], r["ranking"]["weights_in_evaluation"],
                          r["ranking"]["strata_or_psu"], r["ranking"]["preprocessing_all_within"]), (25, 9, 7, 26, 14))
        self.assertEqual((r["no_ranking"]["weights_in_fitting"], r["ranking_stability_and_weights_in_fitting"]), (0, 1))
        y = O["years_2025_2026_113"]
        self.assertEqual((y["2025"]["ranking"], y["2025"]["shap"], y["2026"]["ranking"], y["2026"]["shap"]), (27, 15, 22, 18))
        a = O["agreement_similar_length_113"]
        self.assertEqual((round(a["same_outcome"]["median"], 2), round(a["different_topic"]["median"], 2)), (0.33, 0.2))
        self.assertEqual(O["probast_overall_113"]["PE_OVERALL"], {"HIGH": 375, "UNC": 1, "LOW": 2})
        o112 = json.loads((ROOT / "results/derived/practice_trends_112.json").read_text())
        self.assertTrue(all(O[k] == v for k, v in o112.items()))

    def test_text_en(self):
        en = norm(EN)
        for tok in ("applying at least one supervised learning algorithm outside the regression family",
                    "9 reported using survey weights in model fitting and 7 in evaluation, and 17 reported keeping every preprocessing step",
                    "supervised ML has increasingly been used not only to classify contemporaneously measured health states but also to identify the variables on which these classifications depend",
                    "In this review, an explanation means such model-based variable importance.",
                    "the main practices were recomputed without the core studies it added",
                    "cannot be reconstructed from the retained records",
                    "249 of the 250 included studies were assessed in full text",
                    "\\supptab{8} illustrates the records for ten studies",
                    "IDs in Additional Data~1; distinct variables",
                    "all 22 studies published in 2026 produced a ranking and 18 used SHAP, against 27 and 15 of the 31 published in 2025",
                    "the share rose from 18 of 33 to 45 of 48",
                    
                    "so the counts are of studies reporting it",
                    "it marks a leakage risk, not confirmed leakage",
                    "9 reported using them in model fitting",
                    "all nine studies weighting the fit produced a ranking, and one of them also checked its stability",
                    "except strata or primary sampling units (8.5\\%), which 14 of the 27 used",
                    "None of these makes a ranking reliable by itself",
                    "describes what a model relies on, not a causal effect",
                    "PROBAST+AI rated 375 of the 378 model evaluations",
                    "may also have intended a diagnostic prediction model",
                    "left the main shares similar except strata use"):
            self.assertIn(tok, en, tok)
        for gone in ("has become an explanation tool", "rather than for predicting future events", "supervised, non-regression ML",
                     "listed with their DOIs and main characteristics in \\supptab{8}", "IDs in Supplementary Table S8",
                     "explaining them through variable importance", "nearly all evaluations"):
            self.assertNotIn(gone, en, gone)

    def test_text_ko(self):
        ko = norm(KO)
        for tok in ("회귀 계열 밖의 지도학습 알고리즘을 하나 이상 적용한", "썼다고 보고했으며", "이 검토에서 설명은 이런 모형 기반 변수중요도를 뜻한다",
                    "남은 기록으로 복원할 수 없다", "포함 연구 250편 중 249편은 전문으로 평가했다", "그중 10편의 기록을 예시로",
                    "연구 ID는 추가자료~1", "2026년 출판 22편은 모두 순위를 산출했고 18편이 SHAP을", "33편 중 18편에서 48편 중 45편으로",
                    "정보 누출의 위험을 뜻할 뿐", "적합에 가중치를 쓴 9편은 모두 순위를 산출했고", "8.5\\%로 낮아졌다",
                    "인과 효과를 뜻하지는 않는다", "모형평가 378개 중 375개", "진단 예측모형", "두드러진 산출물이 되었다"):
            self.assertIn(tok, ko, tok)
        for gone in ("설명 도구가 되었다", "설명하는 도구가 되었다", "보충표 S8, 괄호는", "하지 않은 것으로 셌다"):
            self.assertNotIn(gone, ko, gone)

    def test_supplement(self):
        s7 = (ROOT / "manuscript/supplementary/tex/Supplementary_Table_S07_Verification_results.tex").read_text()
        s7 = norm(s7.replace("\\allowbreak{}", ""))
        for tok in ("step 1: items flagged", "406 flagged items in 120 records: 284 consistency flags", "step 2: item decisions",
                    "123 records (120 flagged + 3 from the third scan)",
                    "649 item decisions in 123 records: 519 on flagged items, 116 on dependent items", "413 values changed (95 records); 236 confirmed",
                    "step 3: checks rerun", "140 flags in 69 records: 92 list conditional items only; 48 in 26 records",
                    "222 = 217 that remain among the 250 included studies + 3 removed", "one flagged item can yield several decisions"):
            self.assertIn(tok, s7, tok)
        s8 = norm((ROOT / "manuscript/supplementary/tex/Supplementary_Table_S08_Included_studies.tex").read_text().replace("\\allowbreak{}", "").replace("\\-", ""))
        self.assertIn("Characteristics of ten illustrative included studies", s8)
        self.assertIn("is listed in Additional Data 1.", s8)  # prompt 114
        supp = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")
        self.assertNotIn("Characteristics of the 250 included studies", supp)
        self.assertNotIn("Study IDs: Table S8", supp)
        import openpyxl
        wb = openpyxl.load_workbook(ROOT / "manuscript/supplementary/tables/Supplementary_Data_1_Study_level_dataset.xlsx", read_only=True)
        self.assertIn("SENSITIVITY_ANALYSES", wb.sheetnames)
        rows = list(wb["SENSITIVITY_ANALYSES"].iter_rows(values_only=True))
        wb.close()
        self.assertEqual(rows[1][:3], ("Studies", "192", "165"))

    def test_pdfs(self):
        en = pdf_text(ROOT / "manuscript/bmc_main.pdf")
        self.assertIn("Characteristics of ten illustrative included studies", en)
        self.assertIn("375 of the 378 model evaluations", en.replace("- ", ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
