"""Targeted semantic regressions from independent review; never recode source records."""
from pathlib import Path
from collections import Counter
import ast,json,re
from openpyxl import load_workbook
import build_standalone_supplements as b
import make_streamlined_figures as f
from review_support import POSITIVE_THRESHOLD_CODES
from study_audit_table import responses,participant_count
from protocol_response_labels import response_choices
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_081'
checks={};details={}
def check(name,ok):checks[name]=bool(ok)
# Actual source predicates in every live sibling path reject missing/unresolved states.
negative=[None,'','NR','NA','UNC','UNCLEAR'];predicates=[]
for path in ['build_claim_matched_analysis.py','make_streamlined_figures.py','build_standalone_supplements.py','build_protocol_v1_3_addendum.py']:
    tree=ast.parse((ROOT/'tools'/path).read_text())
    nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Compare) and any(isinstance(c,ast.Name) and c.id=='POSITIVE_THRESHOLD_CODES' for c in n.comparators)]
    if not nodes and path in ['make_streamlined_figures.py','build_standalone_supplements.py']:
        # Cycle083 centralises reporting existence; exercise the imported helper,
        # retaining every previous negative and positive fixture.
        import importlib
        module=importlib.import_module(path[:-3])
        check(path+'_positive_predicate_exists', callable(module.threshold_reported))
        evaluate=lambda v:module.threshold_reported({'protocol_items':{'THR01':[{'value':v}]}})
        check(path+'_rejects_null_empty_unclear',not any(evaluate(v) for v in negative))
        check(path+'_accepts_all_positive_codes',all(evaluate(v) for v in POSITIVE_THRESHOLD_CODES))
        predicates.append(path)
    else:
        check(path+'_positive_predicate_exists',bool(nodes))
    for node in nodes:
        expr=compile(ast.Expression(node),path,'eval')
        def evaluate(value):return eval(expr,{'POSITIVE_THRESHOLD_CODES':POSITIVE_THRESHOLD_CODES,node.left.id:value})
        check(path+'_rejects_null_empty_unclear',not any(evaluate(v) for v in negative))
        check(path+'_accepts_all_positive_codes',all(evaluate(v) for v in POSITIVE_THRESHOLD_CODES))
        predicates.append(path)
core=f.CLS
codes={'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}
eligible=[d for d in core if codes & set(f.PURPOSE_BY_ID[d['study_id']]['proposed_use'])]
def parts(d):return [f.has(d,'VAL02',{'EXTERNAL','TEMPORAL'}),any(f.has(d,k,{'R'}) for k in ['MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R']),any(v in POSITIVE_THRESHOLD_CODES for v in f.flat_values(d,'THR01'))]
counts=[sum(parts(d)[i] for d in eligible) for i in range(3)];ids=[d['study_id'] for d in eligible if all(parts(d))]
check('core_48_components_18_9_23_unchanged',len(eligible)==48 and counts==[18,9,23])
check('five_cooccurrence_study_ids_unchanged',sorted(ids)==['KHM002','KHM033','KHM087','KHM089','KHM178'])
check('missing_threshold_is_negative',not any(v in POSITIVE_THRESHOLD_CODES for v in f.flat_values({'protocol_items':{}},'THR01')))
false=[d['study_id'] for d in core if any(v not in {'NR','NA','UNC'} for v in f.flat_values(d,'THR01')) != any(v in POSITIVE_THRESHOLD_CODES for v in f.flat_values(d,'THR01'))]
check('zero_observed_threshold_changes',not false)
comparison=json.loads((ROOT/'prompts/implementation_records/hermes_cycle_review/construct_comparison.json').read_text())
for u,r in [('OUT16','REP06'),('PRD13','REP07')]:
    tab=Counter(f.reduce_recoverability(d,u)+'/'+f.flat_values(d,r)[0] for d in core)
    check(u+'_independent_cross_tab_reproduced',dict(tab)==comparison['comparisons'][u+'_'+r]['cells'])
    details[u]=dict(tab)
w=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s5.xlsx',read_only=True,data_only=True)
dictrows={r[0]:r for r in list(w.active.values)[1:]}
check('PRD13_R2_fully_recoverable','R2=Fully recoverable' in dictrows['F_candidate_set_completeness'][5])
check('performance_R2_R_squared','R2=R-squared' in dictrows['H_metrics_reported'][5])
check('PRD13_candidate_final_coding_linkage',all(x in dictrows['F_candidate_set_completeness'][2] for x in ['candidate and final selected','coding','model linkage']))
check('S5_study_cooccurrence_semantics','no same-model' in dictrows['M_individual_application_support_criteria_met'][2])
s2=load_workbook(b.TABLES/'Supplementary_Table_S02_Operational_definitions_coding_rules.xlsx',read_only=True,data_only=True)
lookup={r[0]:r for r in list(s2['Response lookup'].values)[1:]}
raw={r[0]:r[4] for r in b.human_protocol_rows(False) if r[4]}
check('S2_raw_choices_lossless_lookup',set(lookup)==set(raw) and all(lookup[k][1]==v for k,v in raw.items()))
printed={r[0]:r[4] for r in list(s2.active.values)[1:] if r[4]}
check('S2_display_lookup_roundtrip',all(lookup[k][2]==printed[k]==response_choices(raw[k],k) for k in raw))
check('S2_no_underscore_codes_in_responses',not any(re.search(r'\b[A-Z]+_[A-Z_]+\b',str(v)) for v in printed.values()))
# Units only when identities are verified, never for duplicated or unknown IDs.
d={'units':{'outcomes':[{'outcome_id':'O1'},{'outcome_id':'O2'}]},'protocol_items':{'OUT10':[{'unit_id':i,'value':'CURRENT','value_status':'ANSWERED'} for i in ['O1','O2']]}}
check('S9_named_units_when_verified',responses(d,'OUT10')=='Current health state: 2 outcomes')
d['protocol_items']['OUT10'][1]['unit_id']='O1'
check('S9_duplicate_ids_are_response_records',responses(d,'OUT10')=='Current health state: 2 response records')
d['protocol_items']['OUT10'][1]['value_status']='PENDING'
check('S9_pending_prominent','Pending' in responses(d,'OUT10'))
check('S9_whole_participants',participant_count('1234.0|2000')=='1,234; 2,000')
s9=load_workbook(b.TABLES/'Supplementary_Table_S09_Study_protocol_audit_results.xlsx',read_only=True,data_only=True)
allcells=' '.join(str(v) for sh in s9 for row in sh.values for v in row)
check('S9_no_answered_wrappers_or_no_positive_code','[ANSWERED]' not in allcells and 'No positive code' not in allcells)
check('S9_descriptive_cross_tab_present',len(list(s9['Panel D'].values))==7)
check('S9_fallback_honest','response records' in allcells and 'Criterion not documented as met' in allcells)
check('S9_evidence_entry_points_tagged','OUT10: KHM' in allcells and 'PD_OVERALL: KHM' in allcells)
for name in ['bmc_main.tex','bmc_main_ko.tex']:
    text=(ROOT/'manuscript'/name).read_text()
    labels=set(re.findall(r'\\label\{([^}]+)\}',text));refs=set(re.findall(r'\\ref\{([^}]+)\}',text))
    check(name+'_references_resolve',refs<=labels)
check('canonical_english',not re.search('[가-힣]',(ROOT/'KNHANES_ML_study_audit_protocol.md').read_text()))
report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'details':{**details,'components':counts,'eligible':len(eligible),'all_three_ids':ids,'threshold_changes':false}}
(OUT/'targeted_semantic_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert all(checks.values())
