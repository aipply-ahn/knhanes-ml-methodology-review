"""Regression checks for record-vs-full-text PRISMA scope."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PrismaScopeTests(unittest.TestCase):
    def test_unknown_full_text_counts_are_not_filled_by_arithmetic(self):
        flow = json.loads((ROOT / 'results/derived/final_selection_flow.json').read_text())
        retrieval = flow.get('full_text_retrieval', {})
        self.assertEqual(retrieval.get('status'), 'NOT_RECONSTRUCTABLE_FROM_CURRENT_RECORDS')
        for key in ('reports_sought', 'reports_not_retrieved', 'reports_assessed'):
            self.assertIn(key, retrieval)
            self.assertIsNone(retrieval[key])
        self.assertIsNone(flow['flow']['eligible_reports_not_retrieved'])


    def test_figure_displays_recorded_flow_and_caption_limits(self):
        import fitz
        with fitz.open(ROOT / 'figures/submission/fig1_prisma.pdf') as pdf:
            text = ' '.join(page.get_text() for page in pdf)
        # Prompt 091 (review v29): "Not advanced" became "Excluded at title and abstract screening".
        self.assertIn('Excluded at title and', text)
        self.assertIn('9,562', text)  # Prompt 106
        self.assertNotIn('one dictionary rule for', text)  # Prompt 106  # prompt 110
        # Prompt 091 (review v29): plain wording for the two KCI full-text checks.
        self.assertNotIn('ML-adjacent', text)  # Prompt 106
        flow = json.loads((ROOT / 'results/derived/final_selection_flow.json').read_text())
        self.assertEqual(flow['terminology_screen']['unresolved_fulltext_recheck_uids'], [])
        self.assertEqual(len(flow['terminology_screen']['resolved_fulltext_rechecks']), 2)
        self.assertNotIn('5,128', text)
        self.assertNotIn('earlier eligible-only', text)
        self.assertNotIn('n unknown', text)
        caption = (ROOT / 'manuscript/bmc_main.tex').read_text()
        # Prompt 088: the caption states the counts were not recorded (same meaning: unknown, not imputed).
        self.assertIn('not retrieved, and assessed were not recorded', caption)
        # Prompt 091 moved the PubMed/OpenAlex source details from the caption to Supplementary Table S3.
        self.assertIn('Source-level counts', caption)
        self.assertNotIn('Reports not retrieved\n(n=0)', text)


if __name__ == '__main__':
    unittest.main()
