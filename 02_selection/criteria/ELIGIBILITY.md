# Eligibility criteria — fixed before title/abstract screening

## Definition
Eligible reports applied **supervised machine learning** to **participant-level KNHANES data**: at least one learner
outside the regression family was fitted to a designated outcome, either to analyse a health-related outcome or to
develop or compare ML methods.

| Element | Eligible | Not eligible |
|---|---|---|
| E1 Data | Participant-level KNHANES data (any cycle) used to develop or evaluate a model, including linked/merged data and KNHANES used only for external validation | KNHANES cited or compared only; published aggregate statistics only; other surveys only (e.g., US NHANES) |
| E2 Analysis | A supervised model fitted to classify or estimate a designated outcome from predictors, with at least one learner outside the regression family: decision/classification/regression trees (CART, CHAID, C4.5), random forest, boosting and other ensembles, support vector machines, k-nearest neighbours, naive Bayes, Bayesian networks, neural networks/deep learning, AutoML, large language models. Causal ML counts only when such a learner is fitted to the outcome (e.g., meta-learners or causal forests built on tree learners); a large language model counts only when it is the model that classifies or estimates the outcome, not when it is used for text processing, coding or writing | Regression-family methods only (linear, logistic, Cox, Poisson, GLM, LASSO, ridge, elastic net, GAM); unsupervised methods only (clustering, latent class/profile, association rules, PCA/factor analysis) |
| E3 Purpose | A health-related outcome (disease or health state, risk factor or biomarker, health behaviour, nutrition, mental health, quality of life, health-care use), or development/comparison of ML methods using KNHANES | Neither |
| E4 Report type | Journal article, full conference paper, preprint | Thesis; conference abstract only; review, commentary, editorial, protocol, erratum |
| E5 Language/date | Any language; published up to the search date (2026-11-02) | — |

Grouping of included studies (core classification, other health task, method study) is done at full text, not here.

## Title/abstract decision (two levels)
- **FULL_TEXT** (default): the report may meet E1-E4, or the abstract is not specific enough to rule it out.
- **EXCLUDE_CERTAIN**: the title/abstract shows clearly that the report fails at least one element. Give one code:
  - X1 KNHANES data not analysed (E1)
  - X2 no supervised non-regression learner: only regression-family and/or unsupervised methods are described (E2)
  - X3 neither a health-related outcome nor ML method development (E3)
  - X4 ineligible report type (E4)
- When in doubt, choose FULL_TEXT. Absence of an algorithm name is not by itself a reason for X2 if the abstract
  mentions machine learning, prediction models, classification or similar without naming the method.
- Every record has screening text: the published abstract, or, when a report has none, its unlabelled lead paragraph, the letter text, or (for one 2-page conference paper) the full text; the source of the text is recorded per record.
