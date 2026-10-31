"""Prompt 087 regression checks: abstract length, wording, float/section order, S2 lossless
common-note compaction, supplement pagination, delivery reconstruction and locked decisions."""
import hashlib, json, re, subprocess, sys, tarfile, tempfile, unittest, zipfile
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "prompts/implementation_records/prompt_087"
sys.path.insert(0, str(ROOT / "tools"))


def abstract_words(pdf):
    d = fitz.open(pdf)
    t = d[0].get_text() + d[1].get_text()
    a = t[t.find("Background:"):t.find("Keywords")]
    a = re.sub(r"(?m)^\d{1,4}\n", "", a)          # line numbers
    a = re.sub(r"-\n(?=[a-z])", "-", a)            # rejoin hyphen breaks without splitting words
    return a, len(a.split())


def headings_and_figures(pdf):
    d = fitz.open(pdf)
    figs, heads = {}, {}
    for i, p in enumerate(d):
        for m in re.finditer(r"^(?:Fig\. ?|그림 ?)(\d+)\b", p.get_text(), re.M):
            figs.setdefault(int(m.group(1)), i + 1)
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                s = "".join(x["text"] for x in l["spans"]).strip()
                if re.match(r"^\d+(\.\d+)?\s+\S", s) and max(x["size"] for x in l["spans"]) >= 10.5:
                    heads.setdefault(s.split()[0], i + 1)
    return figs, heads


class Prompt087(unittest.TestCase):
    def test_A_abstract_length(self):
        text, n = abstract_words(ROOT / "manuscript/bmc_main.pdf")
        # Prompt 089 rewrote the abstract around the claim-evidence position; the BMC limit is 350 words.
        self.assertLessEqual(n, 350)
        flat=" ".join(text.split())
        # Prompt 088 rewrote the abstract (review: lead with findings, drop hedges); the 138/84 contrast stays.
        # Prompt 090 abstract wording (review v28): rankings produced versus interpretation stated as a purpose.
        # (the PDF hyphenates "rankings", so match the words after it)
        # Prompt 091 shortened the abstract lead; the 138/84 contrast stays.
        # Prompt 094 (review v32): authors' purposes are no longer coded, so the 138/84 contrast left the abstract; the
        # ranking/SHAP period values now carry the same finding.
        self.assertIn("49 of 53", flat)  # Prompt 106
        self.assertIn("SHAP was used in 33 of these 53", flat)  # Prompt 106

    def test_B_population_association_joined(self):
        full = "".join(p.get_text() for p in fitz.open(ROOT / "manuscript/bmc_main.pdf"))
        self.assertNotRegex(full, r"population- association")
        self.assertNotIn("population-\n", (ROOT / "manuscript/bmc_main.tex").read_text())

    def test_C_bounded_novelty_claim(self):
        en = (ROOT / "manuscript/bmc_main.tex").read_text(); ko = (ROOT / "manuscript/bmc_main_ko.tex").read_text()
        self.assertNotIn("No previous review has synthesised applied ML across KNHANES", en)
        # Prompt 094 (review v32): the bounded novelty statement no longer names research purposes.
        self.assertIn("No review has mapped this literature as a whole", en)
        self.assertNotIn("KNHANES 전체의 응용 ML을 종합한 선행 리뷰는 없었다", ko)

    def test_D_message_order(self):
        en = (ROOT / "manuscript/bmc_main.tex").read_text()
        # Prompt 094 (review v32): Principal Findings leads with the classification-to-explanation shift and ends with next steps.
        pf = en[en.find("\\subsection{Principal Findings}"):en.find("\\subsection{Explanation as the Main Product}")]
        # Prompt 093 (review v31 section 4.4) deleted the second Principal Findings paragraph (the 138-output
        # restatement); the paragraph now leads with the analysis-centred finding and ends with the headline.
        flat = " ".join(pf.split())
        # Prompt 095 (review v33): "has added explanation to classification" replaces "moved from ... toward"; order is kept.
        # Prompt 096 (review v34): message revision, "has become an explanation tool"; order of the Principal Findings is kept.
        self.assertGreaterEqual(flat.find("has become a prominent output alongside classification"), 0)  # prompt 113
        self.assertLess(flat.find("has become a prominent output alongside classification"), flat.find("These findings point to three steps for interpreting variable"))  # Prompt 101: forward wording  # prompt 111
        concl = en[en.find("\\section{Conclusions}"):]
        # Prompt 090 rewrote this sentence as requested by review v28 (what a study aims, produces, and intends).
        # Prompt 094 (review v32): the Conclusions now state the next steps instead of separating aims from evidence.
        self.assertIn("whether their rankings are stable", " ".join(concl.split()))  # Prompt 096 (review v34): message-revision Conclusions

    def test_F_figures_before_next_heading(self):
        # Prompt 090: eight claim-ordered figures and unnumbered BMC headings; Figures 11-12 became
        # Supplementary Figures S11-S12. Every main figure must precede the Discussion heading.
        for pdf, next_heading in [("bmc_main.pdf", "Discussion"), ("bmc_main_ko.pdf", "고찰")]:
            figs, _ = headings_and_figures(ROOT / "manuscript" / pdf)
            self.assertEqual(sorted(figs), list(range(1, 8)), pdf)  # Prompt 100: five main figures (straight storyline); six since prompt 107  # Prompt 107  # prompt 112
            pages = [p.get_text() for p in fitz.open(ROOT / "manuscript" / pdf)]
            head = next(i + 1 for i, t in enumerate(pages) if re.search(r"^" + next_heading + r"\s*$", t, re.M))
            self.assertLessEqual(max(figs.values()), head, pdf)

    def test_G_s2_lossless_common_notes(self):
        import build_standalone_supplements as b
        rows = b.human_protocol_rows()
        note = b.human_protocol_note()
        self.assertEqual(note.count(b.S2_REP_COMMON), 1)
        self.assertEqual(note.count(b.S2_PROBAST_COMMON_1), 1)
        # Prompt 093: the 306-item instrument is the PROTOCOL_ITEMS sheet of Table S5, written in full (no shared
        # note), so every row must equal the canonical row text; the note compression is still exercised by
        # test_prompt_086 through emit_fixed_table.
        from openpyxl import load_workbook
        wb = load_workbook(ROOT / "manuscript/bmc_supplementary_data1.xlsx", read_only=True)  # Prompt 097: Additional Data 1
        sheet = [list(r) for r in wb["PROTOCOL_ITEMS"].iter_rows(min_row=2, values_only=True)]
        items = [r for r in rows if any(v not in (None, "") for v in r[1:])]
        body = [r for r in sheet if any(v not in (None, "") for v in r[1:])]
        self.assertEqual(len(items), 306)
        self.assertEqual([[b.clean(v) for v in r] for r in items], body)
        for r in rows:  # every original row text is reconstructable from note + row remainder
            if r[5].startswith(b.S2_REP_COMMON + " "):
                self.assertTrue(r[0].startswith("REP"))
            if b.S2_PROBAST_COMMON_1 in r[5]:
                self.assertRegex(r[0], r"^P[DE]_D[1-4]$")

    def test_H_supplement_pages(self):
        data = json.loads((REC / "supplement_page_fill.json").read_text())
        low = [r for r in data["after"] if r["fill_fraction"] < .25 and "Supplementary contents" not in r["head"]
               and "Table S4." not in r["head"]]
        self.assertEqual(low, [])
        # Prompt 093: 7 PDF tables (S5 is the workbook, Additional file 2) + 8 figures = 15 bookmarks.
        # Prompt 094 (review v32): panels moved into main Figures 2 and 6 left six supplementary figures (13 bookmarks).
        self.assertEqual(len(fitz.open(ROOT / "manuscript/bmc_supplementary.pdf").get_toc()), 16)  # Prompt 099: 8 tables + 8 figures (former Figure 4C is S7)

    def test_I_delivery(self):
        with tempfile.TemporaryDirectory() as t:
            with zipfile.ZipFile(ROOT / "manuscript/reviewer_delivery.zip") as z:
                z.extractall(t)
            r = subprocess.run([sys.executable, str(Path(t) / "verify_delivery.py")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            out = json.loads(r.stdout)
            self.assertEqual(out["figure12_period_values_reconstructed"], 68)
            self.assertEqual(out["purpose_output_counts"], [[79, 4, 85, 46], [20, 1, 40, 153]])  # Prompt 106
            for n in ["bmc_main.pdf", "bmc_main_ko.pdf", "bmc_supplementary.pdf", "bmc_supplementary_data1.xlsx"]:  # Prompt 097: Additional Data 1
                self.assertEqual((Path(t) / n).read_bytes(), (ROOT / "manuscript" / n).read_bytes(), n)

    def test_build_logs_and_locked_decisions(self):
        for f in ["bmc_main", "bmc_main_ko"]:
            log = (ROOT / "build/submission" / f"{f}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log); self.assertNotIn("Overfull", log)
        with tarfile.open(REC / "before.tar.gz") as t:
            for name in ["manuscript/bmc_main.tex", "manuscript/bmc_main_ko.tex"]:
                self.assertEqual(t.extractfile(name.replace("manuscript/", "paper/", 1)).read().decode().split("\\begin{document}")[0],
                                 (ROOT / name).read_text().split("\\begin{document}")[0])
        for suffix in ["", "_ko"]:
            text = fitz.open(ROOT / f"figures/submission/fig11_methodological_appraisal{suffix}.pdf")[0].get_text()
            self.assertEqual(text.count("N=192 studies"), 4)  # Prompt 106
        s = (ROOT / "tools/make_streamlined_figures.py").read_text()
        self.assertRegex(s, r"ax\.plot\(range\(4\),pct,.*zorder=2\)")


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
