#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T02:35:00+09:00"
SRC = "references/pdf/byeon2022exploring.pdf"

apply_reviews([
    {
        "reviewed_at": T, "study_key": "byeon2022exploring",
        "object_id": "byeon2022exploring__0001__figure_1", "object_type": "figure",
        "object_label": "figure:1", "object_number": "1", "source_scope": "main",
        "source_path": SRC, "page_or_sheet": "7 / Frontiers g001",
        "caption": "Figure 1. Feature importance of impaired fasting glucose predictors in non-diabetics based on CatBoost (top eight variables).",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/byeon2022exploring__0001__figure_1__publisher_original.jpg",
        "width": 1232, "height": 408,
        "extraction_method": "original publisher JPEG recovered from the official Frontiers figure endpoint",
        "content_domains": "feature importance; model interpretation; impaired fasting glucose",
        "visible_text": "Permutation-style importance is plotted as decrease in AUC for eight coded predictors. Rank order is: (1) age (~0.098), (2) high cholesterol (~0.026), (3) waist-to-height ratio (~0.024), (4) BMI (~0.016), (5) drinking more than one shot per month in the past year (~0.009), (6) marital status (~0.009), (7) hypertension (~0.008), and (8) smoking (~0.005). Error bars are shown for each estimate.",
        "interpretation": "Age dominates the CatBoost importance plot, contributing roughly four times the decrease in AUC of the next-ranked predictor. The remaining seven predictors have much smaller, progressively declining importance. Values are read approximately from the plotted axis rather than treated as tabulated estimates.",
        "key_values": ["Rank 1 age, decrease in AUC approximately 0.098", "Rank 2 high cholesterol approximately 0.026", "Rank 3 waist-to-height ratio approximately 0.024", "Rank 4 BMI approximately 0.016", "Ranks 5-8: drinking, marital status, hypertension, smoking"],
    },
    {
        "reviewed_at": T, "study_key": "byeon2022exploring",
        "object_id": "byeon2022exploring__0003__figure_2", "object_type": "figure",
        "object_label": "figure:2", "object_number": "2", "source_scope": "main",
        "source_path": SRC, "page_or_sheet": "8 / Frontiers g002",
        "caption": "Figure 2. A nomogram for predicting impaired fasting glucose in South Korean non-diabetics.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/byeon2022exploring__0003__figure_2__publisher_original.jpg",
        "width": 1216, "height": 512,
        "extraction_method": "original publisher JPEG recovered from the official Frontiers figure endpoint",
        "content_domains": "nomogram; risk prediction; impaired fasting glucose",
        "visible_text": "The nomogram contains point scales for: (1) age, (2) BMI, (3) high cholesterol, (4) marital status, (5) drinking, (6) waist-to-height ratio, (7) smoking, and (8) hypertension, followed by total points and predicted probability. The displayed example markers accumulate to roughly 350 total points and a probability in the mid-80% range.",
        "interpretation": "The nomogram makes the dominance of older age and high BMI visually explicit, with additional points from cholesterol, marital status, drinking, waist-to-height ratio, smoking, and hypertension. The marked high-risk example corresponds to an estimated impaired-fasting-glucose probability around the mid-80% range (the accompanying text reports 87%).",
        "key_values": ["Eight predictors", "Age has the widest point span", "BMI has the second-widest span", "Displayed total approximately 350 points", "Displayed probability approximately mid-80%; accompanying text 87%"],
    },
])
