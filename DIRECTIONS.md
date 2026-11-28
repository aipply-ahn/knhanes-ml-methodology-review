# The author's directions

The author steered the reconciliation by directions that apply to groups of cases (step 3 in the `step` fields of the
round files). Single records or codings were decided by the author only in three places: the 40 title/abstract and 1
full-text adjudications, and the 26 open pilot codings. Every direction below is implemented in code, so it was applied
in the same way to every case it covers. The stage numbers refer to the four stages in `README.md`.

## Study selection

| When | Direction | Implemented in |
|---|---|---|
| Before screening | Every exclusion on which both systems agree is re-examined once by both; discordant re-examinations go through up to three consensus rounds; records still in disagreement are adjudicated by the author | `02_selection/protocol/SCREENING_PROTOCOL.md` (stage `challenge`), `02_selection/prompts/*_challenge.md` |
| After the title/abstract run | Records that are not research reports by their metadata type (code, data or supplement deposits, conference abstracts, including abstracts published as journal-article records) are removed before screening (protocol amendments 3-5) | `02_selection/protocol/SCREENING_PROTOCOL.md` |
| After the title/abstract run | Second database records of an included article are merged in deduplication as documented exceptions (amendments 6-7) | `02_selection/protocol/SCREENING_PROTOCOL.md`, `01_search/dedup_rule_merges.tsv` |
| After full-text assessment | Retracted publications are excluded | `02_selection/protocol/ELIGIBILITY_PROTOCOL.md` |
| Stage 4 | For every record left to the author, one system writes, blinded to which system held which view, the strongest argument for each position and the question that separates them; the other system checks it (up to three revision rounds; a remaining problem is recorded with the case); the author reviews the arguments and makes the final decision | `02_selection/code/adjudication_arguments.py`, `02_selection/prompts/adjudication_arguments_*.txt`, `02_selection/author_decisions.csv` |

## Data coding

| Direction | Stage | Implemented in |
|---|---|---|
| A difference that does not change what a reader takes from the review table is settled by a structural rule (the side with more printed numbers, then more value entries, then A) when both systems judge it not material | 3: not material | `03_coding/code/coding_material.py` |
| An inconsistency flagged by one coding only is settled by a factual check of the cited places by both systems | 3: inconsistency check | `03_coding/code/coding_inconsistency.py` |
| Differences of form and differences in how a rule applies are settled by rule; only substantive differences go further. Rule-reading differences are checked again blind (the two codings anonymised) | 3: form, rule or substance; blind rule check | `03_coding/code/coding_triage.py`, `03_coding/code/coding_rule_blind.py` |
| The rest is not settled one case at a time: for each item in dispute, both systems find the recurring causes and agree on one minimal common rule in at most three cross-checked rounds (round 3 tests both candidates on other cases), which is applied to every open case of the item | 3: item rule agreed by both | `03_coding/code/coding_field_rules.py` |
| For an item without an agreed rule, the rule is taken from review comments accepted by the author or, otherwise, the suggested rule is adopted after checking that it does not contradict the item definition; it is written in short form by one system and checked by the other, and applied to every open case | 4: item rule set under the author's direction | `03_coding/code/coding_field_decide.py` |
| What remains is settled by rule, without a judgement on the case: the coding is written under the rule once more; if still not accepted, the coding a checker accepted under the rule is kept; otherwise the item is coded unclear | 4: fallback | `03_coding/code/coding_rule_fix.py` |
| In the ten pilot reports, open codings were settled by review comments that the author accepted | 4: pilot codings decided by the author | `03_coding/code/coding_apply_decisions.py` |
| For each of the 26 pilot codings, blinded arguments for each of the two codings are written and checked as for the selection records; the author reviews the arguments and makes the final decision | 4: pilot codings decided by the author | `02_selection/code/adjudication_arguments.py`, `03_coding/author_pilot_decisions.csv` |

The TRIPOD+AI requirement coding (52 requirements x 217 classification studies) followed the same directions.

The author reviewed the arguments for every case and made the final decision recorded in `author_decision`.
