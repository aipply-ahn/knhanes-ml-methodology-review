#!/usr/bin/env python3
"""Derive claim-matched practice and purpose-stratified appraisal counts."""
from review_support import POSITIVE_THRESHOLD_CODES
import glob, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PURPOSE=json.loads((ROOT/'results/derived/study_purpose_audit.json').read_text())
PBY={r['study_id']:r for r in PURPOSE['records']}
V13=json.loads((ROOT/'data/protocol_v1_3/purpose_evidence_addendum.json').read_text())
V13BY={r['study_id']:r for r in V13['records']}

def vals(d,k):
    out=[]
    for row in d.get('protocol_items',{}).get(k,[]):
        v=row.get('value'); out.extend(v if isinstance(v,list) else [v])
    return out
def has(d,k,*wanted): return bool(set(vals(d,k)) & set(wanted))
def included(d): return d.get('corpus_status',{}).get('include',has(d,'ELG04','Y'))

docs=[json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(ROOT/'data/protocol_v1_2/final/KHM*_final.json')))]
docs=[d for d in docs if included(d)]

def record(d): return PBY[d['study_id']]
def survey_design_reported(d):
    return has(d,'SUR04','USED') and (has(d,'SUR08','USED') or has(d,'SUR09','USED') or has(d,'SUR10','USED'))
def association_design_supported(d):
    # v1.3 requires the survey handling to be linked to a substantive
    # association output; study-level coexistence alone is not sufficient.
    return V13BY[d['study_id']]['association_audit']['population_association_was_survey_aware']=='Y'
def calibrated(d): return any(has(d,k,'R') for k in ('MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R'))
def threshold_reported(d): return any(x in POSITIVE_THRESHOLD_CODES for x in vals(d,'THR01'))
def independent_validation(d): return has(d,'VAL02','EXTERNAL','TEMPORAL')

population_claim=[d for d in docs if 'POPULATION_SURVEILLANCE_OR_POLICY' in record(d)['proposed_use']]
association_claim=[d for d in docs if 'POPULATION_ASSOCIATION_ANALYSIS' in record(d)['health_analysis_purpose_components']]
application_codes={'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}
application_claim=[d for d in docs if set(record(d)['proposed_use']) & application_codes and has(d,'TSK01','CLS')]
importance_claim=[d for d in docs if record(d)['study_category']=='HEALTH_ANALYSIS' and has(d,'VI01','USED')]

def intersection(rows, tests): return sum(all(fn(d) for fn in tests) for d in rows)

strata={}
for orientation in ('HEALTH_ANALYSIS','METHOD_RESEARCH'):
    rows=[d for d in docs if record(d)['study_category']==orientation and has(d,'TSK01','CLS','CONT')]
    rep=Counter(next((x for x in vals(d,'REP17') if x!='NA'),'NA') for d in rows)
    pd=Counter(x for d in rows for x in vals(d,'PD_OVERALL') if x!='NA')
    pe=Counter(x for d in rows for x in vals(d,'PE_OVERALL') if x!='NA')
    strata[orientation]={'prediction_studies':len(rows),'final_model_specification':dict(rep),
                         'probast_ai_development_units':dict(pd),'probast_ai_evaluation_units':dict(pe)}

out={
 'schema':'claim_matched_practice_analysis_v1',
 'analysis_status':'POST_HOC_DESCRIPTIVE; criteria are claim-matched and not universal failure rules',
 'population_or_policy_claim':{'denominator':len(population_claim),'survey_weights_plus_strata_cluster_or_design_variance':intersection(population_claim,[survey_design_reported])},
 'population_association_purpose':{
     'denominator':len(association_claim),
     'substantive_association_output':sum(V13BY[d['study_id']]['association_audit']['association_was_substantive_output']=='Y' for d in association_claim),
     'weights_and_design_based_uncertainty':intersection(association_claim,[association_design_supported]),
     'linkage_rule':'v1.3 association output and survey-aware analysis; study-level coexistence alone excluded'},
 'screening_or_individual_application_claim':{
     'denominator':len(application_claim),'independent_or_later_period_validation':intersection(application_claim,[independent_validation]),
     'calibration':intersection(application_claim,[calibrated]),'positive_decision_rule_reported':intersection(application_claim,[threshold_reported]),
     'relaxed_validation_plus_calibration_or_threshold':sum(
         independent_validation(d) and (calibrated(d) or threshold_reported(d)) for d in application_claim),
     'strict_all_three':intersection(application_claim,[independent_validation,calibrated,threshold_reported]),
     # Backward-compatible alias used by the existing supplement generator.
     'all_three':intersection(application_claim,[independent_validation,calibrated,threshold_reported]),
     'criterion_definition':{
         'strict':'independent or later-period validation + calibration + explicit positive-class decision rule',
         'relaxed':'independent or later-period validation + at least one of calibration or an explicit positive-class decision rule',
         'components':'Study-level reported-component summary: independent any-record checks within each study; no same-model, outcome or evaluation linkage required. Threshold reporting does not require independent selection or justification.'}},
 'explicit_model_based_variable_importance':{'denominator':len(importance_claim),'stability_assessed':intersection(importance_claim,[lambda d:has(d,'VI16','USED')])},
 'purpose_stratified_reporting_and_probast_ai':strata,
 'study_ids':{
     'population_or_policy_claim':[d['study_id'] for d in population_claim],
     'population_association_purpose':[d['study_id'] for d in association_claim],
     'screening_or_individual_application_claim':[d['study_id'] for d in application_claim],
     'explicit_model_based_variable_importance':[d['study_id'] for d in importance_claim]},
}
(ROOT/'results/derived/claim_matched_practice_analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
