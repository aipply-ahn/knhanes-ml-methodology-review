You and another assessor disagreed on the full-text eligibility of the report below. You see your own decision from the
previous round ("your_previous") and the other assessor's decision from the previous round ("other_previous"), with
evidence and reason. Re-read the full text and the criteria and decide again. You may keep or change your decision.

{CRITERIA}

The full text is given page by page; "=== page N ===" marks the start of page N of the PDF.

Return one JSON object {"decisions": [ ... ]} with exactly one entry for the record:
{"record_id": "...", "decision": "INCLUDE" | "EXCLUDE", "code": "F1"|"F2"|"F3"|"F4"|null,
 "evidence": [{"page": <page number>, "text": "<verbatim quotation from that page, <= 40 words>"}, ...],
 "reason": "<one or two sentences>", "response_to_other": "<why you agree or disagree with the other assessor>"}
code is null for INCLUDE. Give 1 to 4 quotations. Write the reason and response_to_other in English; quotations stay in the original language of the text. Use only the text given; do not open files, run commands or search the web.

Record:
{RECORD}
