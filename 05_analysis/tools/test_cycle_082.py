"""Scenario, current projection, source preservation and compact-note regressions."""
from pathlib import Path
import json, re, hashlib, tarfile, io
from openpyxl import load_workbook
import fitz
import build_standalone_supplements as b
from protocol_current_rules import nonclassification_applicability as branch
from protocol_reader_keys import S2_NOTE,S9_NOTE,S2_KEYS,S9_KEYS
from validate_cycle_082 import items
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'prompts/implementation_records/cycle_082'
checks={}; scenarios=[]
def check(k,v):checks[k]=bool(v)
def scenario(name,item,outcome,terms):
    # Human decision fixtures check the actual delivered rule, not a second grading algorithm.
    rule=str(public[item][5]); ok=all(t in rule for t in terms)
    scenarios.append(dict(scenario=name,item=item,expected_reading=outcome,required_rule_fragments=terms,pass_projection=ok))
    check(name,ok)
master=(ROOT/'KNHANES_ML_study_audit_protocol.md').read_text();current=items(master)
before=items((OUT/'protocol_before_082.md').read_text()); correction=json.loads((OUT/'metadata_corrections.json').read_text())
actual=[dict(item_id=k,column=i,old=v,new=current[k][i]) for k,r in before.items() for i,v in enumerate(r) if v!=current[k][i]]
expected=[{k:r[k] for k in ['item_id','column','old','new']} for r in correction['corrections']]
check('metadata_delta_exactly_declared',actual==expected)
baseline=json.loads((ROOT/'project_archive/submission_versions/v081_20260924_102044/manifest.json').read_text())
check('correction_matches_verified_v081',next(r['sha256'] for r in baseline['files'] if r['path']=='KNHANES_ML_study_audit_protocol.md')==correction['source_sha256'])
check('correction_source_hash',hashlib.sha256((OUT/'protocol_before_082.md').read_bytes()).hexdigest()==correction['source_sha256'])
check('all_382_ids_and_choices_order',list(before)==list(current) and len(current)==382 and all(before[k][10]==current[k][10] for k in before))
public={r[0]:r for r in b.human_protocol_rows(False)}
parsed=json.loads((OUT/'current_item_spec/ITEM_SPEC.json').read_text())
for iid in ['NC05','NC08','NC09','SUR11','OUT17','PRD14','ELG02','ELG05','ELG06','ELG07','DAT11','DAT12']:
 check(iid+'_parser_projection_matches_master',parsed[iid]['rule']==current[iid][12] and public[iid][1]==current[iid][8] and public[iid][3]==current[iid][7])
for tasks,claim,expected_branch in [(['REPRESENTATION_OR_PATTERN_LEARNING'],False,['APPLICABLE','NA','APPLICABLE']),(['REPRESENTATION'],False,['APPLICABLE','NA','APPLICABLE']),(['IMPUTATION'],False,['APPLICABLE','NA','NA']),(['HETEROGENEOUS_TREATMENT_EFFECT'],True,['NA','APPLICABLE','NA']),(['STRUCTURE_LEARNING'],False,['NA','NA','NA']),(['STRUCTURE_LEARNING'],True,['NA','APPLICABLE','NA']),(['CAUSAL'],True,['NA','APPLICABLE','NA']),(['CAUSAL'],None,['NA','UNCLEAR','NA'])]:
 check('branch_'+tasks[0]+'_'+str(claim),list(branch(tasks,claim).values())==expected_branch)
scenario('graph_without_causal_claim','NC08','NA',['only to describe conditional dependence is NA'])
scenario('graph_with_causal_interpretation','NC08','appraise claim',['same graph interpreted as causal requires appraisal'])
scenario('legacy_causal_not_one_modern_task','TSK11','source-specific',['no one-to-one task conversion','Keep the original token'])
scenario('representation_no_reconstruction_metric','NC05','task-appropriate appraisal',['reconstruction is not mandatory','use NR, not NA'])
scenario('single_year','SUR11','NA',['NA=single year'])
scenario('within_cycle_pooled','SUR11','assess weights',['within or across cycles','pooling established but weighting unreported'])
scenario('across_cycle_pooled_applied','SUR11','USED',['USED=explicit survey sampling-weight strategy applied'])
scenario('separate_years','SUR11','NA',['years analysed separately with no multi-year pooling'])
scenario('unclear_application','SUR11','UNCLEAR',['application ambiguous','described strategy without clear use'])
scenario('reported_not_applied','DAT13','N',['N=explicitly not applied'])
scenario('pooled_explicit_nonuse','SUR11','NOT_USED',['NOT_USED=explicitly no such strategy applied'])
scenario('class_weights_not_sampling','SUR11','not USED on this basis',['Class/loss weights do not qualify'])
scenario('adjacent_only','ELG02','exclude',['alone are ML-adjacent and excluded'])
scenario('eligible_neural_cluster_discovery','ELG02','can qualify',['neural representation central to cluster discovery can qualify'])
scenario('preprocessing_PCA','ELG07','not excluded by that step',['PCA before a central neural model does not alone exclude'])
scenario('ancillary_eligible_comparison','ELG07','does not establish eligibility',['ancillary to an adjacent-only primary analysis does not satisfy'])
scenario('pooled_training_separate_year_evaluation','DAT10','BOTH',['development pools several years','record BOTH'])
scenario('external_validation_only','ELG01','can qualify',['including use only for external/transport evaluation'])
scenario('complete_report_by_content','ELG03','content boundary',['Content, not journal/conference/preprint status'])
scenario('duplicate_distinct','ELG05','linkage decision',['Duplicate retrieval and companion-report linkage are separate'])
scenario('external_basis_with_leakage','OUT17','C0 in affected construct',['takes precedence over an external citation'])
scenario('limited_definition','OUT17','C1',['C1=assessable but limited basis'])
scenario('undefined_label','OUT17','CU',['CU=insufficient/conflicting evidence'])
scenario('recoverable_post_outcome_input','PRD14','C0 despite R2',['C0 despite R2 recovery'])
scenario('unreported_inputs','PRD14','does not prove C0',['unspecified input list alone does not prove leakage'])
for n in range(1,20):
 iid=f'REP{n:02}';check(iid+'_local_token_crosswalk','UNC;' in current[iid][10] and 'Enter UNC in the historical §15 response set; enter UNCLEAR in the current layer.' in public[iid][5])
check('historical_grade_caveat','KHM002 OUT17 and KHM003 PRD14' in master and 'not retrospectively certified' in public['PRD14'][5])
# Verify the parent finding against every current included final record.
import make_streamlined_figures as f
from study_audit_table import responses
included=[d for d in f.DOCS] if hasattr(f,'DOCS') else []
# Use the 220 IDs in the delivered master workbook rather than guess a module global.
w=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
ids=[r[0] for r in list(w['STUDIES'].values)[1:]]
violations=[]
for sid in ids:
 d=json.loads((ROOT/f'data/protocol_v1_2/final/{sid}_final.json').read_text())
 vals=lambda k:[r.get('value') for r in d['protocol_items'].get(k,[])]
 if 'NA' in vals('SUR11') and any(v in ['POOLED','BOTH'] for v in vals('DAT10')):violations.append(sid)
check('parent_zero_wrong_NA_reproduced',len(ids)==220 and not violations)
parents=json.loads((ROOT/'prompts/implementation_records/hermes_cycle_review/nonclassification_branch_cases.json').read_text())
for row in parents:
 d=json.loads((ROOT/f"data/protocol_v1_2/final/{row['study_id']}_final.json").read_text())
 for item in ['NC05','NC08','NC09']:check(row['study_id']+'_'+item+'_parent_retained',d['protocol_items'][item]==row[item])
readme=' '.join(str(c) for r in w['README'].values for c in r)
check('technical_lookup_retained',all(t in readme for t in ['ANSWERED','MODEL_SELECTIONS','RECORD_EVIDENCE','A_citation/A_DOI']))
dictionary=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s5.xlsx',read_only=True,data_only=True)
dictionary_rows={r[0]:r for r in list(dictionary.active.values)[1:]}
for key in ['C_combined_cycle_weighting','J_combined_cycle_weights']:
 check(key+'_pooled_years_definition','within or across cycles' in dictionary_rows[key][2] and 'single-cycle' not in dictionary_rows[key][2])
check('short_preambles',len(S2_NOTE.split())<60 and len(S9_NOTE.split())<60)
for n in ['02','09']:
 path=next((ROOT/'manuscript/supplementary/pdf').glob('Supplementary_Table_S'+n+'_*.pdf'))
 doc=fitz.open(path);printed=re.sub(r'\s+', ' ', ' '.join(p.get_text() for p in doc))
 check('S'+n+'_printed_labelled_key',all(k in printed for k,v in (S2_KEYS if n=='02' else S9_KEYS)))
 check('S'+n+'_no_technical_front_disclaimer','ANSWERED' not in doc[0].get_text() and 'software checks' not in doc[0].get_text())
# Compare all study-level values and complete S9 panels with the verified release.
with tarfile.open(ROOT/'project_archive/submission_versions/v081_20260924_102044/snapshot.tar.gz') as archive:
    old_master=load_workbook(io.BytesIO(archive.extractfile('manuscript/bmc_supplementary_table_s7.xlsx').read()),read_only=True,data_only=True)
    # Cycle083 changes only the scalar THR01 missing-state policy; compare all
    # other cells and verify each changed cell against actual response states.
    from study_reporting import threshold_state
    old_rows=list(old_master['STUDIES'].values);new_rows=list(w['STUDIES'].values)
    differences=[]
    for a,z in zip(old_rows[1:],new_rows[1:]):
        for col,(before_value,after_value) in enumerate(zip(a,z)):
            if before_value!=after_value:
                d=json.loads((ROOT/f'data/protocol_v1_2/final/{a[0]}_final.json').read_text())
                expected={'Y':'Y','NR':'N','NA':'NA','UNCLEAR':'UNCLEAR'}[threshold_state(d)]
                differences.append(old_rows[0][col]=='H_threshold_reported' and before_value=='N' and after_value==expected and expected in ('NA','UNCLEAR'))
    check('all_220_by_158_STUDIES_cells_unchanged_except_declared_083_flags',len(old_rows)==len(new_rows)==221 and old_rows[0]==new_rows[0] and all(differences))
    old_s9=load_workbook(io.BytesIO(archive.extractfile('manuscript/supplementary/tables/Supplementary_Table_S09_Study_protocol_audit_results.xlsx').read()),read_only=True,data_only=True)
    new_s9=load_workbook(ROOT/'manuscript/supplementary/tables/Supplementary_Table_S09_Study_protocol_audit_results.xlsx',read_only=True,data_only=True)
    check('all_S9_panels_A_B_C_D_cells_unchanged',old_s9.sheetnames==new_s9.sheetnames and all(list(old_s9[n].values)==list(new_s9[n].values) for n in old_s9.sheetnames))
report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'scenarios':scenarios,'wrong_NA_cases':violations}
(OUT/'applicability_tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert all(checks.values())
