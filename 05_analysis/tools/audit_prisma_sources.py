#!/usr/bin/env python3
"""Replay screening without rewriting historical records; scope retrieval honestly."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'prompts/implementation_records/prisma_reader_revision'


def load(name):
    return json.loads((ROOT / name).read_text())


def audit(update=False):
    screen = load('results/derived/screen.json')
    corpus = load('results/derived/corpus.json')['records']
    verdicts = load('results/derived/verdicts.json')
    refs = load('references/refs.json')
    by_uid = {r['uid']: r for r in screen['rows']}
    dictionaries = {k: [re.compile(p, re.I) for p in d.values()]
                    for k, d in screen['dictionaries'].items()}
    replay = Counter()
    mismatches = []
    for r in corpus:
        text = ' '.join([r.get('title') or '', r.get('title_ko') or r.get('kdca_title_ko') or '',
                         r.get('abstract') or '', ' '.join(r.get('keywords') or []),
                         ' '.join(r.get('mesh') or [])])
        tier = next((k for k in ('T1', 'T2', 'T3') if any(p.search(text) for p in dictionaries[k])), '--')
        if tier == '--' and r.get('epmc_layer') == 'B':
            tier = 'T3'
        replay[tier] += 1
        if tier != by_uid[r['uid']]['tier']:
            mismatches.append({'uid': r['uid'], 'replayed': tier, 'stored': by_uid[r['uid']]['tier']})
    kci = {'kci:' + r['kci_id']: r for r in load('references/kci_refs.json')}
    excluded_ids = {r['uid'] for r in screen['rows'] if r['tier'] == '--'}
    kci_excluded = excluded_ids & kci.keys()
    assert all(r['uid'] in kci_excluded for r in mismatches if r['stored'] == '--')
    kci_statuses = Counter(kci[u]['acquisition_screening']['status'] for u in kci_excluded)
    no_signal_count = len(excluded_ids - kci_excluded)
    candidate_ids = {r['uid'] for r in screen['rows'] if r['tier'] != '--'}
    decisions = [verdicts[u] for u in sorted(candidate_ids)]
    reasons = Counter(r['reason'].split(':')[0] for r in decisions if r['verdict'] == 'EXCLUDE')
    adjudication = load('data/protocol_v1_2/ADJUDICATION_SUMMARY.json')
    assert adjudication['decisions']['KHM065']['decision'] == 'EXCLUDE_NO_ELIGIBLE_ML'
    # KHM065 is an additional final exclusion, not the out-of-universe rec5359.
    reasons['NO_ML'] += 1
    snapshots = []
    for r in refs:
        local = ROOT / 'references/pdf' / r['pdf_file'] if r.get('pdf_file') else None
        snapshots.append({'uid': r['uid'], 'key': r['key'], 'verdict': r['verdict'],
                          'pdf_tried': bool(r.get('pdf_tried')), 'pdf_file': r.get('pdf_file'),
                          'local_pdf_exists': bool(local and local.is_file())})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'retrieval_metadata_snapshot.tsv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(snapshots[0]), delimiter='\t')
        writer.writeheader(); writer.writerows(snapshots)
    with (OUT / 'terminology_excluded_uids.tsv').open('w') as f:
        f.write('uid\ttier\treason\n')
        for uid, row in sorted(by_uid.items()):
            if row['tier'] == '--':
                reason = ('KCI acquisition status: ' + kci[uid]['acquisition_screening']['status']) if uid in kci_excluded else 'No T1/T2/T3 dictionary match; not EPMC layer B'
                f.write(f'{uid}\t--\t{reason}\n')
    report = {
        'screen_counts_replayed': dict(replay), 'screen_replay_mismatches': mismatches,
        'candidate_uids': len(candidate_ids),
        'not_advanced_screening_partition': {'no_dictionary_signal': no_signal_count, 'kci_not_advanced': len(kci_excluded), 'kci_statuses': dict(kci_statuses)},
        'unresolved_kci_fulltext_rechecks': [dict(uid=u, **kci[u]['acquisition_screening']) for u in sorted(kci_excluded) if kci[u]['acquisition_screening']['status'] == 'RECHECK_FULLTEXT'],
        'candidate_verdict_counts_before_final_adjudication': dict(Counter(r['verdict'] for r in decisions)),
        'final_exclusion_reasons': dict(reasons),
        'excluded_from_aggregation_unmatched_verdict_uids': sorted(set(verdicts) - candidate_ids),
        'final_no_ml_adjustment': '384 candidate-UID NO_ML decisions + KHM065 final exclusion = 385; rec5359 is outside the candidate UID set.',
        'retrieval_metadata_records': len(refs),
        'retrieval_metadata_local_pdfs': sum(r['local_pdf_exists'] for r in snapshots),
        'retrieval_metadata_pdf_tried': sum(r['pdf_tried'] for r in snapshots),
        'candidate_uids_without_refs_metadata': len(candidate_ids - {r['uid'] for r in refs}),
        'retrieval_scope': 'Current metadata is partial and not a complete attempt/outcome ledger. Missing metadata is not proof of unavailability; an existing PDF is not proof it was assessed. No all-candidate sought/not-retrieved/assessed totals can be inferred.',
        'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in [
            'tools/census_screen.py', 'results/derived/screen.json', 'results/derived/corpus.json',
            'results/derived/verdicts.json', 'references/refs.json', 'data/backdata/06_screening_verdicts.tsv',
            'data/protocol_v1_2/ADJUDICATION_SUMMARY.json', 'data/protocol_v1_2/final/KHM065_final.json',
            'references/kci_refs.json', 'tools/integrate_kci_screening.py',
            'results/derived/review/verdict_T3_07.json', 'results/derived/review/verdict_pass3_FT_01.json',
            'references/_logs/pdf_20260903.log', 'tools/fetch_pdf.py']},
    }
    (OUT / 'source_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    if update:
        path = ROOT / 'results/derived/final_selection_flow.json'
        sf = json.loads(path.read_text())
        sf['schema'] = 'final_selection_flow_v2'
        sf['status'] = 'RECORDED_FLOW_RECONCILED_WITH_SCREENING_AND_RETRIEVAL_GAPS'
        sf['unit'] = 'Bibliographic records through candidate eligibility decisions; eligible reports for family linkage; unique studies thereafter'
        sf['provenance']['note'] = 'Manuscript-facing source for Figure 1 and numbered Supplementary Table S3 selection-flow presentation. Arithmetic closure does not establish full-text retrieval or resolution of all screening states.'
        sf['flow']['eligible_reports_not_retrieved'] = None
        sf['terminology_screen'] = {
            'reason': 'No T1/T2/T3 dictionary signal in available metadata, or KCI acquisition status not promoted to a candidate. These are recorded non-advancement states, not uniformly definitive eligibility exclusions.',
            'source': 'tools/census_screen.py:63-84; tools/integrate_kci_screening.py:117-133; results/derived/screen.json; references/kci_refs.json acquisition_screening',
            'partition': report['not_advanced_screening_partition'],
            'unresolved_fulltext_recheck_uids': [r['uid'] for r in report['unresolved_kci_fulltext_rechecks']],
            'interpretation': 'Metadata non-matches do not prove absence of ML in full text. The two KCI RECHECK_FULLTEXT states remain unresolved; the included cohort is unchanged, not certified exhaustive.',
        }
        sf['full_text_retrieval'] = {
            'status': 'NOT_RECONSTRUCTABLE_FROM_CURRENT_RECORDS',
            'reports_sought': None, 'reports_not_retrieved': None, 'reports_assessed': None,
            'definitions': {'reports_sought': 'Full texts for which retrieval was sought',
                            'reports_not_retrieved': 'Full texts unavailable after retrieval attempts',
                            'reports_assessed': 'Full texts actually assessed for eligibility'},
            'legacy_eligible_only_zero': 0,
            'legacy_zero_scope': 'An eligible-cohort closure claim, not an all-candidate retrieval count; linked companions and excluded records were not covered by a complete retrieval ledger.',
            'record_assessment_scope': '1,499 candidates underwent eligibility decisions using available evidence; not a verified count of full texts sought or assessed.',
            'evidence': 'references/refs.json; tools/fetch_pdf.py:126-160; references/_logs/pdf_*.log; original results/derived/review/verdict_*.json',
        }
        sf['provenance']['eligibility_and_adjacent_counts'] = 'results/derived/verdicts.json restricted to 1,499 candidate UIDs in screen.json, plus KHM065 exclusion in data/protocol_v1_2/ADJUDICATION_SUMMARY.json; unmatched rec5359 and rec5405 are not additional candidates.'
        sf['provenance']['source_audit'] = 'prompts/implementation_records/prisma_reader_revision/source_audit.json'
        path.write_text(json.dumps(sf, ensure_ascii=False, indent=2)+'\n')
        from apply_kci_fulltext_rechecks import build as apply_rechecks
        apply_rechecks()
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256', 'screen_replay_mismatches')}, indent=2))


if __name__ == '__main__':
    audit('--update-flow' in sys.argv)
