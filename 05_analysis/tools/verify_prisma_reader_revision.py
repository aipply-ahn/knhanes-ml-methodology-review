#!/usr/bin/env python3
"""Verify bounded PRISMA revision and final rendered artifacts."""
import hashlib
import json
import re
from pathlib import Path

import fitz
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = ROOT / 'prompts/implementation_records/prisma_reader_revision'
OUT = ROOT / 'prompts/implementation_records/prisma_publication_hierarchy'


def main():
    checks = {}
    protected = json.loads((OUT / 'protected_sha256.json').read_text())
    checks['unrelated_scientific_inputs_and_figures_unchanged'] = all(
        hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in protected.items())
    snapshot = OUT / 'before'
    for name in ('bmc_main.tex', 'bmc_main_ko.tex'):
        old = (snapshot / 'manuscript' / name).read_text()
        new = (ROOT / 'manuscript' / name).read_text()
        checks[name + '_preamble_unchanged'] = old.split(r'\begin{document}')[0] == new.split(r'\begin{document}')[0]
        pattern = r'^.*(?:geometry|textwidth|textheight|documentclass|linenumber|linenumbers|pagestyle|oddsidemargin|evensidemargin|topmargin).*$'
        checks[name + '_all_layout_commands_unchanged'] = re.findall(pattern, old, re.M) == re.findall(pattern, new, re.M)
    audit = json.loads((SOURCE_AUDIT / 'source_audit.json').read_text())
    sf = json.loads((ROOT / 'results/derived/final_selection_flow.json').read_text())
    p = audit['not_advanced_screening_partition']
    checks['screen_partition'] = p['no_dictionary_signal'] + p['kci_not_advanced'] == sf['flow']['terminology_exclusions']
    checks['kci_states_preserved'] = sum(p['kci_statuses'].values()) == p['kci_not_advanced'] and p['kci_statuses']['RECHECK_FULLTEXT'] == 2
    checks['no_ml_reason_uid_scope'] = audit['final_exclusion_reasons']['NO_ML'] == 385 and audit['excluded_from_aggregation_unmatched_verdict_uids'] == ['rec5359', 'rec5405']
    checks['eligibility_reason_total'] = sum(audit['final_exclusion_reasons'].values()) + sf['flow']['ml_adjacent_reports_catalogued'] == sf['flow']['reports_excluded_total']
    render_info = {}
    for name, term in [('bmc_main', 'Not advanced'), ('bmc_main_ko', '다음 단계 미진입')]:
        with fitz.open(ROOT / 'manuscript' / (name + '.pdf')) as doc:
            matches = [(i, page) for i, page in enumerate(doc) if term in page.get_text()]
            checks[name + '_one_figure1_page'] = len(matches) == 1
            i, page = matches[0]
            render_dir = OUT / 'rendered'
            render_dir.mkdir(exist_ok=True)
            page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8)).save(render_dir / f'{name}_page_{i+1}.png')
            text = page.get_text()
            checks[name + '_caption_and_unknown_counts_on_page'] = all(token in text for token in ('9,515', '9,578', '1,499', '220', 'S3')) and ('assessed are unavailable' in ' '.join(text.split()) if name == 'bmc_main' else '전체건수는알수없다' in ''.join(text.split()))
            spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
            checks[name + '_page_text_inside_bounds'] = all(fitz.Rect(s['bbox']).x0 >= 0 and fitz.Rect(s['bbox']).y0 >= 0 and fitz.Rect(s['bbox']).x1 <= page.rect.width and fitz.Rect(s['bbox']).y1 <= page.rect.height for s in spans)
            render_info[name] = {'page': i + 1, 'page_count': len(doc), 'minimum_text_font_pt': min(s['size'] for s in spans)}
    book = load_workbook(ROOT / 'manuscript/supplementary/tables/Supplementary_Table_S03_Search_strategies_and_yields.xlsx', read_only=True)
    checks['s3_workbook_scope_panel'] = 'Screening and retrieval' in book.sheetnames and 'Screening sources' in book.sheetnames
    with fitz.open(ROOT / 'manuscript/bmc_supplementary.pdf') as doc:
        matches = [i for i, page in enumerate(doc) if 'RECHECK_FULLTEXT' in page.get_text() and '605' in page.get_text()]
        checks['s3_combined_scope_panel'] = len(matches) == 1
        render_info['supplement_s3_scope_page'] = [i+1 for i in matches]
    result = {'checks': checks, 'pass': all(checks.values()), 'protected_files': len(protected), 'render_info': render_info}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    assert result['pass']


if __name__ == '__main__':
    main()
