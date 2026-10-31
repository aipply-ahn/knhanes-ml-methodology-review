#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews
from remove_visual_aliases import remove_aliases

T="2026-09-14T01:40:00+09:00"
src="references/supplements/dashdondov2026assessing/12889_2026_26868_MOESM1_ESM.docx"
reviews=[
 {"reviewed_at":T,"study_key":"dashdondov2026assessing","object_id":"dashdondov2026assessing__0003__figure_S1","object_type":"figure","object_label":"figure:S1","object_number":"S1","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:1","caption":"Figure S1. Probability plots (a) with and (b) without outliers by Mahalanobis distance for the experimental dataset.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2026assessing__0003__figure_S1__docx_native_panels.png","width":1276,"height":501,"extraction_method":"two native DOCX media panels reassembled in source order","content_domains":"outlier detection; preprocessing; Mahalanobis distance",
  "visible_text":"Two probability plots with probability on the x-axis and Mahalanobis distance on the y-axis. Panel (a), with outliers, has a dense low-distance band and extreme observations extending to roughly 2,350. Panel (b), after outlier removal, forms a smooth descending curve spanning approximately 112 to 15 with no extreme upper tail.",
  "interpretation":"Mahalanobis-distance filtering removes a small but highly extreme tail and substantially compresses the distance range. The figure visually supports the outlier-removal step, although it does not by itself establish that deletion improves generalization.",
  "key_values":["Panel (a): with outliers; maximum distance ≈2,350","Panel (b): without outliers; distance range ≈15–112","Method: Mahalanobis distance"]},
 {"reviewed_at":T,"study_key":"dashdondov2026assessing","object_id":"dashdondov2026assessing__0009__figure_S2","object_type":"figure","object_label":"figure:S2","object_number":"S2","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:2","caption":"Figure S2. Workflow of dataset integration and preprocessing for diabetes risk analysis.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2026assessing__0009__figure_S2__docx_vector_300dpi.png","width":1950,"height":2450,"extraction_method":"DOCX vector figure rendered at 300 dpi and tightly cropped","content_domains":"data integration; preprocessing; feature selection; resampling",
  "visible_text":"KNHANES 2020–2021: N=15,552, F=843; COVID-19 2020–2021: N=710,090, F=4. CBFA integration yields Integrated Dataset N=15,552, F=142 after removing unrelated features/missing values using nutrition score and diabetes. Multicollinearity analysis and Mahalanobis outlier removal yield MAMO Dataset N=7,492, F=71. Factor analysis and K-means nutrition-factor extraction yield MACE/Nutrition Factor Dataset N=5,462 with F=29 then F=25. SMOTEENN produces MASN Dataset N=3,811, F=25.",
  "interpretation":"The workflow combines a high-dimensional KNHANES source with four COVID-19 case features, then repeatedly reduces both records and features before hybrid resampling. The final modeling data retain 3,811 of 15,552 KNHANES records and 25 features; this extensive data-dependent preprocessing is relevant to risk-of-bias assessment and must occur within resampling folds to prevent leakage.",
  "key_values":["KNHANES source: N=15,552, F=843","COVID-19 source: N=710,090, F=4","Integrated: N=15,552, F=142","After multicollinearity/outlier processing: N=7,492, F=71","Factor dataset: N=5,462, F=25","After SMOTEENN: N=3,811, F=25"]},
 {"reviewed_at":T,"study_key":"dashdondov2026assessing","object_id":"dashdondov2026assessing__0006__figure_S3","object_type":"figure","object_label":"figure:S3","object_number":"S3","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:3","caption":"Figure S3. Bar chart for a cluster of nutrition and supplement intake factors.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2026assessing__0006__figure_S3__docx_native.png","width":430,"height":278,"extraction_method":"native DOCX media image","content_domains":"class distribution; nutrition/supplement intake",
  "visible_text":"Grouped bar chart by Nutrition and Supplement Intake (No/Yes) for Normal, Pre_diabetes, and Diabetes. Approximate counts: No—Normal 1,700, Pre_diabetes 1,560, Diabetes 470; Yes—Normal 680, Pre_diabetes 810, Diabetes 235.",
  "interpretation":"Most participants in every glycemic-status group fall in the no-intake cluster. The prediabetes group has a somewhat larger yes-intake count than the normal group, while diabetes is the smallest class in both clusters; the plot is descriptive and unadjusted.",
  "key_values":["No intake: Normal ≈1,700; Prediabetes ≈1,560; Diabetes ≈470","Yes intake: Normal ≈680; Prediabetes ≈810; Diabetes ≈235"]}
]
apply_reviews(reviews)
remove_aliases('dashdondov2026assessing',{
 'dashdondov2026assessing__0016__figure_media1',
 'dashdondov2026assessing__0017__figure_media2',
 'dashdondov2026assessing__0018__figure_S2'})
remove_aliases('choi2025developmenta',{'choi2025developmenta__0002__figure_1A'})
remove_aliases('jang2026routine',{'jang2026routine__0006__figure_3'})
remove_aliases('ko2025machine',{'ko2025machine__0008__figure_S1'})
remove_aliases('oh2022machine',{'oh2022machine__0008__figure_S1'})
