# v15 recoding guide: 14 checklist items read from the full text

You code KNHANES machine-learning classification studies for a reporting checklist. For each study, read the full
text (markdown at the given path; focus on Methods, Results, Discussion/Limitations, tables and supplementary notes in
the file). For each item give `v` = 1 (met), 0 (not met) or "NA" (not applicable, only where stated), and `e` = a short
verbatim quote (<= 25 words) supporting the judgement, or "not found" when 0 because nothing was reported.
Judge what the report states, not what the authors probably did. "Not met" means the requirement is not satisfied,
even if some related information is given. Use the per-study flags supplied (multi_year, ranking, ranking_used_later,
weights_used_fitting) only to decide NA; still read the text.

RC04 Raw data files: met if the report identifies the specific KNHANES data files or release used (file names such as
  HN18_ALL, named datasets such as health interview/examination/nutrition DB files, release version or release/download
  date). A generic "data were obtained from the KNHANES website" is 0.
RC05 Combining years and harmonising variables: NA if only one survey year was analysed (flag multi_year=false). Met if
  the report explains how the years were combined AND how variables that changed across years (questionnaire wording,
  codes, measurement methods) were made comparable, or states that only variables measured identically in all years were
  used. Pooling statement alone is 0.
RC06 Choice of survey weights: met if the report states whether KNHANES sampling weights were used and, if used, which
  weight (variable name such as wt_itvex, wt_tot, wt_pft, or a clear description such as the examination weight); if not
  used, gives a reason. Merely mentioning that KNHANES uses complex sampling is 0.
RC12 Overlap between outcome definition and predictors: met if the report states whether variables used to define the
  outcome (or close proxies, e.g. glucose for diabetes, blood pressure for hypertension) were excluded from, or included
  in, the predictors and how this was handled. An explicit predictor list alone is 0 unless the overlap is addressed.
RC16 Derived predictors: NA if no derived predictors were used (all predictors are raw survey variables). Met if
  derivation rules (formulas, cut-offs, categories, score construction) are given for the derived predictors.
RC19 Special response codes: met if the report describes how KNHANES non-substantive codes (e.g. 8/88/888 not
  applicable, 9/99/999 don't know or no response) were handled (treated as missing, recoded, excluded). Generic
  "missing values were excluded" is 0.
RC23 Pipeline order: met if the order of the preprocessing and training steps (e.g. split -> imputation -> scaling ->
  resampling -> tuning -> fitting) is described clearly enough to repeat it, or a pipeline object/diagram with order is
  given.
RC24 Weights in model fitting: met if the report states whether survey weights were used in fitting the ML model AND,
  if used, how (e.g. passed as sample_weight), or, if not used, why. Weighted descriptive tables only = 0.
RC32 Weights in performance evaluation: met if the report states whether performance measures were weighted AND how,
  or why not.
RC39 Sensitivity to weighting: met if results with and without survey weights are compared, or the report explains why
  this was not needed.
RC41 Importance settings: NA if no variable-importance ranking (flag ranking=false). Met if the settings needed to
  recompute importance are reported: for SHAP the explainer type and the data on which values were computed
  (training/test/background); for permutation importance the data and number of repeats or metric; for model-native
  importance the type (e.g. gain, split count, Gini, coefficient magnitude) and model. Method name alone is 0.
RC43 Survey weights in importance aggregation: NA if ranking=false. Met if the report states whether survey weights
  were used when summarising importance across participants.
RC45 Scope of importance interpretation: NA if ranking=false. Met if the report explicitly states that importance
  reflects the model's predictions/contributions and not causal effects or population associations (e.g. a limitation
  sentence).
RC46 Analyses after the ranking: NA unless the ranking was used to choose variables for a reduced model or a later
  statistical analysis (flag ranking_used_later=true). Met if the rule for carrying variables forward is stated (e.g.
  top-k, threshold) and the data used for that selection are stated.

Output: write a JSON list to the given output path, one object per study:
{"study_id": "KHM001", "key": "...", "RC04": {"v": 0, "e": "not found"}, ..., "RC46": {"v": "NA", "e": "ranking not used later"}}
All 14 item keys must be present for every study.
