#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T02:55:00+09:00"

apply_reviews([
    {
        "reviewed_at": T, "study_key": "choi2014screening",
        "object_id": "choi2014screening__0002__figure_2", "object_type": "figure",
        "object_label": "figure:2", "object_number": "2", "source_scope": "main",
        "source_path": "references/pdf/choi2014screening.pdf", "page_or_sheet": "3 / PMC figure 2",
        "caption": "Figure 2. Flow of KNHANES 2010 and 2011 data used to develop and validate the prediabetes model.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/choi2014screening__0002__figure_2__publisher_original.jpg",
        "width": 600, "height": 426,
        "extraction_method": "original 300-dpi publisher JPEG recovered from PubMed Central",
        "content_domains": "study design; data splitting; internal validation; external validation",
        "visible_text": "Development set from KNHANES 2010 (N=4,685) splits into training (N=3,134) and internal validation (N=1,551). Backward logistic regression feature selection is performed in training; ANN and SVM are optimized using grid search and 10-fold cross-validation; model performance is compared with Lee's screening score. The independent KNHANES 2011 sample (N=4,566) is the external validation set and feeds both the optimized models and screening-score comparison.",
        "interpretation": "The diagram clearly separates development, internal validation, and temporal external validation. Feature selection and model tuning occur on the training branch; KNHANES 2011 is not used for model development, supporting a genuine external validation comparison.",
        "key_values": ["KNHANES 2010 development N=4,685", "Training N=3,134", "Internal validation N=1,551", "KNHANES 2011 external validation N=4,566", "Grid search plus 10-fold cross-validation"],
    },
    {
        "reviewed_at": T, "study_key": "chong2025machine",
        "object_id": "chong2025machine__0002__figure_1", "object_type": "figure",
        "object_label": "figure:1", "object_number": "1", "source_scope": "main",
        "source_path": "references/pdf/chong2025machine.pdf", "page_or_sheet": "6 / JMIR original asset",
        "caption": "Figure 1. Receiver operating characteristic curves of the predictive models in training, test, and validation sets.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/chong2025machine__0002__figure_1__publisher_original.png",
        "width": 752, "height": 902,
        "extraction_method": "original publisher PNG recovered from the official JMIR asset host",
        "content_domains": "model performance; discrimination; external validation; overfitting",
        "visible_text": "Panel A training AUC: logistic regression 0.850, SVM 0.999, random forest 1.000, XGBoost 1.000. Panel B test AUC: logistic regression 0.825, SVM 0.809, random forest 0.797, XGBoost 0.826. Panel C validation AUC: logistic regression 0.798, SVM 0.764, random forest 0.743, XGBoost 0.521.",
        "interpretation": "Tree/complex models show near-perfect training discrimination but substantial test and especially external-validation degradation. Logistic regression is the most stable externally (AUC 0.798), while XGBoost collapses to near-chance validation performance (0.521), visually supporting the authors' concern about overfitting.",
        "key_values": ["Training AUC LR/SVM/RF/XGBoost: 0.850/0.999/1.000/1.000", "Test AUC: 0.825/0.809/0.797/0.826", "Validation AUC: 0.798/0.764/0.743/0.521", "Best external validation: logistic regression 0.798"],
    },
])
