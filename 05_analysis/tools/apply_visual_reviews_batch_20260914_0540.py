#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T="2026-09-14T05:40:00+09:00"
LI="references/supplements/li2024machine/healthcare-3321466-supplementary.pdf"
SH="references/supplements/shangguan2026development/Supplementaryfile1.docx"

def r(study,oid,n,page,wh,caption,visible,interp,vals,source):
 return {"reviewed_at":T,"study_key":study,"object_id":oid,"object_type":"figure","object_label":f"figure:{n}","object_number":n,"source_scope":"supplement","source_path":source,"page_or_sheet":str(page),"caption":caption,"image_path":f"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/{oid}__embedded_original.png","width":wh[0],"height":wh[1],"extraction_method":"native supplementary-file image extracted without page text","content_domains":"SHAP; feature importance; supplementary analysis","visible_text":visible,"interpretation":interp,"key_values":vals}

apply_reviews([
 r("li2024machine","li2024machine__0016__figure_S1","S1",2,(1537,1089),"Figure S1. Data interpolation effect graph.",
   "A 6-column (0-5) panel grid contrasts blue and red observations for 30 variables, including MetS, sex, age, education, marital status, BMI, alcohol, smoking, self-rated health, ADL/IADL, chronic diseases, falls, teeth/hip fracture, sleep, cognition, pulse, puff, grip, cholesterol, LDL, CRP, HbA1c, uric acid, TyG, and TyG-BMI.",
   "The imputation comparison preserves the observed distributions broadly across methods; conspicuous extreme values remain for BMI, cholesterol, TyG-BMI, and several continuous measures. The figure is descriptive and does not identify one objectively best imputation method.",
   ["Six imputation columns","30 displayed variables","Observed/imputed distributions overlap broadly"],LI),
 r("li2024machine","li2024machine__0017__figure_S2","S2",3,(2093,1054),"Figure S2. Correlation matrix of variables considered for metabolic-syndrome prediction.",
   "Two complete matrices are preserved together: a significance/bubble matrix at left and a numeric coefficient heatmap at right. Strong visible correlations include water-food 0.98; hematocrit-RBC count 0.88; carbohydrate-energy 0.88; energy-fat 0.83; energy-food 0.80; phosphorus-potassium and phosphorus-food 0.79; vitamin C-potassium 0.75; systolic-diastolic BP 0.74; TyG with BMI-related TyG 0.72; and potassium-food 0.75.",
   "Several nutritional variables form a high-correlation block, while most clinical/disease-variable pairs are weak. The paired representations expose both magnitude and significance and flag multicollinearity that should be considered during modeling.",
   ["Water-food r=0.98","Hct-RBC r=0.88","Carbohydrate-energy r=0.88","SBP-DBP r=0.74","TyG/TyG-BMI r=0.72"],LI),
 r("li2024machine","li2024machine__0018__figure_S3","S3",4,(1630,1212),"Figure S3. SHAP feature importance in CHARLS, KNHANES, UK Biobank, and NHANES cohorts.",
   "Four mean-|SHAP| bar panels. CHARLS ranks TyG, TyG-BMI, sex, BMI, CRP, age. KNHANES ranks TyG-BMI (~0.148), TyG (~0.141), sex (~0.041), age (~0.034), CRP (~0.026), BMI (~0.021). UK Biobank ranks TyG (~0.151), TyG-BMI (~0.123), BMI (~0.045), sex (~0.041), age and CRP (~0.03). NHANES ranks TyG (~0.071), TyG-BMI (~0.058), sex (~0.020), BMI (~0.017), age (~0.014), CRP (~0.013).",
   "TyG and TyG-BMI dominate all four cohorts, although their order reverses in KNHANES. Sex, BMI, CRP, and age contribute much less.",
   ["Dominant features TyG and TyG-BMI","KNHANES TyG-BMI about 0.148","UK Biobank TyG about 0.151"],LI),
 r("li2024machine","li2024machine__0019__figure_S4","S4",5,(1688,1252),"Figure S4. SHAP analysis of categorical features across four cohorts.",
   "Four panels plot SHAP distributions for TyG quartile, TyG-BMI quartile, sex, BMI category, and CRP quartile. In every cohort, Q4 TyG and Q4 TyG-BMI have strongly positive SHAP values; Q1-Q2 are negative. Female sex is positive and male negative. Obesity/overweight are generally positive, normal/underweight negative. CRP rises from negative lower quartiles toward positive Q4.",
   "The categorical SHAP patterns are directionally consistent across cohorts: higher TyG/TyG-BMI, female sex, excess weight, and higher CRP increase predicted MetS probability.",
   ["TyG Q4 positive","TyG-BMI Q4 positive","Female sex positive","Obesity positive","CRP Q4 positive"],LI),
 r("li2024machine","li2024machine__0020__figure_S5","S5",6,(1672,1246),"Figure S5. SHAP analysis of age across four cohorts.",
   "Four age panels combine scatter/dependence and distribution views. Age has an approximately monotonic positive relationship with SHAP: younger ages are negative, the curves cross near middle age (roughly late 50s to early 60s), and older ages become increasingly positive. The visible SHAP range is approximately -0.06 to +0.08 depending on cohort.",
   "All cohorts show a broadly increasing age effect on predicted MetS, with modest cohort-specific scale and density differences.",
   ["Age-SHAP relation monotonic positive","Zero crossing around late 50s/early 60s","Four cohorts"],LI),
 r("li2024machine","li2024machine__0021__figure_S6","S6",7,(1538,1247),"Figure S6. SHAP force and waterfall plots for individual predictions.",
   "Four example explanations. Panel A moves baseline E[f(x)]=0.325 to f(x)=0.606, driven chiefly by TyG-BMI Q4 +0.13, TyG Q4 +0.0997, and smaller positive terms. Panel B moves 0.323 to 0.752, chiefly TyG Q4 +0.216 and TyG-BMI Q3 +0.188, partly offset by CRP Q2 -0.0352. Panel C moves 0.324 to 0.742, chiefly TyG Q4 +0.243 and TyG-BMI Q3 +0.161. Panel D moves 0.417 to 0.694, chiefly TyG Q4 +0.152 and TyG-BMI Q4 +0.0937.",
   "The individual explanations agree with global importance: TyG and TyG-BMI supply the largest positive contributions in each illustrated high-risk prediction; demographic/CRP terms make smaller adjustments.",
   ["Panel A prediction 0.606","Panel B 0.752","Panel C 0.742","Panel D 0.694","TyG/TyG-BMI dominant"],LI),
 r("shangguan2026development","shangguan2026development__0033__figure_6","6","DOCX embedded image6",(1269,799),"Supplementary Figure 6. SHAP analysis of the XGBoost model in the NHANES cohort.",
   "Panel A beeswarm ranks insulin, age, retinol, height, fasting glucose, WBC, iron, vitamin C, SBP, niacin, 25-OH-D, carbohydrates, HDL-C, triglycerides, and calcium. Panel B mean-|SHAP| bars rank insulin first (~0.024), followed by age and retinol (~0.014 each), height (~0.011), fasting glucose (~0.010), and WBC (~0.009). Panel C is a local waterfall explanation with negative fasting glucose and insulin contributions partly offset by vitamin C and other positive terms.",
   "Insulin is the dominant NHANES XGBoost feature, with age and retinol next. The original inventory caption calling this an external-validation ROC was incorrect; the DOCX's image relationship and adjacent caption identify it as SHAP Figure 6.",
   ["Top feature insulin about 0.024 mean absolute SHAP","Age and retinol about 0.014","Three panels beeswarm/bar/local waterfall","Caption corrected from ROC to SHAP"],SH),
])
