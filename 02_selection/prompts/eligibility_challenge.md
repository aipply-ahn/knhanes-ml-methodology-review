Two assessors agreed to exclude the report below. Your task now is to check whether an eligible report may have been
excluded in error. Re-read the full text against the criteria below, looking in particular for a learner, data use or
purpose described only in the methods, tables, figures or appendices. Return INCLUDE if the report meets all criteria;
otherwise return EXCLUDE with the reason code and supporting evidence.

{CRITERIA}

The full text is given page by page; "=== page N ===" marks the start of page N of the PDF.

Return one JSON object {"decisions": [ ... ]} with exactly one entry for the record:
{"record_id": "...", "decision": "INCLUDE" | "EXCLUDE", "code": "F1"|"F2"|"F3"|"F4"|null,
 "evidence": [{"page": <page number>, "text": "<verbatim quotation from that page, <= 40 words>"}, ...],
 "reason": "<one or two sentences>"}
code is null for INCLUDE. Give 1 to 4 quotations. Write the reason in English; quotations stay in the original language of the text. Use only the text given; do not open files, run commands or search the web.

Record:
{RECORD}
