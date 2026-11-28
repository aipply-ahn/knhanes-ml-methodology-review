# Machine learning studies using KNHANES: records of a methodological review

This repository lets a reader follow how the studies of a systematic methodological review were selected and coded.
The review covers supervised machine-learning studies that used participant-level data of the Korea National Health
and Nutrition Examination Survey (KNHANES). The search was run on 2 November 2026; 287 reports of 279
studies were included.

The article summarises the process. Here you find what the summary rests on: the search queries, the criteria, the
prompts as run, every round of every record and every coding in order, the item rules and the code that computed the
reported numbers.

## The process in brief

Every assessment went through the same sequence. Two AI systems (Anthropic Claude, claude-opus-5-5, and OpenAI Codex,
gpt-6.1-sol) first worked independently, each in an isolated call. Their differences were then reconciled in
structured rounds in which each system saw the other's answer. What remained went to the author.

| Stage | Study selection | Data coding |
|---|---|---|
| 1. Independent review | Both systems assess each record at title/abstract, then each full text | Both systems code every item of every report |
| 2. Mutual review | Disagreements: up to three rounds of mutual review | Disagreements: two rounds in which each system chooses between the two codings, then chooses again after seeing the other's choice |
| 3. Re-review under rules | Every exclusion on which both agreed is re-reviewed once by both; a re-review that reopens the record goes through up to three rounds | Remaining differences are triaged by both systems (not material, difference of form, rule-reading difference, factual inconsistency check, blind rule check). For the rest, both systems write one common rule per item and cross-review it in up to three rounds |
| 4. Author confirmation | For each record still in disagreement, one system writes a blinded argument for each position and the other checks it; the author reviews the arguments and decides | Item rules without agreement are set under the author's direction; for the open pilot codings, blinded arguments for each coding are written and checked in the same way and the author decides; a fixed fallback settles what is still open |

The author's directions were given as rules for groups of cases, not as decisions on single records, except for the
selection adjudications and the pilot codings. `DIRECTIONS.md` lists each direction with the stage it applies to and the
code that implements it.

### Arguments for each position and the author's decision

Every case the author decided (40 title/abstract records, 1 full-text report and 26 pilot codings) carries an argument
for each of the two positions. Claude was given the earlier rounds of the case, with the two positions labelled
Position A and Position B (which system became A was drawn at random per case, and the systems' names were not shown),
the criteria or coding rules and the text both systems had seen. It wrote the strongest argument for each position in
one to three sentences and the question that separates them, without saying which is right. Codex checked each pair
against the record and the criteria (faithful, balanced, no text copied from the report); where it found a problem,
Claude revised the arguments with the problem shown and Codex checked them again, for up to three rounds. Any run of
five or more words repeated from the text the systems had seen (other than names and technical terms) was rephrased, and
the arguments passed the copyright screen described below. The number of revision rounds, the checker's final verdict
and, where the checker still found a problem after the third round, that problem in one line are recorded with each
case (`revision_rounds`, `final_verdict`, `remaining_issue`); such cases are kept as they are and flagged, not removed.

The arguments are recorded with each decision in `02_selection/author_decisions.csv` and
`03_coding/author_pilot_decisions.csv`. The author reviewed the arguments for every case and made the final decision recorded in `author_decision`.
Position A and Position B are labels drawn per case; they do not stand for the same system across cases.

### Study selection

| | Title/abstract screening | Full-text eligibility |
|---|---|---|
| Records assessed | 921 | 363 |
| Stage 1: agreed independently | 868 | 360 |
| Stage 2: disagreements reviewed mutually | 53 (26 agreed in the rounds, 27 still in disagreement) | 3 (2 agreed, 1 still in disagreement) |
| Stage 3: agreed exclusions re-reviewed | 570 (545 kept, 25 reopened: 12 excluded after the rounds, 13 still in disagreement) | 75 (74 kept, 1 reopened and included after the rounds) |
| Stage 4: arguments for each position, then decided by the author | 40 (all sent to full text) | 1 (excluded) |
| Outcome | 364 sought in full text (1 not retrieved), 557 excluded | 287 reports included, 76 excluded |

At full text, one further report was excluded after the run by the author's rule that retracted publications are
excluded; it is not counted as an adjudication. The 287 reports belong to 279 studies; eight studies have a second
report, linked in `02_selection/report_study_links.csv`.

### Data coding

The two systems made 61,326 item codings: 18,081 on CHARMS-based items (287 reports x 63 items) and 43,245 on additional
items (the representative report of each of the 279 studies x 155 items). Each coding was settled once, at the first
stage that settled it:

| Stage | Codings | Share |
|---|---:|---:|
| 1. Agreed independently | 29,248 | 47.7% |
| 2. Agreed in mutual review | 21,020 | 34.3% |
| 3. Settled by rule-based re-review (6,723 by the triage rules, 2,153 by item rules both systems agreed) | 8,876 | 14.5% |
| 4. Settled by the final item rules and exceptions | 2,182 | 3.6% |
| Total | 61,326 | 100% |

Stage 4 consists of 2,147 codings settled by item rules set under the author's direction, 26 pilot codings decided by
the author (the author accepted review comments on the codings still open in the ten pilot reports; each carries the
arguments for both codings described above) and 9 codings
settled by the fallback (5 kept as the coding a checker accepted under the rule, 4 coded unclear). No coding was left
open. Item rules were needed for 207 items: 106 were agreed by both systems (16 in round 2, 90 in round 3) and 101 were
set under the author's direction (13 from review comments the author accepted, 88 by adopting the suggested rule after
checking it against the item definition).

The 52 individual TRIPOD+AI requirements were coded separately for the 217 classification studies, by the same
sequence, and are not part of the 61,326 codings: 11,284 codings, of which 9,849 (87.3%) were agreed independently,
946 in mutual review, 365 by rule-based re-review and 124 at the final stage (115 by item rules, 9 by the fallback).
They are in `03_coding/requirement_rounds.jsonl` and `03_coding/requirement_rules.jsonl`.

The agreement percentages are raw agreement between the outputs of two AI systems, not inter-rater reliability of human
assessors.

## Folders

Each folder has its own `README.md` describing its files.

| Folder | Role |
|---|---|
| `01_search/` | Search: the query strings as run for each database, the search code, record counts per source and deduplication exceptions |
| `02_selection/` | Study selection: eligibility criteria, protocols, the prompts of each round, one line per record with every round in order, the author's decisions with the arguments for each position, the included reports and their study links, the PRISMA flow |
| `03_coding/` | Data coding: item definitions (codebooks), the prompt templates of each stage, one line per report and item with every stage in order, the item rules with their rounds, the pilot codings decided by the author with the arguments for each coding, the item-level reporting status of each eligible report, and the code |
| `04_analysis/` | Analysis: the code that derives the study-level variables and computes every number, figure and supplementary table, the numbers as LaTeX macros, and copies of Additional Data 1 and 2 |

Files at the top level: `DIRECTIONS.md` (the author's directions), `STEP_COUNTS.json` (counts at every stage, recomputed
from the round files), `validate_counts.py` (recomputes the counts reported in the article from the files here) and
`copyright_screen_log.tsv` (what the copyright screen changed, as counts).

## Where the article reports each part

| In the article | Content | Here |
|---|---|---|
| Supplementary Table S1 | PRISMA 2020 checklist (where each reporting item is reported) | Article only |
| Supplementary Table S2 | Eligibility criteria | `02_selection/criteria/` |
| Supplementary Table S3 | Search strategies | `01_search/queries.txt` |
| Supplementary Table S4 | Selection process and counts | `02_selection/` round files, `STEP_COUNTS.json` |
| Supplementary Table S5 | Coding process and counts | `03_coding/` round files and item rules, `STEP_COUNTS.json` |
| Repository only | PRISMA-S checklist | `01_search/PRISMA-S_checklist.md` |
| Repository only | Linked publications and eligibility-boundary cases | `02_selection/linked_reports_and_boundary_cases.md` (`.csv`) |
| Additional Data 1 | Study-level dataset | `04_analysis/Additional_Data_1.xlsx` (copy) |
| Additional Data 2 | Study-level reporting assessment, with the criterion and applicability condition of every element, requirement and proposed item | `04_analysis/Additional_Data_2.xlsx` (copy) |
| Repository only | Unit-level PROBAST+AI judgements for recounting the domain counts | `04_analysis/probast_units.csv` |
| Data availability (repository only) | Report-level reporting status of the 287 eligible reports | `03_coding/reporting_status.csv` |

The prompts are not reprinted in the article; they are in `02_selection/prompts/` and `03_coding/prompts/`.

## Reading the round files

The `step` fields of the round files number the sequence in five steps, in which step 3 is the author's directions
(rules, recorded in `DIRECTIONS.md`) and no record is settled. They map to the four stages above as follows:

| `step` / `settled_at_step` | Stage |
|---|---|
| 1 | 1. Independent review |
| 2 | 2. Mutual review |
| 3 | author's direction applied as a rule (only the retracted report at full text) |
| 4 | 3. Re-review under rules |
| 5 | 4. Author confirmation and final rules |

`02_selection/screening_rounds.jsonl` and `eligibility_rounds.jsonl`: one line per record. `rounds` lists every round
in order with its `stage` (`initial`, `consensus`, `challenge` = re-review of an agreed exclusion, `challenge_consensus`),
each system's `decision`, exclusion `code` and `reason` (the system's own wording), in later rounds each system's reply
to the other (`response_to_*`), and `consensus` (AGREED or DISAGREED). `final_decision` gives the outcome (`AUTHOR: ...`
where the author decided).

`03_coding/coding_rounds.jsonl`: one line per report (`record_id`) and item. `run` is `charms` for the CHARMS-based
items of every report and `additional_1` to `additional_3` for the additional items of the representative report;
`pilot` marks the ten pilot reports. `steps` holds each system's status in stage 1, each system's choice in each
mutual-review round (A = Claude's stage-1 coding, B = Codex's, UNION, NEITHER), each rule-based check with each system's
verdict, and the final-stage action. `final` gives the final `status`, `settled_at_step` and the `route` in words.

`03_coding/field_rules.jsonl`: one line per item that needed a common rule: the open cases, each system's proposed rule
(round 1), the choices in round 2 (P, Q or a revised rule), the acceptance of each candidate in round 3 (tested on other
cases), the `status` (`agreed_r2`, `agreed_r3`, `decided_review`, `decided_suggestion`), the source of the rule and the
final rule. `requirement_rounds.jsonl` and `requirement_rules.jsonl` have the same layout for the TRIPOD+AI
requirements (`decide_open`: no rule passed the check; the open cases went to the fallback).

## Checking the counts

`python validate_counts.py` recomputes from these files the counts reported in the article (records identified,
screened and assessed, reports and studies included, author decisions, the 61,326 codings and the 11,284 requirement
codings by stage, and the item rules) and compares them with the article. As its last check it runs
`04_analysis/code/recount_from_additional_data.py`, which recounts the study-level aggregates, including the PROBAST+AI
unit totals and domain counts, from Additional Data 1 and 2 and `04_analysis/probast_units.csv`.

These records let a reader reconstruct the procedure, trace the route of every record and every coding and recompute
the reported counts. They do not show that a new run of the two systems would return the same answers, or that every
coding is correct; a coding can be re-examined against the report, identified by DOI, PMID or KCI id.

## What is not published, and the copyright screen

Abstracts, full texts, PDFs and the converted report texts; verbatim excerpts and extracted passages from the reports,
and the evidence and reasons of the AI systems that quote them; page or paragraph locations; text hashes; raw model
outputs and logs; credentials. Titles and identifiers of the records are given for identification only. The final
structured codings and reporting judgements (Additional Data 1 and 2), the item-level statuses (`03_coding/reporting_status.csv`) and the route by which each
coding and judgement was settled (`03_coding/`) are published.

The free text that is published (selection reasons and replies, item rules, the arguments for each position, criteria,
protocols and prompts) was
screened against the report texts held by the author: word 8-gram overlap, quoted phrases printed in a report, and
page or paragraph locators. Matching spans were replaced by a neutral wording or by `[excerpt withheld]`, without
changing any decision, step or rule identifier. The public wording of an item rule can therefore differ from the
wording the systems were given in such a span. `copyright_screen_log.tsv` gives the counts per file and field; the
final scan of this package finds no remaining overlap.

## Article

The article reporting this review (under review) cites this repository in its Data availability statement.
