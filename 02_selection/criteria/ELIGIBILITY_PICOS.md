# Eligibility criteria by PICOS element (for orientation; the criteria with the decision rules are Supplementary Table S2 of the article)

The criteria applied in screening are those of ELIGIBILITY.md (E1-E5, exclusion codes X1-X4), fixed before screening.
The PICOS element each criterion corresponds to is shown for orientation only; no criterion is added, removed or changed in meaning.
Unit of eligibility: the report; reports of the same study are linked after full-text assessment.

| Criterion (PICOS element) | Definition in this review | Included | Excluded (code) |
|---|---|---|---|
| E1 Data source (P) | Participants of the Korea National Health and Nutrition Examination Survey (KNHANES), any cycle, analysed at the individual level | Participant-level KNHANES data used to develop or evaluate a model, including linked or merged data and KNHANES used only for external validation | KNHANES cited or compared only; published aggregate statistics only; other surveys only (X1) |
| E2 Analytic approach (I) | Supervised machine learning: a model fitted to classify or estimate a designated outcome from predictors with at least one non-regression learner (operational definition as in Andaur Navarro et al., BMJ 2021) | Trees (CART, CHAID, C4.5), random forest, boosting and other ensembles, support vector machines, k-nearest neighbours, naive Bayes, Bayesian networks, neural networks, AutoML, large language models used as the classifier or estimator; causal ML when such a learner is fitted to the outcome | Regression-family methods only (linear, logistic, Cox, Poisson, GLM, LASSO, ridge, elastic net, GAM); unsupervised methods only (clustering, latent class or profile, association rules, PCA or factor analysis) (X2) |
| Comparator (C) | Not applicable | Comparison with regression or other learners neither required nor excluding | - |
| E3 Purpose (O) | The target of the analysis | A health-related outcome (disease or health state, risk factor or biomarker, health behaviour, nutrition, mental health, quality of life, health-care use), or development or comparison of ML methods | Neither (X3) |
| E4 Report type (S) | Original research reports | Journal articles, full conference papers, preprints | Theses; conference abstracts; reviews, commentaries, editorials, protocols, errata (X4) |
| E5 Language and date | Publication scope | Any language; published up to 2 November 2026 | - |
