#!/usr/bin/env python3
import csv, json
from pathlib import Path
from apply_completed_visual_reviews import ROOT, apply_reviews, rewrite_all_tsv

T = "2026-09-14T00:45:00+09:00"
src = "references/supplements/pant2025development/sj-docx-1-dhj-10.1177_20552076251333660.docx"
reviews = [
 {
  "reviewed_at":T,"study_key":"pant2025development","object_id":"pant2025development__0009__figure_1","object_type":"figure","object_label":"figure:S1","object_number":"S1","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:5","caption":"Supplementary Figure 1. Feature importance based on random forest-based feature selection.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/pant2025development__0009__figure_1__docx_native.png","width":940,"height":602,"extraction_method":"native DOCX media image","content_domains":"feature importance; feature selection",
  "visible_text":"Random-forest feature-importance bar chart. Ranked values: Age 0.1306; Occupation 0.0704; Education level 0.0685; Gender 0.0571; Occupation_M 0.0553; BWChangefY 0.0484; DSf2Ws 0.0400; EEA 0.0384; Average sleep time 0.0246; AST_CT 0.0224; PdLC 0.0155; Diabetes prevalence 0.0152; BWControlfY 0.0150; PHS_M 0.0141; WDiW_M 0.0116; WDiW 0.0113; Perceived health status 0.0111; QoL 0.0091; PdD 0.0083; Perceived stress level 0.0080; Perceived stress level_M 0.0077; Marital status 0.0070; Education level_M 0.0069; InfluenzaVaccination 0.0068; FoPFT 0.0067; PdH 0.0043; NoHM 0.0029; NoHM_M 0.0028.",
  "interpretation":"Age is the dominant random-forest feature, at nearly twice the importance of occupation or education. Occupation, education, gender, annual body-weight change, depressive symptoms, and economic activity form the next tier. The chart also exposes both original and modified variants, supporting the reported pruning of low-importance redundant encodings.",
  "key_values":["Top feature: Age 0.1306","Occupation: 0.0704","Education level: 0.0685","Gender: 0.0571","Occupation_M: 0.0553","BWChangefY: 0.0484","Lowest shown: NoHM_M 0.0028"]
 },
 {
  "reviewed_at":T,"study_key":"pant2025development","object_id":"pant2025development__0010__figure_2","object_type":"figure","object_label":"figure:S2","object_number":"S2","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:10","caption":"Supplementary Figure 2. Receiver operating characteristic curves for 5-fold cross-validation of the proposed model.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/pant2025development__0010__figure_2__docx_native.png","width":578,"height":432,"extraction_method":"native DOCX media image","content_domains":"model performance; cross-validation; discrimination",
  "visible_text":"Five ROC curves and a dashed chance diagonal. Legend: Fold 1 AUC 0.66; Fold 2 AUC 0.72; Fold 3 AUC 0.70; Fold 4 AUC 0.70; Fold 5 AUC 0.67.",
  "interpretation":"Cross-validation discrimination varies from 0.66 to 0.72, with a mean AUC of 0.69 and a 0.06 range. The fold-to-fold spread shows moderate sampling instability that is obscured by reporting only a single aggregate performance value.",
  "key_values":["Fold AUCs: 0.66, 0.72, 0.70, 0.70, 0.67","Mean fold AUC: 0.69","AUC range: 0.06"]
 },
 {
  "reviewed_at":T,"study_key":"pant2025development","object_id":"pant2025development__0017__figure_3","object_type":"figure","object_label":"figure:S3","object_number":"S3","source_scope":"supplement","source_path":src,"page_or_sheet":"docx:8","caption":"Supplementary Figure 3. Participant selection flowchart.","image_path":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/pant2025development__0017__figure_3__docx_vector_300dpi.png","width":1615,"height":1940,"extraction_method":"DOCX vector figure rendered at 300 dpi and tightly cropped","content_domains":"participant flow; cohort selection",
  "visible_text":"KNHANES data for 12 years, 2007–2018, total n=89,512 (year counts: 2007 4,595; 2008 4,595; 2009 9,744; 2010 8,959; 2011 8,518; 2012 8,058; 2013 8,018; 2014 7,550; 2015 7,380; 2016 8,150; 2017 8,127; 2018 7,989). Doctor diagnosis or pulmonary-function-test screening n=89,512; excluded FEV1/FVC >0.7, n=84,009; dependent variable assessed for eligibility n=5,503; excluded because dependent variable was not reported, n=37; included in analysis n=5,466.",
  "interpretation":"The analytic cohort was obtained by retaining participants compatible with airflow obstruction (5,503 of 89,512) and then excluding 37 without the smoking-status dependent variable, yielding 5,466. The diagram supports the final sample size and makes the dominant exclusion step explicit.",
  "key_values":["Initial KNHANES 2007–2018: n=89,512","Excluded FEV1/FVC >0.7: n=84,009","Eligible after pulmonary screening: n=5,503","Missing dependent variable: n=37","Final analysis: n=5,466"]
 }
]

apply_reviews(reviews)

# These two records were paragraph-level cross-references in the main PDF, not
# visual objects. Keep their source files on disk for provenance but remove the
# duplicate pseudo-objects from canonical inventories and active review queues.
aliases={"pant2025development__0001__figure_S1","pant2025development__0004__figure_S2"}

p=ROOT/'data/study_json/pant2025development.json'
d=json.loads(p.read_text())
d['visual_objects']['items']=[x for x in d['visual_objects']['items'] if x.get('object_id') not in aliases]
items=d['visual_objects']['items']
d['visual_objects']['counts']={
 'total':len(items),
 'main_figures':sum(x['type']=='figure' and x['scope']=='main' for x in items),
 'main_tables':sum(x['type']=='table' and x['scope']=='main' for x in items),
 'supplement_figures':sum(x['type']=='figure' and x['scope']=='supplement' for x in items),
 'supplement_tables':sum(x['type']=='table' and x['scope']=='supplement' for x in items),
}
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

jp=ROOT/'data/ALL_REPORT_VISUAL_OBJECTS.jsonl'
rows=[json.loads(line) for line in jp.read_text().splitlines() if line.strip()]
rows=[x for x in rows if x.get('object_id') not in aliases]
jp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
rewrite_all_tsv(rows)

for rel in [
 'data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv',
 'data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv',
 'data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv',
 'data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv',
 'data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv']:
 q=ROOT/rel
 with q.open(encoding='utf-8-sig',newline='') as h:
  rd=csv.DictReader(h,delimiter='\t'); fields=rd.fieldnames or []; rr=[x for x in rd if x.get('object_id') not in aliases]
 with q.open('w',encoding='utf-8-sig',newline='') as h:
  w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rr)

ip=ROOT/'data/STANDARDIZED_STUDY_JSON_INDEX.jsonl'
out=[]
for line in ip.read_text().splitlines():
 if line.strip():
  x=json.loads(line); out.append(d if x.get('study_id')=='pant2025development' else x)
ip.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out))
