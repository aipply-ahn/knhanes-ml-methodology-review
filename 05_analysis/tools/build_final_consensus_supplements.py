#!/usr/bin/env python3
"""Build archived pre-embedding snapshots of former Additional files 2--7."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"project_archive/paper_cleanup_20260918_002038/internal/"
     "supplement_sources/archive_pre_embedded_20260914")
APP.mkdir(parents=True, exist_ok=True)
C=json.loads((ROOT/"results/derived/protocol_v1_2_consensus_results.json").read_text())
A=json.loads((ROOT/"data/protocol_v1_2/ADJUDICATION_SUMMARY.json").read_text())
M=json.loads((ROOT/"results/derived/master_manuscript_results.json").read_text())
T=json.loads((ROOT/"results/derived/exploratory_temporal_practice_analysis.json").read_text())
E=json.loads((ROOT/"results/derived/expanded_model_task_audit.json").read_text())
P=json.loads((ROOT/"results/derived/study_purpose_audit.json").read_text())
CM=json.loads((ROOT/"results/derived/claim_matched_practice_analysis.json").read_text())
N=C["denominators"]; CL=C["classification"]
HEADER=("**Canonical source:** `data/protocol_v1_2/final/*.json` (222 locked full-report packets "
        "representing 220 included study families, one excluded non-ML report, and one preprint "
        "consolidated with its journal report; evidence/unit validation and prespecified rule-based "
        "reconciliation complete). P2 is a blinded LLM agent, "
        "not an independent human reviewer. Full item-, unit-, metric-, visual-, and evidence-level records are in Additional file 8.\n\n")
def table(headers, rows):
    return "| "+" | ".join(headers)+" |\n|"+"|".join(["---"]*len(headers))+"|\n"+"\n".join("| "+" | ".join(map(str,r))+" |" for r in rows)+"\n"
def write(name,title,body): (APP/name).write_text(f"# {title}\n\n{HEADER}{body}\n",encoding="utf-8")

write("additional_file2_methods.md","Additional file 2. Review methods and denominator safeguards",
f"""## Table S2.1. Final review chain

{table(['Stage','Status','Record'],[['P1','Legacy evidence migration; retained for provenance','222'],['P2','Blinded source-read LLM review; COMPLETE','222'],['Validation','Evidence, unit, metric, and panel-parent integrity; PASS','222'],['Reconciliation','Prespecified rule prioritising source-read P2; COMPLETE','222']])}

## Table S2.2. Final denominators

{table(['Denominator','n'],[['Screened full reports',N['reports']],['Included unique studies',N['studies']],['Classification',N['classification']],['Continuous-outcome prediction',N['continuous']],['Other primary tasks',N['other']],['Prediction-model studies',N['prediction']],['Development units',C['probast_ai']['development']['n_units']],['Evaluation units',C['probast_ai']['evaluation']['n_units']]])}

## Table S2.3. Adjudication rules

Comparisons used semantic unit identifiers and evidence references, never list position. Exact agreements and every adjudicated item retain P1/P2 provenance. External-validation-only KNHANES reports were eligible. Unconfirmed integrity signals were flagged rather than automatically excluded. KHM068 was retained for corpus history, descriptions of historically reported methods, and methodological appraisal, but excluded from valid performance evidence and substantive effectiveness claims. Excluding its one development and two evaluation units in sensitivity analysis gave 282/307 low-quality development units and 397/399 high-risk evaluation units, compared with 283/308 and 399/401 in the historical-practice appraisal.
""")

dec=[]
for sid,d in A['decisions'].items(): dec.append([sid,d['decision'],d.get('include',''),d['rationale']])
write("additional_file3_evidence_nonclassification.md","Additional file 4. Evidence base, task groups, and corpus decisions",
f"""## Table S4.1. Included primary-task groups

{table(['Task','n'],[['Classification',N['classification']],['Continuous outcome',N['continuous']],['Other',N['other']]])}

## Table S4.2. KNHANES data role

{table(['Role','n'],[[k,v] for k,v in C['knhanes_role'].items()])}

## Table S4.3. Prespecified corpus decisions

{table(['Study','Decision','Included','Rationale'],dec)}

KHM191/KHM195 and KHM197/KHM198 remain separate papers. Their similarity is retained as an integrity signal only. The 30 included reports with an integrity flag were not excluded solely because a signal was unconfirmed.
""")

def rows(mapping, labels): return [[labels.get(k,k),v] for k,v in mapping.items()]
relationships=Counter(x['ml_statistical_relationship'] for x in E['studies'] if x['task_group']=='CLS')
_final_docs=[json.loads(p.read_text()) for p in sorted((ROOT/'data/protocol_v1_2/final').glob('KHM*_final.json'))]
_cls_docs=[d for d in _final_docs if d.get('corpus_status',{}).get('include',d['protocol_items']['ELG04'][0]['value']=='Y') and d['protocol_items']['TSK01'][0]['value']=='CLS']
def _pvals(d,k):
    out=[]
    for row in d['protocol_items'][k]:
        v=row.get('value'); out.extend(v if isinstance(v,list) else [v])
    return out
_basis_codes=['CLINICAL','INSTRUMENT','REFERENCE','DATA','NR','UNEXPLAINED']
_basis=Counter(code for d in _cls_docs for code in set(_pvals(d,'OUT12')) if code in _basis_codes)
_basis_applicable=sum(any(v!='NA' for v in _pvals(d,'OUT12')) for d in _cls_docs)
write("additional_file4_classification.md","Additional file 6. Adjudicated classification workflow",
f"""This file shadows the classification Results using the final denominator of {N['classification']} studies.

## Table S6.1. Outcome and predictor construction

{table(['Assessment','Robust','Limited','High concern','Not assessable'],[['Outcome',CL['outcome_adequacy'].get('ROBUST',0),CL['outcome_adequacy'].get('LIMITED',0),CL['outcome_adequacy'].get('HIGH',0),CL['outcome_adequacy'].get('NAU',0)],['Predictors',CL['predictor_adequacy'].get('ROBUST',0),CL['predictor_adequacy'].get('LIMITED',0),CL['predictor_adequacy'].get('HIGH',0),CL['predictor_adequacy'].get('NAU',0)]])}

## Table S6.2. Reported basis for categorical outcome definition

{table(['Basis code','Classification studies'],[[k,_basis[k]] for k in _basis_codes])}

OUT12 was applicable in {_basis_applicable}/196 studies; 87 studies were structural NA.
Codes may overlap across multiple outcomes within a study. This construction-basis assessment
is distinct from the measurement source displayed in Figure 6B.

## Table S6.3. Primary missing-data strategy

{table(['Code','Studies'],rows(CL['missing_primary'],{}))}

## Table S6.4. Primary class-imbalance strategy

{table(['Code','Studies'],rows(CL['imbalance_primary'],{}))}

## Table S6.5. Class-distribution recoverability

{table(['Code','Studies'],rows(CL['class_recoverability'],{}))}

\\needspace{{14\\baselineskip}}
## Table S6.6. Decision-threshold selection

{table(['Code','Studies'],rows(CL['threshold_primary'],{}))}

## Table S6.7. Validation approaches (overlap permitted)

{table(['Code','Studies'],rows(CL['validation'],{}))}

## Table S6.8. Performance metrics (overlap permitted)

{table(['Metric','Studies'],rows(CL['metrics'],{}))}

\\needspace{{12\\baselineskip}}
## Table S6.9. Comparative uncertainty reporting

{table(['Item','Studies'],rows(CL['metric_reporting'],{}))}

## Table S6.10. Relationship between ML and conventional statistical analysis

{table(['Relationship','Classification studies'],rows(relationships,{}))}

## Table S6.11. Variable-importance and downstream-use pathway

{table(['Stage','Classification studies'],[['Explicit model-based importance',CL['importance']['VI01']],['Reduced variable set constructed',CL['importance']['VI10']],['Used in downstream statistical analysis',CL['importance']['VI11']],['Same variables clearly carried forward',CL['importance']['VI14']]])}

## Table S6.12. Variable-contribution methods (overlap permitted)

{table(['Method','Classification studies'],rows(M['vi_methods'],{}))}

## Table S6.13. Author-stated rationale for using ML (overlap permitted)

{table(['Rationale code','Studies'],[[k,v] for k,v in C['content'].items() if k.startswith('RAT_')])}

## Tables S6.14--S6.16. Unit-level records

The nonexchangeable model rankings, 6,128 metric records, 308 best-model selections, class-imbalance details, visual evidence, and their evidence references are supplied without pooling in Additional file 8 and `INTEGRATED_STUDY_AUDIT.xlsx`.
""")

content=C['content']; imp=CL['importance']
write("additional_file5_analytic_function.md","Additional file 5. Adjudicated analytic function, importance, and claims",
f"""## Table S5.1. Post-hoc mutually exclusive study category

{table(['Study category','Studies'],rows(P['summary']['study_category'],{}))}

This descriptive extension was added after the initial synthesis. Every study is assigned to
exactly one category: health analysis or method research.

### Table S5.1a. Mutually exclusive type of method research

{table(['Method-research type','Studies'],rows(P['summary']['method_research_category'],{}))}

### Table S5.1b. Mutually exclusive purpose of health analysis

{table(['Health-analysis purpose','Studies'],rows(P['summary']['health_analysis_purpose'],{}))}

Purpose was adjudicated from the primary objective, main result or evaluation target, and the
contribution repeated in the title, abstract, and conclusion. No fixed priority hierarchy was
used; co-primary aims were retained as multiple co-primary purposes, separately from genuinely
unclear primary purposes.

### Table S5.1c. Nonexclusive purpose components in health-focused studies

{table(['Purpose component','Studies'],rows(P['summary']['health_analysis_purpose_components'],{}))}

### Table S5.1d. Purpose combinations in the 53 multiple-co-primary studies

{table(['Combination','Studies'],rows(P['summary']['multiple_co_primary_combinations'],{}))}

### Table S5.1e. Proposed use in health-focused studies (overlap permitted)

{table(['Proposed use','Studies'],rows(P['summary']['proposed_use'],{}))}

### Table S5.1f. Actual outputs in health-focused studies (overlap permitted)

{table(['Analytic output','Studies'],rows(P['summary']['analytic_outputs'],{}))}

### Table S5.1g. Analytic stages targeted by method-focused studies (overlap permitted)

{table(['Targeted stage','Studies'],rows(P['summary']['method_intervention_stages'],{}))}

## Table S5.2. Position of KNHANES and use with other datasets

{table(['KNHANES position','Studies'],rows(P['summary']['knhanes_position'],{}))}

{table(['Joint-use mode','Studies'],rows(P['summary']['multi_dataset_use_mode'],{}))}

## Table S5.3. Stated rationale (overlap permitted)

{table(['Code','Studies'],[[k,v] for k,v in content.items() if k.startswith('RAT_')])}

## Table S5.4. Actual analytic function (overlap permitted)

{table(['Code','Studies'],[[k,v] for k,v in content.items() if k.startswith('FUN_')])}

## Table S5.5. Variable-centred pathway ({N['classification']} classification studies)

{table(['Stage','Studies'],[['Explicit model-based importance',imp['VI01']],['Model-guided subset',imp['VI10']],['Downstream statistical inference',imp['VI11']],['Exact variable carryover',imp['VI14']],['Importance stability/uncertainty',imp['VI16']],['Explanation fidelity/robustness evaluated',imp['VI17']],['Expert/user utility evaluated',imp['VI18']],['Subgroup fairness assessed',imp['VI19']]])}

## Table S5.6. Discussion claims and support (overlap permitted)

{table(['Code','Studies'],[[k,v] for k,v in content.items() if k.startswith('CLM_')])}

## Table S5.7. Claim-matched practices

{table(['Claim-defined cohort','Denominator','Matched practice','Studies'],[
 ['Population/policy use',CM['population_or_policy_claim']['denominator'],'Weights plus strata, clusters, or design-based variance',CM['population_or_policy_claim']['survey_weights_plus_strata_cluster_or_design_variance']],
 ['Population-association purpose',CM['population_association_purpose']['denominator'],'Weights plus design-based uncertainty',CM['population_association_purpose']['weights_and_design_based_uncertainty']],
 ['Screening/individual application',CM['screening_or_individual_application_claim']['denominator'],'Independent/later validation + calibration + threshold',CM['screening_or_individual_application_claim']['all_three']],
 ['Explicit model-based importance',CM['explicit_model_based_variable_importance']['denominator'],'Importance stability assessed',CM['explicit_model_based_variable_importance']['stability_assessed']],
])}

## Tables S5.8--S5.12. Study-level evidence

All supporting sentences, unit references, and adjudication provenance are retained in Additional file 8 rather than duplicated here.
""")

rep=C['reporting']; surv=C['survey']; pd=C['probast_ai']['development']; pe=C['probast_ai']['evaluation']
purpose_probast=CM['purpose_stratified_reporting_and_probast_ai']
health_probast=purpose_probast['HEALTH_ANALYSIS']
method_probast=purpose_probast['METHOD_RESEARCH']
screening_package=CM['screening_or_individual_application_claim']
rep_labels={"REP01":"Title identification of study type","REP02":"Abstract summary","REP03":"Objective, intended use, and target population","REP04":"Data source, design, setting, and dates","REP05":"Eligibility, selection, and exclusions","REP06":"Outcome definition, timing, and source","REP07":"Predictor definition, timing, and availability","REP08":"Analysed sample and event/class counts","REP09":"Sample-size rationale","REP10":"Missingness, handling, and analysis stage","REP11":"Preprocessing, variable selection, and model development","REP12":"Hyperparameters, tuning, and separation from evaluation","REP13":"Internal validation, resampling, and nesting","REP14":"Evaluation data, metrics, and threshold","REP15":"Participant flow, exclusions, and characteristics","REP16":"Performance estimates and uncertainty","REP17":"Reusable final model","REP18":"Limitations, generalisability, and applicability","REP19":"Registration, protocol, data, and code/model availability"}
domain_labels={"D1":"Participants and data sources","D2":"Predictors","D3":"Outcome","D4":"Analysis"}
claim_rows=[[a,b,c,d,e,f] for a,b,c,d,e,f in M['claim_support']]
periods=['≤2019','2020–2022','2023–2024','2025–2026']
temporal_rows=[]
for group in ('interpretation_practices','algorithm_families','reproducibility_reporting'):
    for label, values in T['health_focused_classification'][group].items():
        temporal_rows.append(['health_focused_classification',label]+[f"{values[p]['n']}/{values[p]['denominator']} ({values[p]['percent']:.1f}%)" for p in periods])
topics=T['health_focused_classification']['health_topics']
for j,label in enumerate(topics['categories']):
    temporal_rows.append(['all_health_focused',f"Health topic: {label}"]+[f"{topics['counts'][i][j]}/{topics['period_denominators'][i]} ({100*topics['counts'][i][j]/topics['period_denominators'][i]:.1f}%)" for i in range(4)])
for group in ('types','targeted_stages'):
    for label, values in T['method_focused'][group].items():
        temporal_rows.append(['method_focused',label]+[f"{values[p]['n']}/{values[p]['denominator']} ({values[p]['percent']:.1f}%)" for p in periods])
write("additional_file6_appraisal.md","Additional file 7. Reporting, reproducibility, survey-design, PROBAST+AI, and temporal analyses",
f"""## Table S7.1. Reporting completeness

{table(['Item','Complete','Partial','Not reported','Unclear','NA'],[[f"{k}. {rep_labels[k]}",v.get('R',0),v.get('P',0),v.get('NR',0),v.get('UNC',0),v.get('NA',0)] for k,v in rep.items()])}

## Table S7.2. Complex-survey applicability and adherence

{table(['Item','Distribution'],[[k,json.dumps(v,ensure_ascii=False)] for k,v in surv.items()])}

These distributions describe observed implementation across all 220 included studies. They do
not imply that every survey-design feature was required for every analytic purpose. For
population-level association claims, the purpose-matched audit below is the primary appraisal.

## Table S7.3. PROBAST+AI development methodological-quality units (n={pd['n_units']})

{table(['Domain','High quality','Unclear','Low quality'],[['Overall',pd['overall'].get('HIGH',0),pd['overall'].get('UNC',0),pd['overall'].get('LOW',0)]]+[[domain_labels.get(k,k),v.get('HIGH',0),v.get('UNC',0),v.get('LOW',0)] for k,v in pd['domains'].items()])}

## Table S7.4. PROBAST+AI performance-evaluation risk-of-bias units (n={pe['n_units']})

{table(['Domain','Low risk','Unclear','High risk'],[['Overall',pe['overall'].get('LOW',0),pe['overall'].get('UNC',0),pe['overall'].get('HIGH',0)]]+[[domain_labels.get(k,k),v.get('LOW',0),v.get('UNC',0),v.get('HIGH',0)] for k,v in pe['domains'].items()])}

### Purpose-stratified PROBAST+AI sensitivity analysis

{table(['Orientation','Prediction studies','Low-quality development units','High-risk evaluation units'],[
 ['Health-focused',health_probast['prediction_studies'],f"{health_probast['probast_ai_development_units'].get('LOW',0)}/{sum(health_probast['probast_ai_development_units'].values())}",f"{health_probast['probast_ai_evaluation_units'].get('HIGH',0)}/{sum(health_probast['probast_ai_evaluation_units'].values())}"],
 ['Method-focused',method_probast['prediction_studies'],f"{method_probast['probast_ai_development_units'].get('LOW',0)}/{sum(method_probast['probast_ai_development_units'].values())}",f"{method_probast['probast_ai_evaluation_units'].get('HIGH',0)}/{sum(method_probast['probast_ai_evaluation_units'].values())}"],
])}

PROBAST+AI evaluates prediction-model development and performance evaluation. The uniformly
unfavourable method-focused judgements therefore should not be read as invalidating the
methodological contribution of a demonstration study. Development quality and evaluation risk
of bias also have opposite judgement directions; they are never combined into one score.

### Sensitivity of the screening/individual-use evidence package

{table(['Review-level definition among 49 studies proposing screening or individual use','Studies'],[
 ['Strict: independent/later-period validation + calibration + explicit threshold',f"{screening_package['strict_all_three']}/{screening_package['denominator']}"],
 ['Relaxed: independent/later-period validation + calibration or threshold',f"{screening_package['relaxed_validation_plus_calibration_or_threshold']}/{screening_package['denominator']}"],
 ['Validation component',f"{screening_package['independent_or_later_period_validation']}/{screening_package['denominator']}"],
 ['Calibration component',f"{screening_package['calibration']}/{screening_package['denominator']}"],
 ['Explicit-threshold component',f"{screening_package['positive_decision_rule_reported']}/{screening_package['denominator']}"],
])}

These are prespecified review-level evidence packages, not universal standards. The strict,
relaxed, and component results are reported together to show the sensitivity of the intersection
to the operational definition.

## Table S7.5. Exploratory same-study claim--analysis correspondence

{table(['Claim','Claim n','Prespecified support criterion','Support n','Both','Claim without support'],claim_rows)}

This exploratory cross-tabulation is separate from PROBAST+AI. Model-variable contribution,
hypothesis generation, population-level association, and causal/intervention claims are distinct
constructs. Downstream regression is not required for model-contribution interpretation, while
variable importance alone does not support population or causal claims. Constructs not separately
encoded in the source protocol are retained as NR rather than inferred. Intersections were
calculated within the same study.

## Figure S13. Temporal patterns in method-focused research

\\begin{{center}}
\\includegraphics[width=0.94\\linewidth]{{figures/submission/figS13_method_temporal.pdf}}
\\end{{center}}

Method-development or improvement versus existing-method comparison (A), and analytic stages
addressed by method-focused research (B). Period denominators are 10, 14, 4, and 8; 2025--2026
is incomplete through September 2026.

## Table S7.6. Exploratory temporal analysis

{table(['Cohort','Indicator']+periods,temporal_rows)}

Every cell gives n/period denominator (percentage). Denominators are 32, 32, 52, and 49 for
health-focused classification studies; 36, 34, 56, and 58 for all health-focused studies; and
10, 14, 4, and 8 for method-focused studies. These post-hoc descriptive comparisons are not a
monotonic trend model. The 2025--2026 period is incomplete because the final search ended in
September 2026.

## Tables S7.7--S7.9. Assessment-unit evidence

All 308 development and 401 evaluation units, signalling responses, rationales, and evidence references are in Additional file 8/XLSX. Development labels express methodological quality; evaluation labels express risk of bias and must not be combined.
""")

finals=[]
for p in sorted((ROOT/'data/protocol_v1_2/final').glob('KHM*_final.json')):
 d=json.loads(p.read_text()); one=lambda k:d['protocol_items'][k][0]['value']
 if d.get('corpus_status',{}).get('include',one('ELG04')=='Y') and one('TSK01')=='CLS': finals.append(d)
periods=['≤2019','2020–2022','2023–2024','2025–2026']; pp=lambda y:'≤2019' if y<=2019 else '2020–2022' if y<=2022 else '2023–2024' if y<=2024 else '2025–2026'
den=Counter(pp(int(d['metadata']['publication_year'])) for d in finals); indicators={p:Counter() for p in periods}
for d in finals:
 one=lambda k:d['protocol_items'][k][0]['value']; anyv=lambda k,v:any(x['value']==v or isinstance(x['value'],list) and v in x['value'] for x in d['protocol_items'][k]); p=pp(int(d['metadata']['publication_year']))
 vals={'Explicit importance':anyv('VI01','USED'),'Importance stability':anyv('VI16','USED'),'External/temporal validation':anyv('VAL02','EXTERNAL') or anyv('VAL02','TEMPORAL'),'Calibration':any(m.get('metric') in ('CALSLOPE','CALINT','CALPLOT') for m in d['performance_metrics']),'Paired comparison':anyv('MET_PAIR','Y'),'Open science complete':one('REP19')=='R','Survey weights':one('SUR04')=='USED','Sample-size rationale':one('REP09') in ('R','P')}
 for k,v in vals.items(): indicators[p][k]+=bool(v)
trows=[]
for k in next(iter(indicators.values())).keys(): trows.append([k]+[f"{indicators[p][k]}/{den[p]} ({100*indicators[p][k]/den[p]:.1f}%)" for p in periods])
write("additional_file7_temporal.md","Additional file 7. Adjudicated temporal synthesis",
f"""## Table S7.1. Included studies by period

{table(['Period','All included','Classification'],[['≤2019',46,den['≤2019']],['2020–2022',48,den['2020–2022']],['2023–2024',60,den['2023–2024']],['2025–2026',66,den['2025–2026']]])}

## Table S7.2. Classification indicators by period

{table(['Indicator']+periods,trows)}

## Tables S7.3--S7.4. Interpretation

Period-specific proportions are descriptive, use a fixed within-period classification denominator for every row, and do not establish temporal causation. Superseded pre-consensus regression estimates are not carried forward.
""")
print("Wrote archived pre-embedding snapshots of former Additional files 2--7")
