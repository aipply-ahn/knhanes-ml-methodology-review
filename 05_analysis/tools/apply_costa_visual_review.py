#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

apply_reviews([{
    "reviewed_at": "2026-09-14T03:15:00+09:00",
    "study_key": "costa2026integrated", "object_id": "costa2026integrated__0001__figure_1",
    "object_type": "figure", "object_label": "figure:1", "object_number": "1",
    "source_scope": "main", "source_path": "references/pdf/costa2026integrated.pdf",
    "page_or_sheet": "7", "caption": "Figure 1. Model design pipeline.",
    "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/costa2026integrated__0001__figure_1__page7_300dpi.png",
    "width": 2100, "height": 480,
    "extraction_method": "300-dpi source-page render with exact figure-only recrop",
    "content_domains": "study design; model development; internal validation; external validation; mortality association",
    "visible_text": "Data sources: NHANES 2011–2016 (train/calibration), NHANES 2017–2020 (internal test), KNHANES 2015 (external validation), and linked National Death Index (mortality). Preprocessing: non-laboratory predictor selection, NHANES↔KNHANES harmonization, missing-data handling. Model development: three XGBoost classifiers for diabetes, CKD, and CVD with cross-validated calibration. Model performance: internal NHANES test AUC, PR-AUC, calibration and Brier score; external KNHANES discrimination and calibration. Mortality association: NHANES adults ≥40 years, linked cause-specific death, Cox models per 10%-point predicted probability of disease, and Kaplan–Meier curves by predicted-probability quartiles.",
    "interpretation": "The pipeline separates temporal internal testing from cross-country external validation and then reuses predicted disease probabilities for mortality association analyses. It also makes explicit that the deployed predictors are harmonized non-laboratory variables and that calibration is evaluated alongside discrimination.",
    "key_values": ["NHANES 2011–2016 train/calibration", "NHANES 2017–2020 internal test", "KNHANES 2015 external validation", "Three XGBoost classifiers: diabetes, CKD, CVD", "Metrics: AUC, PR-AUC, calibration, Brier score", "Mortality: Cox HR per 10%-point PPD and Kaplan–Meier by PPD quartile"],
}])
