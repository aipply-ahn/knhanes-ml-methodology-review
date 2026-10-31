"""Supplementary Table S6 (prompts 093-094; renumbered in prompt 097): the human verification protocol as a reader-facing rule table.

Only the rules that produce the reported results are listed; all 306 coding items, their response
codes and the full decision text are in the PROTOCOL_ITEMS and PROTOCOL_RESPONSE_CODES sheets of the
Supplementary Table S5 workbook. Wording follows the canonical protocol items. Prompt 094 (review v32) removed
the author-aim and proposed-use rows and the claim-evidence part: the review no longer codes or judges them.
"""

def _groups():  # review 20261023: group sizes follow the (corrected) purpose records
    import json
    from pathlib import Path as _P
    rows = json.loads((_P(__file__).resolve().parents[1] / "results/derived/study_purpose_audit.json").read_text())["records"]
    health = [r for r in rows if r["study_category"] == "HEALTH_ANALYSIS"]
    core = sum(r["knhanes_actual_ml_task"] == "CLASSIFICATION" for r in health)
    return core, len(health), len(rows) - len(health)


N_CORE, N_HEALTH, N_METHOD = _groups()
HEADERS = ["Item", "Question", "Applies to", "Decision rule", "Table S5 column"]
WIDTHS = [36, 56, 38, 150, 58]

PART_A = [
    ["Reviewers", "Who made and checked each decision?", "All stages",  # prompt 115: AI-assisted extraction, author check
     "Screening and eligibility: the author. Extraction and appraisal: two AI systems with the same source files and protocol. "  # prompt 116
     "OpenAI Codex compiled the first-round records from an earlier extraction and checked them against the source; Anthropic "
     "Claude Opus 5 re-extracted every item without access to them (the 33 studies added at the re-screen after the first round by Claude "
     "Opus 5 alone). Where the two differed, the re-extracted value was kept, except for named corpus decisions. The author "
     "checked the resulting study-level dataset against the full report and supplements.", "–"],
    ["Consistency checks", "How were conflicting or missing entries found?", "All study records",
     "Rule-based checks compared related items within each record (for example, a threshold item recorded without a "
     "threshold-based measure, or a stated test portion coded as no validation). Every flag was resolved by re-reading "
     "the source; counts are in Supplementary Table S7.", "–"],
    ["Evidence", "What supports a coded value?", "Positive and judgement values",
     "Each value is linked to a page, table, figure or supplement location with an excerpt. Values are never inferred "
     "from information the report does not give.", "N_evidence_page_table_figure; N_evidence_anchor_ID"],
    ["Response states", "How are missing values recorded?", "All items",
     "Reported: stated in the report. Not reported: the item applies but the report does not state it. Not applicable: "
     "the item does not apply to the study or unit. Unclear: the report is conflicting or insufficient.",
     "all columns (NR, NA, UNCLEAR)"],
    ["Units", "At what level is an item coded?", "All items",
     "Study items are coded once. Outcome, model, development and evaluation items are coded for each unit; study "
     "summaries take the least reproducible unit for definition grades and at least one unit for reporting items.", "–"],
]

PART_B = [
    ["Orientation", "Is the study health-focused or method-focused?", f"All {N_HEALTH + N_METHOD} studies",
     "Judged from the objective, principal analysis, main results and conclusion together, not from the algorithm or "
     "title. Health-focused: answers a health question. Method-focused: develops, improves or compares an analytic method.",
     "B_primary_orientation"],
    ["Analytic task", "What is the primary analytic task?", f"All {N_HEALTH + N_METHOD} studies",
     "Set by the fitted outcome scale and evaluation, not the authors' wording: classification, continuous or ordered "
     "estimation, or another task. Health-focused classification studies form the core cohort (" + str(N_CORE) + ").",
     "B_analytic_task; B_core_health_classification"],
    ["Health topic", "What is the primary health topic?", f"{N_HEALTH} health-focused",
     "One of 18 categories, assigned by the primary fitted outcome rather than by predictors, exposures or a "
     "disease-restricted sample.", "B_health_topic"],
    ["Produced output", "Which outputs did the study produce?", f"{N_HEALTH} health-focused",
     "Results produced by the study itself: performance estimates, importance rankings, association estimates (OR, RR, "
     "coefficient, correlation), reduced predictor sets, causal estimates, tools, clusters. Cited or symbolic results are "
     "excluded.", "B_analytic_outputs"],
    ["Method contribution", "What did a method-focused study contribute?", f"{N_METHOD} method-focused",
     "Develop or improve a method, or compare existing methods. Applying existing methods to a health question is not "
     "method-focused.", "B_method_contribution"],
    ["Method evaluation", "How was the method evaluated?", f"{N_METHOD} method-focused",
     "Application only, comparison with other methods, simulation with an empirical application, or evaluation in an "
     "independent population; the role of KNHANES (sole, one of several primary datasets, external) is coded separately.",
     "B_method_evaluation_design; B_KNHANES_role"],
    ["Participant selection", "Could a reader follow participant selection?", f"{N_HEALTH} health-focused",
     "Five items: source population size, eligibility criteria, numbers excluded, reasons for exclusion, final analytic "
     "sample; every step requires all five.", "D_complete_participant_flow_reconstruction"],
    ["Outcome definition", "Can the outcome be reproduced from the report?", f"{N_CORE} core",
     "Full: target, source or instrument, timing and every cut-off or composite rule are stated. Partial: the target is "
     "identifiable but a necessary detail is missing. Insufficient: only a label. Source: every source the definition "
     "draws on (questionnaire or scale, physical measurement, laboratory value, diagnosis or history, other); a composite "
     "definition counts under each of its sources.", "E_definition_reproducibility"],
    ["Predictor set", "Can the predictor set be rebuilt?", f"{N_CORE} core",
     "Full: candidate and final inputs (or a statement that they are the same) with essential definitions. Partial: only "
     "part, for example a top-10 ranking. Insufficient: neither. A variable count alone is insufficient.",
     "F_candidate_set_completeness"],
    ["Tuning and evaluation", "Was tuning kept apart from the final evaluation?", f"{N_CORE} core",
     "Kept apart: tuning and model selection used only training or validation data, or there was no tuning. Not shown: "
     "tuning reported without the data used. Evaluation data involved: the final evaluation data were used, including "
     "choosing the final model, the hyperparameters or the threshold by performance on the data that report it.",
     "G_tuning_evaluation_separation"],
    ["Data-dependent steps", "When were data-dependent steps done?", f"{N_CORE} core",
     "Missing-value handling, scaling, feature selection and class rebalancing: within the training data, before the "
     "split or outside the training data, timing unclear, or not applied.", "F_timing_relative_to_split_resampling"],
    ["Evaluation design", "How was the model evaluated?", f"{N_CORE} core",
     "Apparent, single split, cross-validation, bootstrap, later survey period, external dataset (nonexclusive); "
     "cross-validation counts when it produced the reported performance, not when it only tuned within the training data. "
     "Validation beyond the development data means a later survey period or an external dataset.",
     "H_internal_validation; H_later_period_validation; H_external_validation"],
    ["Calibration", "Was calibration reported?", f"{N_CORE} core",
     "A calibration slope, intercept or plot for at least one evaluated model.", "H_calibration_reported"],
    ["Decision threshold", "Was a threshold reported, and chosen without the final evaluation data?", f"{N_CORE} core",
     "Reported: a stated threshold or selection method. Independent: selection documented on data other than the final "
     "evaluation set of the same evaluation.", "H_threshold_reported; H_threshold_selection_method"],
    ["Variable importance", "Was a model-based importance ranking produced, and how?", f"{N_CORE} core",
     "An explicit model-based importance or explanation output (SHAP, model-native, permutation, coefficient, tree or "
     "rule, perturbation, LIME, partial dependence, other). Regression coefficients alone do not qualify.",
     "I_importance_reported; I_importance_methods"],
    # Prompt 097 (review v35): domain rule for the ranking-domain figure (Figure 3B since prompt 100).
    ["Important variables", "Which variables did the ranking name as most important?", "Studies producing a ranking",
     "The variables the report names as most important in a table, figure or text, recorded as reported, in the listed "
     "order and without a fixed number, and assigned to 15 domains plus other: age; sex; body size; blood pressure; glucose; lipids; kidney or urine; smoking; alcohol; physical activity or "
     "function; diet; socioeconomic; mental or subjective health; work or clinical history; pain or musculoskeletal; other.",
     "I_important_variable_domains"],
    ["Ranking stability", "Was the stability of the ranking checked?", "Studies producing a ranking",
     "An explicit comparison of importance across resamples, repeated splits, survey cycles, subgroups or sensitivity "
     "analyses (refits under a changed outcome definition or specification). The authors' analyses were recorded; models were not re-run.", "I_importance_stability"],
    ["Downstream use", "Did the ranking feed a later step?", "Studies producing a ranking",
     "A reduced predictor set built from importance; ML results guiding a subsequent statistical analysis; the exact "
     "selected variables carried into that analysis.",
     "I_reduced_predictor_set; I_downstream_statistical_analysis; I_exact_variable_carryover"],
    ["Survey weights", "Were survey sampling weights mentioned or used?", "All studies",
     "Mentioned; used in model fitting; used in performance evaluation; combined across pooled survey years. Class or "
     "loss weights for outcome imbalance do not qualify.",
     "J_weights_in_fitting; J_weights_in_evaluation; J_combined_cycle_weights"],
    ["Design-based variance", "Were strata and primary sampling units used for uncertainty?", "All studies",
     "Strata- and PSU-aware or equivalent design-based variance for the assessed analysis. Weights alone do not qualify.",
     "J_strata_PSUs_in_uncertainty"],
    ["Final model and code", "Was the final model fully specified, and was code provided?", f"{N_CORE} core",
     "Full specification: inputs, preprocessing, final parameters or a saved model, the threshold where used, and use "
     "instructions. Code: public link, on request, partial, or not provided.",
     "K_final_model_specification; K_code_available"],
    ["Reporting elements", "How completely were the 19 TRIPOD+AI-derived elements reported?", f"{N_CORE} core",
     "Each element is complete, partial, not reported, unclear or not applicable against its listed components; the "
     "elements are columns of Additional Data 1.", "K_REP01 to K_REP19"],  # prompt 117  # prompt 098: plain sheet name  # prompt 115
    ["PROBAST+AI", "What were the quality and risk-of-bias judgements?", f"Units of the {N_CORE} core",
     "The official PROBAST+AI tool (Moons et al., BMJ 2025), applied separately to each model-development unit (quality) "
     "and each performance-evaluation unit (risk of bias); overall judgements follow the tool's domain rules.",
     "L_development_overall_judgements; L_evaluation_overall_judgements"],
    # v17 (prompt 135): the core reporting checklist of the main text (Table 1), linked to its codebook.
    ["Core reporting checklist", "Did the report meet each of the 43 core items (C01-C43, Table 1)?", f"{N_CORE} core",
     "Met, not met or not applicable against the item criterion, which was fixed before judging. 29 items are derived from "
     "the coded values above, 12 by re-reading the full text with the supporting sentence recorded, and two from both. "
     "Items judge reporting, not practice. Criterion, not-applicable condition and source of every item: RC Codebook sheet "
     "of Additional Data 1.", "C01 to C43 (internal codes RC in Additional Data 1)"],
]

NOTE = ("Each column of Additional Data 1 is defined in its header note; the full 306-item instrument is held by the "  # prompt 117
        "author with the coding log. PSU, primary sampling unit.")


def rows():
    return ([["A. Procedure and response states", "", "", "", ""]] + PART_A +
            [["B. Coding rules that produce the reported results", "", "", "", ""]] + PART_B)
