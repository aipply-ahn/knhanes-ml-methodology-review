# 03_coding: data coding

Role: how each item of each included report was coded and settled. Every coding went through independent coding by
both systems, two rounds of mutual review, rule-based re-review (triage rules and one common rule per item, cross-reviewed
in up to three rounds) and a final stage of item rules set under the author's direction, 26 pilot codings decided by the
author and a fallback for 9 codings. The counts are in the top-level `README.md` and in Supplementary Table S5 of the
article.

| Path | Content |
|---|---|
| `items/charms_items_v3.1.3.json` | Codebook of the 63 CHARMS-based items (definitions, allowed values, general coding rules), coded for all 287 reports |
| `items/charms_items_v3.1.3-legacy1.json`, `-legacy2`, `-legacy3` | Codebooks of the 155 additional items (145 + 6 + 4), coded for the representative report of each of the 279 studies |
| `items/charms_items_v3.1.3-legacy4.json` | Codebook of the 52 individual TRIPOD+AI requirements, coded for the 217 classification studies |
| `prompts/` | Prompt templates as run, named by stage: `source_text_conversion` and `table_figure_*` (preparing the report text), `step1_*` independent coding, `step2_cross_review` mutual review, `step4_*` rule-based re-review and item-rule rounds, `step5_*` rules set under the author's direction and the fallback, `after_shorten_*` shortening of long values, `analysis_study_classification` |
| `coding_rounds.jsonl` | One line per report and item (61,326 lines): every stage in order and the final status with its route |
| `field_rules.jsonl` | One line per item that needed a common rule (207): proposals, the choices in each round, the source and the final rule |
| `requirement_rounds.jsonl`, `requirement_rules.jsonl` | The same for the TRIPOD+AI requirements (11,284 codings, 45 requirement rules); not part of the 61,326 |
| `author_pilot_decisions.csv` | The 26 pilot codings decided by the author: a summary of each coding (status, inconsistency flag, number of value entries; A and B are labels drawn per case), the blinded argument for each coding, the question that separates them, the author's decision, the revision rounds, and the checker's final verdict with any remaining problem. The arguments were written by one system and checked by the other, for up to three revision rounds (code and templates in `02_selection/`); the author reviewed them and made the final decision |
| `reporting_status.csv` | Item-level reporting status, one row per eligible report (287 rows; an intermediate coding record, not an attachment of the article): `record_id`, `study_id` (links to Additional Data 1 and `02_selection/report_study_links.csv`), `representative_report` (yes for the 279 reports that represent a study, no for an additional report of the same study), then one column per coding item: the 63 CHARMS-based items for every report and the 155 additional items (`legacy.*`) for the representative reports only (empty by design for additional reports). Values: `reported`, `not_reported`, `unclear` (mentioned but not clearly enough to code), `not_applicable`; the suffix `; inconsistency` marks a report that prints conflicting values for the same object. A status says whether the report gives the information, not whether the practice was adequate |
| `coding_steps_summary.json` | Counts per run and stage, recomputed from the records |
| `code/` | Code of every stage, of the export of these files (`github_coding_records.py`) and of the copyright screen (`github_copyright.py`) |

The `step` numbers inside the records follow the five-step numbering explained in the top-level `README.md` (step 3 is
the author's directions; steps 4 and 5 are stages 3 and 4).

Published: the final structured codings and judgements (Additional Data 1 and 2, copies in `04_analysis/`), the item-level
reporting statuses (`reporting_status.csv`) and
the reconciliation route of every coding (`coding_rounds.jsonl`, `requirement_rounds.jsonl`). Not published: verbatim
excerpts and extracted passages from the reports, and the evidence and reasons of the systems that quote them. Rule
texts were screened against the report texts; example wording taken from a report was replaced by a neutral description.

## Study groups used in the analysis

Each included study is assigned to one of three groups from two coded study-level fields (`study_category` and the
primary analytic task); the combination is made in `04_analysis/code/legacy_figdata.py`:

| Group | Rule | Example |
|---|---|---|
| Health-state classification (the classification studies analysed in detail) | health-focused study whose primary analytic task is classification of a health state | classifying participants with and without diabetes |
| Other health analysis | health-focused study with another primary task | estimating a continuous blood-pressure value |
| ML method study | study whose primary purpose is to develop, improve or compare an ML method using KNHANES | comparing imputation methods on KNHANES data |

Health topics are assigned to classification studies from the primary outcome, not from the predictors or the
conditions used to restrict the sample. The patterns that map reported variable names to harmonised variables and
domains are in `04_analysis/code/practice_trends.py`.
