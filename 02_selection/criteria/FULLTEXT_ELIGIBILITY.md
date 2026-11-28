# Full-text eligibility (draft; to be fixed before the full-text stage)

Criteria: ELIGIBILITY.md (E1-E4), applied to the full text.
Decision codes: INCLUDE or EXCLUDE with one reason code. When several reasons apply, the first in this order is recorded:
- F1 ineligible report type (thesis, conference abstract only, review, commentary, editorial, protocol, erratum) - E4
- F2 participant-level KNHANES data not analysed - E1
- F3 no supervised learner outside the regression family fitted to an outcome (regression-family or unsupervised only) - E2
- F4 neither a health-related outcome nor ML method development or comparison - E3
Evidence: verbatim text (<= 40 words) with page number for the decisive point (data, learner, outcome or report type).
Prompts: prompts/fulltext_round1.md and prompts/fulltext_round_n.md.
Process: as for title/abstract screening - two AI screeners independently, up to three consensus rounds on disagreement,
author adjudication of unresolved records only; one consolidated eligibility_rounds.jsonl, decisions.csv, author_review.csv,
manifest.json.
Not retrieved: reports whose full text could not be obtained are counted as "reports not retrieved" and are not assessed.
Linkage (after eligibility): reports of the same study (preprint and journal version, conference paper and journal
article, Korean and English versions, article and data/code deposit) are linked by DOI, title and authors; the journal
version represents a study when it exists. Ambiguous pairs are proposed by the AI screeners and decided by the author.

Boundary rules (clarifications of E1-E4 applied at full text; they do not change the criteria used in screening):
- KNHANES data may serve model development, internal or external validation, or methodological evaluation (E1).
- Unsupervised steps (e.g., PCA, clustering) combined with an eligible supervised learner: eligible; unsupervised methods
  alone: not eligible (E2).
- Causal ML: eligible only when a non-regression learner is fitted to the outcome (as in E2: e.g., meta-learners or causal
  forests built on tree learners); propensity scores or effect estimates from regression models alone: not eligible (E2).
- Large language models: eligible only when the model itself classifies or estimates the outcome (E2).
- Letters: a research letter reporting an original analysis is a journal article (E4); a letter commenting on another
  publication is a commentary (F1). Letters were not removed by the publication-type rule before screening (that rule
  removed theses, reviews, editorials, errata, corrigenda, retractions, news and protocols), so the same rule applies at
  every stage.
- Regression-family methods described by the authors as "machine learning" (e.g., LASSO) do not satisfy E2.
