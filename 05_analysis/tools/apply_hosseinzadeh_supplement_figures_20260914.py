#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'data/visual_manual_review/latest_after_recrop/decoded_recovered/figure';out.mkdir(exist_ok=True)
items=[
 ("hosseinzadeh2023evaluation__0008__figure_1","1","references/supplements/hosseinzadeh2023evaluation/Image_1.JPEG",(2126,1894),"Supplementary Figure 1. Pairwise feature correlations.","Complete lower-triangular correlation heatmap. Strong visible pairs include sleep weekday/weekend 0.94; reported/quantile carbohydrate 0.90; water/Q-water 0.89; energy/Q-energy 0.87; protein/Q-protein 0.84; SRS/SRR -0.83; energy-protein 0.83; energy-fat 0.77. Nutrient variables form the strongest positive block.","Most demographic, clinical, and behavior correlations are weak, whereas alternative/quantile nutrient representations are strongly correlated and require collinearity handling.",["Sleep weekday-weekend r=0.94","Carbohydrate/Q-carbohydrate r=0.90","Water/Q-water r=0.89","SRS-SRR r=-0.83"]),
 ("hosseinzadeh2023evaluation__0009__figure_2","2","references/supplements/hosseinzadeh2023evaluation/Image_2.JPEG",(2126,2283),"Supplementary Figure 2. Five-fold learning curves by sample size.","Six panels compare Original versus Quantile-based data for logistic regression, XGBoost, and random forest. At the largest sample size, logistic test accuracy is about 0.778 in both versions, XGBoost about 0.868, and random forest about 0.842. XGBoost training remains near 0.895; RF retains a larger train-test gap. Shaded bands narrow generally as samples increase.","XGBoost has the highest and most steadily improving validation accuracy. Logistic regression converges with a smaller gap at lower performance, while random forest shows persistent overfitting. Quantile transformation changes little in the overall learning-curve pattern.",["Logistic test about 0.778","XGBoost test about 0.868","RF test about 0.842","Original and quantile panels"]),
]
reviews=[]
for oid,n,src,wh,cap,vis,interp,vals in items:
 dst=out/f"{oid}__publisher_supplement_original.jpg"
 reviews.append({"reviewed_at":"2026-09-14T06:35:00+09:00","study_key":"hosseinzadeh2023evaluation","object_id":oid,"object_type":"figure","object_label":f"figure:{n}","object_number":n,"source_scope":"supplement","source_path":src,"page_or_sheet":"separate supplementary JPEG","caption":cap,"image_path":str(dst.relative_to(ROOT)),"width":wh[0],"height":wh[1],"extraction_method":"original publisher-supplied supplementary JPEG","content_domains":"correlation; learning curve; model performance","visible_text":vis,"interpretation":interp,"key_values":vals})
apply_reviews(reviews)
