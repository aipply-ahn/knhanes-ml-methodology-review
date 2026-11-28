You are assessing the full text of one report for a systematic methodological review. Apply the eligibility criteria
below literally and independently, using only the text given. Do not use outside knowledge of the paper.

{CRITERIA}

The full text is given page by page; "=== page N ===" marks the start of page N of the PDF.

Return one JSON object {"decisions": [ ... ]} with exactly one entry for the record:
{"record_id": "...", "decision": "INCLUDE" | "EXCLUDE", "code": "F1"|"F2"|"F3"|"F4"|null,
 "evidence": [{"page": <page number>, "text": "<verbatim quotation from that page, <= 40 words>"}, ...],
 "reason": "<one or two sentences>"}
code is null for INCLUDE. Give 1 to 4 quotations. Write the reason in English; quotations stay in the original language of the text. Use only the text given; do not open files, run commands or search the web.

Record:
{RECORD}
