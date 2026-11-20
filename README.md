# Machine learning studies using KNHANES: a methodological review

Materials for the systematic methodological review of supervised machine-learning studies that used the Korea National
Health and Nutrition Examination Survey (KNHANES). The search was run on 2 November 2026; 287 reports of
279 studies were included.

## How the review was done: one linear process

Two AI systems, Anthropic Claude (claude-opus-5-5) and OpenAI Codex (gpt-6.1-sol), made every assessment independently,
each in an isolated call without tools or earlier conversation. Study selection and data coding followed the same five
steps:

| Step | What happens | Selection | Coding |
|---|---|---|---|
| 1 | Independent assessment by both systems | screening, full-text eligibility | every item of every report |
| 2 | Cross-review rounds: each system sees the other's answer | up to three consensus rounds | two rounds (choose the correct coding of the two; choose again after seeing the other's choice) |
| 3 | The author's directions, given as rules, not as decisions on individual cases | re-examine every agreed exclusion; publication-type and deduplication rules; retracted reports excluded | settle the remaining differences by rules: fixed rules for immaterial, form, one-sided inconsistency and rule-reading differences; one common rule per item for the rest |
| 4 | Cross-checks by both systems under those directions | re-examination, then up to three consensus rounds | fixed-rule checks; common rule per item proposed and cross-checked in up to three rounds |
| 5 | Decision on what remained | author adjudication | rules for items without an agreed rule (review comments accepted by the author, or the suggested rule as directed by the author), with a fallback; pilot codings decided by review comments accepted by the author |

The author's directions at step 3, with dates and the code that implements each, are in `DIRECTIONS.md`.
Counts at every step are in `STEP_COUNTS.json` and in Supplementary Table S6 of the article. Nothing in this repository
was re-decided after the steps: the round records are exports of the recorded calls.

## Folders

| Folder | Content |
|---|---|
| `01_search/` | `query.py` (search terms; the Korean terms are the exact terms searched), `queries.txt` (query strings as run), `run_search.py`, `flow.json` (records per source and deduplication), `dedup_rule_merges.tsv` |
| `02_selection/` | `criteria/`, `protocol/` (screening and eligibility protocols as run, including amendments), `prompts/` (prompts of steps 1, 2 and 4), `screening_records.jsonl` (bibliographic identification of every screened record), `screening_rounds.jsonl` and `eligibility_rounds.jsonl` (one line per record, every round in order), `included_reports.csv`, `report_study_links.csv`, `selection_summary.json`, `prisma_flow.pdf`, `code/` |
| `03_coding/` | `items/` (item definitions and general coding rules: CHARMS-based items v3.1.3 and the three sets of additional items), `prompts/` (prompt templates of every step), `coding_rounds.jsonl` (one line per report and item, every step in order), `field_rules.jsonl` (one line per item that needed a common rule), `coding_steps_summary.json`, `code/` |
| `04_analysis/` | `Additional_Data_1.xlsx` (study-level dataset, also Supplementary material 2), `numbers/` (every number in the article as a LaTeX macro), `code/` (derivation of the study-level variables, numbers, figures, supplementary tables and the Excel file) |

## Round records

`02_selection/*_rounds.jsonl`: per record, `rounds` lists every executed round with `stage`, `round`, `step` (1, 2 or 4),
each system's `decision`, exclusion `code` and `reason` (the system's own wording; page references masked), in
reconsideration rounds each system's reply to the other, and `consensus` (AGREED with the decision, or DISAGREED, after
which the next round follows). `final_decision` gives the outcome (`AUTHOR: ...` where the author decided at step 5) and
`settled_at_step` the step at which it was fixed.

`03_coding/coding_rounds.jsonl`: per report (`record_id`) and item, `run` (`charms` for the CHARMS-based items of all
reports; `additional_1` to `additional_3` for the additional items of the representative report of each study),
`pilot` (one of the ten pilot reports) and `steps`:
step 1 each system's `status` and `inconsistency` flag and the comparison class; step 2 each system's `choice` in each
round (A = Claude's step-1 coding, B = Codex's, UNION, NEITHER); step 4 each check with each system's verdict
(`materiality`, `inconsistency flag`, `form, rule or substance` with the side that follows the rule, `blind rule check`
mapped back to A/B) and the outcome of the field rule; step 5 the application of rules set at step 5, the fallback and
pilot decisions. `final` gives the final `status`, `settled_at_step`, the `route` in words and the internal route code
(`how`).

`03_coding/field_rules.jsonl`: per item, the number of open cases, each system's proposed rule (round 1), choices in
round 2 (P, Q or a revised rule), acceptance of each candidate in round 3 (counter-example test), the `status`
(`agreed_r2`, `agreed_r3`, `decided_review`, `decided_suggestion`), the source of the rule and the final rule.

## What is not published

Abstracts, full texts, PDFs and the converted report texts; coded values, evidence identifiers and the systems' coding
reasons (they contain text copied from the reports); verbatim quotations; page numbers; text hashes; raw model outputs
and logs; credentials. The coded values are held by the author. The round records therefore let a reader trace every
decision and its route and re-examine it against the report (identified by DOI, PMID or KCI id); they do not by
themselves reproduce the exact input texts. The analysis code documents how every number was computed; it runs on the
coded values held by the author and on the study-level dataset in `04_analysis/Additional_Data_1.xlsx`.

## Article

The article reporting this review (under review) cites this repository in its Data availability statement.
