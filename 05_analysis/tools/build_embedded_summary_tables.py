#!/usr/bin/env python3
"""Build the former Additional files 2--7 summaries as numbered manuscript tables."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/submission/generated_tables"
C = json.loads((ROOT / "results/derived/protocol_v1_2_consensus_results.json").read_text())
A = json.loads((ROOT / "data/protocol_v1_2/ADJUDICATION_SUMMARY.json").read_text())
M = json.loads((ROOT / "results/derived/master_manuscript_results.json").read_text())
N, CL = C["denominators"], C["classification"]


def esc(x):
    s = str(x)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("_", r"\_"), ("#", r"\#"), ("$", r"\$")):
        s = s.replace(a, b)
    return s


def table(caption, label, headers, rows, widths=None, size=r"\small"):
    if widths is None:
        widths = [1 / len(headers)] * len(headers)
    cols = "".join(r">{" + size + r"\RaggedRight\arraybackslash}p{" + f"{w:.3f}" + r"\textwidth}" for w in widths)
    lines = [r"\begin{table}[htbp]", r"\centering", r"\setlength{\tabcolsep}{2.5pt}",
             f"\\caption{{{caption}}}\\label{{{label}}}", f"\\begin{{tabular}}{{{cols}}}", r"\toprule",
             " & ".join(rf"\textbf{{{esc(x)}}}" for x in headers) + r" \\", r"\midrule"]
    lines += [" & ".join(esc(x) for x in row) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def longtable(caption, label, headers, rows, widths, size=r"\scriptsize"):
    cols = "".join(r">{" + size + r"\RaggedRight\arraybackslash}p{" + f"{w:.3f}" + r"\textwidth}" for w in widths)
    head = " & ".join(rf"\textbf{{{esc(x)}}}" for x in headers) + r" \\" 
    lines = [r"\begingroup", r"\setstretch{1.0}", r"\setlength{\tabcolsep}{2pt}",
             f"\\begin{{longtable}}{{{cols}}}", f"\\caption{{{caption}}}\\label{{{label}}}\\\\",
             r"\toprule", head, r"\midrule", r"\endfirsthead",
             rf"\multicolumn{{{len(headers)}}}{{l}}{{\tablename\ \thetable\ (continued)}}\\",
             r"\toprule", head, r"\midrule", r"\endhead",
             rf"\midrule\multicolumn{{{len(headers)}}}{{r}}{{Continued on next page}}\\", r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    lines += [" & ".join(esc(x) for x in row) + r" \\" for row in rows]
    lines += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(lines)


def write(name, parts):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("% Generated from adjudicated protocol-v1.2 final JSON; do not edit manually.\n" + "\n".join(parts) + r"\FloatBarrier" + "\n")


# Methods: former Additional file 2.
methods = [
    table("Completed review and reconciliation chain.", "tab:review-chain", ["Stage", "Status", "Records"], [
        ["P1 migration", "Legacy evidence-linked extraction retained for provenance", 222],
        ["P2 source review", "Blinded LLM source-package review complete", 222],
        ["Validation", "Evidence, unit, metric, and panel-parent integrity passed", 222],
        ["Reconciliation", "Prespecified rule prioritising source-read P2; named corpus decisions recorded separately", 222]], [.16, .67, .10]),
    table("Final report, study, task, and assessment-unit denominators.", "tab:final-denominators", ["Denominator", "n"], [
        ["Full reports entering final adjudication", N["reports"]], ["Included unique studies", N["studies"]],
        ["Classification studies", N["classification"]], ["Continuous-outcome prediction studies", N["continuous"]],
        ["Other primary-task studies", N["other"]], ["Prediction-model studies", N["prediction"]],
        ["Development units", C["probast_ai"]["development"]["n_units"]],
        ["Performance-evaluation units", C["probast_ai"]["evaluation"]["n_units"]]], [.76, .17]),
    table("Prespecified reconciliation and evidence-handling rules.", "tab:adjudication-rules", ["Rule", "Operational handling"], [
        ["Semantic matching", "Compared item and semantic unit identifiers with evidence references; list position was not used."],
        ["Provenance", "Retained exact agreements and P1/P2 provenance for every adjudicated item."],
        ["External validation", "Included reports using KNHANES only as an eligible external-validation dataset."],
        ["Integrity signals", "Flagged unconfirmed signals without automatic exclusion."],
        ["Retraction", "Retained publication history but excluded retracted evidence from valid performance and methodological synthesis."]], [.22, .71])]
write("tables_methods_summary.tex", methods)
write("table_method_governance.tex", [methods[0]])
write("table_method_denominators.tex", [methods[1]])
eligibility=table("Eligibility, ML-boundary, report-family, and evidence-status rules.","tab:eligibility-rules",["Decision point","Rule"],[
 ["Eligible ML","A learning algorithm was fitted for a primary analytic objective using KNHANES in development or evaluation."],
 ["ML-adjacent boundary","Conventional regression alone and classical clustering, PCA, latent-class/profile, penalised regression, or association rules without another eligible ML component were excluded."],
 ["Preprocessing","Use of a method only in preprocessing did not determine primary-task assignment."],
 ["Report family","Preprint and journal versions of the same analysis were linked; the journal version represented the study."],
 ["Companion reports","Distinct reports from one study family were linked without erasing report-level provenance."],
 ["Retraction","Retracted work remained in publication history but was excluded from valid performance and methodological evidence."]],[.22,.71],r"\scriptsize")
write("table_method_eligibility.tex",[eligibility])
write("table_method_reconciliation.tex", [methods[2]])

# Evidence base: former Additional file 3.
decision_labels = {
    "EXCLUDE_NO_ELIGIBLE_ML": "Exclude: no eligible ML",
    "MERGE_PREPRINT_INTO_KHM100": "Merge preprint into KHM100",
    "REPRESENTATIVE_FOR_KHM076_KHM100": "Representative journal report",
    "RETAIN_CORPUS_EXCLUDE_VALID_EVIDENCE": "Retain history; exclude valid evidence",
    "INCLUDE_EXTERNAL_VALIDATION": "Include external validation",
}
decisions = [[sid, decision_labels.get(d["decision"], d["decision"]), "Yes" if d.get("include") else "No", d["rationale"]] for sid, d in A["decisions"].items()]
evidence = [
    table("Included studies by mutually exclusive primary analytic task.", "tab:task-groups", ["Primary task", "Studies"],
          [["Classification", N["classification"]], ["Continuous-outcome prediction", N["continuous"]], ["Other", N["other"]]], [.76, .17]),
    table("Role of KNHANES data in the included studies.", "tab:knhanes-role", ["KNHANES role", "Studies"],
          [["Primary development/analysis data", C["knhanes_role"].get("PRIMARY", 0)], ["External validation data", C["knhanes_role"].get("EXTVAL", 0)], ["Multiple roles", C["knhanes_role"].get("MULTI", 0)]], [.76, .17]),
    longtable("Prespecified corpus-level adjudication decisions.", "tab:corpus-decisions", ["Study", "Decision", "In corpus?", "Rationale"], decisions, [.10, .24, .10, .49])]
write("tables_evidence_summary.tex", evidence)
write("tables_evidence_core.tex", evidence)
closed=table("Closed accounting from search retrieval to final analytic cohorts.","tab:closed-accounting",["Stage","Count","Accounting"],[
 ["Source records",18517,"6,046 Europe PMC + 10,000 OpenAlex + 52 PubMed-unique + 2,079 KDCA + 340 KCI"],
 ["Duplicate records removed",7440,"18,517 - 7,440 = 11,077 unique records"],
 ["Terminology-screen exclusions",9578,"11,077 - 9,578 = 1,499 assessed reports"],
 ["Ineligible reports",1120,"Content eligibility assessment"],["ML-adjacent reports",134,"Catalogued outside the eligible ML corpus"],
 ["Eligible reports",245,"1,499 - 1,120 - 134"],["Linked additional/companion reports",25,"Report-family consolidation"],
 ["Included unique studies",220,"245 - 25"],["Final task cohorts",220,"196 classification + 12 continuous + 12 other"]],[.29,.11,.53],r"\scriptsize")
write("table_closed_accounting.tex",[closed])

topic_labels={'mental_health':'Mental health','diabetes':'Diabetes','cvd':'Cardiovascular disease','osteoporosis_sarcopenia':'Osteoporosis/sarcopenia','nutrition_diet':'Nutrition/diet','metabolic_syndrome':'Metabolic syndrome','oral_health':'Oral health'}
top_topics=sorted(M['topics'].items(),key=lambda x:-x[1])[:7]
corpus_rows=[["Publication period","2009--September 2026","220 studies"],
 ["Leading health topics",'; '.join(f"{topic_labels.get(k,k)}={v}" for k,v in top_topics),"Fixed 18-category taxonomy"],
 ["KNHANES role","Primary=198; multiple=9; external validation=13","Mutually exclusive study role"],
 ["Survey-year scope","One year=38; multiple within cycle=55; across cycles=121; unclear=6","Study level"],
 ["Supplement retrieval","Files reviewed=80; no study-specific file identified=140","172 files across 80 studies"],
 ["Visual inventory","Main figures=876; main tables=854; supplement figures=134; supplement tables=275","2,143 containers plus 1,243 labelled panels"]]
write("table_corpus_characteristics.tex",[table("Corpus characteristics and reporting-package coverage.","tab:corpus-characteristics",["Characteristic","Distribution","Definition"],corpus_rows,[.22,.48,.23],r"\scriptsize")])
visual_rows=[["All visual objects",3386],["Containers",2143],["Labelled panels",1243],["Main-report figure containers",876],["Main-report table containers",854],["Supplementary figures",134],["Supplementary tables",275],["Image-interpreted objects",2119],["Complete image interpretations",2100],["Source-unavailable",14],["Manual review required",5],["Metric-sensitive figure objects",921],["Studies with metric-sensitive figures",150]]
write("table_visual_coverage.tex",[table("Visual and supplementary evidence coverage.","tab:visual-coverage",["Audit unit","n"],visual_rows,[.76,.17],r"\scriptsize")])

def rows(mapping, labels):
    return [[labels.get(k, k), v] for k, v in mapping.items()]

# Classification workflow: former Additional file 4.
classification = [
    table("Outcome construction and predictor-set adequacy in classification studies ($n=196$).", "tab:construction-adequacy",
          ["Assessment", "Robust", "Limited", "High concern", "Not assessable"],
          [["Outcome", 43, 106, 36, 11], ["Predictors", 7, 129, 52, 8]], [.23, .16, .16, .19, .19]),
    table("Primary missing-data strategy in classification studies ($n=196$).", "tab:missing-strategy", ["Strategy", "Studies"],
          rows(CL["missing_primary"], {"COMPLETE":"Complete-case analysis","MULTIPLE":"Multiple strategies","SINGLE_IMP":"Single imputation","NR":"Not reported","OTHER":"Other","MULTI_IMP":"Multiple imputation","INDICATOR":"Missingness indicator","MODEL_NATIVE":"Model-native handling"}), [.76,.17]),
    table("Primary class-imbalance strategy in classification studies ($n=196$).", "tab:imbalance-strategy", ["Strategy", "Studies"],
          rows(CL["imbalance_primary"], {"NONE":"No active intervention","WEIGHT":"Weighting/cost-sensitive","SMOTE":"SMOTE/ADASYN","MULTIPLE":"Multiple strategies","RANDOM":"Random over/undersampling","OTHER":"Other","NR":"Not reported"}), [.76,.17]),
    table("Class-distribution recoverability in classification studies ($n=196$).", "tab:class-recoverability", ["Recoverability", "Studies"],
          rows(CL["class_recoverability"], {"P":"Partly recoverable","R":"Recoverable","NR":"Not recoverable","UNC":"Unclear"}), [.76,.17]),
    table("Decision-threshold selection in classification studies ($n=196$).", "tab:threshold-selection", ["Rule", "Studies"],
          rows(CL["threshold_primary"], {"NR":"Not reported","YOUDEN":"Youden index","NA":"Not applicable","FIXED05":"Fixed 0.5","OTHER":"Other","VAL_OOF":"Validation/out-of-fold","CLINICAL":"Clinical rule","F1":"F1 optimised"}), [.76,.17]),
    table("Validation approaches in classification studies; categories may overlap ($n=196$).", "tab:validation-approaches", ["Approach", "Studies"],
          rows(CL["validation"], {"APPARENT":"Apparent/internal","SPLIT":"Single split","CV":"Cross-validation","BOOT":"Bootstrap","TEMPORAL":"Temporal","EXTERNAL":"External","NONE_NR":"None/not reported","OTHER":"Other"}), [.76,.17]),
    table("Reported classification-performance metrics; categories may overlap ($n=196$).", "tab:performance-metrics", ["Metric", "Studies"], rows(CL["metrics"], {}), [.76,.17], r"\scriptsize"),
    table("Comparative uncertainty and appropriateness reporting in classification studies ($n=196$).", "tab:comparative-uncertainty", ["Item", "Studies"],
          rows(CL["metric_reporting"], {"MET_CI":"Confidence interval","MET_SD":"SD/resampling distribution","MET_PAIR":"Paired model comparison","MET_APPROPRIATE":"Purpose-appropriate metric set"}), [.76,.17])]
write("tables_classification_summary.tex", classification)
write("table_classification_target.tex",[classification[0]])
write("tables_classification_preprocessing.tex",classification[1:5])
write("tables_classification_evaluation.tex",classification[5:])

d=M['data_scale']; data_rows=[
 ["Survey-year scope","One year / within-cycle multi-year / across-cycle multi-year / unclear",f"{d['survey_scope'].get('ONE_YEAR',0)} / {d['survey_scope'].get('MULTI_SAME',0)} / {d['survey_scope'].get('MULTI_CROSS',0)} / {d['survey_scope'].get('UNC',0)}"],
 ["Pooling operation","Pooled / separate / both / unclear / not applicable",f"{d['pooling'].get('POOLED',0)} / {d['pooling'].get('SEPARATE',0)} / {d['pooling'].get('BOTH',0)} / {d['pooling'].get('UNC',0)} / {d['pooling'].get('NA',0)}"],
 ["Analytic sample size","Reported studies; median (IQR); range",f"{d['analytic_sample_reported']}; {d['analytic_sample_median']:.0f} ({d['analytic_sample_q1']:.0f}--{d['analytic_sample_q3']:.0f}); {d['analytic_sample_min']:.0f}--{d['analytic_sample_max']:.0f}"],
 ["Event count","Studies with recoverable event count",d['event_count_recoverable']],
 ["Candidate/input count","Reported studies; median (IQR); range",f"{d['input_count_recoverable']}; {d['input_median']:.0f} ({d['input_q1']:.0f}--{d['input_q3']:.0f}); {d['input_min']:.0f}--{d['input_max']:.0f}"],
 ["Joint effective information","Studies with both event and input counts",d['event_and_input_recoverable']],
 ["External-data linkage","Classification studies linking an external dataset",d['external_linkage']]]
write("table_data_scale.tex",[table("Data scale and effective-information recoverability in classification studies ($n=196$).","tab:data-scale",["Item","Summary measure","Result"],data_rows,[.22,.48,.23],r"\scriptsize")])

detail_rows=[]
for title,key,labels in [
 ("Imbalance intervention timing",'imbalance_timing',{'BEFORE':'Before split','TRAIN':'Training set only','WITHIN':'Within resampling partition','ORDER_NR':'Order not reported','NA':'Not applicable','OTHER':'Other'}),
 ("Evaluation prevalence",'test_distribution',{'ORIGINAL':'Original prevalence retained','ALTERED':'Altered','NR':'Not reported','UNC':'Unclear','NA':'Not applicable'}),
 ("Threshold independence",'threshold_independence',{'USED':'Independent','NOT_USED':'Not independent','NR':'Not reported','UNC':'Unclear','NA':'Not applicable'}),
 ("Post-imbalance recalibration",'recalibration',{'USED':'Used','NOT_USED':'Not used','NR':'Not reported','NA':'Not applicable'})]:
 detail_rows += [[title,labels.get(k,k),v] for k,v in M[key].items()]
write("table_imbalance_detail.tex",[table("Detailed imbalance timing, evaluation distribution, and threshold handling; repeated model/evaluation units may contribute more than once.","tab:imbalance-detail",["Dimension","Category","Units"],detail_rows,[.30,.49,.14],r"\scriptsize")])

write("table_algorithms.tex",[table("Algorithms evaluated and author-designated best models in classification studies. Frequencies describe heterogeneous tasks and do not establish intrinsic algorithm superiority.","tab:algorithms",["Algorithm family","Studies evaluating","Best selections","Criterion recoverable"],M['algorithms'],[.37,.18,.18,.20],r"\scriptsize")])
perf_extra=[["Best-model criterion",k,v] for k,v in M['best_criterion'].items()]+[["Evaluation context",k,v] for k,v in M['evaluation_context'].items()]
write("table_performance_context.tex",[table("Best-model designation criteria and evaluation contexts in classification studies.","tab:performance-context",["Dimension","Category","Studies"],perf_extra,[.25,.52,.16],r"\scriptsize")])

# Analytic function: former Additional file 5.
content, imp = C["content"], CL["importance"]
analytic = [
    table("Stated rationales for ML; categories may overlap ($n=220$).", "tab:ml-rationale", ["Rationale", "Studies"],
          rows({k:v for k,v in content.items() if k.startswith("RAT_")}, {"RAT_PERF":"Expected performance gain","RAT_SCREEN":"Screening/personalisation","RAT_COMPLEX":"Complexity/nonlinearity","RAT_FACTOR":"Factor discovery/interpretation","RAT_METHOD":"Method/data problem","RAT_DEPLOY":"Dynamic/deployment","RAT_NONE":"No explicit rationale"}), [.76,.17]),
    table("Actual analytic functions of ML; categories may overlap ($n=220$).", "tab:analytic-function", ["Function", "Studies"],
          rows({k:v for k,v in content.items() if k.startswith("FUN_")}, {"FUN_PRED":"Prediction/classification","FUN_COMPARE":"Algorithm comparison","FUN_INTERP":"Feature/factor interpretation","FUN_PROCESS":"Data processing/augmentation","FUN_TRANSPORT":"External validation/transport","FUN_PATTERN":"Pattern discovery","FUN_TOOL":"Implemented tool"}), [.76,.17]),
    table("Variable-centred pathway in classification studies ($n=196$).", "tab:importance-pathway", ["Stage", "Studies"],
          [["Explicit model-based importance",imp["VI01"]],["Model-guided subset",imp["VI10"]],["Downstream statistical inference",imp["VI11"]],["Exact variable carryover",imp["VI14"]],["Importance stability/uncertainty",imp["VI16"]],["Explanation fidelity/robustness evaluated",imp["VI17"]],["Expert/user utility evaluated",imp["VI18"]],["Subgroup fairness assessed",imp["VI19"]]], [.76,.17]),
    table("Discussion claims and support statements; categories were coded independently and may overlap ($n=220$).", "tab:discussion-claims", ["Claim/support statement", "Studies"],
          rows({k:v for k,v in content.items() if k.startswith("CLM_")}, {"CLM_BETTER":"Better prediction claimed","CLM_FACTOR":"Factor/association insight","CLM_SCREEN":"Screening/personalisation proposed","CLM_NONCAUSAL":"Noncausal caveat","CLM_EXTVAL":"External validation/calibration discussed","CLM_SURVEY":"Complex-survey limitation discussed","CLM_IMPLEMENT":"Implementation/deployment discussed"}), [.76,.17])]
write("tables_analytic_summary.tex", analytic)
write("tables_analytic_rationale.tex",analytic[:2])
write("table_analytic_pathway.tex",[analytic[2]])
write("table_analytic_claims.tex",[analytic[3]])

vimap={'SHAP':'SHAP','MODEL_NATIVE':'Model-native importance','PERMUTATION':'Permutation','PDP':'PDP','ALE':'ALE','ICE':'ICE','LIME':'LIME','PERTURBATION_ABLATION':'Perturbation/ablation','COEFFICIENT_STATISTIC':'Coefficient/statistic','TREE_RULE':'Tree/rule','NETWORK_SPECIFIC':'Network-specific','OTHER':'Other'}
vrmap={'RANKING_ONLY':'Ranking only','FIXED_TOP_K':'Fixed top-k','RECURSIVE_WRAPPER':'Recursive/wrapper','THRESHOLD':'Importance threshold','CROSS_MODEL_CONSENSUS':'Cross-model consensus','PENALISED_STATISTICAL_FILTER':'Penalised/statistical filter','EXPERT_JUDGEMENT':'Expert judgement','AVAILABILITY_MISSINGNESS':'Availability/missingness','NR':'Not reported','OTHER':'Other'}
virows=[["Importance/explanation method",vimap.get(k,k),v] for k,v in M['vi_methods'].items()]+[["Selection rule",vrmap.get(k,k),v] for k,v in M['vi_rules'].items()]
write("table_vi_methods.tex",[table("Variable-importance methods and rules used to designate important variables; categories may overlap.","tab:vi-methods",["Dimension","Method/rule","Studies"],virows,[.30,.49,.14],r"\scriptsize")])
vdmap={'AGE':'Age','ADIPOSITY_BODY_SIZE':'Adiposity/body size','SEX':'Sex','BLOOD_PRESSURE':'Blood pressure','GLYCAEMIA_DIABETES':'Glycaemia/diabetes','LIPIDS':'Lipids','KIDNEY_URINE':'Kidney/urine','MENTAL_SUBJECTIVE_HEALTH':'Mental/subjective health','SOCIOECONOMIC':'Socioeconomic context','DIET':'Diet/nutrients','PHYSICAL_ACTIVITY_FUNCTION':'Physical activity/function','SMOKING':'Smoking','ALCOHOL':'Alcohol','PAIN_MUSCULOSKELETAL':'Pain/musculoskeletal','WORK_CLINICAL_HISTORY':'Work/clinical history','OTHER':'Other'}
vdrows=[[vdmap.get(k,k),v,f"{100*v/M['vi_codable_n']:.1f}%"] for k,v in sorted(M['vi_domains'].items(),key=lambda x:-x[1])]
write("table_vi_domains.tex",[table(f"Reported important-variable domains among {M['vi_codable_n']} classification studies with codable variable names; categories may overlap.","tab:vi-domains",["Variable domain","Studies","Conditional percentage"],vdrows,[.58,.16,.19],r"\scriptsize")])
ds=[]
for r in M['downstream']:
 ds.append([f"{r['study_id']} ({r['year']})",', '.join(r['selected_n']) or 'NR','; '.join(r['downstream_model'])[:110] or 'NR',', '.join(r['downstream_n']) or 'NR','Yes' if r['exact_carryover'] else 'No'])
write("table_downstream.tex",[longtable("Study-level transition from variable ranking to downstream statistical inference.","tab:downstream",["Study","Selected n","Downstream model","Model n","Exact carryover"],ds,[.16,.13,.39,.12,.13])])
claim_rows=[[a.replace("/", " or "),b,c.replace("/", " or "),d,e,f] for a,b,c,d,e,f in M['claim_support']]
write("table_claim_support.tex",[table("Within-study claim--support correspondence. Support criteria were prespecified and intersections were calculated within the same study.","tab:claim-support",["Claim","Claim n","Support criterion","Support n","Both","Without support"],claim_rows,[.17,.07,.30,.10,.07,.13],r"\footnotesize")])

# Appraisal: former Additional file 6.
rep_labels={"REP01":"Title identification of study type","REP02":"Abstract summary","REP03":"Objective, intended use, and target population","REP04":"Data source, design, setting, and dates","REP05":"Eligibility, selection, and exclusions","REP06":"Outcome definition, timing, and source","REP07":"Predictor definition, timing, and availability","REP08":"Analysed sample and event/class counts","REP09":"Sample-size rationale","REP10":"Missingness, handling, and analysis stage","REP11":"Preprocessing, variable selection, and model development","REP12":"Hyperparameters, tuning, and separation from evaluation","REP13":"Internal validation, resampling, and nesting","REP14":"Evaluation data, metrics, and threshold","REP15":"Participant flow, exclusions, and characteristics","REP16":"Performance estimates and uncertainty","REP17":"Reusable final model","REP18":"Limitations, generalisability, and applicability","REP19":"Registration, protocol, data, and code/model availability"}
rep_rows=[[rep_labels[k],v.get("R",0),v.get("P",0),v.get("NR",0),v.get("UNC",0),0] for k,v in C["reporting"].items()]
survey_labels={"SUR04":"Survey weights","SUR05":"Strata","SUR06":"Clusters/PSU","SUR07":"Combined-cycle weights","SUR08":"Target population","SUR09":"Estimand","SUR10":"Weighted performance","SUR11":"Variance estimation","SUR12":"Design applicability","SUR14":"Overall adherence"}
survey_rows=[[survey_labels[k], "; ".join(f"{a}={b}" for a,b in v.items())] for k,v in C["survey"].items()]
pd, pe=C["probast_ai"]["development"],C["probast_ai"]["evaluation"]
appraisal = [
    longtable("Reporting completeness across prediction-model studies ($n=208$); the 12 other-task studies were outside this assessment.", "tab:reporting-completeness", ["Item","Complete","Partial","Not reported","Unclear","NA"], rep_rows, [.32,.12,.12,.15,.10,.10]),
    table("Complex-survey applicability and adherence across included studies ($n=220$).", "tab:survey-appraisal", ["Item", "Distribution"], survey_rows, [.28,.65], r"\scriptsize"),
    table("PROBAST+AI development methodological-quality units ($n=308$).", "tab:probast-development", ["Domain", "Low quality", "High quality", "Unclear"],
          [["Overall",pd["overall"].get("LOW",0),pd["overall"].get("HIGH",0),pd["overall"].get("UNC",0)]]+[[k,v.get("LOW",0),v.get("HIGH",0),v.get("UNC",0)] for k,v in pd["domains"].items()], [.39,.18,.18,.18]),
    table("PROBAST+AI performance-evaluation risk-of-bias units ($n=401$).", "tab:probast-evaluation", ["Domain", "Low risk", "High risk", "Unclear"],
          [["Overall",pe["overall"].get("LOW",0),pe["overall"].get("HIGH",0),pe["overall"].get("UNC",0)]]+[[k,v.get("LOW",0),v.get("HIGH",0),v.get("UNC",0)] for k,v in pe["domains"].items()], [.39,.18,.18,.18])]
write("tables_appraisal_summary.tex", appraisal)
write("table_reporting.tex",[appraisal[0]])
write("table_survey.tex",[appraisal[1]])
write("tables_probast.tex",appraisal[2:])

# Temporal synthesis: former Additional file 7.
periods=["Through 2019","2020--2022","2023--2024","2025--2026"]
den=[42,42,56,56]
vals={"Explicit importance":[20,28,45,50],"Importance stability":[2,5,8,12],"External/temporal validation":[5,5,10,18],"Calibration":[1,2,3,14],"Paired comparison":[7,4,5,12],"Open science fully met":[0,0,1,0],"Survey weights":[6,6,9,18],"Sample-size rationale":[1,0,2,2]}
trows=[[k]+[f"{x}/{d} ({100*x/d:.1f}%)" for x,d in zip(xs,den)] for k,xs in vals.items()]
temporal = [
    table("Included studies by publication period.", "tab:period-counts", ["Period","All included","Classification"], [[periods[0],46,42],[periods[1],48,42],[periods[2],60,56],[periods[3],66,56]], [.45,.24,.24]),
    table("Classification indicators by publication period. Percentages use the fixed within-period classification denominator shown in each cell.", "tab:temporal-indicators", ["Indicator"]+periods, trows, [.29,.16,.16,.16,.16], r"\scriptsize")]
write("tables_temporal_summary.tex", temporal)
tr=M['temporal']; period_rows=[[p.replace('≤','Through '),x['n'],x['classification'],x['observed_topics'],f"{x['shannon']:.3f}",f"{x['effective_topics']:.2f}",f"{x['normalized_H_log18']:.3f}",f"{x['top3_pct']:.1f}%"] for p,x in tr.items()]
write("table_temporal_characteristics.tex",[table("Publication-period characteristics and diversity based on the fixed 18-topic taxonomy.","tab:temporal-characteristics",["Period","All","Class.","Topics","Shannon H","exp(H)","H/log(18)","Top 3"],period_rows,[.15,.08,.08,.09,.13,.11,.13,.11],r"\scriptsize")])
trend_rows=[]
for x in M['trends']:
 pval='<0.001' if x['p'] < .001 else f"{x['p']:.3f}"
 label=x['indicator'].replace('External/temporal','External or temporal')
 model='Logit' if x['method']=='Logistic' else x['method']
 trend_rows.append([label]+[f"{a}/{n} ({100*a/n:.1f}%)" for a,n in x['by_period']]+[f"{x['or']:.2f} ({x['lo']:.2f}--{x['hi']:.2f})",pval,model])
write("table_temporal_trends.tex",[table("Temporal indicators and trend models. Odds ratios are per publication year; Firth penalisation is used for sparse events.","tab:temporal-trends",["Indicator","To 2019","2020--22","2023--24","2025--26","OR (95% CI)","P","Model"],trend_rows,[.135,.105,.105,.105,.105,.13,.075,.075],r"\footnotesize")])

active_outputs=list(OUT.glob("*.tex"))
caption_n=sum(p.read_text().count(r"\caption{") for p in active_outputs)
print(f"Wrote {caption_n} table renderings across {len(active_outputs)} generated TeX files")
