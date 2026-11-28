# Title/abstract screening process (two AI screeners, consensus rounds)

Screeners: Claude (Claude Code CLI) and Codex (Codex CLI); model identifiers and versions recorded in manifest.json.
Input: screening_input.jsonl, fixed before round 1: one line per record with record_id, title, screening_text and
text_source (published abstract; or, for reports without an abstract, the lead paragraph, the letter text or the full
text of a 2-page paper). Every round uses this same input.
Decision codes in every stage: FULL_TEXT or EXCLUDE_CERTAIN (with code X1-X4); the same parser reads all rounds.
Execution: each screener is called in a fresh empty directory outside the project, with customisations disabled and no
tools (Claude: --safe-mode, --tools "", no setting sources, no MCP servers; Codex: an isolated CODEX_HOME holding only the
login, user configuration and rules ignored, tool-capable features disabled, read-only sandbox, and any tool event rejects
the output), without session persistence and with a JSON schema for the output, in batches of 20 records (the same
batches for both screeners). A decision is recorded for a record only when the call completed without error and the
output for that record passes every check: the record is returned exactly once; decision and code agree (code null for
FULL_TEXT, X1-X4 for EXCLUDE_CERTAIN); reason (and, in reconsideration rounds, response_to_other) is not empty; evidence is
not empty, has at most 40 words and is found verbatim (case-insensitive, ignoring whitespace, bare formatting tags such as <i> or <sub>, and HTML
entities; ' ... ' separates phrases) in the title or screening text. Records failing a check are requested again (at most four requests per run of a step); a step
that still lacks decisions stops as an execution error and is resumed later for the missing records only. Failed
outputs are not recorded as decisions.
Steps are run one at a time; each finished step is verified (tools/oct_search/screening_verify.py and an independent
check by the second AI system that maintains the pipeline) and approved in gates.jsonl before the next step can start.
The run is frozen in manifest.json before the first call: input, criteria, process, prompts, runner and verifier (SHA256),
model identifiers, reasoning effort, CLI versions, isolation settings and the record list; a changed item stops the run.
Amendment 1 (during initial-1, before the step was completed): evidence matching ignores whitespace, bare
formatting tags (h1-h6, i, b, em, strong, sub, sup, title, p, br, span, div, bold, italic, u, sc) and HTML entities;
other '<' and '>' characters (e.g. 'p < 0.05', '<median') are kept. Reason: two records could not be quoted under the
original rule (markup such as <i>n</i> in a stored abstract; spaces inside words in a PDF-extracted Korean abstract).
All decisions recorded before the amendment pass both rules; no input, criterion, prompt or decision changed.
Previous versions and hashes: amendments/amendment_1/.
Amendment 2 (final step, before approval): the first derivation of decisions.csv classified the 13 records
whose challenge disagreement remained after three rounds as excluded (their earlier agreed exclusion), contrary to
step 4 below; runner and verifier are corrected so these records go to author adjudication, and the verifier now also
checks the counts. No screening decision changed; decisions.csv and author_review.csv are re-derived. Previous versions
and the withdrawn files: amendments/amendment_2/.
Amendment 3 (after the final step): the publication-type rule applied before screening was extended to
records that are not research reports by their metadata type (code, data or supplement deposits, a repository project,
conference abstracts); 19 such records had been screened. They are removed from the screening input and reported as
removed before screening; their recorded decisions (16 exclusions, 3 selections for full text) are kept in
amendments/amendment_3/removed_records_rounds.jsonl and do not enter decisions.csv. No other decision changed.
Amendment 4: conference abstracts published as journal-article records (found from supplement issue or page numbering and each confirmed on the publisher page) were added to the publication-type rule; 8 records (OCT0070, OCT0222, OCT0236, OCT0296, OCT0339, OCT0393, OCT0609, OCT1501) are removed from the
screening input and reported as removed before screening; their recorded decisions are kept in
amendments/amendment_4/removed_records_rounds.jsonl. No other decision changed.
Amendment 5: further conference abstracts published as journal-article records (supplement issue or page numbering; each confirmed on the publisher page) were added to the publication-type rule; 7 records (OCT0219, OCT0233, OCT0482, OCT0483, OCT0484, OCT0568, OCT0757) are removed from the
screening input and reported as removed before screening; their recorded decisions are kept in
amendments/amendment_5/removed_records_rounds.jsonl. No other decision changed.
Amendment 6: a second database record of an included article (OpenAlex entry with the subtitle in the title and no DOI; the same article as OCT0580) was merged in deduplication as a documented exception; 1 records (OCT1301) are removed from the
screening input and reported as removed before screening; their recorded decisions are kept in
amendments/amendment_6/removed_records_rounds.jsonl. No other decision changed.
Amendment 7: three OpenAlex entries with only the Korean title and no DOI, each a second database record of an included KCI article, were merged in deduplication as documented exceptions; 3 records (OCT1470, OCT1473, OCT1491) are removed from the
screening input and reported as removed before screening; their recorded decisions are kept in
amendments/amendment_7/removed_records_rounds.jsonl. No other decision changed.
Reported exclusion reason: when both screeners exclude with different codes, the first in the order X4, X1, X2, X3.

1. Stage `initial` (round 1): both screeners judge every record independently (prompts/round1.md).
2. Stage `consensus` (rounds 1-3, prompts/round_n.md) for records on which the screeners disagree. In round k each screener
   receives its own decision from the previous round (round k-1; the initial stage for k = 1) and the other screener's
   decision, evidence and reason from that round. Records on which the screeners agree leave the stage with that decision.
3. Stage `challenge` (round 1, prompts/challenge.md): both screeners independently re-examine every record excluded by
   agreement in stages 1-2. If both return EXCLUDE_CERTAIN the exclusion is final; if both return FULL_TEXT the record
   goes to full-text review. Only discordant records enter stage `challenge_consensus` (rounds 1-3, prompts/round_n.md,
   same input rule as stage 2), where agreement on FULL_TEXT sends the record to full-text review and agreement on
   EXCLUDE_CERTAIN makes the exclusion final.
4. The author adjudicates only records whose disagreement remains unresolved after three consensus rounds or three
   challenge-consensus rounds. No random or additional author verification of agreed decisions is performed.

## Records kept (one consolidated file per stage)
- screening_input.jsonl: the fixed screening text, in the language in which it was given to the screeners (Korean-language
  reports keep their original title and abstract; nothing is translated). For copyrighted text that cannot be published
  (one full text) the public file gives the source, identifier and SHA256 of the text instead; rerunning that record
  requires obtaining the text from its source, while its recorded decisions remain inspectable in screening_rounds.jsonl.
- screening_rounds.jsonl: one line per AI decision in every executed stage and round, with decision_id
  (<record_id>-<stage>-<round>-<screener>), record_id, stage, round, screener, run_id, prompt_id, decision, code,
  evidence, reason and, in reconsideration rounds, response_to_other. The structured outputs are kept as returned; they
  are not rewritten or summarised afterwards. Rounds that were not executed produce no lines.
- decisions.csv: one line per record with the final decision, the stage and round in which it was fixed, the decision_ids
  it rests on, and the author adjudication where applicable.
- author_review.csv: author decisions on unresolved records.
- manifest.json: frozen file hashes, model identifiers, reasoning effort, CLI versions, isolation settings, record list and,
  per step, start/finish times, number of calls and re-requests (referenced by run_id and prompt_id; not repeated on every
  JSONL line).
- gates.jsonl: verification and approval of each finished step.
- Not kept in the public package: temporary batch files, terminal transcripts, retry/debug logs, API transport logs,
  token counts and model reasoning traces.

## Language
All public documentation, protocols, prompts, decision records (including the screeners' reasons) and metadata are in
English. Korean appears only in source data: the Korean search terms (verbatim) and the bibliographic records of
Korean-language reports (titles and abstracts as screened).
