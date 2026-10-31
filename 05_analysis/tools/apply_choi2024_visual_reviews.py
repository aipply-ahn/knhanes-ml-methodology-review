#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T02:45:00+09:00"
COMMON = {
    "reviewed_at": T, "study_key": "choi2024application", "object_type": "figure",
    "source_scope": "main", "source_path": "references/pdf/choi2024application.pdf",
    "extraction_method": "full-resolution publisher PNG recovered from Springer Nature",
}

apply_reviews([
    COMMON | {
        "object_id": "choi2024application__0004__figure_4", "object_label": "figure:4", "object_number": "4",
        "page_or_sheet": "10 / Springer Fig4", "width": 2031, "height": 1070,
        "caption": "Fig. 4. Prevalence of osteopenia and osteoporosis according to the developed risk scores. (A) Development set. (B) Validation set.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/choi2024application__0004__figure_4__publisher_original.png",
        "content_domains": "risk stratification; prevalence; odds ratios; validation",
        "visible_text": "Development set (A), osteopenia prevalence by score quartile: 43%, 69%, 87%, 98%; adjusted ORs vs Q1: Q2 2.84 (2.48–3.24), Q3 8.43 (7.15–9.94), Q4 59.66 (43.26–82.27), all p<0.001. Osteoporosis prevalence: 3%, 10%, 23%, 62%; ORs: 4.07 (2.93–5.65), 11.54 (8.47–15.71), 61.54 (45.40–83.42), all p<0.001. Validation set (B), osteopenia prevalence: 47%, 69%, 82%, 98%; ORs: 2.52 (1.77–3.59), 5.29 (3.48–8.03), 45.26 (18.11–113.12), all p<0.001. Osteoporosis prevalence: 2%, 10%, 25%, 71%; ORs: 4.66 (1.88–11.52), 14.55 (6.14–34.44), 104.13 (43.87–247.15), all p<0.001.",
        "interpretation": "Both development and validation panels show a steep monotonic risk gradient across prediction-score quartiles. The pattern is especially strong for osteoporosis: validation prevalence rises from 2% in Q1 to 71% in Q4, with a Q4 OR of 104.13, although the wide confidence interval reflects imprecision at the extreme.",
        "key_values": ["Development osteopenia Q1–Q4: 43%, 69%, 87%, 98%", "Development osteoporosis Q1–Q4: 3%, 10%, 23%, 62%", "Validation osteopenia Q1–Q4: 47%, 69%, 82%, 98%", "Validation osteoporosis Q1–Q4: 2%, 10%, 25%, 71%", "Validation osteoporosis Q4 OR 104.13 (43.87–247.15)"],
    },
    COMMON | {
        "object_id": "choi2024application__0009__figure_6", "object_label": "figure:6", "object_number": "6",
        "page_or_sheet": "12 / Springer Fig6", "width": 2031, "height": 1004,
        "caption": "Fig. 6. Bone mineral density (BMD) prediction results. (A) Importance calculated by standardized beta coefficients. (B) Predicted versus actual BMD in the validation set.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/choi2024application__0009__figure_6__publisher_original.png",
        "content_domains": "feature importance; regression; external validation; bone mineral density",
        "visible_text": "Panel A: for total-femur BMD, sex, weight, and age dominate absolute standardized coefficients; for femoral-neck BMD, age, weight, and sex dominate; for lumbar-spine BMD, weight, sex, and age dominate. Smaller retained variables include ptosis, low vision, diabetes mellitus, early AMD, hypertension, and dyslipidemia depending on site. Panel B Pearson correlations between predicted and true BMD: total femur r=0.714, femoral neck r=0.683, lumbar spine r=0.589; all p<0.001.",
        "interpretation": "The model has strongest agreement for total-femur BMD, moderate agreement for femoral-neck BMD, and weaker agreement for lumbar-spine BMD. Demographic/body-size predictors carry most of the standardized coefficient magnitude, while ocular variables contribute smaller increments.",
        "key_values": ["Total femur Pearson r 0.714, p<0.001", "Femoral neck r 0.683, p<0.001", "Lumbar spine r 0.589, p<0.001", "Dominant predictors: sex/weight/age, with ordering varying by skeletal site"],
    },
])
