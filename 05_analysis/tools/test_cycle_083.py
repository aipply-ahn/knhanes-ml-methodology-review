"""Order, mixed-state and linkage regressions; migration is an explicit policy change."""
from pathlib import Path
import json, copy, random, csv, tarfile, io
from collections import Counter
from openpyxl import load_workbook
import make_streamlined_figures as f
from study_reporting import *
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_083'
checks={}
def check(k,v):
    checks[k]=bool(v)
    assert v,k
cases=[(['NA','OTHER'],'Y'),(['NR','OTHER'],'Y'),(['UNCLEAR'],'UNCLEAR'),([None,''],'UNCLEAR'),([], 'UNCLEAR'),(['NA','NA'],'NA'),(['NA','NR'],'NR'),(['NR','UNCLEAR'],'UNCLEAR'),(['UNKNOWN'],'UNCLEAR'),(['OTHER','UNCLEAR',None],'Y'),([[]],'UNCLEAR')]
for i,(vs,result) in enumerate(cases):
    check('mixed_state_'+str(i),reduce_reporting([{'value':v} for v in vs],POSITIVE_THRESHOLD_CODES)==result)
old_a={'protocol_items':{'THR01':[{'value':'NR'},{'value':'OTHER'}]}}
old_b=copy.deepcopy(old_a);old_b['protocol_items']['THR01'].reverse()
check('old_policy_demonstrably_order_dependent',(f.first_applicable(old_a,'THR01') in POSITIVE_THRESHOLD_CODES)!=(f.first_applicable(old_b,'THR01') in POSITIVE_THRESHOLD_CODES))
check('new_policy_fixes_old_counterexample',threshold_state(old_a)==threshold_state(old_b)=='Y')
check('partial_distribution_not_full',reduce_reporting([{'value':'P'},{'value':'NR'}],{'R'},{'P'})=='P')
check('full_distribution_over_partial',reduce_reporting([{'value':'P'},{'value':'R'}],{'R'},{'P'})=='Y')
def response(unit,v,links=None):return {'primary_unit':'Evaluation','unit_id':unit,'value':v,'related_ids':links or {'model_id':'M','dataset_id':'D','outcome_id':'O'}}
d={'units':{'evaluations':[{'evaluation_id':'E1','model_id':'M','dataset_id':'D','outcome_id':'O'},{'evaluation_id':'E2','model_id':'M','dataset_id':'D','outcome_id':'O'}]},'protocol_items':{'THR01':[response('E1','OTHER')],'THR03':[response('E2','USED')]}}
check('same_model_dataset_different_evaluation_not_joined',not linked_independent_units(d))
d['protocol_items']['THR03']=[response('E1','USED')];check('same_evaluation_joined',linked_independent_units(d)==['E1'])
duplicate=copy.deepcopy(d);duplicate['units']['evaluations'].append({'evaluation_id':'E1','dataset_id':'conflict'})
check('duplicate_conflicting_registry_rejected',not linked_independent_units(duplicate))
duplicate['units']['evaluations'].reverse()
check('duplicate_registry_order_invariant',not linked_independent_units(duplicate))
d['protocol_items']['THR03'][0]['related_ids']['dataset_id']='D2';check('conflicting_dataset_not_joined',not linked_independent_units(d))
d['protocol_items']['THR03']=[response('missing','USED')];d['protocol_items']['THR01']=[response('missing','OTHER')];check('unregistered_id_not_joined',not linked_independent_units(d))
for v in [None,'','NR','NA','UNC','UNCLEAR',True,False,-1,0,1.5,'unknown',[]]:
 check('invalid_sample_'+str(v),not sample_size_reported({'protocol_items':{'VAL10':[{'value':v}]}}))
for v in [1,1.0,'123','123.0']:check('valid_sample_'+str(v),sample_size_reported({'protocol_items':{'VAL10':[{'value':v}]}}))
check('altered_not_original',study_reporting({'protocol_items':{'IMB04':[{'value':'ALTERED'}]}})['original_prevalence']!='Y')
base=reporting_summary(f.CLS);delta=[];rng=random.Random(83)
for doc in f.CLS:
    sid=doc['study_id'];expected=study_reporting(doc)
    for repeat in range(8):
        perm=copy.deepcopy(doc)
        for rs in perm['protocol_items'].values():rng.shuffle(rs)
        for rs in perm.get('units',{}).values():rng.shuffle(rs)
        check(sid+'_permutation_'+str(repeat),study_reporting(perm)==expected and all(categorical_methods(perm,k)==categorical_methods(doc,k) for k in ['PRE01','IMB01']))
    old={'threshold_reported':f.first_applicable(doc,'THR01') in POSITIVE_THRESHOLD_CODES,'threshold_independent':f.first_applicable(doc,'THR03')=='USED','class_distribution':f.first_applicable(doc,'IMB05')=='R'}
    for k,v in old.items():
        new=sid in base['members'][k]
        if v!=new:delta.append({'study_id':sid,'indicator':k,'before':v,'after':new,'reason':'At least one unit; same-evaluation join for independence','source_units':json.dumps(records(doc,{'threshold_reported':'THR01','threshold_independent':'THR03','class_distribution':'IMB05'}[k]),ensure_ascii=False)})
    for k in ['PRE01','IMB01']:
        before=f.first_applicable(doc,k);after=categorical_methods(doc,k)
        if before!=after:delta.append({'study_id':sid,'indicator':k,'before':before,'after':after,'reason':'Distinct categorical methods -> MULTIPLE; no presumed primary unit','source_units':json.dumps(records(doc,k),ensure_ascii=False)})
for k,expected in {'threshold_reported':['KHM004','KHM089','KHM135'],'threshold_independent':['KHM089','KHM135','KHM178','KHM221'],'class_distribution':['KHM003','KHM005','KHM051','KHM074','KHM085','KHM089','KHM103','KHM123','KHM178']}.items():
 check(k+'_named_differences',sorted(r['study_id'] for r in delta if r['indicator']==k)==expected)
check('165_core',len(base['by_study'])==165)
check('observed_counts',{k:len(v) for k,v in base['members'].items()}=={'threshold_reported':41,'threshold_independent':18,'class_distribution':37,'sample_size':106,'original_prevalence':41})
check('states',base['decision_states']=={'NR':108,'NA':16,'Y':41})
with (OUT/'study_deltas.tsv').open('w') as fp:
 writer=csv.DictWriter(fp,fieldnames=list(delta[0]),delimiter='\t');writer.writeheader();writer.writerows(delta)
# Every STUDIES cell except exactly justified scalar missing-state corrections stays fixed.
w=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
with tarfile.open(ROOT/'project_archive/submission_versions/v082_20260924_104700/snapshot.tar.gz') as archive:
 oldw=load_workbook(io.BytesIO(archive.extractfile('manuscript/bmc_supplementary_table_s7.xlsx').read()),read_only=True,data_only=True)
 h,*new=list(w['STUDIES'].values);oh,*old=list(oldw['STUDIES'].values);check('study_headers_preserved',h==oh)
 changes=[]
 for a,b in zip(old,new):
  check(a[0]+'_same_study',a[0]==b[0])
  for j,(av,bv) in enumerate(zip(a,b)):
   if av!=bv:
    doc=json.loads((ROOT/f'data/protocol_v1_2/final/{a[0]}_final.json').read_text())
    expected={'Y':'Y','NR':'N','UNCLEAR':'UNCLEAR','NA':'NA'}[threshold_state(doc)]
    check(a[0]+'_declared_flag_delta',h[j]=='H_threshold_reported' and av=='N' and bv==expected and bv in ('NA','UNCLEAR'))
    changes.append({'study_id':a[0],'field':h[j],'old':av,'new':bv})
 old9=load_workbook(io.BytesIO(archive.extractfile('manuscript/supplementary/tables/Supplementary_Table_S09_Study_protocol_audit_results.xlsx').read()),read_only=True,data_only=True)
 new9=load_workbook(ROOT/'manuscript/supplementary/tables/Supplementary_Table_S09_Study_protocol_audit_results.xlsx',read_only=True,data_only=True)
 check('all_S9_cells_unchanged',old9.sheetnames==new9.sheetnames and all(list(old9[n].values)==list(new9[n].values) for n in old9.sheetnames))
(OUT/'study_flag_deltas.json').write_text(json.dumps(changes,indent=2)+'\n')
dictionary=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s5.xlsx',read_only=True,data_only=True)
dictionary_rows={r[0]:r for r in list(dictionary.active.values)[1:]}
tr=dictionary_rows['H_threshold_reported']
check('threshold_dictionary_study_unit',tr[3]=='Study (across evaluations)')
check('threshold_dictionary_exact_states',all(v in tr[5] for v in ['Y','N','UNCLEAR','NA']))
check('threshold_dictionary_derivation','THR01' in tr[7] and 'THR03' in tr[7])
from reconstruct_reporting_083 import reconstruct
reconstruct()
(OUT/'tests.json').write_text(json.dumps({'status':'PASS','checks':checks,'study_deltas':len(delta),'study_flag_deltas':changes},indent=2)+'\n')
print('PASS',len(checks),'checks;',len(changes),'exact S7 flag changes')
