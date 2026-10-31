#!/usr/bin/env python3
"""Prompt 099 (review v37 storyline): Figure 2 as the bridge (A studies per year, B topics, C algorithm families by period,
D familiar evaluation work, E what was classified), Figure 3 B rankings within each major topic and C grouped methods,
Figure 4 without the pairwise panel (Supplementary Figure S7), Figure 5 one slope chart with ranking stability and 2025/2026
diamonds, Figure 6 A how stability was checked (survey cycles 0) and C an all-steps summary row, no amber in main figures,
methods testbed as a paragraph of the Figure 2 section, supplementary figures S1-S8 in citation order."""
import json
import re
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
PT = json.loads((ROOT / "results/derived/practice_trends_099.json").read_text())
MM = (ROOT / "tools/make_main_figures.py").read_text()


def pdf_text(path):
    t = " ".join(" ".join(p.get_text() for p in fitz.open(path)).split())
    t = re.sub(r"(\w)[\u2011-] (\w)", r"\1\2", t)
    return t.replace("\u2011", "-")


SUPP = pdf_text(ROOT / "manuscript/bmc_supplementary.pdf")


def fig_text(stem):
    return " ".join(fitz.open(ROOT / f"manuscript/figs/{stem}.pdf")[0].get_text().split())


def results(tex, start, end):
    return tex.split(start)[1].split(end)[0]


class Prompt099(unittest.TestCase):
    def test_values_computed(self):
        self.assertEqual(PT["algorithm_families_by_period"]["boosting"], [1, 15, 34, 42])
        fe = PT["familiar_evaluation"]
        self.assertEqual([fe[k] for k in ("auroc", "algorithms_compared", "train_test_split", "systematic_tuning_search", "cross_validation")],
                         [134, 132, 116, 95, 79])
        co = PT["classified_outcome"]
        self.assertEqual((co["current_state_same_survey"], co["timing_unclear"], co["future_event"]), (164, 1, 0))
        self.assertEqual(list(co["source"].values()), [62, 41, 29, 16, 17])
        rt = PT["ranking_by_topic_period"]
        self.assertEqual([(v["ranking"][0], v["n"][0], v["ranking"][-1], v["n"][-1]) for v in rt.values()],
                         [(2, 7, 15, 16), (4, 5, 11, 11), (3, 5, 5, 5), (1, 6, 5, 5)])
        self.assertEqual(PT["preprocessing_summary"], {"applied": 163, "all_within_training": 15, "any_before_split": 83, "unclear_only": 65})
        for n in ("094", "095", "096", "097", "098"):
            self.assertTrue((ROOT / f"results/derived/practice_trends_{n}.json").exists())

    def test_figure2_bridge(self):
        for stem, words in (("fig2_literature_map", ["A. Studies per publication year",  # Prompt 104: A-K grid  # Prompt 108
                                                      "B. Task (N=250)"]),  # Prompt 104  # Prompt 106
                            ("fig3_analysis_workflow", ["H. Algorithms fitted", "J. Evaluation steps", "C. Outcome timing", "B. Survey years", "not reported 3"]),  # Prompt 108  # prompt 110  # prompt 112
                            ("fig2_literature_map_ko", ["A. 출판연도별 연구 수", "B. 과제"])):  # Prompt 107  # Prompt 108
            t = fig_text(stem)
            for w in words:
                self.assertIn(w, t, (stem, w))
        self.assertIn("\\caption{\\textbf{How the 192 core studies were analysed.}", EN)  # Prompt 100: neutral caption  # Prompt 107
        self.assertNotIn("What they classified, however", EN)  # Prompt 100: no reversal

    def test_figure3_and_4(self):
        t = fig_text("fig4_variable_importance")
        for w in ("Importance ranking and SHAP by publication period", "0/45", "Used SHAP (56 of 192)"):  # Prompt 100: topic slopes S3E, methods S5E  # Prompt 106  # Prompt 107  # prompt 110  # prompt 112
            self.assertIn(w, t)
        self.assertNotIn("Later use of rankings", t)
        t4 = fig_text("fig4_variable_importance")  # Prompt 100: rankings figure merged into Figure 3  # Prompt 107
        self.assertNotIn("Agreement between pairs", t4)
        self.assertIn("First author and year", fig_text("fig5_rankings_named"))  # prompt 110  # prompt 112
        self.assertIn("occurred in each of the four largest topics", " ".join(EN.split()))  # Prompt 100: positive sentence, slopes in S3E  # prompt 110
        self.assertIn("Supplementary\nFigures S1--S8.", EN)
        self.assertIn("0.25 and 0.17; \\suppfig{7}A)", " ".join(EN.split()))  # Prompt 102: agreement figure S8 cited in the Discussion  # prompt 109  # prompt 110

    def test_figure5_and_6(self):
        t5 = fig_text("fig6_maturing_practice")  # Prompt 100: small multiples  # prompt 112
        for w in ("B. Calibration reported", "C. Validation beyond the", "1/45", "14/53", "17/53"):  # Prompt 101: denominator in the title  # Prompt 106  # Prompt 107  # prompt 109
            self.assertIn(w, t5)
        t6 = fig_text("fig7_next_steps")  # Prompt 100: former Figure 6  # prompt 112
        for w in ("Across survey cycles", "All applied steps", "Step not applied", "Not applicable"):  # Prompt 106  # Prompt 107
            self.assertIn(w, t6)
        self.assertNotIn("Stability checks by period", t6)
        body = MM.split("def figure2(")[1].split("FIGURES = (")[0]
        self.assertNotIn("AMBER", body.replace("AMBER,", ""))  # no amber in the main figures
        self.assertIn("Thin lines connect observations across the ordered publication periods", EN)
        self.assertIn("가는 선은 순서가 있는 출판 시기의 관측값을 시각적으로 연결", KO)

    def test_section_order_and_citations(self):
        heads = re.findall(r"\\subsection\{([^}]*)\}", EN.split("\\section{Results}")[1].split("\\section{Discussion}")[0])
        self.assertEqual(heads, ["Study Selection", "How Machine Learning Was Used", "Variable Importance as the Main Product",
                                 "What the Rankings Named", "Practices That Became More Common", "Ranking Stability, Survey Design and Preprocessing"])  # Prompt 100: forward headings  # prompt 109  # prompt 112
        self.assertNotIn("Methods Testbed", EN)
        self.assertIn("Of the 36 method-focused studies, 26 developed or improved a method", " ".join(EN.split()))  # Prompt 100: shortened paragraph
        for tex in (EN, KO):
            body = tex.split("\\section*{Declarations}")[0].split("\\section*{선언}")[0]
            figs = [int(x) for x in re.findall(r"\\suppfig\{(\d)\}", body)]
            first = list(dict.fromkeys(figs))
            self.assertEqual(first, list(range(1, 9)))

    def test_supplement(self):
        toc = [x[1] for x in fitz.open(ROOT / "manuscript/bmc_supplementary.pdf").get_toc()]
        self.assertEqual(len(toc), 16)
        self.assertIn("Supplementary Figure S7. Agreement between pairs of rankings", toc)  # Prompt 102: renumbered in citation order  # prompt 109
        self.assertIn("Supplementary Figure S8. Reporting completeness and PROBAST+AI", toc)  # Prompt 102  # prompt 109
        self.assertIn("The final analytic sample is shown in Figure 3E", SUPP)  # Prompt 107  # Prompt 108  # prompt 110
        self.assertNotIn("A. Source of the outcome (N=165)", SUPP)
        self.assertNotIn("B. Algorithm families", SUPP)
        self.assertIn("summarised in Figure 3J", SUPP)  # Prompt 100: evaluation steps are Figure 2G  # Prompt 106  # Prompt 107  # Prompt 108  # prompt 110

    def test_logs_and_words(self):
        for name in ("bmc_main", "bmc_main_ko", "bmc_supplementary"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")
        import subprocess
        out = subprocess.run(["python3", str(ROOT / "prompts/implementation_records/prompt_099/word_counts.py")], capture_output=True, text=True).stdout
        w = dict(line.split() for line in out.strip().splitlines())
        self.assertLessEqual(int(w["Abstract"]), 350)
        self.assertLessEqual(int(w["Discussion"]), 1300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
