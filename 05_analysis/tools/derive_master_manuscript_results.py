#!/usr/bin/env python3
"""Derive all aggregate master-manuscript results from adjudicated final JSON."""
import csv, json, math, re, glob
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.stats import norm, spearmanr

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'results/derived/protocol_v1_2_consensus_results.json').read_text())
records=[json.loads(p.read_text()) for p in sorted((ROOT/'data/protocol_v1_2/final').glob('KHM*_final.json'))]
def one(r,k): return r['protocol_items'][k][0]['value']
def included(r): return r.get('corpus_status',{}).get('include',one(r,'ELG04')=='Y')
R=[r for r in records if included(r)]; CLS=[r for r in R if one(r,'TSK01')=='CLS']; PRED=[r for r in R if one(r,'TSK01') in ('CLS','CONT')]
def values(r,k):
    out=[]
    for row in r['protocol_items'][k]:
        v=row.get('value'); out.extend(v if isinstance(v,list) else [v])
    return out
def anyv(r,k,v='USED'): return any(x==v for x in values(r,k))
def numeric_values(r,k):
    out=[]
    for x in values(r,k):
        try:
            z=float(str(x).replace(',',''))
            if math.isfinite(z) and z>=0: out.append(z)
        except: pass
    return out
def period(y): return '≤2019' if y<=2019 else '2020–2022' if y<=2022 else '2023–2024' if y<=2024 else '2025–2026'
periods=['≤2019','2020–2022','2023–2024','2025–2026']

def study_count(rows,k): return sum(bool(values(r,k)) and any(x not in ('NA','NR','UNC',None,'') for x in values(r,k)) for r in rows)
def study_counter(rows,k,allowed=None):
    c=Counter()
    for r in rows:
        seen=set(values(r,k))
        for x in seen:
            if allowed is None or x in allowed: c[x]+=1
    return c

# Publication, task, topic, data scope and sample information.
years=Counter(int(r['metadata']['publication_year']) for r in R)
tasks_by_year={y:Counter(one(r,'TSK01') for r in R if int(r['metadata']['publication_year'])==y) for y in sorted(years)}
# The fixed 18-category topic taxonomy is the controlled topic field already linked to
# each canonical key; final JSON remains authoritative for inclusion and all audit items.
topic_by_key={Path(p).stem:json.loads(Path(p).read_text()).get('appendix15_fields',{}).get('topic','other') for p in glob.glob(str(ROOT/'data/study_json/*.json'))}
topic_by_key.update({'byeon2015feature': 'cvd', 'doh2008imputation': 'methodology', 'anon20082005': 'obesity', 'so2011relationship': 'cvd', 'kang2011group': 'diabetes', 'so2012relationship': 'other', 'byeon2013prediction': 'hearing_vision', 'kim2014factors': 'nutrition_diet', 'kim2015mining': 'cvd', 'kim2016decision': 'mental_health', 'mun2016development': 'obesity', 'kim2017decision': 'hypertension', 'yoo2017decision': 'oral_health', 'choi2018deriving': 'diabetes', 'anon2019paper': 'mental_health', 'kim2019convergence': 'cvd', 'nam2020explanatory': 'hearing_vision', 'yi2021factors': 'qol_health_behavior', 'anon20212016': 'diabetes', 'kim2022factors': 'mental_health', 'hwang2023machine': 'oral_health', 'lim2023predictive': 'cvd', 'anon2023risk': 'qol_health_behavior', 'lee2023depression': 'mental_health', 'choi2023predictiona': 'nutrition_diet', 'kim2023identification': 'dyslipidemia', 'kim2024prediction': 'qol_health_behavior', 'shim2025decision': 'mental_health', 'shin2025decision': 'hearing_vision', 'kim2025obesity': 'obesity', 'minju2025prediction': 'qol_health_behavior', 'kim2026identification': 'osteoporosis_sarcopenia', 'choi2026association': 'hypertension', 'oh2013diabetic': 'diabetes', 'choi2025phenotypic': 'respiratory', 'lee2025risk': 'other', 'jeong2024investigating': 'nutrition_diet'})  # review-loop inclusions 2026-10-24 (screening category); prompt 106: legacy 18-topic labels for the criterion-A additions (from each record's TSK04/TSK05)
topics=Counter(topic_by_key[r['canonical_key']] for r in R)
components=study_counter(R,'DAT14')
# These scale summaries use the classification cohort; corpus-wide source
# characteristics are reported separately in the evidence-base section.
scope=Counter(one(r,'DAT08') for r in CLS); pooling=Counter(one(r,'DAT10') for r in CLS)
samples=[numeric_values(r,'POP09')[0] for r in CLS if numeric_values(r,'POP09')]
inputs=[numeric_values(r,'PRD02')[0] for r in CLS if numeric_values(r,'PRD02')]
with (ROOT/'data/input_counts.tsv').open(encoding='utf-8-sig') as f:
    stage_labelled_counts={x['key']:int(x['n_variables']) for x in csv.DictReader(f,delimiter='\t') if x.get('n_variables')}
initial_candidates=[stage_labelled_counts[r['canonical_key']] for r in CLS if r['canonical_key'] in stage_labelled_counts]
event_recoverable={r['study_id'] for r in CLS if numeric_values(r,'POP12')}
input_recoverable={r['study_id'] for r in CLS if numeric_values(r,'PRD02')}
external_linkage=sum(any(x not in ('NA','NR','UNC','NOT_USED','N',None,'') for x in values(r,'DAT15')) for r in CLS)
def flow_true(r,k):
    return r.get('adjudication',{}).get('analytic_flow',{}).get('fields',{}).get(k,{}).get('value') is True
cohort_formation={k:sum(flow_true(r,k) for r in CLS) for k in (
 'source_population_size_reported','eligibility_criteria_reported','exclusion_numbers_reported',
 'exclusion_reasons_reported','final_analytic_sample_reported',
 'outcome_cases_or_prevalence_reported','complete_cohort_traceability')}
data_scale={'survey_scope':scope,'pooling':pooling,'analytic_sample_reported':len(samples),
 'analytic_sample_median':float(np.median(samples)),'analytic_sample_q1':float(np.percentile(samples,25)),'analytic_sample_q3':float(np.percentile(samples,75)),'analytic_sample_min':min(samples),'analytic_sample_max':max(samples),
 'initial_candidate_count_reported':len(initial_candidates),'initial_candidate_median':float(np.median(initial_candidates)),
 'event_count_recoverable':len(event_recoverable),'input_count_recoverable':len(input_recoverable),'event_and_input_recoverable':len(event_recoverable&input_recoverable),
 'input_median':float(np.median(inputs)),'input_q1':float(np.percentile(inputs,25)),'input_q3':float(np.percentile(inputs,75)),'input_min':min(inputs),'input_max':max(inputs),'external_linkage':external_linkage,
 'cohort_formation':cohort_formation}

# Study-level algorithm families and author-designated best selections.
def family(label):
    s=str(label).lower()
    rules=[('XGBoost',r'xgboost|xgb'),('LightGBM',r'lightgbm|lgbm'),('CatBoost',r'catboost'),('Random forest',r'random forest|randomforest|\brf\b'),('Gradient boosting',r'gradient boost|\bgbm\b|histgradient'),('AdaBoost',r'adaboost|adaptive boost'),('Decision tree',r'decision tree|\bcart\b'),('SVM',r'support vector|\bsvm\b|svc'),('Logistic regression',r'logistic'),('Naive Bayes',r'na.?ve bayes|bayesian classifier'),('kNN',r'k[- ]?nearest|\bknn\b|\bk-nn\b'),('DNN/MLP',r'deep neural|\bdnn\b|multilayer|\bmlp\b|neural network|\bann\b'),('Ensemble/stacking',r'ensemble|stacking|soft voting|bagging'),('Penalised regression',r'lasso|elastic net|ridge'),('Other',r'.*')]
    for name,pat in rules:
        if re.search(pat,s): return name
evaluated=Counter(); best=Counter(); criterion_recoverable=Counter()
for r in CLS:
    mids={m['model_id']:m for m in r['units']['models']}; seen={family(m.get('label')) for m in mids.values()}
    evaluated.update(seen)
    for b in r['best_model_selections']:
        if not b.get('author_designated'): continue
        crit=str(b.get('criterion') or '')
        recover=not (not crit or crit.upper().startswith('NR') or 'not reported' in crit.lower() or 'no comparative selection criterion' in crit.lower())
        for mid in b.get('selected_model_ids') or []:
            f=family(mids.get(mid,{}).get('label',mid)); best[f]+=1; criterion_recoverable[f]+=recover
algorithm_rows=[[k,evaluated[k],best[k],criterion_recoverable[k]] for k,_ in evaluated.most_common() if k!='Other']

# Detailed imbalance, threshold and evaluation context.
imb_timing=study_counter(CLS,'IMB03'); test_dist=study_counter(CLS,'IMB04'); threshold_ind=study_counter(CLS,'THR03'); recal=study_counter(CLS,'THR04')
eval_context=Counter()
for r in CLS:
    vv=set(values(r,'VAL02'))
    if vv & {'APPARENT','SPLIT','CV','BOOT'}: eval_context['Internal/apparent']+=1
    if 'TEMPORAL' in vv: eval_context['Temporal']+=1
    if 'EXTERNAL' in vv: eval_context['External']+=1
    if 'NONE_NR' in vv: eval_context['None/not reported']+=1
best_criterion=Counter()
for r in CLS:
    txt=' '.join(str(b.get('criterion') or '') for b in r['best_model_selections']).lower()
    if not txt: best_criterion['No selection record']+=1
    elif txt.startswith('nr') or 'not reported' in txt: best_criterion['Criterion not recoverable']+=1
    elif 'multiple' in txt or sum(w in txt for w in ['accuracy','auroc','auc','f1','auprc','precision','recall'])>1: best_criterion['Multiple metrics/author judgement']+=1
    elif 'f1' in txt: best_criterion['F1']+=1
    elif 'auroc' in txt or 'auc' in txt: best_criterion['AUROC']+=1
    elif 'accuracy' in txt: best_criterion['Accuracy']+=1
    else: best_criterion['Other author criterion']+=1

# Variable-importance methods, rules, domains and downstream pathway.
vi_methods=study_counter(CLS,'VI02',{'SHAP','MODEL_NATIVE','PERMUTATION','PDP','ALE','ICE','LIME','PERTURBATION_ABLATION','COEFFICIENT_STATISTIC','TREE_RULE','NETWORK_SPECIFIC','OTHER'})
vi_rules=study_counter(CLS,'VI08',{'RANKING_ONLY','FIXED_TOP_K','RECURSIVE_WRAPPER','THRESHOLD','CROSS_MODEL_CONSENSUS','PENALISED_STATISTICAL_FILTER','EXPERT_JUDGEMENT','AVAILABILITY_MISSINGNESS','NR','OTHER'})
vi_domains=study_counter(CLS,'VI07',{'AGE','ADIPOSITY_BODY_SIZE','SEX','BLOOD_PRESSURE','GLYCAEMIA_DIABETES','LIPIDS','KIDNEY_URINE','MENTAL_SUBJECTIVE_HEALTH','SOCIOECONOMIC','DIET','PHYSICAL_ACTIVITY_FUNCTION','SMOKING','ALCOHOL','PAIN_MUSCULOSKELETAL','WORK_CLINICAL_HISTORY','OTHER'})
codable=sum(any(x not in ('NA','NR','UNC') for x in values(r,'VI07')) for r in CLS)
downstream=[]
for r in CLS:
    if not anyv(r,'VI11'): continue
    downstream.append({'study_id':r['study_id'],'year':r['metadata']['publication_year'],'selected_n':sorted(set(map(str,values(r,'VI09')))-{'NA','NR','UNC'}),'downstream_model':sorted(set(map(str,values(r,'VI12')))-{'NA','NR','UNC'}),'downstream_n':sorted(set(map(str,values(r,'VI13')))-{'NA','NR','UNC'}),'exact_carryover':anyv(r,'VI14'),'changes':sorted(set(map(str,values(r,'VI15')))-{'NA','NR','UNC'})})

# Same-study claim/support correspondence.
def claim(r,k): return anyv(r,k,'PRESENT')
def calibration(r): return any(anyv(r,k,'R') for k in ('MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R'))
claim_defs=[
 ('Better prediction','CLM_BETTER','Paired model comparison',lambda r:anyv(r,'MET_PAIR','Y') or anyv(r,'MET_PAIR','USED')),
 ('Screening/personalisation','CLM_SCREEN','External/temporal validation + calibration + independent threshold',lambda r:(any(x in ('EXTERNAL','TEMPORAL') for x in values(r,'VAL02')) and calibration(r) and anyv(r,'THR03','USED'))),
 ('Model-variable contribution','CLM_FACTOR','Explicit model-based importance/interpretation',lambda r:anyv(r,'VI01')),
 ('Population-level association','CLM_SURVEY','Reported survey weights plus linked statistical analysis',lambda r:anyv(r,'SUR04') and anyv(r,'VI11')),
 ('Implementation','CLM_IMPLEMENT','Implemented interface or prospective deployment',lambda r:anyv(r,'MOD17') or anyv(r,'MOD18'))]
claim_support=[]
for label,k,crit,fn in claim_defs:
    cc={r['study_id'] for r in R if claim(r,k)}; ss={r['study_id'] for r in R if fn(r)}
    claim_support.append([label,len(cc),crit,len(ss),len(cc&ss),len(cc-ss)])
claim_support.extend([
 ['Hypothesis generation','NR','Not separately encoded in the source protocol','NR','NR','NR'],
 ['Causal/intervention effect','NR','Not separately encoded; not inferred from importance or association wording','NR','NR','NR']])

# Reporting applies only to prediction studies; OTHER rows are structural NA and excluded.
reporting={k:{z:v.get(z,0) for z in ('R','P','NR','UNC')} for k,v in C['reporting'].items()}

# Temporal diversity and trend models.
temporal={}
for p in periods:
    rr=[r for r in R if period(int(r['metadata']['publication_year']))==p]; cc=Counter(topic_by_key[r['canonical_key']] for r in rr); n=len(rr)
    probs=[x/n for x in cc.values()]; H=-sum(x*math.log(x) for x in probs)
    temporal[p]={'n':n,'classification':sum(one(r,'TSK01')=='CLS' for r in rr),'observed_topics':len(cc),'shannon':H,'effective_topics':math.exp(H),'normalized_H_log18':H/math.log(18),'top3_pct':100*sum(v for _,v in cc.most_common(3))/n}

def firth_logit(y,x):
    X=np.column_stack([np.ones(len(x)),np.asarray(x,float)]); y=np.asarray(y,float); b=np.zeros(2)
    for _ in range(100):
        eta=X@b; p=1/(1+np.exp(-np.clip(eta,-35,35))); w=p*(1-p); info=X.T@(w[:,None]*X); inv=np.linalg.pinv(info)
        h=np.einsum('ij,jk,ik->i',X,inv,X)*w; score=X.T@(y-p+h*(.5-p)); step=inv@score; b+=step
        if np.max(np.abs(step))<1e-9: break
    se=math.sqrt(np.linalg.pinv(X.T@((p*(1-p))[:,None]*X))[1,1]); z=b[1]/se
    return math.exp(b[1]),math.exp(b[1]-1.96*se),math.exp(b[1]+1.96*se),2*norm.sf(abs(z))
indicators={
 'Explicit variable importance':lambda r:anyv(r,'VI01'),
 'SHAP':lambda r:'SHAP' in values(r,'VI02'),
 'External/temporal validation':lambda r:any(x in ('EXTERNAL','TEMPORAL') for x in values(r,'VAL02')),
 'Calibration':calibration,
 'Code available':lambda r:anyv(r,'MOD15'),
 'Survey weights reported':lambda r:anyv(r,'SUR04')}
trends=[]
for label,fn in indicators.items():
    base=CLS if label not in ('Code available','Survey weights reported') else PRED
    y=[int(fn(r)) for r in base]; x=[int(r['metadata']['publication_year']) for r in base]; events=sum(y)
    OR,lo,hi,p=firth_logit(y,x); method='Firth' if min(events,len(y)-events)<10 else 'Logistic'
    by=[]
    for per in periods:
        rr=[r for r in base if period(int(r['metadata']['publication_year']))==per]; a=sum(fn(r) for r in rr); by.append([a,len(rr)])
    trends.append({'indicator':label,'by_period':by,'or':OR,'lo':lo,'hi':hi,'p':p,'method':method,'events':events,'n':len(base)})
scores=[]
for r in PRED:
    vals19=[one(r,f'REP{i:02d}') for i in range(1,20)]; scores.append((int(r['metadata']['publication_year']),sum(v=='R' for v in vals19)/19))
rho,rho_p=spearmanr([x for x,_ in scores],[y for _,y in scores])

payload={'status':'PASS','source':'data/protocol_v1_2/final/*.json','denominators':{'reports':222,'studies':len(R),'prediction':len(PRED),'classification':len(CLS)},
 'years':years,'tasks_by_year':tasks_by_year,'topics':topics,'components':components,'data_scale':data_scale,'algorithms':algorithm_rows,
 'imbalance_timing':imb_timing,'test_distribution':test_dist,'threshold_independence':threshold_ind,'recalibration':recal,
 'evaluation_context':eval_context,'best_criterion':best_criterion,'vi_methods':vi_methods,'vi_rules':vi_rules,'vi_domains':vi_domains,'vi_codable_n':codable,
 'downstream':downstream,'claim_support':claim_support,'reporting_prediction':reporting,'temporal':temporal,'trends':trends,'reporting_spearman':{'rho':rho,'p':rho_p,'n':len(scores)}}
(ROOT/'results/derived/master_manuscript_results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','studies':len(R),'classification':len(CLS),'prediction':len(PRED),'sample_reported':len(samples),'input_reported':len(input_recoverable),'downstream':len(downstream),'rho':rho,'rho_p':rho_p},ensure_ascii=False,indent=2))
