#!/usr/bin/env python3
"""Apply ChatGPT image rereads for Amarbayasgalan and anonymous 2026 objects."""
from apply_completed_visual_reviews import apply_reviews

TS = "2026-09-14T07:32:00+09:00"
reviews = [
    {
        "reviewed_at": TS, "study_key": "amarbayasgalan2019reconstruction", "source_scope": "main",
        "source_path": "references/pdf/amarbayasgalan2019reconstruction.pdf",
        "object_id": "amarbayasgalan2019reconstruction__0001__figure_1", "object_type": "figure",
        "object_label": "figure:1", "object_number": "1", "page_or_sheet": "3",
        "caption": "Fig 1. General architecture of the proposed AE-DNNs method.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/amarbayasgalan2019reconstruction__0001__figure_1.png",
        "width": 2017, "height": 1300, "extraction_method": "original embedded PDF figure",
        "review_stage": "complete_figure_chatgpt_image_reread",
        "content_domains": "model architecture; autoencoder; coronary heart disease prediction",
        "visible_text": "Dataset branches to DAE-general and DAE-risky. DAE-general reconstructs x to x' and its reconstruction error (RE) is used to choose an appropriate DNN. DAE-risky reconstructs x to x', creates an RE-based new feature, and combines it with CHD risk factors. The two paths feed DNN model 1 and DNN model 2 for CHD risk prediction; RE is explicitly appended to the DNN inputs.",
        "interpretation": "The proposed architecture uses two autoencoder roles: general-subset reconstruction error guides DNN selection, while risky-subset reconstruction error becomes a new predictive feature combined with conventional CHD risk factors. Two resulting DNNs form the prediction strategy.",
        "key_values": {"inputs": ["dataset", "CHD risk factors"], "autoencoders": ["DAE-general", "DAE-risky"], "derived_feature": "reconstruction error", "predictors": ["DNN model 1", "DNN model 2"], "outcome": "CHD risk"}
    },
    {
        "reviewed_at": TS, "study_key": "amarbayasgalan2021efficient", "source_scope": "main",
        "source_path": "references/pdf/amarbayasgalan2021efficient.pdf",
        "object_id": "amarbayasgalan2021efficient__0016__table_7", "object_type": "table",
        "object_label": "table:7", "object_number": "7", "page_or_sheet": "11",
        "caption": "Table 7. Results of compared algorithms on the KNHANES dataset.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/table/amarbayasgalan2021efficient__0016__table_7__table_only.png",
        "width": 1240, "height": 690, "extraction_method": "ChatGPT-verified high-resolution table-only crop",
        "review_stage": "complete_table_chatgpt_image_reread", "content_domains": "classification performance; CHD prediction",
        "visible_text": "Metrics are accuracy, precision, recall, specificity, F-measure. KNN 0.785/0.825/0.829/0.702/0.827; NB 0.759/0.802/0.812/0.652/0.807; DT 0.761/0.807/0.810/0.674/0.808; SVM 0.780/0.805/0.852/0.650/0.828; RF 0.827/0.859/0.863/0.760/0.861; AdaBoost 0.822/0.859/0.854/0.763/0.857; VAE-Two-DNN 0.892/0.911/0.920/0.844/0.915.",
        "interpretation": "VAE-Two-DNN is best on every reported classification metric, with F-measure 0.915 and accuracy 0.892. RF is the strongest conventional comparator by accuracy and F-measure.",
        "key_values": {"metric_order": ["accuracy", "precision", "recall", "specificity", "F_measure"], "KNN": [0.785,0.825,0.829,0.702,0.827], "NB": [0.759,0.802,0.812,0.652,0.807], "DT": [0.761,0.807,0.810,0.674,0.808], "SVM": [0.780,0.805,0.852,0.650,0.828], "RF": [0.827,0.859,0.863,0.760,0.861], "AdaBoost": [0.822,0.859,0.854,0.763,0.857], "VAE_Two_DNN": [0.892,0.911,0.920,0.844,0.915], "best_model": "VAE-Two-DNN", "selection_metric": "F-measure", "best_score": 0.915}
    },
    {
        "reviewed_at": TS, "study_key": "amarbayasgalan2021efficient", "source_scope": "main",
        "source_path": "references/pdf/amarbayasgalan2021efficient.pdf",
        "object_id": "amarbayasgalan2021efficient__0018__table_8", "object_type": "table",
        "object_label": "table:8", "object_number": "8", "page_or_sheet": "11",
        "caption": "Table 8. Results of the ROC curve analysis for compared algorithms on the KNHANES dataset.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/table/amarbayasgalan2021efficient__0018__table_8__table_only.png",
        "width": 1240, "height": 650, "extraction_method": "ChatGPT-verified high-resolution table-only crop",
        "review_stage": "complete_table_chatgpt_image_reread", "content_domains": "ROC analysis; CHD prediction",
        "visible_text": "KNN AUC 0.765, p=4.29E-52, 95% CI 0.745-0.786; NB 0.732, 2.36E-33, 0.711-0.753; DT 0.745, 2.51E-38, 0.721-0.762; SVM 0.751, 2.02E-40, 0.730-0.771; RF 0.810, 1.90E-72, 0.793-0.830; AdaBoost 0.809, 5.35E-68, 0.790-0.827; VAE-Two-DNN 0.882, 1.34E-56, 0.867-0.896.",
        "interpretation": "In this ROC-analysis table, VAE-Two-DNN has the largest AUC (0.882) and its confidence interval does not overlap most weaker comparators; RF and AdaBoost are next at about 0.81.",
        "key_values": {"KNN": [0.765,0.745,0.786], "NB": [0.732,0.711,0.753], "DT": [0.745,0.721,0.762], "SVM": [0.751,0.730,0.771], "RF": [0.810,0.793,0.830], "AdaBoost": [0.809,0.790,0.827], "VAE_Two_DNN": [0.882,0.867,0.896], "best_model": "VAE-Two-DNN", "best_AUC_in_table_8": 0.882}
    },
    {
        "reviewed_at": TS, "study_key": "anon2026association", "source_scope": "main",
        "source_path": "references/pdf/anon2026association.pdf",
        "object_id": "anon2026association__0001__table_3", "object_type": "table",
        "object_label": "table:3", "object_number": "3", "page_or_sheet": "5",
        "caption": "Table 3. Correlation Analysis between Circadian Rhythm Parameters and Quality of Life, Stress, and Depression Indices.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/table/anon2026association__0001__table_3__table_only.png",
        "width": 2300, "height": 1710, "extraction_method": "correct source-page recovery followed by ChatGPT-verified table-only crop",
        "review_stage": "complete_table_chatgpt_image_reread", "content_domains": "correlation; circadian rhythm; quality of life; stress; depression",
        "visible_text": "Table 3 reports r(p) for 11 rhythm parameters against EQ5D, EQ5D_low, mh_stress, BP1, BP5, PHQ_S, PHQ_S5 and PHQ_S10. Strongest displayed magnitudes include Mesor with PHQ_S r=-0.199 (p<.001) and EQ5D r=0.159 (p<.001); M10 with PHQ_S r=-0.194 (p<.001), EQ5D r=0.150 (p<.001), and PHQ_S10 r=-0.147 (p<.001); acrophase with BP1 r=0.152 (p<.001), mh_stress r=0.131 (p<.001); IS with PHQ_S r=-0.152 (p<.001); amplitude with PHQ_S r=-0.154 (p<.001).",
        "interpretation": "Higher overall/activity-period levels (Mesor, amplitude and M10) correlate with better EQ-5D and lower depression scores. Later acrophase correlates with stress measures, while lower interdaily stability correlates with depressive symptom measures. Correlations are generally small in magnitude.",
        "key_values": {
            "columns": ["EQ5D","EQ5D_low","mh_stress","BP1","BP5","PHQ_S","PHQ_S5","PHQ_S10"],
            "r_matrix": {
                "Mesor": [0.159,-0.077,-0.098,-0.085,-0.096,-0.199,-0.112,-0.142],
                "Amplitude": [0.126,-0.072,-0.101,-0.085,-0.105,-0.154,-0.058,-0.124],
                "Acrophase": [0.113,-0.061,0.131,0.152,-0.066,0.089,0.050,0.018],
                "CQ": [-0.061,-0.017,-0.035,-0.025,-0.040,0.092,0.110,0.045],
                "IS": [0.036,-0.002,-0.050,-0.013,-0.058,-0.152,-0.109,-0.122],
                "IV": [-0.046,0.023,-0.032,-0.054,0.025,-0.021,-0.013,-0.044],
                "RA": [-0.006,-0.024,-0.010,0.005,-0.015,0.010,0.071,-0.031],
                "L8": [0.061,-0.026,-0.029,-0.043,-0.015,-0.092,-0.121,-0.042],
                "M10": [0.150,-0.078,-0.111,-0.099,-0.099,-0.194,-0.098,-0.147],
                "L8_start": [0.089,-0.038,0.123,0.137,-0.040,-0.018,0.015,-0.031],
                "M10_start": [-0.109,0.052,-0.090,-0.110,0.056,-0.036,-0.009,-0.002]
            }
        }
    },
    {
        "reviewed_at": TS, "study_key": "anon2026partial", "source_scope": "main",
        "source_path": "references/pdf/anon2026partial.pdf",
        "object_id": "anon2026partial__0006__figure_5", "object_type": "figure",
        "object_label": "figure:5", "object_number": "5", "page_or_sheet": "12",
        "caption": "Figure 5. Accumulated local effects plots with ALER band for four predictors.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/anon2026partial__0006__figure_5__figure_only.png",
        "width": 1580, "height": 1480, "extraction_method": "ChatGPT-verified high-resolution figure-only crop",
        "review_stage": "complete_figure_chatgpt_image_reread", "content_domains": "model explanation; accumulated local effects; quality of life",
        "visible_text": "Four ALE panels for predicted LQ_total: age, self_health, stress and suicidal. Age is nearly flat then gently declines after about 40; self_health declines markedly from category 1 to 5 (about 26 to 22); stress rises from categories 1-4 (about 24.3 to 26); suicidal=1 has a lower prediction than 0 (about 24.0 vs 24.7). Horizontal exact and p(ALER) reference lines with +/-0.050 and +/-0.010 bands are shown. Suicidal distribution is 96% category 0 and 4% category 1.",
        "interpretation": "The model's clearest ALE relationship is poorer self-rated health corresponding to lower predicted quality of life. Stress has a positive monotonic model effect, age a modest negative effect, and suicidal status a small negative difference; the 4% suicidal category indicates sparse support for that contrast.",
        "key_values": {"predictors": ["age","self_health","stress","suicidal"], "self_health_direction": "negative", "stress_direction": "positive", "age_direction": "slightly negative", "suicidal_yes_direction": "negative", "suicidal_distribution_percent": {"no":96,"yes":4}, "ALER_bands": [0.05,0.01]}
    }
]

apply_reviews(reviews)
