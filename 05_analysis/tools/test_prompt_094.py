#!/usr/bin/env python3
"""Prompt 094 (review v32): ML use and maturing practice instead of claim-evidence framing."""
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
from test_prompt_093 import section, supp_text, words  # noqa: E402

EN = body((ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8"))
KO = body((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8"))
EN_FULL = (ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8")
PT = json.loads((ROOT / "results/derived/practice_trends_094.json").read_text(encoding="utf-8"))
MAIN = ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"]  # Prompt 100: four figures after PRISMA; Figure 2 split  # Prompt 107  # prompt 112
PERIODS = [32, 32, 52, 49]


class Calculations(unittest.TestCase):
    """The four [S7 calculation] items of review v32 section 7."""

    def test_period_denominators(self):
        self.assertEqual(PT["period_n"], PERIODS)

    def test_practice_series(self):
        p = PT["practices"]
        self.assertEqual(p["boosting"], [1, 15, 34, 42])
        self.assertEqual(p["validation_beyond_development"], [5, 5, 10, 18])
        self.assertEqual(p["calibration"], [1, 2, 3, 14])
        self.assertEqual(p["code_link"], [1, 2, 6, 8])
        self.assertEqual(p["importance_ranking"], [17, 22, 44, 46])
        self.assertEqual(p["shap"], [0, 6, 17, 34])
        self.assertEqual(PT["stability_among_ranking"], [2, 3, 8, 12])
        self.assertEqual(PT["importance_ranking_total"], 129)

    def test_preprocessing_trend(self):
        # Review v32 [S7]: the before-split share fell in every period, so the period values are reported
        # in the Abstract and Figure 4 (plotted as studies with no step before the split).
        before = PT["any_step_before_split"]
        self.assertEqual(before, [18, 17, 27, 21])
        self.assertEqual(PT["any_step_before_split_total"], 83)
        share = [b / n for b, n in zip(before, PERIODS)]
        self.assertEqual(share, sorted(share, reverse=True))
        # Prompt 095 (review v33): "no step before the split" mixes in unclear timing, so it left the abstract and Figure 4; the
        # before-split fall is stated in Next Steps and the positive indicator is Figure 6D.
        flat = " ".join(EN.split())
        # Prompt 096 (review v34): the "fell" sentence was removed (the fall moved into unclear timing; Supplementary Figure S6E).
        self.assertIn("96 performed at least one step before the data were split", flat)  # Prompt 099: summary-row wording  # Prompt 106  # Prompt 107
        self.assertNotIn("split fell from 18 of 32", flat)
        with fitz.open(ROOT / "figures/submission/fig7_next_steps.pdf") as d:  # Prompt 100: former Figure 6  # Prompt 107  # prompt 112
            # Prompt 096 (review v34): the flat preprocessing line left Figure 6; Figure 6A shows stability by period.
            self.assertIn("Across survey cycles", d[0].get_text())  # Prompt 099: stability trend (2/17 -> 12/46) moved to Figure 5


class MainText(unittest.TestCase):
    def test_title_and_keywords(self):
        flat = " ".join(EN_FULL.split())
        self.assertIn("From Classification to Explanation: A Systematic Methodological Review of Supervised Machine Learning in a National Health Survey", flat)  # Prompt 106
        ko = " ".join((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8").split())
        ko_title = ko[ko.index("\\title{"):ko.index("}", ko.index("\\title{"))]
        self.assertNotIn(".", ko_title)  # colon form, no full stop inside the title
        kw = EN_FULL[EN_FULL.index("\\keywords{"):EN_FULL.index("}", EN_FULL.index("\\keywords{"))]
        self.assertNotIn("research purpose", kw)
        for k in ("variable importance", "SHAP", "complex survey design", "reporting guideline"):  # Prompt 096 (review v34): message-revision keywords
            self.assertIn(k, " ".join(kw.split()))

    def test_six_figures(self):
        for tex, suffix in ((EN, ""), (KO, "_ko")):
            graphics = [g.removesuffix("_ko") for g in re.findall(r"figs/([A-Za-z0-9_]+)\.pdf", tex)]
            self.assertEqual(graphics, MAIN)
            for stem in MAIN:
                self.assertTrue((ROOT / "figures/submission" / f"{stem}{suffix}.pdf").exists(), stem)
        for old in ("fig2_use_and_claims", "fig3_classification_evidence", "fig4_further_claims", "fig5_claim_evidence"):
            self.assertNotIn(old, EN + KO)

    def test_results_and_discussion_structure(self):
        res = re.findall(r"\\subsection\{([^}]*)\}", section(EN, "\\section{Results}", "\\section{Discussion}"))
        self.assertEqual(res, ["Study Selection", "How Machine Learning Was Used", "Variable Importance as the Main Product", "What the Rankings Named", "Practices That Became More Common", "Ranking Stability, Survey Design and Preprocessing"])  # Prompt 100: forward headings  # prompt 109  # prompt 112
        dis = re.findall(r"\\subsection\{([^}]*)\}", section(EN, "\\section{Discussion}", "\\section{Conclusions}"))
        # Prompt 096 (review v34): new "Prediction Standards and Explanation Studies"; "Toward Reporting Guidance" merged into Next Steps.
        self.assertEqual(dis[:5], ["Principal Findings", "Explanation as the Main Product", "Reuse and Comparison of Results",  # Prompt 101: Discussion follows Results  # prompt 109  # prompt 111
                                   "Stable and Representative Explanations", "Prediction Standards and Explanation Standards"])  # Prompt 102: three steps  # prompt 111
        self.assertEqual(len(re.findall(r"\\subsection\{", section(KO, "\\section{결과}", "\\section{고찰}"))), 6)  # Prompt 100: five Results subsections  # prompt 112

    def test_recommended_practice_table_in_discussion(self):
        self.assertIn("\\label{tab:recommended-practice}", section(EN, "\\section{Results}", "\\section{Discussion}"))  # prompt 109
        self.assertIn("\\label{tab:recommended-practice-ko}", section(KO, "\\section{결과}", "\\section{고찰}"))  # prompt 109
        self.assertNotIn("tab:purpose-framework", EN + KO)

    def test_claim_framing_removed(self):
        # The one intended mention states that aims and proposed uses were not coded (review v32 section 3).
        self.assertIn("We did not code authors' aims or proposed uses.", EN)
        en = EN.replace("We did not code authors' aims or proposed uses.", "")
        # Prompt 096 (review v34): "requirement" now names the stability and representativeness requirements of an explanation
        # (message revision); claim/proposed-use/stated-purpose framing stays excluded.
        for w in ("claim", "proposed use", "stated purpose"):
            self.assertIsNone(re.search(r"\b" + w, en, re.I), w)
        for w in ("주장", "제안 용도", "명시 목적"):
            self.assertNotIn(w, KO)

    def test_word_counts(self):
        self.assertLessEqual(words(section(EN, "\\section{Discussion}", "\\section{Conclusions}")), 1300)
        _, n = abstract_words(ROOT / "build/submission/bmc_main.pdf")
        self.assertLessEqual(n, 350)

    def test_citation_order(self):
        for tex in (EN, KO):
            seq = []
            for m in re.finditer(r"\\supp(tab|fig)\{(\d+)\}", tex):
                k = (m.group(1), int(m.group(2)))
                if k not in seq:
                    seq.append(k)
            self.assertEqual([n for t, n in seq if t == "tab"], list(range(1, 9)))
            self.assertEqual([n for t, n in seq if t == "fig"], list(range(1, 9)))  # Prompt 099: eight supplementary figures

    def test_figure_placement_and_logs(self):
        for pdf, heading in (("bmc_main.pdf", "Discussion"), ("bmc_main_ko.pdf", "고찰")):
            with fitz.open(ROOT / "build/submission" / pdf) as d:
                pages = [p.get_text() for p in d]
            figs = {int(m.group(1)): i for i, t in enumerate(pages) for m in re.finditer(r"^(?:Fig\.|그림) ?(\d+)\b", t, re.M)}
            self.assertEqual(sorted(figs), [1, 2, 3, 4, 5, 6, 7], pdf)  # Prompt 100: five main figures; six since prompt 107  # Prompt 107  # prompt 112
            head = next(i for i, t in enumerate(pages) if re.search(r"^" + heading + r"\s*$", t, re.M))
            self.assertLessEqual(max(figs.values()), head, pdf)
        for name in ("bmc_main", "bmc_main_ko", "bmc_supplementary"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")

    def test_figure_numbers(self):
        with fitz.open(ROOT / "figures/submission/fig6_maturing_practice.pdf") as d:  # prompt 112
            f4 = d[0].get_text()  # Prompt 107
        # Prompt 095 (review v33): boosting moved out of Figure 4 (algorithm choice, stated in How ML Was Used and Figure S6B).
        for token in ("1/45", "6/45", "17/53", "14/53", "8/53"):  # Prompt 106
            self.assertIn(token, f4)
        self.assertIn("42 of 53 in 2025--2026", " ".join(EN.split()))  # Prompt 106
        with fitz.open(ROOT / "figures/submission/fig5_rankings_named.pdf") as d:  # prompt 112
            f3 = d[0].get_text()  # Prompt 107
        for token in ("16", "Kim 2026", "31"):  # prompt 110  # prompt 112
            self.assertIn(token, f3)


class Colours(unittest.TestCase):
    def test_no_red_in_figure_sources(self):
        for f in ("make_main_figures.py", "make_supplementary_figures.py"):
            src = (ROOT / "tools" / f).read_text(encoding="utf-8")
            self.assertNotRegex(src, r"color=VERM|#D55E00|\"red\"|'red'", f)


class Supplement(unittest.TestCase):
    def test_structure(self):
        with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
            self.assertLessEqual(len(d), 21)  # Prompt 099: S2 regained a panel and S7 was added
            names = [t[1].split(".")[0] for t in d.get_toc()]
        self.assertEqual(names, [f"Supplementary Table S{n}" for n in range(1, 6)] + [f"Supplementary Figure S{n}" for n in range(1, 9)] + ["Supplementary Table S6", "Supplementary Table S7", "Supplementary Table S8"])  # Prompt 097 (review v35): citation order; workbook is Additional Data 1

    def test_purpose_and_claim_coding_removed(self):
        text = supp_text()
        for gone in ("Stated purpose", "Proposed use", "Part C", "Evidence required for each claim", "claim"):
            self.assertNotIn(gone, text)

    def test_verification_row_keeps_output_rechecks(self):
        with fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S07_Verification_results.pdf") as d:  # Prompt 097: renumbered
            text = " ".join(" ".join(p.get_text() for p in d).split())
        self.assertNotIn("Purpose, output and use", text)
        self.assertIn("12", text)

    def test_captions_point_to_main_figures(self):
        text = supp_text()
        self.assertNotIn("shown in Figure 2 of the main text", text)  # Prompt 097 (review v35): no cross-reference sentences in legends
        self.assertNotIn("Figure 6B of the main text", text)  # Prompt 097 (review v35): legends carry no cross-reference sentences


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
