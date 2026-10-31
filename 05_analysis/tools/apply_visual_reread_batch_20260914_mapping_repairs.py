#!/usr/bin/env python3
"""Apply direct image-model rereads for corrected table source mappings."""
from PIL import Image
from apply_completed_visual_reviews import apply_reviews

TS="2026-09-14T03:05:00+09:00"
B="data/visual_manual_review/latest_after_recrop/decoded_recovered/table/"

def dims(name):
    with Image.open(name) as im: return im.size

def rec(study, oid, number, page, caption, image, text, interpretation, values,
        source=None, scope="main"):
    w,h=dims(image)
    return {"reviewed_at":TS,"study_key":study,"source_scope":scope,
        "source_path":source or f"references/pdf/{study}.pdf","object_id":oid,
        "object_type":"table","object_label":f"table:{number}","object_number":number,
        "page_or_sheet":page,"caption":caption,"image_path":image,"width":w,"height":h,
        "extraction_method":"correct source recovery and ChatGPT-verified high-resolution table crop",
        "review_stage":"complete_table_chatgpt_image_reread_after_source_remap",
        "content_domains":"source-remapped table","visible_text":text,
        "interpretation":interpretation,"key_values":values}

reviews=[]
reviews.append(rec("choi2026development","choi2026development__0001__table_1","1","13",
 "Table 1. Data Pre-processing Flow",B+"choi2026development__0001__table_1__table_only.png",
 "Flow: Initial data 36,816 people; delete 10,782 records with blank values, leaving 26,034; delete 3,342 people under age 30, leaving 22,692; delete 2,657 selected records for no-response/not-registered, leaving final data 20,035 people.",
 "The full diagram resolves every previously clipped stage and confirms a final analytic data set of 20,035 from an initial 36,816.",
 {"initial":36816,"blank_deleted":10782,"after_blank":26034,"under_30_deleted":3342,"after_age":22692,"nonresponse_or_unregistered_deleted":2657,"final":20035}))
reviews.append(rec("kang2019sarcopenia","kang2019sarcopenia__0007__table_2_recovered","2","7",
 "Table 2. Scoring for common risk factors according to different machine learning models, data from elderly female participants.",B+"kang2019sarcopenia__0007__table_2_recovered__table_only.png",
 "Columns are LR, GB, SVM, RF and Score. Rows (LR/GB/SVM/RF; score): BMI 1/1/1/1;4; water intake 0/1/0/1;2; 15-s pulse 1/0/1/0;2; vitamin C 0/1/0/1;2; GPT 0/0/0/0;0; fiber 0/1/1/0;2; carotene 0/0/0/0;0; WBC 1/0/1/1;3; iron 1/0/1/0;2; potassium 0/0/0/0;0; PTH 1/0/1/1;3; RBC 1/0/0/0;1; niacin 1/0/0/0;1; calcium 0/0/0/0;0; age 1/0/1/0;2; BUN 1/0/1/0;2; retinol 0/0/0/0;0; HDL 0/0/1/0;1; protein 1/0/1/0;2; sodium 0/1/0/0;1.",
 "BMI is selected by all four models; WBC and PTH by three. Ten additional factors score two, while five score zero.",
 {"BMI":4,"WBC":3,"PTH":3,"score_2":["water intake","15-s pulse rate","vitamin C","fiber","iron","age","BUN","protein intake"]}))
reviews.append(rec("kim2024gender","kim2024gender__0002__table_S1","S1","Supplemental DOCX p1",
 "Supplemental Table 1. Detailed parameters of the MR images.",B+"kim2024gender__0002__table_S1__table_only.png",
 "Manufacturer: Phillips Medical System. Models: Intera and Ingenia. Magneticity: 1.5 and 3.0 Tesla; slice thickness 4 mm for both; field of view 512×512 and 960×960 pixels. For Intera T1/T2: repetition time 695/3500 ms and echo time 12/120 ms. For Ingenia T1/T2: repetition time 593/2643 ms and echo time 16/100 ms.",
 "The supplementary table documents two Philips MR systems with different field strengths, matrices and T1/T2 timing parameters.",
 {"manufacturer":"Phillips Medical System","Intera":{"tesla":1.5,"slice_mm":4,"fov":"512x512","TR_ms":{"T1":695,"T2":3500},"TE_ms":{"T1":12,"T2":120}},"Ingenia":{"tesla":3.0,"slice_mm":4,"fov":"960x960","TR_ms":{"T1":593,"T2":2643},"TE_ms":{"T1":16,"T2":100}}},
 source="references/supplements/kim2024gender/Table_S1.docx",scope="supplementary"))
reviews.append(rec("oh2015artificial","oh2015artificial__0006__table_1_recovered","1","4-5",
 "Table 1. Clinical Characteristics of Participants in the KNHANES V-1 by Glaucoma Status.",B+"oh2015artificial__0006__table_1_recovered__complete_table.png",
 "Columns: Healthy N=3,727; glaucoma suspect (GS) N=292; open-angle glaucoma (OAG) N=94; total N=4,113; P value comparing GS and OAG. The two-page table covers demographics, physical measures, blood pressure/tests, medical and women's histories, systemic factors and ophthalmic examinations. OAG differs from GS notably in age (57.7 vs 44.5 y, p<0.001), hyperopia (26.6% vs 10.3%, p<0.001), astigmatism (72.3% vs 58.2%, p=0.014), cataract (42.6% vs 18.8%, p<0.001), vertical C/D (0.61 vs 0.54, p<0.001), ISNT-rule violation (39.4% vs 14.7%, p<0.001), RNFLD_ST (17.0% vs 2.1%, p<0.001), and RNFLD_IT (20.2% vs 1.7%, p<0.001).",
 "The OAG subgroup is older and has substantially more structural optic-nerve and ocular abnormalities than glaucoma suspects; the table is descriptive/unadjusted.",
 {"N":{"healthy":3727,"GS":292,"OAG":94,"total":4113},"OAG_vs_GS":{"age":[57.7,44.5],"vertical_CD":[0.61,0.54],"ISNT_violation_percent":[39.4,14.7],"RNFLD_ST_percent":[17.0,2.1],"RNFLD_IT_percent":[20.2,1.7]}}))
reviews.append(rec("tran2024explainable","tran2024explainable__0016__table_2_recovered","2","4",
 "Table 2. List of abbreviations.",B+"tran2024explainable__0016__table_2_recovered__table_only.png",
 "Abbreviations: AdaBoost adaptive boosting; AUC area under the curve; AUC-ROC area under the receiver operating characteristic curve; CPU central processing unit; CS Test chi-squared test; CTGAN conditional tabular generative adversarial network; DL deep learning; EHR electronic health record; ELBO evidence lower bound; ENN edited nearest neighbors; F1-score harmonic mean of precision and recall; FT-Transformer feature tokenizer transformer (duplicated as printed); GAD-7 generalized anxiety disorder-7; GBM gradient boosting machine; GPU graphics processing unit; KCDC Korea Centers for Disease Control and Prevention; KNHANES Korea National Health and Nutrition Examination Survey; KS/KSTest Kolmogorov-Smirnov test; LightGBM light gradient boosting machine; ML machine learning; MRMD max-relevance max-distance; mRmR maximum relevance minimum redundancy; Optuna hyperparameter optimization framework; PHQ-9 patient health questionnaire-9; RF random forest; SHAP Shapley additive explanations.",
 "This is a terminology table, not a results table; it defines the study's preprocessing, augmentation, modeling and explainability abbreviations.",
 {"entries":28,"printed_duplicate":"FT-Transformer"}))
reviews.append(rec("ullah2023machine","ullah2023machine__0004__table_2_recovered","2","8",
 "Table 2. Evaluation of several machine learning models of postmenopausal women from Taiwan and Korea with Data sets 1 and 2.",B+"ullah2023machine__0004__table_2_recovered__table_only.png",
 "Data set 1 rows (AUROC %, sensitivity %, specificity %, p vs OSTA): ANN 78.2,85.5,69.7,0.0257; SVM 81.2,88.8,67.6,0.0142; KNN 7.68,85.5,77.5,0.0345; OSTA 74.5,74.6,69.5. Data set 2 printed rows (Metric 1, sensitivity, specificity, accuracy 95% CI): ANN 0.747,0.58,0.66,0.713 (0.672-0.753); SVM 0.0142,88.8%,67.6%,0.728 (0.674-0.758); KNN 0.0345,85.5%,77.5%,0.743 (0.693-0.777).",
 "For Data set 1 SVM has the highest displayed AUROC (81.2%). For Data set 2 the accuracy column ranks KNN 0.743, SVM 0.728, ANN 0.713. Values are transcribed exactly as printed, including apparent column inconsistencies.",
 {"dataset1":{"ANN":[78.2,85.5,69.7],"SVM":[81.2,88.8,67.6],"KNN":[7.68,85.5,77.5],"OSTA":[74.5,74.6,69.5]},"dataset2_accuracy":{"ANN":0.713,"SVM":0.728,"KNN":0.743}}))
reviews.append(rec("ullah2023machine","ullah2023machine__0005__table_3_recovered","3","8",
 "Table 3. Performance evaluation of different ANN models for predictive analysis of pregnant women having the issue of BMD from Data set 3.",B+"ullah2023machine__0005__table_3_recovered__table_only.png",
 "Metrics are AUROC (95% CI), sensitivity, specificity, true positive value, negative predictive value, and accuracy (95%). Model 1: 0.982 (0.971-0.993), 0.952, 0.966, 0.260, 0.998, accuracy 0.97. Model 2: 0.651,0.710,0.570,0.022,0.994,0.57. Model 3: 0.818,0.684,0.890,0.075,0.996,0.89. Model 4: 0.850,0.829,0.752,0.042,0.998,0.76. Model 5: 0.978,0.951,0.926,0.142,0.999,0.93; confidence intervals are present for each metric.",
 "Model 1 has the highest AUROC and accuracy, narrowly ahead of Model 5; Model 2 performs worst.",
 {"best_model":"Model 1","AUROC":0.982,"accuracy":0.97,"runner_up":"Model 5","runner_up_AUROC":0.978,"runner_up_accuracy":0.93}))

apply_reviews(reviews)
