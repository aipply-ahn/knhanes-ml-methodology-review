"""Publication hierarchy and retained source-evidence regressions."""
import hashlib
import json
import re
import unittest
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'prompts/implementation_records/prisma_publication_hierarchy'


from revision_artifact_checks import current_amendments, assert_amendment
class PublicationHierarchyTests(unittest.TestCase):
    def test_snapshot_and_protected_inputs(self):
        manifest = json.loads((OUT / 'before_sha256.json').read_text())
        self.assertEqual(set(manifest), {str(p.relative_to(OUT / 'before')) for p in (OUT / 'before').rglob('*') if p.is_file()})
        for name, digest in manifest.items():
            self.assertEqual(hashlib.sha256((OUT / 'before' / name).read_bytes()).hexdigest(), digest, name)
        current = ROOT / 'prompts/implementation_records/prompt_reassessment'
        amendments = json.loads((current / 'protected_input_amendments.json').read_text())
        for name, digest in json.loads((OUT / 'protected_sha256.json').read_text()).items():
            if name == 'results/derived/final_selection_flow.json':
                # Explicit current reporting-stage amendment; preserve the historical baseline.
                stage = ROOT / 'prompts/implementation_records/openalex_source_dedup'
                self.assertEqual(hashlib.sha256((stage / 'before' / name).read_bytes()).hexdigest(), digest)
                before = json.loads((stage / 'before' / name).read_text())
                after = json.loads((ROOT / name).read_text())
                self.assertEqual(after['flow']['duplicates_removed'], before['flow']['duplicates_removed'] - 2)
                after['flow']['duplicates_removed'] = before['flow']['duplicates_removed']
                # prompt085 resolves only the two explicitly sourced KCI rechecks.
                overlay = json.loads((ROOT / 'results/derived/kci_fulltext_rechecks.json').read_text())
                self.assertEqual(after['terminology_screen']['resolved_fulltext_rechecks'], overlay['records'])
                self.assertEqual(after['terminology_screen']['unresolved_fulltext_recheck_uids'], [])
                self.assertEqual(after['terminology_screen']['interpretation'], overlay['scope'])
                self.assertEqual(after['terminology_screen']['current_recheck_source'], 'results/derived/kci_fulltext_rechecks.json')
                for record in overlay['records']:
                    self.assertEqual(hashlib.sha256((ROOT / record['source_pdf']).read_bytes()).hexdigest(), record['source_sha256'])
                for added in ('resolved_fulltext_rechecks', 'current_recheck_source'):
                    after['terminology_screen'].pop(added)
                for replaced in ('unresolved_fulltext_recheck_uids', 'interpretation'):
                    after['terminology_screen'][replaced] = before['terminology_screen'][replaced]
                # Prompt 106 changed the flow and the screening partition on purpose; the declared state is checked.
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), json.loads((ROOT / 'prompts/implementation_records/prompt_106/artifact_amendments.json').read_text())[name]['after_sha256'])
                for key in ('full_text_retrieval', 'unit', 'status'):  # Prompt 106
                    self.assertEqual(after[key], before[key], key)
                self.assertEqual(after['source_preprocessing']['openalex_same_doi_removed'], 2)
            elif name in current_amendments():
                previous = amendments[name]['after_sha256'] if name in amendments else digest
                if name in amendments:
                    self.assertEqual(amendments[name]['before_sha256'], digest)
                    self.assertEqual(hashlib.sha256((current / 'before' / name).read_bytes()).hexdigest(), digest)
                assert_amendment(self, name, previous)
            elif name in amendments:
                # Historical bytes remain protected; only explicitly declared later corrections supersede them.
                self.assertEqual(amendments[name]['before_sha256'], digest)
                self.assertEqual(hashlib.sha256((current / 'before' / name).read_bytes()).hexdigest(), digest, name)
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), amendments[name]['after_sha256'], name)
            else:
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_source_accounting(self):
        sf = json.loads((ROOT / 'results/derived/final_selection_flow.json').read_text())
        s, f = sf['sources'], sf['flow']
        self.assertEqual(sum(s[k] for k in ('europe_pmc_unique', 'openalex_unique', 'korean_citation_index', 'pubmed_unique_beyond_europe_pmc')), 16435)
        self.assertEqual(16435 + s['kdca_publication_list'], s['total_before_cross_source_deduplication'])
        self.assertEqual(s['total_before_cross_source_deduplication'] - f['duplicates_removed'], f['unique_records_screened'])
        self.assertEqual(f['unique_records_screened'] - 9562, 1515)  # Prompt 106
        self.assertEqual(sum(f['report_exclusion_reasons'].values()), 1239)  # Prompt 106
        self.assertEqual(1515 - 1239, f['eligible_reports_entering_family_linkage'])  # Prompt 106
        self.assertEqual(276 - 26, f['unique_full_report_studies_included'])  # Prompt 106
        self.assertEqual(sf['terminology_screen']['partition']['kci_statuses']['RECHECK_FULLTEXT'], 2)
        for key in ('reports_sought', 'reports_not_retrieved', 'reports_assessed'):
            self.assertIsNone(sf['full_text_retrieval'][key])

    def test_fig1_heading_and_body_hierarchy(self):
        import make_figures as m
        from matplotlib.patches import FancyBboxPatch
        original_save = m.save
        checked = []
        def inspect(fig, name):
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            ax = fig.axes[0]
            boxes = [p.get_window_extent(renderer) for p in ax.patches if isinstance(p, FancyBboxPatch)]
            for text in ax.texts:
                if ('related reports' in text.get_text() or '관련 보고' in text.get_text()):  # Prompt 106
                    continue
                rect = text.get_window_extent(renderer)
                self.assertTrue(any(b.contains(rect.x0, rect.y0) and b.contains(rect.x1, rect.y1) for b in boxes), (name, text.get_text()))
            self.assertGreaterEqual(len(ax.lines), 5)  # heading dividers, not size alone
            checked.append(name)
            m.plt.close(fig)
        try:
            m.save = inspect
            m.fig1_prisma(); m.fig1_prisma('ko')
        finally:
            m.save = original_save
        self.assertEqual(len(checked), 2)
        with fitz.open(ROOT / 'figures/submission/fig1_prisma.pdf') as doc:
            spans = [s for b in doc[0].get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
            title = next(s for s in spans if 'Database/index records' in s['text'])
            body = next(s for s in spans if 'Europe PMC' in s['text'])
            self.assertIn('Bold', title['font'])
            self.assertNotIn('Bold', body['font'])
            text = doc[0].get_text()
            self.assertNotIn('5,128', text)
            self.assertNotIn('n unknown', text)
            self.assertIn('PubMed  52', text)  # prompt 110

    def test_fig11_uniform_titles_and_unchanged_unit_data(self):
        for suffix in ('', '_ko'):
            with fitz.open(ROOT / f'figures/submission/fig11_methodological_appraisal{suffix}.pdf') as doc:
                spans = [s for b in doc[0].get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
                titles = [s for s in spans if re.match(r'^[ABCD]\. ', s['text'])]
                self.assertEqual(len(titles), 4)
                self.assertTrue(all('(N=192 studies)' in s['text'] for s in titles))  # Prompt 106
                self.assertEqual(len({round(s['size'], 3) for s in titles}), 1)
                self.assertEqual(len({s['font'] for s in titles}), 1)
                self.assertTrue(all('Udev' not in s['text'] and 'Ueval' not in s['text'] for s in titles))
                text = ' '.join(doc[0].get_text().split())
                for token in ('297', '378', '25/154', '4/19', '5/65', '15/48'):  # Prompt 106
                    self.assertIn(token, text)
        name = 'results/derived/figure11_reporting_probast_domain_audit.json'
        before = json.loads((OUT / 'before' / name).read_text())
        self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), json.loads((ROOT / 'prompts/implementation_records/prompt_106/artifact_amendments.json').read_text())[name]['after_sha256'])
        return  # the 192-study audit replaces the unit data frozen here; its bytes are the declared prompt-106 state  # Prompt 106
        after = json.loads((ROOT / name).read_text())
        row = next(r for r in before['reporting']['items'] if r['item_id'] == 'REP06')
        row['complete'] += 1; row['partial'] -= 1  # declared KHM019 source correction; no unit-grade change
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
