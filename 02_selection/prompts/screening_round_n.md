You are re-examining records on which two independent screeners disagreed. Apply the same eligibility criteria.
For each record you see your own decision from the previous round ("your_previous") and the other screener's decision
from the previous round ("other_previous"), with evidence and reason. Re-read the title and screening text, consider the
other argument, and give your decision now. You may keep or change it.

{ELIGIBILITY}

Return one JSON object {"decisions": [...]} with exactly one entry per record, in the input order:
{"record_id": "...", "decision": "FULL_TEXT" | "EXCLUDE_CERTAIN", "code": "X1"|"X2"|"X3"|"X4"|null,
 "evidence": "<verbatim phrase(s) copied from the title or screening text, <= 40 words; separate non-adjacent phrases with ' ... '>",
 "reason": "<one sentence>", "response_to_other": "<why you agree or disagree with the other screener>"}
code is null for FULL_TEXT. Use only the text given; do not open files, run commands or search the web.
Choose FULL_TEXT whenever exclusion is not certain from the text.

Records (JSON lines):
{RECORDS}
