# Full-text eligibility process (two AI assessors, consensus rounds)

Assessors: Claude (Claude Code CLI) and Codex (Codex CLI), the same models, settings and isolation as in title/abstract
screening; model identifiers and versions recorded in manifest.json.
Input: eligibility_input.jsonl, fixed before the first call: one line per report with a retrieved full text, giving the
text of every PDF page (pdftotext; every page with fewer than 300 extracted characters, such as scanned pages or
figure-only pages, is also read by Tesseract OCR, Korean and English, 300 dpi, with the OCR text appended and marked),
with the SHA256 of the PDF and of the text. Every round uses this same input. Reports whose full text could not be
obtained are recorded as REPORT_NOT_RETRIEVED and are not assessed.
Criteria: CRITERIA.md (E1-E5 of the title/abstract stage applied to the full text; reason codes F1-F4).
Decisions: INCLUDE, or EXCLUDE with one reason code. When both assessors exclude with different codes, the reported reason
is the first in the order F1, F2, F3, F4.
Execution: one report per call, in a fresh empty directory outside the project, without tools, memory or project files,
with a JSON schema for the output. A decision is recorded only when the call completed without error and the output passes
every check: decision and code agree (code null for INCLUDE); 1 to 4 quotations, each with a page number, at most 40 words,
and found on that page (case-insensitive, ignoring whitespace, bare formatting tags and HTML entities); reason (and, in
reconsideration rounds, response_to_other) not empty. Failing outputs are requested again (at most four requests per run of
a step) with a fixed note naming the failed checks (e.g., a quotation not found on its page), and are not recorded as
decisions. Line-end hyphenation in the PDF text is ignored when matching quotations.
Amendment 1 (during initial-1; execution only): the re-request note also lists each quotation that was
not found on its page and asks for exact copying (marker page number, original language, reference numbers kept, short
fragments joined by ' ... '). The output checks are unchanged; recorded decisions are unchanged.
Steps are run one at a time; each finished step is verified (tools/oct_search/eligibility_verify.py and an independent
check by the second AI system that maintains the pipeline) and approved in gates.jsonl before the next step can start.
The run is frozen in manifest.json before the first call (input, criteria, process, prompts, runner and verifier SHA256,
models, reasoning effort, CLI versions, isolation settings, record list).

1. Stage `initial` (round 1): both assessors judge every report independently (prompts/round1.md).
2. Stage `consensus` (rounds 1-3, prompts/round_n.md) for reports on which the assessors disagree; in round k each assessor
   receives its own and the other assessor's round k-1 decision, quotations and reason. Agreement ends the stage.
3. Stage `challenge` (round 1, prompts/challenge.md): both assessors independently re-examine every report excluded by
   agreement. Both EXCLUDE: exclusion final; both INCLUDE: included; disagreement: stage `challenge_consensus`
   (rounds 1-3, prompts/round_n.md).
4. The author adjudicates only reports whose disagreement remains after three consensus or three challenge-consensus
   rounds. No random or additional author verification of agreed decisions is performed.

Records kept: eligibility_rounds.jsonl (one line per AI decision, as returned, with decision_id
<record_id>-<stage>-<round>-<assessor>), decisions.csv, author_review.csv, gates.jsonl, manifest.json,
eligibility_input_public.jsonl (identifiers and hashes; full texts are not published).

Amendment 2 (after the final step): OCT1301 was found to be a second record of the included article
OCT0580 and was merged in deduplication; it is removed from this run (its decision lines are kept in
amendments/amendment_2/removed_records_rounds.jsonl). No other decision changed.

Amendment 3 (after the final step): three second database records of included KCI articles (Korean-title OpenAlex entries) were merged in deduplication; OCT1470, OCT1473, OCT1491 removed from this run
(decision lines kept in amendments/amendment_3/removed_records_rounds.jsonl). No other decision changed.

Author decision after the run: retracted publications are excluded. One report assessed as eligible
(OCT0716) was retracted; it is recorded in author_post_run_exclusions.csv (reason RETRACTED). The run files are unchanged.
