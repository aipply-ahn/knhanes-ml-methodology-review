"""Prompt 088: review-procedure wording, reader-facing codes, abstract, PRISMA boxes and figure fixes."""
from pathlib import Path
import re
import sys
import unittest

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_prompt_087 import abstract_words, headings_and_figures  # noqa: E402


def body(tex):
    """Manuscript text without comment lines."""
    return "\n".join(line for line in tex.splitlines() if not line.lstrip().startswith("%"))


def pdf_text(name):
    with fitz.open(ROOT / "manuscript" / name) as doc:
        return " ".join(" ".join(p.get_text() for p in doc).split()).replace("\u2011", "-")  # PDF non-breaking hyphens


class Prompt088(unittest.TestCase):
    def setUp(self):
        self.en = body((ROOT / "manuscript/bmc_main.tex").read_text())
        self.ko = body((ROOT / "manuscript/bmc_main_ko.tex").read_text())

    def test_review_procedure_wording(self):
        for text in (self.en, self.ko):
            for token in ("LLM verification", "blinded source-read", "independent human", "reverif",
                          "not independently validated", "LLM 검증", "독립적인 사람", "재검증", "이중검토",
                          "kappa", "second reviewer"):
                self.assertNotIn(token, text)
        # Prompt 089 rewrote this sentence (single reviewer, performed and verified); the meaning is unchanged.
        self.assertIn("The author made all screening and eligibility decisions.", self.en)
        self.assertIn("선별과 적격성 판정은 모두 저자가 했다", self.ko)
        supp = pdf_text("bmc_supplementary.pdf")
        for token in ("machine-assisted", "human duplicate", "second human reviewer", "LLM-assisted"):
            self.assertNotIn(token, supp)
        self.assertIn("The author checked the", supp)  # Prompt 098: reviewer row shortened (review v36)  # prompt 115

    def test_no_internal_codes_in_reader_text(self):
        pattern = re.compile(r"\b(REP\d\d|OUT\d\d|PRD\d\d|KHM\d{3}|R[012]\b|PROTOCOL\\_|RECORD\\_)")
        for text in (self.en, self.ko):
            self.assertEqual(pattern.findall(text), [])
        for name in ("fig6_classification_outcomes", "fig11_methodological_appraisal"):
            for suffix in ("", "_ko"):
                with fitz.open(ROOT / f"figures/submission/{name}{suffix}.pdf") as doc:
                    self.assertIsNone(re.search(r"REP\d\d|OUT\d\d", doc[0].get_text()), name + suffix)

    def test_abstract(self):
        text, n = abstract_words(ROOT / "manuscript/bmc_main.pdf")
        self.assertLessEqual(n, 350)
        flat = " ".join(text.split())
        # Prompt 089 removed the cohort-prediction framing ("future-event outcome") from the abstract.
        # Prompt 090 replaced the PROBAST+AI line with a representative number; prompt 091 sharpened it to 0 of 120.
        # Prompt 093 merged the headline into "None of the 120 studies ... reported all the evidence their claims required".
        # Prompt 094 (review v32): the claim-evidence headline was replaced by the practice-change headline.
        for token in ("29 of 45", "49 of 53", "33 of these 53"):  # Prompt 106; ranking stability left the abstract list  # Prompt 107
            self.assertIn(token, flat)
        self.assertNotIn("does not indicate analytic error", flat)
        self.assertNotIn("exploratory", flat)

    def test_prisma_boxes(self):
        # Author decision 2026-09-28: citation searching (no added records) left the flow diagram; Methods/Table S3 keep it.
        # Prompt 092 (review v30): "sought, not retrieved, and assessed: not recorded".
        for suffix, tokens in (("", ("Korea Disease Control and", "not recorded", "Excluded candidates (n=1,239)", "Unsupervised or regression- family methods only 97")),  # Prompt 097 (review v35): the list is in Additional Data 1  # Prompt 106
                               ("_ko", ("질병관리청 출판목록", "기록되지 않음", "제외 후보 (n=1,239)"))):  # Prompt 106
            with fitz.open(ROOT / f"figures/submission/fig1_prisma{suffix}.pdf") as doc:
                text = " ".join(doc[0].get_text().split())
            for token in tokens:
                self.assertIn(token, text)

    def test_counts_and_denominators_explained(self):
        # Prompt 089 replaced the "packets" wording with plain "extraction records".
        # Prompt 091 removed the extraction-record sentence (review v29: work record, already in Figure 1 counts).
        self.assertNotIn("The two extraction records that did not become separate studies", self.en)
        # Prompt 090 claim-ordered Results: period values in words, weights-mention in Figure 6A, 37 core vs 42 in Figure 3B.
        # Prompt 093 moved period-specific values to the Supplementary Figure S8 caption (review v31 section 4.3).
        supp = pdf_text("bmc_supplementary.pdf")
        # Prompt 095 (review v33): the S6 caption states the final-model values in panel D's parenthesis.
        # Prompt 096 (review v34): final-model specification by period is drawn in Figure 4B (3/32 ... 5/49), not repeated in S6.
        self.assertNotIn("Figure 4 of the main text", supp)  # Prompt 097 (review v35): legends no longer cross-refer to main figures
        self.assertNotIn("complete final-model specification increased from 3/32 to 5/49", self.en)
        # Prompt 094 (review v32): the weights-mention count is reported with the survey-design stages (Figure 6B).
        self.assertIn("Of the 192 studies, 50 mentioned survey weights", " ".join(self.en.split()))  # Prompt 100: forward wording  # Prompt 106  # Prompt 107
        # Prompt 093 shortened the PROBAST+AI paragraph to the overall ratings; domain counts are in Figure S7.
        self.assertIn("PROBAST+AI rated 375 of the 378 model evaluations here at high risk", " ".join(self.en.split()))  # Prompt 106  # prompt 109  # prompt 113
        # Prompt 091 lists all four core-cohort claim denominators in one sentence (82, 19, 37, 48).
        # Prompt 094 (review v32): claim denominators were removed with purpose coding; the survey-weight denominators remain.
        self.assertIn("9 reported using them in model fitting and 7 in performance evaluation", " ".join(self.en.split()))  # prompt 113  # Prompt 100: same denominators, reordered sentence  # Prompt 106  # Prompt 107
        self.assertNotIn("seed 20260917", self.en)

    def test_figure_placement_and_logs(self):
        # Prompt 090: eight main figures, unnumbered headings; each figure sits before the next section heading.
        for pdf, next_heading in (("bmc_main.pdf", "Discussion"), ("bmc_main_ko.pdf", "고찰")):
            with fitz.open(ROOT / "build/submission" / pdf) as doc:  # manuscript-only build (prompt 092)
                pages = [p.get_text() for p in doc]
            fig_pages = {int(m.group(1)): i for i, t in enumerate(pages) for m in re.finditer(r"^(?:Fig\.|그림) ?(\d+)\b", t, re.M)}
            self.assertEqual(sorted(fig_pages), list(range(1, 8)), pdf)  # Prompt 100: five main figures; six since prompt 107  # Prompt 107  # prompt 112
            head = next(i for i, t in enumerate(pages) if re.search(r"^" + next_heading + r"\s*$", t, re.M))
            self.assertLessEqual(fig_pages[6], head, pdf)  # Prompt 100: last main figure is Figure 5; Figure 6 since prompt 107  # Prompt 107
        for name in ("bmc_main", "bmc_main_ko"):
            log = (ROOT / "build/submission" / f"{name}.log").read_text(errors="ignore")
            self.assertNotIn("Missing character", log)
            self.assertNotRegex(log, r"Overfull|Float too large")

    def test_locked_decisions(self):
        source = (ROOT / "tools/make_streamlined_figures.py").read_text()
        self.assertRegex(source, r"ax\.plot\(range\(4\),pct,.*zorder=2\)")
        # Figure 11 is Supplementary Figure S11 since prompt 090; the locked title format is unchanged.
        with fitz.open(ROOT / "figures/submission/fig11_methodological_appraisal.pdf") as doc:
            text = doc[0].get_text()
        self.assertEqual(text.count("N=192 studies"), 4)  # Prompt 106
        for token in ("297", "378"):  # Prompt 106
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
# prompt 116: repinned to the sentences revised for review v52 (update_historical_tests.py)
