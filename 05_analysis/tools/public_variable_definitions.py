"""Content definitions shared by reader S5 and technical S7 dictionaries."""
DEFINITIONS = dict(line.split('|', 1) for line in '''
B_classification_confidence|Certainty of the research-orientation decision: HIGH=clear concordant objectives/main analyses/results; MODERATE=some interpretation needed; LOW=weak or conflicting support; UNCLEAR=not resolvable. This is not model performance or risk of bias.
B_KNHANES_role|Role of KNHANES in the actual analysis: primary data, one of multiple primary datasets, external/transport evaluation, or application/test data. A parallel dataset is not participant-level linkage.
B_method_contribution|Broad methodological contribution of a method-focused study; a display summary, not a substitute for detailed method types in RECORD_DETAILS.
B_method_evaluation_design|Study-level methodological evaluation design; multiple evaluation settings may coexist. Named criteria, comparisons and evidence remain in RECORD_DETAILS.
C_survey_years|Exact survey years actually analysed, not publication years or the continuous span between first and last year; retain nonconsecutive years.
C_cycles|Named KNHANES survey cycles contributing analysed observations; multiple cycles are retained rather than inferred from publication date.
C_number_of_years|Count of distinct analysed survey years for each recorded dataset; nonconsecutive years count individually, not as the first-to-last span.
C_pooling_structure|How multiple years/datasets were actually used: pooling, separate analyses, development/evaluation separation, or another stated arrangement. Multiple-year use alone does not establish pooling.
C_components_used|KNHANES health interview, examination, nutrition or other components actually used; retain all reported components.
C_linked_data|Names/sources of additional datasets recorded by DAT16; check DAT15 and dataset-role detail before interpreting a named source as participant-level linkage.
C_role_relative_to_other_datasets|Structured multi-dataset relationship and other dataset names; distinguishes linkage, parallel analysis, model development and evaluation roles.
D_target_population|Population the analysis concerns, including stated eligibility; distinguish the intended population from the observed final sample and evaluation subset.
D_age_restriction|Flag indicating age-based eligibility restrictions, not a numeric age bound. Actual cutoffs and source explanations remain in POP03/04/06/07 responses and the selection-restriction record.
D_sex_restriction|Flag indicating sex-based eligibility or subgroup restriction; not a sex category or the sex proportions of an unrestricted sample. Read source responses for the actual restriction.
D_disease_risk_restriction|Flag indicating inclusion/exclusion based on disease, diagnosis or risk state; distinguish selection criteria from the model outcome. The specific condition is in the detailed source record.
D_measurement_restriction|Flag indicating selection requiring particular measurements, complete variables or component availability; not the names of the required measurements. Read the detailed selection criteria for those names.
D_source_sample|Reported starting eligible/candidate count in the participant-flow record, before subsequent exclusions; not automatically the total national survey sample.
D_final_sample|Final analytic participant count retained by the participant-flow audit; not automatically the model-development or held-out evaluation count. Consult unit-specific responses for subgroup differences.
D_event_count|Positive cases/events in the relevant analytic population; not total participants or predicted positives. Outcome and sample linkage must be checked before using a denominator.
D_prevalence|Reported positive-class/event proportion for the analytic population, stored on the 0–1 scale; distinguish weighted estimates from raw event-count/sample ratios and from evaluation prevalence.
D_complete_participant_flow_reconstruction|Whether the starting sample, eligibility/exclusions and final analytic sample can be reconciled from reported information; missing intermediate counts preclude complete reconstruction.
E_outcome_name|Author-defined model target for each outcome; multiple names are retained at study level and separated by outcome_id in ITEM_RESPONSES.
E_timing|Temporal relation of predictor measurement to outcome ascertainment; concurrent association is not future prognosis.
E_scale|Scale of the fitted target (binary, multiclass, continuous, ordered or other); does not inherit classification from a title or downstream risk-group label.
E_ascertainment_source|Instrument, examination, laboratory measure, interview, record or other source used to establish the outcome.
E_threshold_definition|Numerical cutoff or logical rule defining outcome classes, including composite conditions; distinct from the model's probability decision threshold.
E_full_definition|Combined outcome name, original measurement and cutoff from OUT02/03/08; this study-level composite does not replace linked outcome-specific responses.
F_candidate_predictor_definition|Reported candidate inputs before selection or dimensionality reduction; distinguish named original variables from encoded columns and derived features.
F_initial_predictor_count|Number of candidate inputs entering the ML pipeline from the analytic-flow audit; not the final selected count or an inferred count of one-hot columns.
F_feature_selection_method|Reported feature-selection approach and its role in constructing the model inputs; timing relative to resampling is recorded separately.
G_algorithm_families|Families of algorithms actually developed/used, from the expanded model audit; multiple families may occur in one study and are not counts of model instances.
G_hyperparameter_search|Whether and how tuning/selection was conducted according to the expanded audit; software defaults are not a reported hyperparameter search.
G_tuning_method|Reported search or optimisation method (for example grid or random search); distinct from the resampling/partition used to compare candidates.
G_tuning_evaluation_separation|Data partition used for tuning relative to final performance evaluation; an independent test set must not also select hyperparameters.
G_author_selected_model|Models designated by the authors, resolved from selection records (fallback: MOD05); not necessarily the largest metric. MODEL_SELECTIONS retains outcome, ties and IDs.
G_selection_criterion|Author-stated criterion for final model selection, including eligibility constraints and tie-breaking when reported; array order is not a priority ranking.
H_internal_validation|Retained VAL02 evaluation methods, including apparent, resampling and any temporal/external codes; multiple methods can coexist. NONE_NR is unresolved nonuse/nonreporting, not confirmed nonuse.
H_later_period_validation|Derived flag: Y if a retained VAL02 record explicitly contains TEMPORAL; N means no such positive code, not proof of explicit nonuse.
H_external_validation|Derived flag: Y if a retained VAL02 record explicitly contains EXTERNAL; N means no such positive code, not proof of explicit nonuse.
H_evaluation_sample_size|Reported sample count of each evaluation unit; multiple counts are not additive and must be linked to evaluation_id before comparison with development samples.
H_evaluation_prevalence|Positive-class/event proportion in each evaluation sample on the 0–1 scale; not the full analytic population prevalence.
H_threshold_reported|Study-level at-least-one THR01 positive method (FIXED05, YOUDEN, VAL_OOF, F1, CLINICAL, OTHER) yields Y. Otherwise unclear/missing precedes NR (N), then wholly NA. N is not explicit nonuse; mixed evaluation records remain public.
H_threshold_selection_method|All retained THR01 methods and missing states across evaluations, without an author-designated primary unit; differs from the cutoff defining the clinical outcome.
H_metrics_reported|Performance metrics with positive reporting records, or retained metric names when those records are absent; not a ranking or proof of independent evaluation.
H_calibration_reported|Derived Y for a reported calibration slope/intercept/plot; N means no positive reporting record, not proof that calibration was never examined.
H_Brier_score_reported|Reporting status of the Brier prediction-error score; not the score itself and not by itself proof of calibration adequacy.
H_decision_curve_reported|Reporting status of decision-curve/net-benefit analysis; not evidence that a useful decision threshold was independently validated.
H_confidence_interval_reported|Whether uncertainty intervals for performance were reported in the applicable evaluation; inspect evaluation-specific responses rather than assuming all metrics have intervals.
H_paired_comparison_reported|Whether paired performance comparisons were reported for models evaluated on the same observations/splits; not any unpaired difference between published estimates.
I_importance_reported|Whether an explicit model-based importance/explanation method and output were reported; conventional association coefficients alone do not establish this item.
I_importance_methods|Methods producing model-based importance or explanations; retain multiple methods and model/outcome linkage in ITEM_RESPONSES.
I_importance_stability|Whether importance was compared across resampling, cycles, subgroups or sensitivity analyses; applies to studies with eligible importance outputs, not all included studies.
J_weights_in_fitting|Use of KNHANES survey sampling weights during model fitting; class/loss weights for imbalance are not survey weights. NR and explicit nonuse remain distinct.
J_weights_in_evaluation|Use of KNHANES sampling weights in performance estimates; weighted descriptive statistics do not establish weighted evaluation.
J_combined_cycle_weights|Reported application of a survey sampling-weight strategy when multiple survey years are pooled within or across cycles. Single-year or separately analysed years with no pooling are structurally inapplicable; unclear pooling/application remains UNCLEAR and unreported weighting in established pooling is NR. Reporting a strategy alone does not establish use; class/loss weights do not qualify. Nonuse alone is not a quality judgement.
J_strata_PSUs_in_uncertainty|Accounting for survey strata and primary sampling units in variance/uncertainty estimation; sampling weights alone and resampling folds do not establish this condition.
K_code_available|Reported availability/access state of prediction-model code, not data availability; NA for the source prediction-model item outside its applicable scope. A reported public link is not verified access.
L_development_unit_count|Number of retained development-unit records, not number of algorithm labels or studies; nonapplicable units are not automatically eligible for the figure denominator.
L_development_overall_judgements|Distinct retained development-quality judgements at study level; HIGH is favourable. ITEM_RESPONSES preserves each development unit and its overall value.
L_evaluation_unit_count|Number of retained performance-evaluation-unit records; not sample size and not necessarily the applicable appraisal denominator.
L_evaluation_overall_judgements|Distinct retained evaluation risk-of-bias judgements; HIGH is unfavourable. ITEM_RESPONSES preserves each evaluation unit and its overall value.
N_evidence_page_table_figure|Source file, page and object/section locations associated with the study; use EVIDENCE_ANCHORS for the exact excerpt and individual response linkage.
N_extraction_notes|Retained analytic-flow interpretation/non-inference notes; identify limits of extraction rather than substituting for a response.
N_adjudication_notes|Rationale for current study classification or consensus; preserves the stated reason, not a new independent judgement.
N_protocol_exceptions|Retained classification-reason/exception codes; these flag qualifications rather than silently changing eligibility or the original locked responses.
'''.strip().splitlines())

for metric in ('accuracy', 'AUROC', 'AUPRC', 'F1'):
    base = f'H_best_{metric}'
    rule = ('Prioritise author-selected metric records; within that priority choose the largest reported value; '
            'otherwise choose the largest reported value. Percentages are converted to proportions. '
            'This display rule does not designate the author-selected model; consult MODEL_SELECTIONS.')
    DEFINITIONS[base] = f'Study-level displayed {metric} estimate. ' + rule
    DEFINITIONS[base+'_model'] = f'Model label linked to the displayed {metric} estimate, not an independently selected best model. ' + rule
    DEFINITIONS[base+'_evaluation'] = f'Evaluation-unit ID linked to the displayed {metric} estimate; resolves the sample/context in EVALUATIONS. ' + rule
