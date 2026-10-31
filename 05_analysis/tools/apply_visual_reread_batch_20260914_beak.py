#!/usr/bin/env python3
"""Apply ChatGPT image rereads for selected Beak 2024 figures."""
from apply_completed_visual_reviews import apply_reviews

TS="2026-09-14T07:48:00+09:00"
SRC_MAIN="references/pdf/beak2024driven.pdf"
SRC_SUPP="references/supplements/beak2024driven/S240584402408527X-mmc1.docx"
BASE="data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/"
reviews=[
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"main","source_path":SRC_MAIN,
  "object_id":"beak2024driven__0001__figure_1","object_type":"figure","object_label":"figure:1","object_number":"1","page_or_sheet":"2","caption":"Fig. 1. Overall workflow chart.",
  "image_path":BASE+"beak2024driven__0001__figure_1.png","width":2301,"height":1548,"extraction_method":"original embedded PDF figure","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"study workflow; feature selection; model development; external validation",
  "visible_text":"Survey path: KNHANES n=10,654 with >1,000 variables; exclusions are missing diagnosis n=2,708 and missing predictors n=519; correlation analysis n=7,427; 16 significant risk factors; prediction algorithms LR, SVM, RF, XGB and NN; training/cross-validation n=5,198 (70%) and test n=2,229 (30%). Clinical path: GPMC n=120 with 16 variables, preprocessing, then clinical validation n=120.",
  "interpretation":"The figure documents derivation, internal validation and an independent clinical validation stream. Feature selection precedes the 70/30 split as drawn, which is relevant to leakage appraisal; the clinical dataset is kept separate for external validation.",
  "key_values":{"KNHANES_initial":10654,"excluded_missing_diagnosis":2708,"excluded_missing_predictors":519,"analysis_n":7427,"selected_features":16,"train_n":5198,"train_percent":70,"test_n":2229,"test_percent":30,"clinical_validation_n":120,"models":["LR","SVM","RF","XGB","NN"]}},
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"main","source_path":SRC_MAIN,
  "object_id":"beak2024driven__0002__figure_2","object_type":"figure","object_label":"figure:2","object_number":"2","page_or_sheet":"6","caption":"Fig. 2. Feature importance of the data-driven prediction models. (a) RF and (b) XGB models.",
  "image_path":BASE+"beak2024driven__0002__figure_2.png","width":2300,"height":949,"extraction_method":"original embedded PDF figure","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"feature importance; RF; XGBoost",
  "visible_text":"Panel (a) RF ranks age first (~0.30), smoking period second (~0.14), then waist and self-perceived oral health (~0.09 each), BMI and duration of hypertension (~0.05), followed by average smoking/day, prosthetic condition, walking, dyslipidemia, alcohol, diabetes, heavy drinking and sex. Panel (b) XGB ranks age first (~0.25), smoking period (~0.14), sex (~0.11), self-perceived oral health (~0.09), average smoking/day (~0.08), then waist, maxillary prosthetic condition, dyslipidemia, diabetes, BMI, alcohol/drinking, walking and hypertension.",
  "interpretation":"Age and smoking duration dominate both models. RF gives waist/BMI and hypertension more weight, whereas XGB elevates sex, self-perceived oral health and smoking intensity; rankings are model-dependent rather than a single stable causal ordering.",
  "key_values":{"panels":{"a":"RF","b":"XGB"},"RF_top5":["age","smoking period","waist","self-perceived oral health","BMI"],"XGB_top5":["age","smoking period","sex","self-perceived oral health","average smoking per day"]}},
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"supplement","source_path":SRC_SUPP,
  "object_id":"beak2024driven__0007__figure_media2","object_type":"figure","object_label":"figure:S2","object_number":"S2","page_or_sheet":"docx:12","caption":"Figure S2. Model development, tuning, test evaluation, and clinical validation workflow.",
  "image_path":BASE+"beak2024driven__0007__figure_media2__white_bg.png","width":1030,"height":814,"extraction_method":"original DOCX RGBA image composited on white background for complete ChatGPT reading","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"cross-validation; hyperparameter optimization; validation workflow",
  "visible_text":"KNHANES n=7,427 is split 70% train and 30% test. The training set undergoes grid search with stratified 5-fold cross-validation, model and hyperparameter optimization, then model retraining with the entire training set. The held-out test set feeds model evaluation. Separately, clinical data n=120 feed clinical validation.",
  "interpretation":"The diagram clarifies nested workflow roles: five-fold folds are used only within the training set for grid search, the selected configuration is retrained on all training observations, and evaluation uses held-out KNHANES test data plus a separate clinical cohort.",
  "key_values":{"KNHANES_n":7427,"train_percent":70,"test_percent":30,"cross_validation":"stratified 5-fold","tuning":"grid search","clinical_n":120}},
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"supplement","source_path":SRC_SUPP,
  "object_id":"beak2024driven__0010__figure_S5","object_type":"figure","object_label":"figure:S5","object_number":"S5","page_or_sheet":"docx:23","caption":"Figure S5. ROC curve of data-driven prediction model (decision tree).",
  "image_path":BASE+"beak2024driven__0010__figure_S5.png","width":670,"height":542,"extraction_method":"original DOCX embedded figure","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"ROC; decision tree; periodontal disease",
  "visible_text":"Decision-tree ROC for prediction target CPI3-4 in the test set n=2,229. AUC=0.796 with 95% CI 0.776-0.815. Axes are sensitivity versus 1-specificity.",
  "interpretation":"The held-out-test decision tree shows moderate-to-good discrimination for CPI3-4, with AUC 0.796 and a relatively narrow confidence interval.",
  "key_values":{"model":"decision tree","target":"CPI3-4","test_n":2229,"AUC":0.796,"CI95":[0.776,0.815]}},
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"supplement","source_path":SRC_SUPP,
  "object_id":"beak2024driven__0029__figure_S8","object_type":"figure","object_label":"figure:S8","object_number":"S8","page_or_sheet":"6","caption":"Figure S8. Heatmap for Pearson correlation between risk factors.",
  "image_path":BASE+"beak2024driven__0029__figure_S8.png","width":866,"height":738,"extraction_method":"original DOCX embedded figure","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"correlation; multicollinearity; risk factors",
  "visible_text":"Sixteen-factor Pearson matrix. Largest positive correlations are waist-BMI 0.87, alcohol amount-heavy drinking 0.84, drinking frequency-alcohol amount 0.75, drinking frequency-heavy drinking 0.75. Other notable values: sex-smoking period -0.55, age-duration hypertension 0.41, hypertension-dyslipidemia 0.39, hypertension-diabetes 0.37, smoking period-average smoking/day 0.37, age-maxillary prosthetic condition 0.37 and age-mandibular condition 0.36.",
  "interpretation":"The matrix reveals strong redundancy within adiposity measures and within alcohol-use measures, plus moderate clustering among age and disease-duration variables. These correlations matter for feature stability and interpretation across models.",
  "key_values":{"waist_BMI":0.87,"alcohol_heavy_drinking":0.84,"drinking_frequency_alcohol":0.75,"drinking_frequency_heavy":0.75,"sex_smoking_period":-0.55,"age_hypertension_duration":0.41}},
 {"reviewed_at":TS,"study_key":"beak2024driven","source_scope":"supplement","source_path":SRC_SUPP,
  "object_id":"beak2024driven__0030__figure_S9","object_type":"figure","object_label":"figure:S9","object_number":"S9","page_or_sheet":"7","caption":"Figure S9. Heatmap for Pearson correlation between clinical factors.",
  "image_path":BASE+"beak2024driven__0030__figure_S9.png","width":470,"height":373,"extraction_method":"original DOCX embedded figure","review_stage":"complete_figure_chatgpt_image_reread","content_domains":"correlation; periodontal clinical factors",
  "visible_text":"Eight-variable clinical correlation matrix. CPI3-4 correlates 0.86 with individual probing depth and 0.47 with mean probing depth. CPI4 correlates 0.79 with mean probing depth and 0.65 with gingival bleeding. Mean probing depth correlates 0.63 with gingival bleeding and 0.55 with individual probing depth. Bone-loss measures correlate 0.50 with each other; most tooth-loss correlations are small (0.11-0.32).",
  "interpretation":"CPI definitions are closely aligned with probing-depth and bleeding measures, while radiographic bone loss and tooth loss form less strongly connected domains. The strongest coefficient (0.86) suggests substantial construct overlap between CPI3-4 and individual probing depth.",
  "key_values":{"CPI3_4_individual_probing":0.86,"CPI4_mean_probing":0.79,"CPI4_bleeding":0.65,"mean_probing_bleeding":0.63,"mean_individual_probing":0.55,"bone_loss_pair":0.50}}
]
apply_reviews(reviews)
