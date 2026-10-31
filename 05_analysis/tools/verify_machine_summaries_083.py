"""Link the full-classification compatibility summary to the current core summary."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_083'
legacy=json.loads((ROOT/'results/derived/protocol_v1_2_consensus_results.json').read_text())
core=json.loads((ROOT/'results/derived/study_reporting_summary.json').read_text())
public=json.loads((OUT/'public_reconstruction.json').read_text())
assert legacy['denominators']['classification']==196
assert len(legacy['classification']['reporting_prevalence']['by_study'])==196
assert len(core['by_study'])==165
assert all(r==legacy['classification']['reporting_prevalence']['by_study'][sid]==public['by_study'][sid] for sid,r in core['by_study'].items())
report={'status':'PASS','full_classification_studies':196,'current_health_core_studies':165,'core_states_match_independent_public_reconstruction':True,'scope':'Compatibility *_primary keys now contain order-invariant categorical or overlapping method-presence summaries, not scientific primary-unit claims. Former archived tables/figures were not regenerated.'}
(OUT/'machine_summary_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
