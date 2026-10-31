"""Build the performance-figure subset from the exhaustive visual-object ledger.

Image content in ``ALL_REPORT_VISUAL_OBJECTS.tsv`` was transcribed and interpreted by
ChatGPT vision. Native PDF/OOXML text is retained where available. This script never
imports or invokes an OCR engine; it only subsets those already-audited records.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from canonical_data import included_extractions

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
OUT_STUDY = ROOT / "data/FIGURE_PERFORMANCE_AUDIT.tsv"
OUT_FIGURE = ROOT / "data/FIGURE_PERFORMANCE_CANDIDATES.tsv"

METRICS = {
    "AUROC/AUC": r"\b(?:auroc|auc)\b|receiver operating characteristic|roc curve",
    "accuracy": r"\baccuracy\b|정확도",
    "sensitivity/recall": r"\bsensitiv(?:ity|ities)\b|\brecall\b|민감도|재현율",
    "specificity": r"\bspecificity\b|특이도",
    "precision/PPV": r"\bprecision\b|\bppv\b|정밀도",
    "F1": r"\bf[ -]?1(?:[ -]?score)?\b",
    "AUPRC": r"\bauprc\b|average precision|precision.?recall curve",
    "RMSE/MSE": r"\brmse\b|root mean squar|\bmse\b|mean squared error",
    "MAE": r"\bmae\b|mean absolute error",
    "R2": r"\br\s*[²2]\b|r[- ]squared",
    "calibration": r"calibrat|brier",
    "confusion matrix": r"confusion matrix",
    "loss/error": r"\bloss\b|prediction error|error rate",
    "model rank/comparison": r"model performance|performance comparison|compar(?:ison|ing).{0,30}(?:model|algorithm)|rank(?:ing|ed)?",
}
METRIC_RE = {k: re.compile(v, re.I) for k, v in METRICS.items()}
NUMBER_RE = re.compile(r"(?<!\d)(?:0?\.\d{2,4}|\d{1,2}\.\d+|\d{1,3}(?:\.\d+)?\s*%)(?!\d)")


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def actual_task_group(d: dict) -> str:
    if d.get("task") == "classification":
        return "Classification"
    if d.get("task") == "regression":
        return "Continuous-outcome prediction"
    return "Non-predictive/structural/data-processing"


def main() -> None:
    extraction = {d["key"]: d for d in included_extractions()}
    included = set(extraction)
    with open(LEDGER, encoding="utf-8-sig") as f:
        objects = [r for r in csv.DictReader(f, delimiter="\t")
                   if r["study_key"] in included and r["object_type"] == "figure"]

    by_study: dict[str, list[dict]] = defaultdict(list)
    candidates: list[dict] = []
    for r in objects:
        key_values = clean(r.get("chatgpt_key_values"))
        evidence = " ".join(filter(None, [
            clean(r.get("caption")), clean(r.get("native_text")),
            clean(r.get("chatgpt_visible_text")), clean(r.get("chatgpt_interpretation")),
            key_values,
        ]))
        found = [name for name, pattern in METRIC_RE.items() if pattern.search(evidence)]
        numbers = list(dict.fromkeys(x.replace(" ", "") for x in NUMBER_RE.findall(
            " ".join([clean(r.get("chatgpt_visible_text")), key_values, clean(r.get("native_text"))])
        )))
        rec = {
            "manuscript": r["study_key"], "pdf_path": r["source_path"],
            "source_scope": r["source_scope"], "page": r["page_or_sheet"],
            "figure": r["object_number"] or r["object_label"], "object_id": r["object_id"],
            "caption": clean(r["caption"]), "image_path": r["image_path"],
            "chatgpt_vision_status": r["chatgpt_vision_status"],
            "detected_metrics": "; ".join(found),
            "numeric_labels_detected": "; ".join(numbers[:60]),
            "vision_text_excerpt": clean(r.get("chatgpt_visible_text"))[:1200],
            "vision_interpretation_excerpt": clean(r.get("chatgpt_interpretation"))[:1200],
            "candidate": "Y" if found else "N",
        }
        by_study[r["study_key"]].append(rec)
        if found:
            candidates.append(rec)

    fields = list(candidates[0]) if candidates else []
    with open(OUT_FIGURE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(candidates)

    study_rows = []
    for key in sorted(included):
        figs = by_study.get(key, [])
        cands = [r for r in figs if r["candidate"] == "Y"]
        detected = sorted({m for r in cands for m in r["detected_metrics"].split("; ") if m})
        d = extraction[key]
        extracted = clean(d.get("metrics"))
        locations = "; ".join(f"Fig {r['figure']} ({r['source_scope']} {r['page']})" for r in cands)
        if d.get("source") == "abstract_only":
            status = "Abstract-only report; no full-report figure available"
        elif not figs:
            status = "No figure object recovered from the available report package"
        elif not cands:
            status = "All recovered figures screened; no performance candidate detected"
        elif all(r["chatgpt_vision_status"] in {"completed", "not_required"} for r in cands):
            status = "Performance candidate(s) interpreted in the ChatGPT/native-text visual ledger"
        else:
            status = "Performance candidate(s) present; at least one remains uncertain or unreadable"
        study_rows.append({
            "key": key, "task": actual_task_group(d), "source": d.get("source", ""),
            "catalogued_figures_screened": len(figs),
            "performance_figure_candidates": len(cands),
            "detected_metrics": "; ".join(detected), "candidate_locations": locations,
            "structured_metrics_has_numeric_value": "Y" if NUMBER_RE.search(extracted) else "N",
            "audit_status": status,
        })
    with open(OUT_STUDY, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(study_rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(study_rows)

    print(json.dumps({
        "included_studies": len(included), "figures_screened": len(objects),
        "candidate_figures": len(candidates),
        "studies_with_candidates": len({r["manuscript"] for r in candidates}),
        "image_transcription": "ChatGPT vision only; no OCR engine",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
