#!/usr/bin/env python3
"""Verify supplement disclosures in full reports still lacking archived files.

The publisher/PMC collection pass can miss files when landing pages are blocked or
structured unusually.  This second pass searches the full report itself for explicit
supplement cross-references and inspects every PDF URI annotation.  Abstract-only
reports are retained as not assessable rather than treated as negative findings.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "ARTICLE_SUPPLEMENT_AUDIT.tsv"
OUT = ROOT / "data" / "MAIN_REPORT_SUPPLEMENT_VERIFICATION.tsv"

EXPLICIT = re.compile(
    r"(?i)(supplement(?:ary|al)\s+(?:material|information|data|files?|tables?|figures?|methods?|results?|appendi(?:x|ces))"
    r"|supporting\s+information|additional\s+files?|online\s+resources?|electronic\s+supplement"
    r"|multimedia\s+appendi(?:x|ces)|보충\s*자료|추가\s*자료|온라인\s*자료)"
)
APPENDIX_HEADER = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?(?:appendix|appendices|부록)\s+[A-Z0-9]")
LINK = re.compile(
    r"(?i)(supplement|supporting|additional.?file|online.?resource|MOESM|/mmc\d"
    r"|\.s\d{3}(?:\.|$)|esm(?:\.|/|$))"
)

# Each strict text/link hit was read in context.  These are content embedded in the
# main PDF or generic checklist/reference language, not disclosures of separate files.
ADJUDICATION = {
    "costello2020identifying": "Appendix A (variable table) is embedded in the main PDF.",
    "davagdorj2020xgboost": "Appendices A-B are embedded in the main PDF; the supplementary-information phrase is the generic TRIPOD checklist item, and the matching PDF URI is a cited supplement-issue article.",
    "shim2021machine": "Appendix A (optimal hyperparameters) is embedded in the main PDF.",
    "dashdondov2023deep": "Appendices A-B are described as sections of the paper and embedded in the main PDF.",
    "kim2025bridging": "The experimental-settings appendix is embedded in the main PDF.",
    "kim2019chronic": "The 'Supplementary Materials' statement links only to the public KNHANES data portal; Appendix A is embedded in the main PDF and no separate study file is disclosed.",
    "khongorzul2022comparison": "Appendix A (correlation and multicollinearity table) is embedded in the main PDF.",
    "dashdondov2024enhancing": "Appendix A (correlation tables) is embedded in the main PDF; the article states that data are contained within the article.",
}


def snippet(text: str, match: re.Match[str]) -> str:
    value = text[max(0, match.start() - 140):match.end() + 220]
    return re.sub(r"\s+", " ", value).strip()[:700]


def main() -> None:
    studies = list(csv.DictReader(AUDIT.open(encoding="utf-8"), delimiter="\t"))
    studies = [r for r in studies if r["supplement_status"] == "not_identified_in_reachable_sources"]
    rows = []
    for r in studies:
        key = r["key"]
        if r["report_source"] != "full_text":
            rows.append({
                "key": key, "report_source": r["report_source"], "main_text_checked": "N",
                "pdf_links_checked": "N", "explicit_text_hits": "", "appendix_header_hits": "",
                "candidate_pdf_links": "", "adjudication": "not_assessable_abstract_only",
                "evidence": "The full report was unavailable; absence of a supplement cannot be inferred.",
            })
            continue

        md = ROOT / "references" / "md" / f"{key}.md"
        pdf = ROOT / "references" / "pdf" / f"{key}.pdf"
        text = md.read_text(encoding="utf-8", errors="ignore")
        explicit = list(EXPLICIT.finditer(text))
        appendices = list(APPENDIX_HEADER.finditer(text))
        links = []
        with fitz.open(pdf) as doc:
            for page_number, page in enumerate(doc, 1):
                for item in page.get_links():
                    uri = item.get("uri") or ""
                    if uri and LINK.search(uri):
                        links.append(f"p{page_number}:{uri}")

        has_signal = bool(explicit or appendices or links)
        evidence = ADJUDICATION.get(key, "")
        if has_signal and not evidence:
            decision = "requires_manual_follow_up"
            evidence = "A strict disclosure signal was found and requires contextual adjudication."
        elif has_signal:
            decision = "embedded_or_false_positive_no_separate_file"
        else:
            decision = "verified_no_disclosure_in_main_report"
            evidence = "No explicit supplement cross-reference or supplement-like PDF URI annotation was found."
        snippets = [snippet(text, m) for m in (explicit + appendices)[:4]]
        rows.append({
            "key": key, "report_source": r["report_source"], "main_text_checked": "Y",
            "pdf_links_checked": "Y", "explicit_text_hits": len(explicit),
            "appendix_header_hits": len(appendices), "candidate_pdf_links": "; ".join(links),
            "adjudication": decision, "evidence": evidence + (" | " + " || ".join(snippets) if snippets else ""),
        })

    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["adjudication"] for r in rows)
    lines = [
        "# Main-report verification of supplementary-material disclosures", "",
        f"- Reports remaining after archive retrieval: {len(rows)}",
        f"- Full reports with main-text and PDF-link verification: {sum(r['main_text_checked'] == 'Y' for r in rows)}",
        f"- Abstract-only reports, not assessable from the main report: {counts['not_assessable_abstract_only']}",
        f"- No disclosure signal in the full report: {counts['verified_no_disclosure_in_main_report']}",
        f"- Embedded appendices/checklist/reference false positives: {counts['embedded_or_false_positive_no_separate_file']}",
        f"- Unresolved candidates requiring follow-up: {counts['requires_manual_follow_up']}", "",
        "A negative result means that no explicit cross-reference or supplement-like PDF hyperlink was found in the retrieved main report. It does not prove that a publisher never hosted an unlinked file.", "",
        "| Study | Report | Decision | Evidence |", "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['key']} | {r['report_source']} | {r['adjudication']} | {r['evidence'].replace('|', '/')} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(dict(counts))


if __name__ == "__main__":
    main()
