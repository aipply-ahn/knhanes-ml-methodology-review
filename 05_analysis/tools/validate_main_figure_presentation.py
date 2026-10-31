#!/usr/bin/env python3
"""Audit the twelve manuscript figures at the publication layer.

The audit is intentionally independent of the plotting code.  It reads the
exported vector PDFs, checks typography/bounds/reader-facing terminology, and
verifies the PRISMA arithmetic against the locked selection-flow JSON.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "manuscript" / "figs"
OUT = ROOT / "results" / "derived" / "main_figure_presentation_audit.json"
FIGURES = [
    "fig1_prisma",
    "fig2_landscape",
    "fig3_data_use",
    "fig4_populations",
    "fig5_nonclassification",
    "fig6_classification_outcomes",
    "fig7_predictor_training",
    "fig8_model_development",
    "fig9_validation_evaluation",
    "fig10_variable_interpretation",
    "fig11_methodological_appraisal",
    "fig12_temporal_changes",
]
FORBIDDEN = (
    "legacy",
    "pending",
    "source linkage",
    "not yet reviewed",
    "awaiting direct application",
)


def spans(page):
    return [
        span
        for block in page.get_text("dict")["blocks"]
        if "lines" in block
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]


def audit_pdf(stem: str) -> dict:
    path = FIG / f"{stem}.pdf"
    doc = fitz.open(path)
    page = doc[0]
    items = spans(page)
    text = " ".join(item["text"] for item in items)
    normalized = " ".join(text.split())
    # Mathtext subscripts dev/eval are deliberately smaller than their parent
    # U labels and are the only accepted sub-8-point typographic exception.
    substantive = [x for x in items if x["text"].strip() not in {"dev", "eval"}]
    min_font = min(x["size"] for x in substantive)
    clipped = [
        x["text"]
        for x in items
        if x["bbox"][0] < -0.5
        or x["bbox"][1] < -0.5
        or x["bbox"][2] > page.rect.width + 0.5
        or x["bbox"][3] > page.rect.height + 0.5
    ]
    panel_titles = []
    for item in items:
        label = item["text"].strip()
        if re.match(r"^[A-D]\.\s", label):
            panel_titles.append(
                {
                    "label": label,
                    "x_fraction": round(item["bbox"][0] / page.rect.width, 4),
                    "font_pt": round(item["size"], 2),
                }
            )
    checks = {
        "single_page": len(doc) == 1,
        "no_overall_title_inside_figure": not bool(
            re.search(r"(?:^|\s)(?:Figure|Fig\.)\s*\d+", normalized, re.I)
        ),
        "no_internal_workflow_terms": not any(term in normalized.lower() for term in FORBIDDEN),
        "all_text_within_page": not clipped,
        "minimum_substantive_font_at_least_8pt": min_font >= 8.0,
        "denominator_or_count_visible": bool(re.search(r"\b[Nn]\s*=|\bN\s*\(|\bn\s*\(", normalized)),
    }
    return {
        "file": str(path.relative_to(ROOT)),
        "page_width_pt": round(page.rect.width, 2),
        "page_height_pt": round(page.rect.height, 2),
        "minimum_substantive_font_pt": round(min_font, 2),
        "panel_titles": panel_titles,
        "clipped_text": clipped,
        "checks": checks,
        "pass": all(checks.values()),
    }


def prisma_checks() -> dict:
    source = json.loads((ROOT / "results" / "derived" / "final_selection_flow.json").read_text())
    nums = json.loads((ROOT / "results" / "derived" / "protocol_v1_2_manuscript_numbers.json").read_text())["numbers"]
    s, f = source["sources"], source["flow"]
    total = s["total_before_cross_source_deduplication"]
    screened = f["unique_records_screened"]
    assessed = f["records_assessed_against_eligibility"]
    retrieval = source["full_text_retrieval"]
    included_reports = f["eligible_reports_entering_family_linkage"]
    fig1_text = " ".join(
        " ".join(span["text"] for span in spans(page))
        for page in fitz.open(FIG / "fig1_prisma.pdf")
    )
    return {
        # Prompt 091 moved the PubMed raw-retrieval count from the Figure 1 caption to Supplementary Table S3.
        "pubmed_raw_retrieval_count_in_caption_not_diagram": (
            f"{s['pubmed_raw_retrievals']:,}" not in fig1_text
            and "Source-level counts" in (ROOT / "manuscript/bmc_main.tex").read_text()
        ),
        "pubmed_cross_source_unique_contribution_is_visible": (
            f"PubMed  {s['pubmed_unique_beyond_europe_pmc']:,}" in fig1_text  # prompt 110: "not in Europe PMC" stated in the caption
        ),
        "database_index_and_other_source_counts_are_visible": (
            f"Database/index records (n={total - s['kdca_publication_list']:,})" in fig1_text
            and f"n={s['kdca_publication_list']:,}" in fig1_text
        ),
        "identified_minus_duplicates_equals_screened": total - f["duplicates_removed"] == screened,
        "screened_minus_not_advanced_equals_candidates": screened - f["terminology_exclusions"] == assessed,
        "full_text_counts_unknown_not_imputed": all(retrieval[k] is None for k in ("reports_sought", "reports_not_retrieved", "reports_assessed")),
        "unknown_retrieval_in_caption": "not retrieved, and assessed were not recorded" in (ROOT / "manuscript/bmc_main.tex").read_text(),  # prompt 088 wording
        # Prompt 091: plain wording for the two KCI full-text checks.
        "screening_reasons_and_resolved_rechecks_visible": f"No ML or prediction term {f['terminology_exclusions']:,}" in " ".join(fig1_text.split()) and "one dictionary rule" not in fig1_text,  # prompt 106: unified screening rule, no separate KCI row; prompt 110: rule in the caption
        "candidate_decisions_minus_exclusions_equals_eligible_reports": assessed - f["reports_excluded_total"] == included_reports,
        "unique_study_count_matches_locked_manuscript_number": nums["studies"] == 250,  # prompt 106: criterion A (was 220)
    }


def main() -> None:
    rows = [audit_pdf(stem) for stem in FIGURES]
    prisma = prisma_checks()
    result = {
        "schema": "main_figure_presentation_audit_v1",
        "scope": "twelve English main-manuscript vector PDFs",
        "figure_count": len(rows),
        "figures": rows,
        "prisma_arithmetic": prisma,
        "overall_pass": all(row["pass"] for row in rows) and all(prisma.values()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{sum(row['pass'] for row in rows)}/{len(rows)} figure PDFs pass")
    print(f"PRISMA: {sum(prisma.values())}/{len(prisma)} checks pass")
    print(f"overall_pass={result['overall_pass']}")
    if not result["overall_pass"]:
        for row in rows:
            failed = [key for key, value in row["checks"].items() if not value]
            if failed:
                print(row["file"], ", ".join(failed))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
