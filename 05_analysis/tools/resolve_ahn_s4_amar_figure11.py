#!/usr/bin/env python3
"""Correct two falsely escalated visual-review records after direct source review."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHN = "ahn2025machine__0008__table_S4"
AMAR = "amarbayasgalan2021efficient__0017__figure_11"
AHN_SOURCE = "references/supplements/ahn2025machine/sj-docx-3-cnr-10.1177_10547738251367551.docx"
AHN_IMAGE = "data/visual_manual_review/latest_after_recrop/decoded_recovered/table/ahn2025machine__0008__table_S4__supplement_page5.png"
AMAR_IMAGE = "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/amarbayasgalan2021efficient__0017__figure_11__page12_450dpi.png"

AHN_VISIBLE = (
    "Supplementary Table S4. Columns: Cutoff, Accuracy, Recall, Precision, Specificity, F1-score, AUC. "
    "0.678: 0.940, 0.943, 0.940, 0.938, 0.942, 0.984. "
    "0.766: 0.892, 0.880, 0.896, 0.903, 0.888, 0.955. "
    "0.803: 0.878, 0.867, 0.882, 0.888, 0.875, 0.944."
)
AHN_INTERP = (
    "The clinical cutoff 0.678 has the highest value for every reported performance metric. "
    "The author-designated XGBoost result is Accuracy 0.940, Recall 0.943, Precision 0.940, "
    "Specificity 0.938, F1 0.942, and AUC 0.984."
)
AHN_VALUES = [
    "0.678: Accuracy 0.940; Recall 0.943; Precision 0.940; Specificity 0.938; F1 0.942; AUC 0.984",
    "0.766: Accuracy 0.892; Recall 0.880; Precision 0.896; Specificity 0.903; F1 0.888; AUC 0.955",
    "0.803: Accuracy 0.878; Recall 0.867; Precision 0.882; Specificity 0.888; F1 0.875; AUC 0.944",
]

AMAR_VISIBLE = (
    "Figure 11 is a seven-model ROC plot. Legend AUCs: KNN 0.765; NB 0.732; DT 0.745; "
    "SVM 0.751; RF 0.810; AdaBoost 0.809; VAE based Two-DNN 0.882. "
    "Axes are False Positive Rate and True Positive Rate."
)
AMAR_INTERP = (
    "VAE based Two-DNN has the highest displayed mean AUC (0.882), followed by RF (0.810) "
    "and AdaBoost (0.809). The final rendered Figure 11 and Table 8 both display 0.882; "
    "the isolated 0.881 text-extraction string is not used as the figure-derived value."
)
AMAR_VALUES = [
    "KNN AUC 0.765", "NB AUC 0.732", "DT AUC 0.745", "SVM AUC 0.751",
    "RF AUC 0.810", "AdaBoost AUC 0.809", "VAE based Two-DNN AUC 0.882",
]


def digest(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def update_object(obj: dict) -> None:
    oid = obj.get("object_id")
    if oid == AHN:
        obj.update({
            "source_scope": "supplement",
            "source_path": AHN_SOURCE,
            "source_sha256": digest(AHN_SOURCE),
            "source_format": ".docx",
            "page_or_sheet": "5",
            "caption": "Supplementary Table S4: Predictive performance of the XGBoost model across different cutoff thresholds",
            "image_path": AHN_IMAGE,
            "image_width_px": "2975",
            "image_height_px": "3850",
            "extraction_method": "supplement DOCX rendered to PDF page at 350 dpi",
            "extraction_confidence": "verified",
            "vision_required": "N",
            "chatgpt_vision_status": "completed",
            "chatgpt_review_stage": "supplement_original_review",
            "chatgpt_visible_text": AHN_VISIBLE,
            "chatgpt_interpretation": AHN_INTERP,
            "chatgpt_key_values": json.dumps(AHN_VALUES, ensure_ascii=False),
            "chatgpt_uncertainty": "",
            "manual_review_reason": "",
        })
    elif oid == AMAR:
        obj.update({
            "page_or_sheet": "12",
            "caption": "FIGURE 11. Average AUC of the compared seven algorithms together.",
            "image_path": AMAR_IMAGE,
            "image_width_px": "1750",
            "image_height_px": "1300",
            "extraction_method": "full source-page crop at 450 dpi",
            "extraction_confidence": "verified",
            "vision_required": "N",
            "chatgpt_vision_status": "completed",
            "chatgpt_review_stage": "full_page_recrop_chatgpt_reread",
            "chatgpt_visible_text": AMAR_VISIBLE,
            "chatgpt_interpretation": AMAR_INTERP,
            "chatgpt_key_values": json.dumps(AMAR_VALUES, ensure_ascii=False),
            "chatgpt_uncertainty": "",
            "manual_review_reason": "",
        })


def update_canonical(study: str) -> None:
    path = ROOT / f"data/study_json/{study}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for obj in data["visual_objects"]["items"]:
        update_object(obj)
        if obj.get("object_id") == AHN:
            obj.update({"scope": "supplement", "source_path": AHN_SOURCE, "page_or_sheet": "5", "caption": "Supplementary Table S4: Predictive performance of the XGBoost model across different cutoff thresholds", "image_path": AHN_IMAGE, "visible_text": AHN_VISIBLE, "interpretation": AHN_INTERP, "key_values": AHN_VALUES, "vision_status": "completed", "vision_review_stage": "supplement_original_review", "uncertainty": "", "manual_review_reason": ""})
        elif obj.get("object_id") == AMAR:
            obj.update({"page_or_sheet": "12", "caption": "FIGURE 11. Average AUC of the compared seven algorithms together.", "image_path": AMAR_IMAGE, "visible_text": AMAR_VISIBLE, "interpretation": AMAR_INTERP, "key_values": AMAR_VALUES, "vision_status": "completed", "vision_review_stage": "full_page_recrop_chatgpt_reread", "uncertainty": "", "manual_review_reason": ""})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_annotations() -> None:
    for oid, visible, interpretation, values, stage in (
        (AHN, AHN_VISIBLE, AHN_INTERP, AHN_VALUES, "supplement_original_review"),
        (AMAR, AMAR_VISIBLE, AMAR_INTERP, AMAR_VALUES, "full_page_recrop_chatgpt_reread"),
    ):
        path = ROOT / f"data/visual_object_audit/vision_annotations/{oid}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update({"status": "completed", "visible_text": visible, "interpretation": interpretation, "key_values": values, "uncertainty": "", "manual_review_reason": "", "review_stage": stage})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rewrite_tsv(rel: str, *, remove: set[str] = set(), latest: bool = False, decoded: bool = False) -> None:
    path = ROOT / rel
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        rows = list(reader)
    out = []
    for row in rows:
        oid = row.get("object_id", "")
        if oid in remove:
            continue
        update_object(row)
        if latest and oid in {AHN, AMAR}:
            row["decode_status"] = "COMPLETE_AFTER_SOURCE_RECOVERY_CHATGPT_IMAGE_REREAD"
            row["crop_recovery_status"] = "supplement_docx_rendered_350dpi" if oid == AHN else "repaired_manual_450dpi"
            row["scientific_interpretation_status"] = "COMPLETE"
            row["latest_review_image"] = AHN_IMAGE if oid == AHN else AMAR_IMAGE
            row["latest_image_kind"] = "supplement_source_page" if oid == AHN else "manual_full_figure_crop"
            row["source_file"] = AHN_SOURCE if oid == AHN else "references/pdf/amarbayasgalan2021efficient.pdf"
            row["remaining_uncertainty"] = ""
            row["required_followup"] = ""
            row["chatgpt_image_transcription"] = AHN_VISIBLE if oid == AHN else AMAR_VISIBLE
            row["chatgpt_image_interpretation"] = AHN_INTERP if oid == AHN else AMAR_INTERP
        out.append(row)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader(); writer.writerows(out)


def sync_decoded_from_latest() -> None:
    latest_path = ROOT / "data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv"
    decoded_path = ROOT / "data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv"
    with latest_path.open(encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h, delimiter="\t"); fields = reader.fieldnames or []; latest = list(reader)
    decoded = [r for r in latest if r.get("scientific_interpretation_status") != "SOURCE_RECOVERY_REQUIRED"]
    with decoded_path.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n"); writer.writeheader(); writer.writerows(decoded)


def rebuild_review_queue() -> None:
    """Rebuild the full vision queue from the canonical visual-object ledger."""
    source = ROOT / "data/ALL_REPORT_VISUAL_OBJECTS.tsv"
    target = ROOT / "data/CHATGPT_VISION_REVIEW_QUEUE.tsv"
    with source.open(encoding="utf-8-sig", newline="") as h:
        rows = list(csv.DictReader(h, delimiter="\t"))
    fields = [
        "study_key", "object_id", "object_type", "object_label", "source_scope", "source_path",
        "page_or_sheet", "caption", "image_path", "chatgpt_vision_status", "annotation_path",
        "chatgpt_review_stage", "chatgpt_visible_text", "chatgpt_interpretation", "chatgpt_key_values",
        "chatgpt_uncertainty", "manual_review_reason",
    ]
    queue = []
    for row in rows:
        annotation = ROOT / f"data/visual_object_audit/vision_annotations/{row['object_id']}.json"
        if not annotation.is_file():
            continue
        row["annotation_path"] = str(annotation.relative_to(ROOT))
        queue.append(row)
    with target.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader(); writer.writerows(queue)


def rewrite_jsonl(rel: str) -> None:
    path = ROOT / rel
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        obj=json.loads(line); update_object(obj); rows.append(obj)
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")


def sync_study_index() -> None:
    path = ROOT / "data/STANDARDIZED_STUDY_JSON_INDEX.jsonl"
    replacements = {s: json.loads((ROOT / f"data/study_json/{s}.json").read_text(encoding="utf-8")) for s in ("ahn2025machine", "amarbayasgalan2021efficient")}
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        obj=json.loads(line); rows.append(replacements.get(obj.get("study_id"), obj))
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")


def main() -> None:
    update_canonical("ahn2025machine")
    update_canonical("amarbayasgalan2021efficient")
    update_annotations()
    rewrite_jsonl("data/ALL_REPORT_VISUAL_OBJECTS.jsonl")
    rewrite_tsv("data/ALL_REPORT_VISUAL_OBJECTS.tsv")
    rebuild_review_queue()
    rewrite_tsv("data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv", remove={AHN, AMAR})
    rewrite_tsv("data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv", latest=True)
    rewrite_tsv("data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv", remove={AHN})
    rewrite_tsv("data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv", remove={AHN})
    sync_decoded_from_latest()
    sync_study_index()
    print("resolved", AHN, AMAR)


if __name__ == "__main__":
    main()
