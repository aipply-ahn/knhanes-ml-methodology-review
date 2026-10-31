"""Prompt 089: analysis-centred positioning, claim-evidence wording, plain denominators, Table 1 counts."""
from pathlib import Path
import re
import sys
import unittest

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_prompt_087 import abstract_words  # noqa: E402
from test_prompt_088 import body  # noqa: E402


class Prompt089(unittest.TestCase):
    def setUp(self):
        self.en = body((ROOT / "manuscript/bmc_main.tex").read_text())
        self.ko = body((ROOT / "manuscript/bmc_main_ko.tex").read_text())

    def test_title_and_position(self):
        # Prompt 094 (review v32): new title; the analysis-tool position is kept in the Background and the Korean abstract.
        self.assertIn("From Classification to Explanation: A Systematic", self.en)  # Prompt 106
        self.assertIn("분류에서 설명으로: 국가 건강조사의 지도학습 머신러닝", self.ko)  # Prompt 106
        self.assertIn("ML is often used to classify a current health state", self.en)  # Prompt 096 (review v34): Background no longer states the result in advance
        self.assertIn("그 분류가 의존하는 변수의 순위를 내는 데에도", " ".join(self.ko.split()))  # prompt 113  # Prompt 096 (review v34): message-revision Conclusions
        self.assertNotIn("analysis-oriented", self.en)

    def test_cohort_prediction_framing_removed(self):
        for token in ("future-event", "rather than predicting future", "linkage to\nmortality",
                      "supports linkage", "available but unused", "Future-event prediction remains possible",
                      "absence of future-event outcomes"):
            self.assertNotIn(token, self.en)
        for token in ("미래사건", "사망 및\n국민건강보험", "활용되지 않은 기회"):
            self.assertNotIn(token, self.ko)
        with fitz.open(ROOT / "figures/submission/fig3_classification_evidence.pdf") as doc:  # prompt 093 numbering
            self.assertNotIn("future", doc[0].get_text().lower())

    def test_symbols_and_work_terms_removed(self):
        for token in ("U_{dev}", "U_{eval}", "N_{app}", "packets", "ART002908025", "ART003146879",
                      "non-candidate", "four-state", "extraction\ndisagreements"):
            self.assertNotIn(token, self.en)
        for token in ("U_{\\mathrm{dev}}", "N_{\\mathrm{app}}", "패킷", "ART00", "후보 미지정", "네 상태"):
            self.assertNotIn(token, self.ko)
        # Prompt 093 (review v31 section 4.5): "Proportions are given with named denominators."
        self.assertIn("Proportions are given with named denominators", " ".join(self.en.split()))

    def test_definitions_and_denominators(self):
        # Prompt 090 moved these definitions into "Evidence required for each claim" and the claim-ordered Results.
        flat = " ".join(self.en.split())
        # Prompt 094 (review v32): claim definitions left with purpose coding; the 25/129 stability value is unchanged.
        self.assertIn("25 of the 192 studies checked their ranking in all", flat)  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109
        self.assertIn("Checks of ranking stability rose in every period, from 2 of 45 through 2019 to 12 of 53", " ".join(self.en.split()))  # Prompt 100: Practices That Became More Common (Figure 4B)  # Prompt 106  # Prompt 107  # prompt 109
        self.assertIn("We did not code authors' aims or proposed uses.", self.en)  # Prompt 094 (review v32)
        self.assertIn("The author made all screening and eligibility decisions", self.en)
        self.assertIn("mostly in studies published in 2026 (12 each, against 2 and 5 of the 31 published in 2025", flat)  # Prompt 100: forward wording  # Prompt 107  # prompt 109  # prompt 110  # prompt 112
        self.assertLessEqual(self.en.count("increasingly common"), 1)  # prompt 119: abstract only (review v54)

    def test_table1_observed_column(self):
        # Prompt 093: Table 1 is a three-column rule table in Methods; observed values moved to Figure 5B.
        # Prompt 094 (review v32): Table 1 is the recommended-practice table with an observed-adoption column.
        self.assertIn("All (N=192)", self.en)  # Prompt 107  # prompt 109
        table = self.en[self.en.index("\\label{tab:recommended-practice}"):self.en.index("\\end{tabularx}")]
        for token in ("154 (80.2)", "12 (22.6)", "9 (4.7)", "17 (8.9)", "97 (50.5)"):  # Prompt 106  # Prompt 107  # prompt 109
            self.assertIn(token, table)

    def test_fig7_before_split(self):
        with fitz.open(ROOT / "figures/submission/fig7_predictor_training.pdf") as doc:
            text = doc[0].get_text()
        for token in ("32", "91", "104"):  # Prompt 106
            self.assertIn(token, text)
        # Prompt 093: the 83/165 finding is stated with main Figure 3B.
        self.assertIn("96 performed at least one step before the data were split", " ".join(self.en.split()))  # Prompt 099: Figure 6C summary row  # Prompt 106  # Prompt 107

    def test_abstract_and_logs(self):
        _, n = abstract_words(ROOT / "manuscript/bmc_main.pdf")
        self.assertLessEqual(n, 350)
        for name in ("bmc_main", "bmc_main_ko"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")

    def test_locked_preamble(self):
        import tarfile
        rec = ROOT / "prompts/implementation_records/prompt_089/before.tar.gz"
        with tarfile.open(rec) as t:
            for name in ("manuscript/bmc_main.tex", "manuscript/bmc_main_ko.tex"):
                old = t.extractfile(name.replace("manuscript/", "paper/", 1)).read().decode().split("\\begin{document}")[0]
                self.assertEqual(old, (ROOT / name).read_text().split("\\begin{document}")[0])


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
