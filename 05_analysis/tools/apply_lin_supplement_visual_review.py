#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T02:10:00+09:00"

apply_reviews([
    {
        "reviewed_at": T,
        "study_key": "lin2026association",
        "object_id": "lin2026association__0006__figure_S3",
        "object_type": "figure",
        "object_label": "figure:S3",
        "object_number": "S3",
        "source_scope": "supplement",
        "source_path": "references/web_assets/lin2026association/FSN3-14-e72232-s001.docx",
        "page_or_sheet": "supplement DOCX native images",
        "caption": "Figure S3: Precision–recall curves for the 12 machine-learning models. (A) Prediction of HF-defined CRAS in the NHANES internal validation set. (B) Exploratory cross-phenotype application to the MI–CKD–anemia phenotype in KNHANES. The horizontal dashed line in each panel represents the observed outcome prevalence in the corresponding evaluation sample. AP denotes average precision.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/lin2026association__0006__figure_S3__docx_native_panels.png",
        "width": 7716,
        "height": 3000,
        "extraction_method": "native supplement DOCX panel images recovered through Europe PMC and reassembled in caption order",
        "content_domains": "model performance; precision-recall; internal validation; cross-phenotype application",
        "visible_text": "Panel A (NHANES internal validation; prevalence 0.321): AdaBoost AP 0.507, CatBoost 0.556, Decision Tree 0.549, GBDT 0.548, Gaussian NB 0.494, KNN 0.487, LightGBM 0.575, Logistic Regression 0.510, MLP 0.510, Random Forest 0.539, SVM 0.500, XGBoost 0.587. Panel B (KNHANES cross-phenotype application; prevalence 0.426): AdaBoost AP 0.683, CatBoost 0.698, Decision Tree 0.588, GBDT 0.692, Gaussian NB 0.673, KNN 0.611, LightGBM 0.672, Logistic Regression 0.686, MLP 0.671, Random Forest 0.667, SVM 0.686, XGBoost 0.672.",
        "interpretation": "All 12 precision–recall curves are now directly readable. In panel A, XGBoost has the largest displayed AP (0.587), followed by LightGBM (0.575) and CatBoost (0.556), above the 0.321 prevalence baseline. In panel B, CatBoost ranks first (0.698), narrowly ahead of GBDT (0.692), logistic regression and SVM (both 0.686), above the 0.426 baseline. Panel-specific readings are retained because the two panels represent different outcomes/settings and should not be pooled.",
        "key_values": [
            "Panel A prevalence: 0.321",
            "Panel A highest displayed AP: XGBoost 0.587",
            "Panel A LightGBM AP: 0.575",
            "Panel A CatBoost AP: 0.556",
            "Panel B prevalence: 0.426",
            "Panel B highest AP: CatBoost 0.698",
            "Panel B GBDT AP: 0.692",
            "Panel B Logistic Regression and SVM AP: 0.686 each"
        ],
    }
])
