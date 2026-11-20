You are screening titles and abstracts for a systematic methodological review. Apply the eligibility criteria below
literally and independently. Do not use outside knowledge of the paper beyond the text given.

{ELIGIBILITY}

Each record has record_id, title, text_source and screening_text. Return one JSON object {"decisions": [...]} with exactly one entry per record, in the input order:
{"record_id": "...", "decision": "FULL_TEXT" | "EXCLUDE_CERTAIN", "code": "X1"|"X2"|"X3"|"X4"|null,
 "evidence": "<verbatim phrase(s) copied from the title or screening text, <= 40 words; separate non-adjacent phrases with ' ... '>",
 "reason": "<one sentence>"}
code is null for FULL_TEXT. Use only the text given; do not open files, run commands or search the web.
Choose FULL_TEXT whenever exclusion is not certain from the text.

Records (JSON lines):
{RECORDS}
