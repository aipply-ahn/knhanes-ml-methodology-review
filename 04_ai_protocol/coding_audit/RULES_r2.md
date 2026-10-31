# Round 1 adjudication rules (fixed 2026-10-29 by Claude Code before adjudicating; apply to every study)

General: items judge reporting, not practice. Use the main text and any supplement available in references/ (if a
supplement is cited but unavailable, judge what is available and say so). A value is 1 only with a quotable basis.

RC01 met if the population the results describe (target population or analytic sample) is stated.
RC03 met if the components used are named (sentence or per-variable source); general KNHANES descriptions = 0.
RC05 verb only (pooled/combined/integrated/merged) = 0; operation detail, integrated file/weight or year variable = 1.
RC06 met if weight use is stated and the weight is identified by name or unambiguous description (integrated weight,
  examination weight, "4-year average weight"), or non-use is stated with a reason.
RC08 met if any explicit inclusion/exclusion conditions of the analytic sample are reported; an age limit is not required.
RC17 met only if missingness is reported by variable (or by variable in a table); pooled exclusion counts or a
  missingness threshold = 0.
RC20 NA if no data-dependent preprocessing step; 1 if each step's timing relative to the split is stated (fitted on
  training data, or done before the split); timing inferable only from sentence order = 0.
RC24/RC32/RC42 "not used" without any reason = 0; used and how, or not used and why = 1.
RC25 NA if no tuning; tuning without a search space = 0.
RC26 met if it can be determined whether the final evaluation data were used to choose the model, hyperparameters or
  threshold (either way, including when the same data visibly served both); unstated tuning/selection data = 0.
RC27 values or a stated use of defaults = 1; names of tuned parameters without values = 0.
RC28 split proportions or fold counts stated = 1.
RC29 1 if split indices, or seed value with split rule, or a deterministic split rule (e.g. by survey year); a "fixed
  seed" without its value = 0.
RC30 1 if a discrimination measure and the data on which it was computed are stated.
RC31 applies when any threshold-based measure (accuracy, balanced accuracy, sensitivity, specificity, PPV, NPV, F1,
  MCC, kappa, misclassification) is reported; met if the threshold or class-assignment rule and how it was chosen are
  stated; a multiclass argmax rule counts if stated. NA only if no threshold-based measure is reported.
RC33 confidence intervals, SDs or distributions across resamples = 1.
RC34 met if strata/PSUs (or clusters) are named as used, or explicitly not used; "complex sample analysis" alone = 0.
RC35 full specification for application to new data (equation/coefficients, saved model, or tree rules with inputs).
RC36 public code link or repository = 1; "on request"/"upon acceptance" = 0.
RC39-RC45 apply when the study produced a model-based importance or explanation output (SHAP, model-native, permutation,
  ML coefficient importance, tree or rule split importance presented as importance, LIME, partial dependence). A ranking
  by regression odds ratios alone does not make them apply.
RC44 judged from the Discussion/Conclusion: met if the ranking is presented as what the model relies on, or, when
  ranked variables are presented as risk factors, determinants or associations, the report explicitly states that
  importance reflects model contributions and not causal effects or population associations; otherwise 0. A general
  cross-sectional limitation sentence alone is not enough.
RC46 1 only for actions making variables comparable across the combined years (recoding, restricting to identically
  measured or commonly available variables, excluding years because a measure changed); choosing years because the
  outcome or a variable was measured only then = 0.
Other items: the criterion text in criteria.json.

## Clarifications fixed at round-2 integration (2026-10-29), applied to every study
RC31 met only if the applied threshold value, or a self-contained class-assignment rule (argmax, majority/hard voting,
  stated 0.5), is reported together with how it was chosen. An optimisation criterion alone (Youden's index, closest to
  the upper-left corner, maximised F1) without the resulting cutoff = 0.
RC13 class counts for each class, or one class's count with the total, stated directly = 1; a percentage with the total
  only (count not recoverable exactly) = 0.
RC17 missingness reported for each variable or each variable group = 1; one count pooled across several variables = 0.
RC30 ranking discrimination (AUROC, c-statistic, gains/lift) with the data on which it was computed = 1; accuracy,
  sensitivity, F1 or misclassification alone = 0.
RC35 a saved model without the preprocessing needed to apply it to new data = 0; a printed tree or equation with defined
  inputs = 1.
RC36 public analysis code = 1; public code for an app or inference only, or analysis code on request = 0.
RC46 the report must state the restriction or harmonisation; inferring it from the variable list = 0.
