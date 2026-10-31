#!/usr/bin/env python3
"""Apply direct ChatGPT image rereads for the four user-identified repaired crops."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"

UPDATES = {
    "ahn2025machine__0001__figure_1": {
        "visible": "Complete participant flow: KNHANES 2016–2020 participants n=39,738; 7,610 aged under 19 excluded, leaving adults aged ≥19 n=32,128. Of these, 29,012 without diagnosed diabetes were excluded, leaving 3,116 participants with diabetes. A further 615 were excluded (pregnancy n=0, missing EQ-5D index n=231, missing weights n=384), yielding final analytic n=2,501.",
        "interpretation": "The flow is arithmetically consistent: 39,738−7,610=32,128; 32,128−29,012=3,116; 3,116−615=2,501. The final-stage exclusions sum to 615. The repaired crop now contains the complete selection pathway, not only the exclusion boxes.",
    },
    "anon2025improving__0003__figure_2": {
        "visible": "Figure 2 experimental workflow: 실제 데이터 (real data) → 데이터 전처리 (data preprocessing). The preprocessed data branch to 언더샘플링 (undersampling) and 합성데이터 Class 1 (synthetic data, Class 1); these feed 훈련데이터 증강 (training-data augmentation), followed by XGBoost 분류 모델 학습 및 성능 평가 (XGBoost classifier training and performance evaluation).",
        "interpretation": "The study combines majority-class undersampling with minority Class-1 synthetic-data generation to construct an augmented training set, then trains and evaluates an XGBoost classifier. The repaired crop is a workflow only; the prior transcription of Table 2 performance values did not belong to this figure and has been removed from this object-level reading.",
    },
    "anon2026partial__0002__figure_1": {
        "visible": "Complete Figure 1 correlation heatmap. Predictor labels are sex, age, edu, self_health, Hypertension, Diabetes, Asthma, perceived.body.image, GAD, stress, suicidal, mental_counsel, smoking, weekly_walking_days, BMI, drinking, marital_status, and employment. The legend spans correlation −1.0 (purple/blue) to 0 (white) to +1.0 (red). Most displayed cells are close to white; a few moderate positive and negative cells are present.",
        "interpretation": "The matrix suggests generally weak pairwise correlation among predictors, with isolated stronger associations rather than a broad multicollinearity block. Exact pairwise coefficients are not printed, so numerical correlations should not be inferred from color alone. The repaired crop now exposes the full predictor-label axis and heatmap extent.",
    },
    "anon2026partial__0005__figure_4": {
        "visible": "Complete four-panel partial-dependence figure. Age: predicted y is nearly flat around 25.2 in the early 20s and gradually decreases to about 24.2 by the mid-60s. self_health categories 1–5: predicted y decreases monotonically from about 26.0 to about 22.0. Stress categories 1–4: predicted y rises from about 23.8–24.0 to about 25.4. Suicidal: predicted y is about 24.7 for No and 23.6 for Yes. Rug marks show observed support along continuous/ordinal axes.",
        "interpretation": "Conditional on the fitted model, poorer self-rated health category and suicidal=Yes are associated with lower predicted outcome, while higher stress category is associated with a modestly higher predicted outcome; age shows a small downward trend. These are model-based partial-dependence patterns, not causal effects. All four captioned predictors are now visible in the repaired crop.",
    },
}


def main():
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t")); fields = list(rows[0])
    for r in rows:
        u = UPDATES.get(r["object_id"])
        if not u:
            continue
        r["current_visible_text"] = u["visible"]
        r["current_interpretation"] = u["interpretation"]
        r["uncertainty"] = ""
        r["manual_review_reason"] = ""
        r["reviewer_decision"] = "complete_after_repaired_crop_chatgpt_image_reread"
        r["reviewer_transcription"] = u["visible"]
        r["reviewer_notes"] = f"{stamp} | {u['interpretation']} | OCR engine not used."
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    for fp in (ROOT / "data/study_json").glob("*.json"):
        data = json.loads(fp.read_text(encoding="utf-8")); changed = False
        for obj in data.get("visual_objects", {}).get("items", []):
            u = UPDATES.get(obj.get("object_id"))
            if not u:
                continue
            obj["visible_text"] = u["visible"]
            obj["interpretation"] = u["interpretation"]
            obj["vision_status"] = "completed"
            obj["vision_review_stage"] = "post_recrop_direct_chatgpt_image_reread"
            obj["uncertainty"] = ""
            obj["manual_review_reason"] = ""
            changed = True
        if changed:
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({"updated_objects": len(UPDATES), "review_method": "direct_chatgpt_image", "ocr_engine_used": False})


if __name__ == "__main__":
    main()
