#!/usr/bin/env python3
"""Prompt 097 (review v35, 88/100): literature map (new Figure 2), what the rankings pointed to (new Figure 4),
methods testbed moved to the supplement, supplement as numbered tables and figures only, workbook renamed
Additional Data 1, included-studies table with DOIs, and the small v35 fixes (boosting citation, intervals,
Table 1 bracket, Figure 6B colour, KHM019 sample)."""
import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
PT = json.loads((ROOT / "results/derived/practice_trends_097.json").read_text())


def pdf_text(path):
    t = " ".join(" ".join(p.get_text() for p in fitz.open(path)).split())
    t = re.sub(r"(\w)\u2011 (\w)", r"\1\2", t)  # line-break hyphens
    return t.replace("\u2011", "-")  # non-breaking hyphens in the PDF text layer


SUPP = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")


def main_text(tex):
    return tex.split("\\section*{Declarations}")[0].split("\\section*{선언}")[0]


class Prompt097(unittest.TestCase):
    def test_new_values_are_computed_and_earlier_files_kept(self):
        self.assertEqual(len(PT["literature_map"]), 220)
        self.assertEqual((PT["sample_summary"]["median"], PT["sample_summary"]["reported"]), (7176, 215))
        a = PT["ranking_domains_all"]
        self.assertEqual((a["n"], a["AGE"], a["ADIPOSITY_BODY_SIZE"], a["SOCIOECONOMIC"], a["MENTAL_SUBJECTIVE_HEALTH"]), (129, 97, 79, 72, 54))
        t = PT["ranking_domains_by_topic"]
        self.assertEqual((t["MENTAL_HEALTH"]["n"], t["MENTAL_HEALTH"]["SOCIOECONOMIC"], t["MENTAL_HEALTH"]["MENTAL_SUBJECTIVE_HEALTH"]), (31, 24, 23))
        self.assertEqual((t["CARDIOVASCULAR"]["n"], t["CARDIOVASCULAR"]["LIPIDS"]), (13, 8))
        g = PT["domain_agreement"]
        self.assertEqual((g["pairs_within_topic"], g["pairs_between_topics"], g["median_jaccard_within"], g["median_jaccard_between"]),
                         (1377, 6879, 0.286, 0.25))
        for n in ("094", "095", "096"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_main_figures(self):
        for tex, suf in ((EN, ""), (KO, "_ko")):
            figs = re.findall(r"figs/(fig\d_[a-z_]+?)(?:_ko)?\.pdf", tex)
            self.assertEqual(figs, ["fig1_prisma", "fig2_literature_map", "fig3_analysis_workflow", "fig4_variable_importance", "fig5_rankings_named", "fig6_maturing_practice", "fig7_next_steps"])  # Prompt 100: four figures after PRISMA  # Prompt 107  # prompt 112
            for f in figs:
                self.assertTrue((ROOT / f"manuscript/figs/{f}{suf}.pdf").exists(), f)
        self.assertNotIn("fig5_methods_testbed", EN + KO)
        self.assertIn("Age, socioeconomic variables and body size were named across outcomes", EN)  # Prompt 100: paragraph of the importance section  # Prompt 106  # prompt 112
        self.assertIn("나이, 사회경제 변수, 체격은 결과와 관계없이 꼽혔고", " ".join(KO.split()))  # Prompt 100  # Prompt 106  # prompt 112
        src = (ROOT / "tools/make_main_figures.py").read_text()
        self.assertIn('axB.barh(i, r["used"], color=TEAL, height=.62)', src)  # Prompt 099: still teal, comment dropped  # Prompt 107
        self.assertIn("All applied steps", src)  # Prompt 099: Figure 6C adds a summary row; counts inside the bar

    def test_ranking_sentences(self):
        self.assertIn("age in 113, a socioeconomic variable in 93 and a body-size measure in 87", " ".join(EN.split()))  # Prompt 100: rewrapped  # Prompt 106
        self.assertIn("0.30", " ".join(fitz.open(ROOT / "manuscript/supplementary/figures/Supplementary_Figure_S07_Agreement_between_rankings.pdf")[0].get_text().split()))  # Prompt 102: overlap in Figure S8  # prompt 109
        self.assertIn("Beyond age, sex and body size, two studies with the same outcome shared more variable domains", " ".join(EN.split()))  # Prompt 104: 2G cited  # Prompt 106  # prompt 110  # prompt 112
        self.assertIn("나이·성별·체격을 빼면 같은 결과를 다룬 두 연구가", " ".join(KO.split()))  # Prompt 104: 2G cited  # Prompt 106  # prompt 110  # prompt 112
        self.assertIn("Jaccard index", EN)

    def test_small_fixes(self):
        self.assertIn("42 of 53 in 2025--2026 (Figure~\\ref{fig:analysis}H;", EN)  # Prompt 104: algorithms are Figure 2I  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110
        self.assertIn("external data (2) or intervals (1),", " ".join(EN.split()))  # prompt 109
        self.assertIn("구간 추정(1편)", KO)
        for tex in (EN, KO):
            self.assertNotIn("(8/48)", tex)
        self.assertIn("Of the 44 studies reporting a decision threshold, 21 chose it without using the final evaluation data.", " ".join(EN.split()))  # Prompt 101: in the S5 caption  # Prompt 106  # prompt 110  # prompt 111
        self.assertNotIn("but the difference moved into unclear timing", " ".join(" ".join(pg.get_text() for pg in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))  # Prompt 100: trend sentence in the S3 caption  # prompt 109
        self.assertIn("are given for all 250 included studies in Additional Data~1; \\supptab{8} illustrates", " ".join(EN.split()))  # prompt 113  # prompt 114
        self.assertNotIn("The author verified every\ndecision against the source report.", EN)
        self.assertIn("The final analytic sample is shown in Figure 3E", " ".join(" ".join(pg.get_text() for pg in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf")).split()))  # Prompt 099: sample-size panel moved to S2C  # Prompt 102: page 13 after renumbering (S4)  # Prompt 107  # Prompt 108  # prompt 110

    def test_citation_order(self):
        for tex in (main_text(EN), main_text(KO)):
            tabs = [int(x) for x in re.findall(r"\\supptab\{(\d)\}", tex)]
            figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", tex)]
            first = lambda xs: [x for i, x in enumerate(xs) if x not in xs[:i]]
            self.assertEqual(first(tabs), list(range(1, 9)))
            self.assertEqual(first(figs), list(range(1, 9)))  # Prompt 099: eight supplementary figures
            self.assertNotIn("\\supptab{9}", tex)
            self.assertNotIn("Table S5", tex); self.assertNotIn("보충표 S5", tex.replace("\\supptab{5}", ""))

    def test_declarations(self):
        self.assertIn("Supplementary Tables S1--S8 and Supplementary\nFigures S1--S8.", EN)  # Prompt 099
        self.assertIn("Additional file 2] KNHANES\\_ML\\_review\\_Additional\\_Data\\_1.xlsx (XLSX). Additional Data 1,", EN)
        self.assertIn("보충표 S1--S8과 보충그림 S1--S8", KO)  # Prompt 099: eight supplementary figures

    def test_supplement_structure(self):
        toc = [l for l in (ROOT / "manuscript/supplementary/supplementary_manifest.tsv").read_text().splitlines()[1:]]
        items = [l.split("\t")[0] for l in toc]
        self.assertEqual(items, [f"Supplementary Table S{n}" for n in range(1, 6)] + [f"Supplementary Figure S{n}" for n in range(1, 9)]  # Prompt 099
                         + ["Supplementary Table S6", "Supplementary Table S7", "Supplementary Table S8", "Full coding log"])
        self.assertTrue((ROOT / "manuscript/bmc_supplementary_data1.xlsx").exists())
        self.assertFalse((ROOT / "manuscript/bmc_supplementary_table_s5.xlsx").exists())
        self.assertEqual(len(fitz.open(ROOT / "manuscript/bmc_supplementary.pdf").get_toc()), 16)  # Prompt 099: eight supplementary figures
        # no front-page guide text and no work-record sentences
        for gone in ("is supplied as the accompanying workbook", "summarises individual studies", "format preview",
                     "will be deposited", "not the same 165 studies", "18 documented choosing it",  # Prompt 100: the preprocessing trend is an S3 caption fact
                     "shown in Figure 2 of the main text", "Retracted; excluded from performance evidence. Hwang"):
            self.assertNotIn(gone, SUPP, gone)
        self.assertIn("Sole primary dataset", (ROOT / "tools/make_supplementary_figures.py").read_text())

    def test_tables(self):
        self.assertIn("Supplementary Table S8. Characteristics of ten illustrative included studies", SUPP)  # Prompt 098: title  # Prompt 106  # prompt 113
        self.assertIn("10.", SUPP.split("Supplementary Table S8. Characteristics of ten illustrative included studies")[-1][:3000])  # Prompt 098: title  # Prompt 106  # prompt 113
        self.assertIn("2007–2018; 217,598*", SUPP.replace(", 598", ",598"))  # Prompt 098: n in the "Survey years; n" column
        self.assertIn("Records replicated in proportion to sampling weights, not participants", SUPP)
        s5 = SUPP.split("Supplementary Table S5.")[-1][:6000]
        self.assertIn("Task-specific checks were not reported", s5)  # prompt 111
        self.assertIn("except overlap and sensitivity", s5)  # prompt 111
        self.assertIn("\u2020Retracted; excluded from performance evidence.", SUPP)
        self.assertNotIn("Table S5 column", SUPP)
        self.assertIn("11,077 records screened", SUPP)
        self.assertIn("Total not advanced", SUPP)


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 117: repinned (single-sheet Additional Data 1; review v53 sentences; update_historical_tests.py)
