#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T02:25:00+09:00"
BASE = {
    "reviewed_at": T,
    "study_key": "amarbayasgalan2019reconstruction",
    "object_type": "figure",
    "source_scope": "main",
    "source_path": "references/pdf/amarbayasgalan2019reconstruction.pdf",
    "extraction_method": "original large PNG recovered from the official PLOS figure endpoint",
    "content_domains": "model performance; discrimination; cross-validation",
}

reviews = [
    BASE | {
        "object_id": "amarbayasgalan2019reconstruction__0012__figure_7",
        "object_label": "figure:7", "object_number": "7", "page_or_sheet": "13 / PLOS g007",
        "caption": "Fig 7. Receiver operating characteristic curves of compared algorithms.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/amarbayasgalan2019reconstruction__0012__figure_7__publisher_original.png",
        "width": 1400, "height": 2240,
        "visible_text": "Seven 10-fold ROC panels report mean AUC ± SD: (a) Naive Bayes 0.7370 ± 0.0166; (b) K-nearest neighbors 0.7889 ± 0.0105; (c) Decision tree 0.7807 ± 0.0169; (d) Random forest 0.8430 ± 0.0121; (e) Support vector machine 0.8153 ± 0.0093; (f) PCA-DNNs 0.8562 ± 0.0153; (g) AE-DNNs 0.8665 ± 0.0143.",
        "interpretation": "The full seven-panel figure is readable as one hierarchy, with each panel retaining its model identity and fold curves. AE-DNNs has the highest displayed mean cross-validated AUC (0.8665), followed by PCA-DNNs (0.8562), random forest (0.8430), and SVM (0.8153).",
        "key_values": ["Naive Bayes AUC 0.7370 ± 0.0166", "KNN 0.7889 ± 0.0105", "Decision tree 0.7807 ± 0.0169", "Random forest 0.8430 ± 0.0121", "SVM 0.8153 ± 0.0093", "PCA-DNNs 0.8562 ± 0.0153", "AE-DNNs 0.8665 ± 0.0143"],
    },
    BASE | {
        "object_id": "amarbayasgalan2019reconstruction__0013__figure_8",
        "object_label": "figure:8", "object_number": "8", "page_or_sheet": "14 / PLOS g008",
        "caption": "Fig 8. The average receiver operating characteristic curves of compared algorithms.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/amarbayasgalan2019reconstruction__0013__figure_8__publisher_original.png",
        "width": 1350, "height": 1067,
        "visible_text": "Average ROC legend: Naive Bayes mean AUC 0.7370; K-nearest neighbors 0.7889; Decision tree 0.7807; Random forest 0.8430; Support vector machine 0.8153; PCA-DNNs 0.8562; AE-DNNs 0.8665.",
        "interpretation": "The overlaid mean ROC curves confirm the ranking seen in Figure 7: AE-DNNs is highest, narrowly ahead of PCA-DNNs; the conventional comparators are lower.",
        "key_values": ["Highest: AE-DNNs 0.8665", "Second: PCA-DNNs 0.8562", "Random forest 0.8430", "SVM 0.8153", "KNN 0.7889", "Decision tree 0.7807", "Naive Bayes 0.7370"],
    },
    BASE | {
        "object_id": "amarbayasgalan2019reconstruction__0014__figure_9",
        "object_label": "figure:9", "object_number": "9", "page_or_sheet": "14 / PLOS g009",
        "caption": "Fig 9. Improvement of area under the curve scores based on input features and the number of deep neural network classifiers.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/amarbayasgalan2019reconstruction__0014__figure_9__publisher_original.png",
        "width": 1350, "height": 837,
        "visible_text": "AUC values: single DNN trained on CHD risk factors in Table 1, 0.8534; two DNNs trained on those CHD risk factors, 0.8572; AE-DNNs, 0.8665.",
        "interpretation": "The staged comparison shows a small gain from one to two DNN classifiers (+0.0038 AUC) and a larger total gain for the autoencoder-based AE-DNNs over the single-DNN baseline (+0.0131).",
        "key_values": ["Single DNN AUC 0.8534", "Two DNNs AUC 0.8572", "AE-DNNs AUC 0.8665", "AE-DNNs minus single DNN +0.0131"],
    },
]

apply_reviews(reviews)
