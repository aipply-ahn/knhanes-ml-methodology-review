# 02_selection: study selection

Role: which records were included and why. Every record went through independent review by both systems, mutual review
of disagreements (up to three rounds), a re-review of every agreed exclusion, and author adjudication of what remained
(40 records at title/abstract, 1 at full text). For each record left to the author, one system wrote a blinded
argument for each position from the earlier records and the other system checked it, for up to three revision rounds
(see the top-level `README.md`). The author reviewed the arguments for every case and made the final decision recorded in `author_decision`. The counts are in the top-level `README.md` and in Supplementary Table
S4 of the article; the criteria and the decision rules are printed in Supplementary Table S2.

| Path | Content |
|---|---|
| `criteria/ELIGIBILITY.md` | Eligibility criteria E1-E5 and exclusion codes X1-X4, fixed before screening (printed, with the decision rules, as Supplementary Table S2) |
| `criteria/ELIGIBILITY_PICOS.md` | The same criteria arranged by PICOS element, for orientation |
| `criteria/FULLTEXT_CRITERIA.md` | Full-text stage: the same criteria applied to the full text, reason codes F1-F4 (as run) |
| `criteria/FULLTEXT_ELIGIBILITY.md` | Earlier draft of the full-text criteria, kept for the record; superseded by `FULLTEXT_CRITERIA.md` |
| `protocol/` | Screening and eligibility protocols as run, with their numbered amendments. They name the working files of the run: `prompts/round1.md`, `round_n.md` and `challenge.md` are published here as `prompts/screening_*.md` and `prompts/eligibility_*.md`, `tools/oct_search/*.py` as `code/*.py`, and the rounds of every screened record as `screening_rounds.jsonl` and `eligibility_rounds.jsonl`; the other working files (`decisions.csv`, `author_review.csv`, `gates.jsonl`, `manifest.json`, `amendments/`, including the rounds of the records an amendment removed before screening) are kept by the author; the final decisions are in the round files and `author_decisions.csv` |
| `prompts/screening_*.md`, `prompts/eligibility_*.md` | Prompts of each round: `round1` independent review, `round_n` mutual review, `challenge` re-review of agreed exclusions |
| `screening_records.jsonl` | Identification of every screened record (title, DOI, PMID, KCI id, kind of text screened); no abstracts |
| `screening_rounds.jsonl` | Title/abstract stage: one line per record, every round in order with both systems' decisions, codes and reasons |
| `eligibility_rounds.jsonl` | Full-text stage: the same, one line per report |
| `author_decisions.csv` | Every decision made by the author on a single record (40 + 1), and the report excluded by the rule on retracted publications. For the 41 adjudicated records: each position's decision through the rounds (`position_A_decision`, `position_B_decision`; A and B are labels drawn per case, not systems), the argument for each position, the question that separates them, the author's decision, the number of revision rounds, and the checker's final verdict with any remaining problem (`remaining_issue`) |
| `prompts/adjudication_arguments_write.txt`, `prompts/adjudication_arguments_check.txt` | Templates of the argument step (writer and checker), also used for the pilot codings |
| `linked_reports_and_boundary_cases.md`, `linked_reports_and_boundary_cases.csv` | Reports of the same study counted once (with the representative report), the full-text exclusions by reason, the report not retrieved and the reports included with KNHANES as the external evaluation dataset (published here only) |
| `included_reports.csv` | The 287 included reports |
| `report_study_links.csv` | Report-to-study links: 279 studies, one representative report each, eight second reports |
| `selection_summary.json` | Counts of the PRISMA flow |
| `prisma_flow.pdf`, `prisma_flow.png` | The PRISMA flow diagram |
| `code/` | Code that ran the rounds, checked them, exported these files and drew the flow diagram |

The reasons are the systems' own short statements. They were screened against the report texts; wording repeated from
a report was replaced by a neutral summary (see `copyright_screen_log.tsv` at the top level).
