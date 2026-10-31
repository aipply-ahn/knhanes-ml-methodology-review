#!/usr/bin/env python3
"""Prompt 106: criterion A applied end to end (250 studies): records, selection flow, derived values, figures,
manuscripts and supplement."""
import csv
import json
import re
import subprocess
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "results/derived"
FLOW = json.loads((DER / "final_selection_flow.json").read_text())
O = json.loads((DER / "practice_trends_106.json").read_text())
EN = (ROOT / "manuscript/bmc_main.tex").read_text()
KO = (ROOT / "manuscript/bmc_main_ko.tex").read_text()


def pdf_text(name):
    return " ".join(" ".join(p.get_text().split()) for p in fitz.open(ROOT / name))


class Prompt106(unittest.TestCase):
    def test_records(self):
        adds = list(csv.DictReader(open(ROOT / "data/protocol_v1_2/criterion_a_additions.tsv"), delimiter="\t"))
        self.assertEqual(len(adds), 33)
        self.assertEqual({a["study_id"] for a in adds}, {f"KHM{i}" for i in range(223, 256)})
        included = []
        for p in sorted((ROOT / "data/protocol_v1_2/final").glob("KHM*_final.json")):
            d = json.loads(p.read_text())
            if d.get("corpus_status", {}).get("include", True):
                included.append(d["study_id"])
        self.assertEqual(len(included), 250)
        self.assertFalse({"KHM073", "KHM129", "KHM156", "KHM256"} & set(included))
        for sid in ("KHM223", "KHM251", "KHM255"):
            d = json.loads((ROOT / f"data/protocol_v1_2/final/{sid}_final.json").read_text())
            self.assertEqual(d["review_mode"], "single_review_criterion_a")
            self.assertEqual(d["protocol_items"]["QA10"][0]["value"], "N")
        R = json.loads((DER / "criterion_a_rescreen.json").read_text())
        self.assertEqual([a["study_id"] for a in R["exclusion_recheck"]["added"]], ["KHM255"])
        self.assertIn("KHM256", R["exclusion_recheck"]["extracted_then_excluded"])

    def test_flow(self):
        f = FLOW["flow"]
        self.assertEqual((f["unique_records_screened"], f["terminology_exclusions"], f["records_assessed_against_eligibility"]), (11077, 9562, 1515))
        self.assertEqual((f["reports_excluded_total"], f["eligible_reports_entering_family_linkage"], f["additional_or_companion_reports_linked"],
                          f["unique_full_report_studies_included"]), (1239, 276, 26, 250))
        self.assertEqual(f["unique_records_screened"] - f["terminology_exclusions"], f["records_assessed_against_eligibility"])
        self.assertEqual(f["reports_excluded_total"] + f["eligible_reports_entering_family_linkage"], f["records_assessed_against_eligibility"])
        self.assertEqual(sum(f["report_exclusion_reasons"].values()), f["reports_excluded_total"])
        self.assertEqual(FLOW["terminology_screen"]["partition"]["kci_not_advanced"], 0)
        self.assertEqual(FLOW["unified_screening"]["rule"], "T1/T2/T3 dictionary replay for every source, KCI included")

    def test_values(self):
        tc = O["task_composition"]
        self.assertEqual(sum(tc["health"].values()) + sum(tc["method"].values()), 250)
        self.assertEqual((O["classified_outcome"]["n"], O["period_n"], O["importance_ranking_total"]), (192, [45, 35, 59, 53], 154))
        self.assertEqual(len(O["literature_map"]), 250)
        # earlier practice_trends files are not rewritten
        self.assertTrue((DER / "practice_trends_104.json").exists())

    def test_manuscripts(self):
        self.assertIn("A Systematic\nMethodological Review of Supervised Machine Learning in a National Health Survey}", EN)
        self.assertNotRegex(EN.split("\\title[")[1].split("\\author")[0], r"\d")
        for tex in (EN, KO):
            body = re.sub(r"(?m)^%.*$", "", tex.split("\\begin{document}")[1])
            self.assertNotRegex(body, r"(?<![\d.,])(220|165|129|134|1,499|245)(?![\d.,])")
            self.assertIn("christodoulou2019systematic", body)
            self.assertIn("250", body)
        self.assertIn("extracted once", EN)
        self.assertIn("from its abstract alone", EN)  # prompt 116
        self.assertIn("한 번 추출", KO)
        self.assertIn("same rule was applied\nto every source", EN)
        self.assertIn("christodoulou2019systematic", (ROOT / "manuscript/supporting_refs.bib").read_text())
        out = subprocess.run(["python3", str(ROOT / "prompts/implementation_records/prompt_099/word_counts.py")], capture_output=True, text=True).stdout
        w = dict(line.split() for line in out.strip().splitlines())
        self.assertLessEqual(int(w["Abstract"]), 350)
        self.assertLessEqual(int(w["Discussion"]), 1300)

    def test_pdfs(self):
        en = pdf_text("build/submission/bmc_main.pdf")
        for s in ("1,515", "276 reports of 250 unique", "49 of 53", "154 (80.2)"):  # prompt 109
            self.assertIn(s, en)
        supp = pdf_text("manuscript/bmc_supplementary.pdf")
        self.assertNotRegex(supp, r"(?<![\d.,/=])(220|165|184|129|134|1,499|1,254|259|346)(?![\d.,%])")
        self.assertIn("Characteristics of ten illustrative included studies", supp)  # prompt 113
        for name in ("bmc_main", "bmc_main_ko", "bmc_supplementary"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotRegex(log, r"Float too large|Missing character|undefined")

    def test_figure1(self):
        t = pdf_text("manuscript/figs/fig1_prisma.pdf")
        for s in ("9,562", "1,515", "1,239", "276", "250", "Unsupervised or regression-"):
            self.assertIn(s, t)
        self.assertNotIn("Korean Citation Index records", t)
        self.assertNotIn("ML-adjacent", t)


if __name__ == "__main__":
    unittest.main()
