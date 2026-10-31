#!/usr/bin/env python3
"""Prompt 090: claim-ordered Results, eight main figures, claim-evidence synthesis."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8")
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8")
SYN = json.loads((ROOT / "results/derived/claim_evidence_synthesis.json").read_text(encoding="utf-8"))
# Prompt 093 (review v31 section 4.2): eight main figures became five.
# Prompt 094 (review v32): the four claim-ordered figures were replaced by five practice figures (Figures 2-6).
FIGS = ["fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"]  # Prompt 100: four figures after PRISMA; five since prompt 107  # Prompt 107  # prompt 112


def results(tex, start, end):
    return tex[tex.index(start):tex.index(end)]


def body(tex):
    return tex[tex.index("\\begin{document}"):]


class ClaimOrderedResults(unittest.TestCase):
    def test_results_headings_follow_claim_types(self):
        en = re.findall(r"\\subsection\{([^}]*)\}", results(EN, "\\section{Results}", "\\section{Discussion}"))
        # Prompt 093 (review v31 section 4.3): one claim and one figure per subsection.
        # Prompt 094 (review v32): Results follow how ML was used and how practice matured.
        self.assertEqual(en, ["Study Selection", "How Machine Learning Was Used", "Variable Importance as the Main Product", "What the Rankings Named", "Practices That Became More Common", "Ranking Stability, Survey Design and Preprocessing"])  # Prompt 100: forward headings  # Prompt 099: testbed is a paragraph of the Figure 2 section  # Prompt 097 (review v35)  # prompt 109  # prompt 112
        ko = re.findall(r"\\subsection\{([^}]*)\}", results(KO, "\\section{결과}", "\\section{고찰}"))
        self.assertEqual(len(ko), 6)  # Prompt 100: five Results subsections  # prompt 112

    def test_main_figures_in_order(self):
        for tex, suffix in ((EN, ""), (KO, "_ko")):
            graphics = re.findall(r"figs/(fig\d+_[a-z_]+?)(?:_ko)?\.pdf", body(tex))
            self.assertEqual(graphics, ["fig1_prisma"] + FIGS)
            for stem in FIGS:
                self.assertTrue((ROOT / "figures/submission" / f"{stem}{suffix}.pdf").exists())

    def test_no_dangling_old_figure_labels(self):
        for label in ("data-use", "evidence-support", "probast-ai", "variable-interpretation", "publication",
                      "analytic-function", "nonclassification", "problem", "dataset-preparation",
                      "algorithm-development", "evaluation"):
            self.assertNotIn("ref{fig:%s}" % label, EN)
            self.assertNotIn("ref{fig:%s-ko}" % label, KO)
        self.assertNotIn("Figure 6--12", KO)

    def test_synthesis_numbers(self):
        claims = {c["claim"]: (c["studies_making_claim"], c["studies_with_required_evidence"]) for c in SYN["claims"]}
        self.assertEqual(claims, {"classification": (192, 15), "interpretation": (81, 15), "association": (19, 4),  # Prompt 106
                                  "policy": (48, 15), "individual": (65, 5)})  # Prompt 106
        self.assertEqual(SYN["studies_with_all_claims_supported"], 4)  # Prompt 106
        self.assertEqual((SYN["studies_with_purpose_or_use_claims"], SYN["studies_with_all_purpose_or_use_claims_supported"]), (138, 12))  # Prompt 106
        self.assertEqual(sum(SYN["use_composition"].values()), 250)  # Prompt 106
        self.assertEqual(SYN["method_claims"]["development"]["beyond_single_knhanes_application"], 4)  # Prompt 106
        self.assertEqual(SYN["method_claims"]["comparison"]["uncertainty_or_paired_comparison"], 1)
        self.assertEqual(len(SYN["studies"]), 192)  # Prompt 106

    def test_headline_numbers_in_text(self):
        # Prompt 091 replaced the "3 of 165" headline with "none of the 120 ... beyond classification".
        # Prompt 093 dropped the "3 of 165" clause from the abstract; it stays in Results.
        # Prompt 094 (review v32): claim-evidence counts removed; the 12-of-165 rebuild count and practice counts remain.
        # Prompt 096 (review v34): the reproducibility sentence moved to Maturing Practice ("all three ... in 12").
        self.assertIn("15 (8%)", " ".join(fitz.open(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S03_Outcome_and_predictor_construction.pdf")[0].get_text().split()))  # Prompt 101: rebuild count in Figure S4D and Table 1  # Prompt 102: now S2D  # Prompt 106  # prompt 110
        for phrase in ("25 of the 192 studies checked their ranking in all", "9 reported using them in model fitting"):  # prompt 113  # Prompt 101  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 109
            self.assertIn(phrase, " ".join(EN.split()))
        for phrase in ("보고서로 결과변수 재구성 가능", "\\suppfig{2}"):  # Prompt 104: rebuildability is S2B  # prompt 109
            self.assertIn(phrase, " ".join(KO.split()))

    def test_sentence_requests(self):
        # Prompt 094 (review v32): keywords per review v32 ("research purpose" removed).
        self.assertIn("variable importance, SHAP", EN)
        self.assertNotIn("research purpose", EN[EN.index("\\keywords{"):EN.index("\\title[From")])
        self.assertNotIn("in the screening ledger;", EN)
        self.assertNotIn("objective anchors", EN)
        # Prompt 093 moved the combined-item sentence to Table S7 (review v31 section 4.5).
        self.assertIn("Registration, data and code availability", " ".join(" ".join(p.get_text() for p in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))
        self.assertNotIn("For example, one final model developed", EN)
        # Prompt 093 shortened the Discussion (2,050 -> 1,300 words); the AUROC sentence was removed with it.
        self.assertNotIn("These findings describe the formation", EN)
        self.assertIn("\\cite{probastplus2025}", EN)
        self.assertIn("dhiman2022methodological", EN)
        self.assertIn("\\setcounter{secnumdepth}{0}", EN)
        self.assertNotIn("Not separately assessed", EN)
        # Prompt 093: Table 1 lost its observed column (values are in Figure 5B); 1/10 is stated in Results.
        self.assertIn("one reported uncertainty or a paired comparison", " ".join(" ".join(pg.get_text() for pg in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))  # Prompt 100: 1-of-10 fact in the Figure S6 caption

    def test_abstract_word_limit(self):
        doc = fitz.open(ROOT / "manuscript/bmc_main.pdf")
        text = re.sub(r"-\n", "", doc[0].get_text() + doc[1].get_text())
        abstract = text[text.index("Background:"):text.index("Keywords")]
        words = [w for line in abstract.splitlines() if not re.fullmatch(r"\s*\d+\s*", line) for w in line.split()]
        self.assertLessEqual(len(words), 350)

    def test_no_internal_codes_in_body(self):
        for tex in (EN, KO):
            b = re.sub(r"(?m)^%.*$", "", body(tex))
            self.assertIsNone(re.search(r"\b(KHM\d{3}|REP\d\d|OUT\d\d|PRE\d\d|FUN_[A-Z]+)\b", b))
            self.assertIsNone(re.search(r"(LLM|language model)[^.\n]{0,40}(verif|assist|check)", b))


if __name__ == "__main__":
    unittest.main()
