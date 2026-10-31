#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

apply_reviews([{
    "reviewed_at": "2026-09-14T03:05:00+09:00",
    "study_key": "chang2023classification",
    "object_id": "chang2023classification__0008__figure_6",
    "object_type": "figure", "object_label": "figure:6", "object_number": "6",
    "source_scope": "main", "source_path": "references/pdf/chang2023classification.pdf",
    "page_or_sheet": "9 / PMC figure 6",
    "caption": "Fig. 6. Sensitivity index values for 11 inputs.",
    "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/chang2023classification__0008__figure_6__publisher_original.jpg",
    "width": 789, "height": 552,
    "extraction_method": "original 600-dpi publisher JPEG recovered from PubMed Central",
    "content_domains": "feature importance; sensitivity analysis; nutrition; diabetes prediction",
    "visible_text": "Sensitivity indices, descending: thiamine 1.42; carbohydrate 1.30; potassium 0.77; energy 0.71; cholesterol 0.48; sugar 0.34; vitamin A 0.25; riboflavin 0.21; protein 0.18; vitamin C 0.11; fat 0.09.",
    "interpretation": "Thiamine and carbohydrate are the dominant nutrient inputs in the reported ANN sensitivity analysis. Potassium and energy form a second tier above 0.5, while the other seven inputs have substantially smaller sensitivity indices. These are model-sensitivity measures, not causal nutrient effects.",
    "key_values": ["Thiamine 1.42", "Carbohydrate 1.30", "Potassium 0.77", "Energy 0.71", "Cholesterol 0.48", "Sugar 0.34", "Vitamin A 0.25", "Riboflavin 0.21", "Protein 0.18", "Vitamin C 0.11", "Fat 0.09"],
}])
