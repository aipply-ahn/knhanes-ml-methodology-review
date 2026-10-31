# knhanes-ml-methodology-review

This repository provides search records, eligibility decisions, study-level coding, TRIPOD+AI mapping,
survey-design reporting assessments, AI-assisted verification documentation, and scripts for reproducing the
systematic methodological review results.

Review: *From Classification to Explanation: A Systematic Methodological Review of Supervised Machine Learning in a
National Health Survey* (Hongryul Ahn, The University of Suwon; manuscript under submission).

## Layout
| Folder | Content |
|---|---|
| 01_search | queries by source, retrieved records (bibliographic fields only), search runs, deduplication and keyword-filter code |
| 02_screening | eligibility criteria, dictionary screening decisions, report-level decisions and exclusions, report-study links, PRISMA counts |
| 03_coding | study-level coded data (Additional Data 1), raw coding protocol, evidence locations, verification log, newly coded items |
| 04_ai_protocol | AI model manifest, prompts and coding guides, written decision rules, audit logs and summary |
| 05_analysis | analysis scripts and the order of steps |
| 06_reporting_checklist | official TRIPOD+AI sub-item mapping, core checklist, public-to-internal ID map, scoring rules |
| 07_survey_design | survey-design coding rules and stage-specific codes (descriptive statistics, model fitting, evaluation, importance) |
| data | one row per study with identifiers and study group |

## Units
Record (search hit) -> report (publication) -> study (one or more reports; study_id KHMnnn) -> coded values with
evidence locations -> author verification -> tables and figures.

Deterministic steps (searches, DOI/PMID/title deduplication, dictionary screen, aggregation) are separated from
AI-assisted judgements (extraction, checklist coding, audit) and author decisions; 04_ai_protocol states what each AI
system did. No step that was not performed is reported as performed.

## Not included
Copyright-protected article PDFs and their extracted full texts, abstracts of retrieved records, and API credentials.

## Status
A search update re-running the baseline queries started on 31 October 2026; its records and a comparison with the
baseline will be added. Some checklist items (06_reporting_checklist, 03_coding/new_items) are under cross-review.

## Licence
Code: MIT (LICENSE). Coded data and documentation: CC BY 4.0.
