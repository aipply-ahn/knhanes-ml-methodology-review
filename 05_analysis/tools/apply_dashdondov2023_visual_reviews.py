#!/usr/bin/env python3
from apply_completed_visual_reviews import apply_reviews

T = "2026-09-14T03:30:00+09:00"
C = {
    "reviewed_at": T, "study_key": "dashdondov2023deep", "object_type": "figure",
    "source_scope": "main", "source_path": "references/pdf/dashdondov2023deep.pdf",
    "extraction_method": "250-dpi source-page render with exact figure-only recrop",
}

apply_reviews([
    C | {
        "object_id": "dashdondov2023deep__0001__figure_2", "object_label": "figure:2", "object_number": "2",
        "page_or_sheet": "25", "caption": "Figure 2. Tolerance values from multicollinearity analysis of selected features in Dataset I and Dataset II.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2023deep__0001__figure_2__page25_250dpi.png",
        "width": 1950, "height": 1220, "content_domains": "feature selection; multicollinearity; data preprocessing",
        "visible_text": "Paired tolerance values (Dataset I / Dataset II) are shown for 19 variables: sodium urinary .888/.924; platelets .808/.499; leukocyte .757/.543; blood urea nitrogen .599/.430; AST .509/.702; HDL cholesterol .626/.714; adult diabetes prevalence .661/.252; waist circumference .201/.438; end systolic blood pressure .400/.991; pulse regularity .984/.970; adult counseling for drinking problems .971/.543; weight control .858/.861; education level .712/.163; EuroQol anxiety/depression .968/.879; influenza vaccination .834/.769; marital status .482/.149; income quartile .901/.226; gender .319/.947; COVID_state .976 (the final paired bar is visually adjacent at the plot boundary).",
        "interpretation": "Tolerance varies markedly by dataset for several features, indicating that multicollinearity structure changes after integration. The lowest clearly displayed values include marital status 0.149, education 0.163, waist circumference 0.201, and income quartile 0.226; all displayed values remain above 0.1.",
        "key_values": ["19 selected features", "Minimum displayed tolerance 0.149", "Education tolerance includes 0.163", "Waist circumference includes 0.201", "COVID_state up to 0.976"],
    },
    C | {
        "object_id": "dashdondov2023deep__0002__figure_3", "object_label": "figure:3", "object_number": "3",
        "page_or_sheet": "26", "caption": "Figure 3. Architecture of the deep autoencoder neural network used in the proposed method.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2023deep__0002__figure_3__page26_250dpi.png",
        "width": 1700, "height": 940, "content_domains": "model architecture; autoencoder; outlier detection",
        "visible_text": "The encoder contracts 37 inputs (X1–X37) through hidden layers h1–h14 and h1–h5 to a single bottleneck node using ReLU. The decoder mirrors the structure from one node through 5 and 14 hidden units back to 37 reconstructed outputs, with tanh indicated on the decoder side.",
        "interpretation": "This is a symmetric 37–14–5–1–5–14–37 deep autoencoder. The one-unit bottleneck forces strong compression; reconstruction error from this model is subsequently used for outlier detection.",
        "key_values": ["Architecture 37–14–5–1–5–14–37", "Encoder activation ReLU", "Decoder activation tanh", "Single-node bottleneck"],
    },
    C | {
        "object_id": "dashdondov2023deep__0003__figure_5", "object_label": "figure:5", "object_number": "5",
        "page_or_sheet": "27", "caption": "Figure 5. Distribution of the COVID-19 feature in the original and outlier-removed datasets.",
        "image_path": "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/dashdondov2023deep__0003__figure_5__page27_250dpi.png",
        "width": 1840, "height": 1200, "content_domains": "outlier detection; data preprocessing; distribution",
        "visible_text": "Two violin plots compare 'outlier' and 'no outlier' versions of the COVID-19 feature over approximately 0.5–3.1. Both are strongly bimodal near 1.0 and 2.0. The original/outlier distribution also shows a small dense component around 3.0; after outlier removal this becomes only a very thin upper tail.",
        "interpretation": "The autoencoder-based removal preserves the dominant bimodal structure near 1 and 2 while substantially reducing the isolated mass near 3. The figure demonstrates a distributional change, not predictive performance.",
        "key_values": ["Dominant modes near 1.0 and 2.0", "Original data include a small cluster near 3.0", "Outlier-removed data retain only a thin upper tail"],
    },
])
