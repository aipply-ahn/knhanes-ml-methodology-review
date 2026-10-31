#!/usr/bin/env python3
"""Apply direct image-model rereads of five repaired figure-only crops."""
from pathlib import Path
from PIL import Image
from apply_completed_visual_reviews import apply_reviews

ROOT = Path(__file__).resolve().parents[1]
BASE = 'data/visual_manual_review/latest_after_recrop/decoded_recovered/figure'
TS = '2026-09-14T03:35:00+09:00'

items = [
  dict(study_key='jo2023development', object_id='jo2023development__0005__figure_2',
    page='7', caption='Figure 2. Impurity based feature importance of tree based machine learning methods.',
    image=f'{BASE}/jo2023development__0005__figure_2__figure_only_upright.png',
    visible='Complete four-panel feature-importance figure: (a) Random forests, (b) XGBoost, (c) LGBM, and (d) MERF. Random forests, XGBoost, and LGBM rank cumulative number of acute exacerbations (AEs) first; MERF ranks number of AEs in 90 days first and cumulative AEs second. Other high-ranking variables include numbers/recency of COPD hospital visits, recent AE counts, smoking status, and weather or air-pollution measures.',
    interp='The fully exposed figure confirms that prior exacerbation burden is the dominant predictor across all four tree-based models. Health-care utilization/recency variables form the next tier, while meteorological and air-pollution variables have smaller model-specific contributions.',
    keys={'panels':['Random forests','XGBoost','LGBM','MERF'],'dominant_pattern':'prior acute-exacerbation history'}),
  dict(study_key='kim2024machinea', object_id='kim2024machinea__0001__figure_1',
    page='6', caption='Figure 1. Flowchart of the study',
    image=f'{BASE}/kim2024machinea__0001__figure_1__figure_only.png',
    visible='KNHANES data samples 37,753; selected 5,573 after excluding participants without dual-energy X-ray absorptiometry, those aged under 60, and nonresponders; sarcopenia 1,597 and normal 3,976; preprocessing comprised scaling, upsampling, and feature selection; train/test split 80%/20%; training used multilayer perceptron, XGBoost, LightGBM, and RandomForest; model evaluation used test data.',
    interp='The complete flowchart establishes the analytic cohort, class counts, class-balancing/preprocessing step, 80:20 holdout design, four trained classifiers, and test-set evaluation.',
    keys={'initial_n':37753,'selected_n':5573,'sarcopenia_n':1597,'normal_n':3976,'train_percent':80,'test_percent':20,'models':['MLP','XGBoost','LightGBM','RandomForest']}),
  dict(study_key='ko2025weight', object_id='ko2025weight__0005__figure_2',
    page='9', caption='Figure 2. Receiver Operating Characteristic (ROC) curve for the CHAID decision tree model.',
    image=f'{BASE}/ko2025weight__0005__figure_2__figure_only.png',
    visible='ROC Curve; y-axis Sensitivity, x-axis 1 - Specificity; diagonal reference line; the plotted CHAID curve passes approximately through (0,0), (0.36,0.75), and (1,1). Annotation: Area of Under Curve=0.69 (95% Confidential Interval 0.66-0.72).',
    interp='The actual Figure 2 is present on PDF page 9 and confirms fair/modest discrimination for the CHAID weight-control model: AUC 0.69 with 95% CI 0.66–0.72.',
    keys={'model':'CHAID decision tree','auc':0.69,'ci95':[0.66,0.72]}),
  dict(study_key='suh2023interpretable', object_id='suh2023interpretable__0007__figure_5',
    page='11', caption='Figure 5. Impact of the top 10 features and 6 features in particular on the classification of osteoporosis.',
    image=f'{BASE}/suh2023interpretable__0007__figure_5__figure_only.png',
    visible='Two upper LIME impact panels give the top 10 features for NHANES and KNHANES. NHANES lists sex, age, BMI, arm circumference, arthritis, healthy diet, smoking at least 100 cigarettes, alkaline phosphatase, depression, and family PIR. KNHANES lists sex, age, obesity, age at osteoarthritis diagnosis, diabetes, BMI, age at hypertension diagnosis, motor ability, education, and stroke treatment. Six lower plots relate impact to original BMI, arm circumference, vitamin D, alkaline phosphatase, family PIR, and parathyroid hormone values.',
    interp='Sex and age dominate both datasets, with body-size and disease-history variables also prominent. Lower BMI, smaller arm circumference, lower vitamin D and lower family PIR align with positive osteoporosis impact, while higher alkaline phosphatase and parathyroid hormone align with positive impact.',
    keys={'datasets':['NHANES','KNHANES'],'method':'LIME','detail_variables':['BMI','arm circumference','vitamin D','alkaline phosphatase','family PIR','parathyroid hormone']}),
  dict(study_key='suh2023interpretable', object_id='suh2023interpretable__0008__figure_6',
    page='12', caption='Figure 6. Individualized risk assessment for osteoporosis with feature integrated contributions from the explainable artificial intelligence model.',
    image=f'{BASE}/suh2023interpretable__0008__figure_6__figure_only.png',
    visible='Three individualized contribution bar plots. Sample 1: total osteoporosis probability 62.31%, with positive contributions including 21.77, 19.05, 10.07, 8.68, 5.40, 5.06, and 3.05 and negative contributions -5.09, -4.33, and -1.36. Sample 2: total osteoporosis probability 68.48%, with major positive contributions 28.34, 16.74, 12.99, and 12.74. Sample 3: total normal probability 82.59%, with dominant negative osteoporosis contributions -22.05 and -20.11 and a small positive contribution 2.70.',
    interp='The XAI model supplies patient-level decompositions rather than only global importance. Two older, low-BMI female examples are predicted as osteoporosis (62.31% and 68.48%); a younger male with higher BMI is predicted normal (82.59%), with feature contributions showing the direction and magnitude of each prediction driver.',
    keys={'sample_1_osteoporosis_probability':0.6231,'sample_2_osteoporosis_probability':0.6848,'sample_3_normal_probability':0.8259}),
]

reviews=[]
for x in items:
    p=ROOT/x['image']
    with Image.open(p) as im: w,h=im.size
    reviews.append({'reviewed_at':TS,'study_key':x['study_key'],'source_scope':'main',
      'source_path':f"references/pdf/{x['study_key']}.pdf",'object_id':x['object_id'],
      'object_type':'figure','object_label':'figure:'+x['object_id'].rsplit('_',1)[-1],
      'object_number':x['object_id'].rsplit('_',1)[-1],'page_or_sheet':x['page'],
      'caption':x['caption'],'image_path':x['image'],'width':w,'height':h,
      'extraction_method':'high_resolution_pdf_page_render_then_figure_only_crop',
      'review_stage':'complete_after_direct_chatgpt_image_reread_20260914',
      'content_domains':'model_workflow_or_results','visible_text':x['visible'],
      'interpretation':x['interp'],'key_values':x['keys'],
      'crop_recovery_status':'repaired_high_resolution_figure_only_crop',
      'latest_image_kind':'recovered_canonical_crop'})
apply_reviews(reviews)
print({'repaired_and_reread':len(reviews)})
