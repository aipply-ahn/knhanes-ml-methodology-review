Both screeners agreed to exclude the records below. Your task now is to look for eligible studies that may have been
missed. For each record, ask whether the title and screening text leave any realistic possibility that the report fitted
a supervised non-regression learner to participant-level KNHANES data for a health outcome or ML method development
(for example, a method named only in the full text, KNHANES used as a validation set, or an ambiguous term such as
"prediction model" or "data mining"). Apply the eligibility criteria below.

{ELIGIBILITY}

Use the same decision codes as in screening. Return FULL_TEXT if the record should be reconsidered at full text;
otherwise return EXCLUDE_CERTAIN with the exclusion code and supporting evidence.
Return one JSON object {"decisions": [...]} with exactly one entry per record, in the input order:
{"record_id": "...", "decision": "FULL_TEXT" | "EXCLUDE_CERTAIN", "code": "X1"|"X2"|"X3"|"X4"|null,
 "evidence": "<verbatim phrase(s) copied from the title or screening text, <= 40 words; separate non-adjacent phrases with ' ... '>",
 "reason": "<one sentence>"}
code is null for FULL_TEXT. Use only the text given; do not open files, run commands or search the web.

Records (JSON lines):
{RECORDS}
