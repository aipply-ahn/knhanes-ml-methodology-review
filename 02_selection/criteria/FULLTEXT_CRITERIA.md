# Full-text eligibility criteria (frozen before the full-text stage)

The eligibility criteria are E1-E5 of the title/abstract stage (ELIGIBILITY.md), applied to the full text. The full-text
stage adds no inclusion or exclusion condition; reason codes F1-F4 record which criterion a report fails.

## Criteria
E1 Data: participant-level KNHANES data (any cycle) used to develop, validate or evaluate a model, including linked or
merged data and KNHANES used only for external validation. Not eligible: KNHANES cited or compared only; published
aggregate statistics only; other surveys only (e.g., US NHANES).
E2 Analytic approach: a supervised model fitted to classify or estimate a designated outcome from predictors, with at
least one learner outside the regression family: decision, classification or regression trees (CART, CHAID, C4.5),
random forest, boosting and other ensembles, support vector machines, k-nearest neighbours, naive Bayes, Bayesian
networks, neural networks or deep learning, AutoML, large language models. Causal ML counts only when such a learner is
fitted to the outcome (e.g., meta-learners or causal forests built on tree learners); a large language model counts only
when it is the model that classifies or estimates the outcome, not when it is used for text processing, coding or
writing. Not eligible: regression-family methods only (linear, logistic, Cox, Poisson, GLM, LASSO, ridge, elastic net,
GAM), whether or not the authors call them machine learning; unsupervised methods only (clustering, latent class or
profile, association rules, PCA or factor analysis).
E3 Purpose: a health-related outcome (disease or health state, risk factor or biomarker, health behaviour, nutrition,
mental health, quality of life, health-care use), or development or comparison of ML methods using KNHANES.
E4 Report type: an original research report, that is, a journal article (including a research letter reporting an
original analysis), a full conference paper, a chapter in a book or proceedings volume that reports an original
analysis, or a preprint. Not eligible: thesis; conference abstract only; review, introductory or textbook chapter;
commentary, editorial or letter commenting on another publication; protocol; erratum.
E5 Language and date: any language; published up to 2 November 2026.

Book chapters were not named in the title/abstract criteria. Before the full-text stage it was specified that a chapter
reporting an original analysis is an original research report (E4); no record had been removed before screening or
excluded at title/abstract because it was a book chapter.

Applying the criteria to a full text:
- KNHANES may serve model development, internal or external validation, or methodological evaluation (E1).
- Unsupervised steps (e.g., PCA, clustering) followed by an eligible supervised learner satisfy E2; unsupervised
  methods alone do not.
- Propensity scores or effect estimates from regression models alone do not satisfy E2.

## Decision
INCLUDE, or EXCLUDE with one reason code. EXCLUDE only when the full text shows that a criterion is not met; when the
text does not settle a criterion, the report is not excluded on that criterion.
Reason codes, in the order used when several apply:
- F1 ineligible report type (E4)
- F2 participant-level KNHANES data not analysed (E1)
- F3 no supervised learner outside the regression family fitted to an outcome (E2)
- F4 neither a health-related outcome nor ML method development or comparison (E3)
Evidence: verbatim quotations (each <= 40 words) with the page number on which they appear, for the points that decide the
report: KNHANES data, the learner and its outcome for INCLUDE; the failed criterion for EXCLUDE.

## Reports without a full text
Reports whose full text could not be obtained are recorded as REPORT_NOT_RETRIEVED, are not assessed and are not counted
as ineligible; PRISMA reports them as "reports not retrieved". No eligibility decision is inferred from the abstract.

## After eligibility
Reports of the same study (preprint and journal version, conference paper and journal article, Korean and English
versions) are linked by DOI, title and authors; the journal version represents a study when it exists.
