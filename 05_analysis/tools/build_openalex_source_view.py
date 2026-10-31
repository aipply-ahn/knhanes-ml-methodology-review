"""Current reporting-stage DOI collapse; never modify acquisition or corpus data.
This derived input view is not a claim about the historical API/search procedure.
"""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/derived'
AUDIT = ROOT / 'prompts/implementation_records/openalex_source_dedup'

def load(name):
    return json.loads((ROOT / name).read_text())

def build():
    raw = load('results/raw/openalex_20260905.json')['records']
    evidence = load('prompts/implementation_records/openalex_recount/doi_collision_assessment.json')
    legacy = load('prompts/implementation_records/openalex_recount/legacy_merge_mapping.json')
    corpus = load('results/derived/corpus.json')['records']
    screen = load('results/derived/screen.json')['rows']
    assert len(raw) == len({r['oa_id'] for r in raw}) == 10000
    assert {r['uid'] for r in corpus} == {r['uid'] for r in screen}
    mapping = {r['oa_id']: r['target_uid'] for r in legacy if r['source'] == 'OpenAlex'}
    by_id = {r['oa_id']: r for r in raw}
    removed = set(); pairs = []
    for group in evidence:
        ids = {r['oa_id'] for r in group['records']}
        matches = [r for r in corpus if r.get('doi') == group['doi']]
        assert len(ids) == 2 and len(matches) == 1
        representative = matches[0]['oa_id']
        assert representative in ids
        assert all(by_id[i]['doi'] == group['doi'] and mapping[i] == matches[0]['uid'] for i in ids)
        other = (ids - {representative}).pop(); removed.add(other)
        pairs.append(dict(doi=group['doi'], retained_id=representative, removed_id=other,
                          representative_id=representative, corpus_uid=matches[0]['uid'],
                          evidence=group['assessment'], representative_basis='Existing corpus oa_id; no representative change'))
    records = [r for r in raw if r['oa_id'] not in removed]
    old_targets = {r['target_uid'] for r in legacy}
    retained_legacy = [r for r in legacy if not (r['source'] == 'OpenAlex' and r['oa_id'] in removed)]
    assert {r['target_uid'] for r in retained_legacy} == old_targets
    # Exercise the actual merger in memory on the derived view. Never write corpus.json.
    import census_merge as merger
    import contextlib, io
    saved_latest, saved_dump = merger.latest, merger.dump
    captured = []
    def source(pattern):
        if pattern == 'openalex_*.json': return {'records': records}
        return saved_latest(pattern)
    try:
        merger.latest = source
        merger.dump = lambda result, path: captured.append(result)
        with contextlib.redirect_stdout(io.StringIO()): merger.main()
    finally:
        merger.latest, merger.dump = saved_latest, saved_dump
    assert len(captured) == 1
    assert {r['uid'] for r in captured[0]['records']} == old_targets
    s = load('results/derived/final_selection_flow.json')['sources']
    db = s['europe_pmc_unique'] + s['pubmed_unique_beyond_europe_pmc'] + s['korean_citation_index'] + len(records)
    total = db + s['kdca_publication_list']
    counts = dict(openalex_raw=len(raw), source_preexcluded=len(removed), openalex_merge_inputs=len(records),
                  database_index_inputs=db, merged_flow_inputs=total, raw_source_total=total+len(removed),
                  remaining_duplicates=total-len(screen), screened=len(screen),
                  candidates=sum(r['tier'] != '--' for r in screen),
                  initial_merge_targets=len(old_targets), initial_remaining_merges=len(retained_legacy)-len(old_targets))
    note = ('Current reporting-stage preprocessing collapses only two verified same-DOI pairs. '
            'The frozen export remains 10,000 unique OpenAlex IDs; 9,998 is neither the original API yield '
            'nor a fully adjudicated unique-publication total. These two removals were already included in '
            'the historical net reduction and are now allocated before merging, not counted twice. '
            'Historical corpus metadata and all final screening identifiers remain unchanged.')
    view = dict(schema='openalex_source_input_view_v1', basis=note, raw_source='results/raw/openalex_20260905.json',
                raw_sha256=hashlib.sha256((ROOT/'results/raw/openalex_20260905.json').read_bytes()).hexdigest(),
                n_records=len(records), excluded_pairs=pairs, records=records)
    (OUT/'openalex_source_input_view.json').write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n')
    audit = dict(schema='openalex_source_preprocessing_v1', basis=note, counts=counts, pairs=pairs,
                 input_view='results/derived/openalex_source_input_view.json',
                 evidence_source='prompts/implementation_records/openalex_recount/doi_collision_assessment.json',
                 mapping_source='prompts/implementation_records/openalex_recount/legacy_merge_mapping.json',
                 initial_target_membership_unchanged=True, actual_merger_replay_uid_set_unchanged=True,
                 actual_merger_inputs=captured[0]['inputs'], corpus_screen_uid_sets_equal=True)
    (OUT/'openalex_source_preprocessing.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    sf=load('results/derived/final_selection_flow.json')
    sf['sources']['openalex_unique']=len(records)
    sf['sources']['openalex_raw_unique_ids']=len(raw)
    sf['sources']['database_index_inputs']=db
    sf['sources']['raw_source_total']=total+len(removed)
    sf['sources']['total_before_cross_source_deduplication']=total
    sf['source_preprocessing']=dict(openalex_same_doi_removed=len(removed), basis=note, provenance='results/derived/openalex_source_preprocessing.json')
    sf['flow']['duplicates_removed']=counts['remaining_duplicates']
    sf['closure_checks']['source_total']=f"6046 + {len(records)} + 52 + 339 + 2079 = {total}"
    sf['closure_checks']['deduplication']=f"{counts['remaining_duplicates']} + {len(screen)} = {total}"
    sf['closure_checks']['raw_yield']=f"{total} + {len(removed)} source-preexcluded = {total+len(removed)}"
    sf['provenance']['source_counts']='Current source-preprocessed merge-input reporting view; raw exports preserved. OpenAlex 10000 IDs minus two verified same-DOI excess records; PubMed 52 additional records (5128 retrieved).'
    (OUT/'final_selection_flow.json').write_text(json.dumps(sf,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(counts,indent=2))
    return audit
if __name__ == '__main__':
    build()
