#!/usr/bin/env python3
"""Prompt 093 (review v31): supplement 130 -> ~25 pages, five main figures, shorter prose, detail fixes."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import fitz
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_prompt_087 import abstract_words  # noqa: E402
from test_prompt_088 import body  # noqa: E402

EN = body((ROOT / "manuscript/bmc_main.tex").read_text(encoding="utf-8"))
KO = body((ROOT / "manuscript/bmc_main_ko.tex").read_text(encoding="utf-8"))
SYN = json.loads((ROOT / "results/derived/claim_evidence_synthesis.json").read_text(encoding="utf-8"))
# Prompt 094 (review v32): six practice figures replaced the five claim-ordered figures.
MAIN = ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"]  # Prompt 100: rankings figure merged into Figure 3; maturing Figure 4; next steps Figure 5; Figure 2 split  # Prompt 107  # prompt 112


def words(tex):
    tex = re.sub(r"\\begin\{(figure|table)\}.*?\\end\{\1\}", "", tex, flags=re.S)
    tex = re.sub(r"\\(cite|supptab|suppfig|ref|label)\{[^}]*\}", "X", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?", "", tex)
    return len(re.sub(r"[{}~]", " ", tex).split())


def section(tex, a, b):
    return tex[tex.index(a):tex.index(b)]


def supp_text():
    with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
        return " ".join(" ".join(p.get_text() for p in d).split()).replace("\u2011", "-")


class Supplement(unittest.TestCase):
    def test_length_and_order(self):
        with fitz.open(ROOT / "manuscript/bmc_supplementary.pdf") as d:
            self.assertLessEqual(len(d), 32)
            names = [t[1].split(".")[0] for t in d.get_toc()]
        self.assertEqual(names, [f"Supplementary Table S{n}" for n in range(1, 6)] + [f"Supplementary Figure S{n}" for n in range(1, 9)] + ["Supplementary Table S6", "Supplementary Table S7", "Supplementary Table S8"])  # Prompt 097 (review v35): citation order; workbook is Additional Data 1

    def test_no_internal_traces(self):
        text = supp_text()
        for token in ("data/protocol_v1_2", "P2_work", "prisma_reader_revision", "source_audit.json", "seed 20260917",
                      "TOPIC_CROSSWALK", "S7/", "PD_OVERALL", "NO_ML_EVIDENCE_IN_ABSTRACT", "Do not silently repair",
                      "Figure 9 counts", "historical §15", "retained locally", "Local release bundle", "repository scripts",
                      "Methods: Data Extraction", "Methods: Synthesis;", "Methods—Screening", "KHM001-EV"):
            self.assertNotIn(token, text, token)
        self.assertNotRegex(text, r"\b(OUT|VAL|REP|PRD|THR|SUR)\d\d\b")

    def test_verification_results_table(self):
        with fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S07_Verification_results.pdf") as d:  # Prompt 097: renumbered
            text = " ".join(" ".join(p.get_text() for p in d).split())
        for token in ("413 values changed", "236 confirmed", "140 flags",  # prompt 113
                       "not recorded", "2 grades changed",
                      "that remain among the 250 included studies + 3 removed under the final criterion + 1 report excluded", "1 preprint",  # prompt 113
                       "merged into its journal article",  # Prompt 097: footnote wording  # Prompt 106
                      "held by the author"):
            self.assertIn(token, text)
        self.assertNotIn("Record", text.split("Stage")[1][:120])

    def test_rules_table(self):
        with fitz.open(ROOT / "manuscript/supplementary/pdf/Supplementary_Table_S06_Human_verification_protocol.pdf") as d:  # Prompt 097: renumbered
            self.assertLessEqual(len(d), 6)
            text = " ".join(" ".join(p.get_text() for p in d).split())
        for token in ("A. Procedure and response states", "B. Coding rules that produce the reported results",
                      "Decision rule", "answers a health question"):  # Prompt 097 (review v35): workbook-column column removed
            self.assertIn(token, text)

    def test_workbook_sheets(self):
        wb = load_workbook(ROOT / "manuscript/bmc_supplementary_data1.xlsx", read_only=True)  # Prompt 097: Additional Data 1
        for sheet, rows in (("VARIABLE_DICTIONARY", 159), ("ML_ADJACENT_REPORTS", 102), ("STUDIES", 251)):  # Prompt 106
            self.assertEqual(wb[sheet].max_row, rows, sheet)
        for sheet in ("PROTOCOL_ITEMS", "PROTOCOL_RESPONSE_CODES", "ASSESSMENT_SCOPE", "ASSESSMENT_VALIDATION_SURVEY",
                      "ASSESSMENT_APPRAISAL", "ASSESSMENT_RECOVERY_VS_REPORTING", "ASSESSMENT_SOURCE_RECHECKS"):
            self.assertIn(sheet, wb.sheetnames)
        wb.close()
        self.assertFalse((ROOT / "manuscript/bmc_supplementary_table_s7.xlsx").exists())

    def test_prisma_locations(self):
        text = supp_text()
        self.assertIn("Methods: Supporting Assessments", text)
        self.assertIn("coding rules in Supplementary Table S6", text)  # Prompt 097: renumbered
        self.assertIn("analysis code not yet publicly deposited", text)


class MainText(unittest.TestCase):
    def test_five_figures_and_table_in_methods(self):
        for tex, suffix in ((EN, ""), (KO, "_ko")):
            graphics = re.findall(r"figs/(fig\d_[a-z_]+?)(?:_ko)?\.pdf", tex)
            self.assertEqual(graphics, MAIN)
            for stem in MAIN:
                self.assertTrue((ROOT / "figures/submission" / f"{stem}{suffix}.pdf").exists())
        # Prompt 094 (review v32): Table 1 is the recommended-practice table in the Discussion.
        self.assertIn("\\label{tab:recommended-practice}", section(EN, "\\section{Results}", "\\section{Discussion}"))  # prompt 109
        self.assertIn("\\label{tab:recommended-practice-ko}", section(KO, "\\section{결과}", "\\section{고찰}"))  # prompt 109

    def test_results_headings(self):
        heads = re.findall(r"\\subsection\{([^}]*)\}", section(EN, "\\section{Results}", "\\section{Discussion}"))
        self.assertEqual(heads, ["Study Selection", "How Machine Learning Was Used", "Variable Importance as the Main Product", "What the Rankings Named", "Practices That Became More Common", "Ranking Stability, Survey Design and Preprocessing"])  # Prompt 100: forward headings  # prompt 109  # prompt 112
        self.assertEqual(len(re.findall(r"\\subsection\{", section(KO, "\\section{결과}", "\\section{고찰}"))), 6)  # Prompt 100: five Results subsections  # prompt 112

    def test_word_counts(self):
        self.assertLessEqual(words(section(EN, "\\section{Discussion}", "\\section{Conclusions}")), 1300)
        self.assertLessEqual(words(section(EN, "\\section{Results}", "\\section{Discussion}")), 1400)
        self.assertLessEqual(words(section(EN, "\\section{Background}", "\\section{Conclusions}")) + 200, 4700)
        _, n = abstract_words(ROOT / "build/submission/bmc_main.pdf")
        self.assertLessEqual(n, 350)  # Prompt 094 (review v32): the v32 abstract text is set at the 350-word BMC limit

    def test_unsupported_and_conflicting_sentences_removed(self):
        for gone in ("The further a study's claims went beyond classification", "depends less on its algorithm",
                     "KNHANES was the primary analysis dataset in 165", "Individual studies include applications to osteoporosis",
                     "supplemented algorithm comparison with variable interpretation", "External validation or transport (38)",
                     "\\subsection{An Analysis-Centred Use Profile", "the 3 of 165 studies that did so made only the"):
            self.assertNotIn(gone, EN)
        self.assertNotIn("주장이 분류를 넘어설수록", KO)
        self.assertNotIn("220편 중 165편에서 주 분석자료", KO)
        pct = [v["percent"] for v in SYN["requirement_fulfilment_by_claim_count"].values()]
        self.assertEqual(pct, [7.4, 12.5, 16.0, 14.3])  # Prompt 106
        self.assertNotEqual(pct, sorted(pct, reverse=True))

    def test_headline_kept(self):
        # Prompt 094 (review v32): claim headlines removed; the author-locked period-connector wording is kept (Figure 4 caption).
        self.assertIn("\\subsection{Variable Importance as the Main Product}", EN)  # Prompt 100: headline as the section heading
        self.assertIn("Thin lines connect observations across the ordered publication periods", EN)
        self.assertIn("가는 선은 순서가 있는 출판 시기의 관측값을 시각적으로 연결", KO)

    def test_citation_order(self):
        for tex in (EN, KO):
            b = tex[:tex.find("\\section*{Supplementary materials}") if "Supplementary materials" in tex else tex.find("\\section*{보충자료}")]
            seq = []
            for m in re.finditer(r"\\supp(tab|fig)\{(\d+)\}", b):
                k = (m.group(1), int(m.group(2)))
                if k not in seq:
                    seq.append(k)
            self.assertEqual([n for t, n in seq if t == "tab"], [1, 2, 3, 4, 5, 6, 7, 8])
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

    def test_figure_text(self):
        with fitz.open(ROOT / "figures/submission/fig2_use_and_claims.pdf") as d:
            f2 = d[0].get_text()
        self.assertNotIn("163", f2); self.assertNotIn("core\ncohort", f2)
        for token in ("138", "84", "56", "21", "core cohort 48"):
            self.assertIn(token, f2)
        with fitz.open(ROOT / "figures/submission/fig4_further_claims.pdf") as d:
            f4 = d[0].get_text()
        for token in ("4/19", "8/37", "5/48", "34/46", "12/46"):
            self.assertIn(token, f4)


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
