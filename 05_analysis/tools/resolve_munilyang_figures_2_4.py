#!/usr/bin/env python3
"""Promote directly extracted and vision-reviewed Mun/Lee/Yang 2025 Figures 2--4."""
from __future__ import annotations
import csv,json
from pathlib import Path

R=Path(__file__).resolve().parents[1]; S="munilyang2025methodology"
D={
 f"{S}__0014__figure_2":{
  "image":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/munilyang2025methodology_embedded/page_32-000.png","w":"926","h":"554",
  "visible":"Thirteen-step workflow: 1 input KNHANES 2020–2023 (N=10,825); 2 XGBoost binary-logistic association model; 3 Lift-chart risk assessment; 4 undiagnosed high-risk group selection; 5 variables classified as immutable, constrained, or free; 6 constraints set (including BMI ≤20% and waist circumference ≤15 cm change); 7 DiCE generates four counterfactual alternatives; 8 hypothetical lower-risk scenarios; 9 association-based prompt design; 10 on-premise Meerkat-8B medical LLM; 11 VARCO-8B Korean translation; 12 individualized health guide; 13 insurance use. Side boxes list major constraints and limitations.",
  "interpretation":"The workflow combines association modelling and Lift-chart stratification with constrained DiCE counterfactual generation, then uses locally served translation and medical LLMs to produce explicitly hypothetical guidance. The figure states that cross-sectional data establish association rather than causality and do not constitute medical diagnosis.",
  "values":["KNHANES 2020–2023","N=10,825","13 stages","XGBoost","Lift chart","DiCE: four alternatives","Meerkat-8B","VARCO-8B"]},
 f"{S}__0017__figure_3":{
  "image":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/munilyang2025methodology_embedded/page_36-000.png","w":"1307","h":"661",
  "visible":"Hardware: NVIDIA GeForce RTX 4060Ti 16GB; Intel i5-14500; RAM 128GB; Ubuntu 24.04 LTS. On-premise environment with REST API serving interface. Llama-VARCO-8B-Instruct Korean translation model feeds Meerkat-8B (v1.0) medical-specialized LLM. Both use 4-bit GPTQ quantization and vLLM 0.8.4 inference acceleration.",
  "interpretation":"The system is a fully on-premise two-model pipeline: a Korean/English translation model passes content to a medical-specialized LLM through a REST API, with quantization and vLLM acceleration on a single workstation-class GPU.",
  "values":["RTX 4060Ti 16GB","Intel i5-14500","RAM 128GB","Ubuntu 24.04 LTS","Llama-VARCO-8B-Instruct","Meerkat-8B v1.0","GPTQ 4-bit","vLLM 0.8.4"]},
 f"{S}__0019__figure_4":{
  "image":"data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/munilyang2025methodology_embedded/page_38-000.png","w":"1216","h":"789",
  "visible":"Research-only technical validation screen. Input example: 75-year-old man, current risk 72%, waist 85.7→71.8 cm, with structured JSON. Meerkat-8B output states an association-based estimated diabetes-risk reduction to 24%. Quality review marks disclaimer inclusion and structural adequacy, but flags excessive confidence, insufficient practical advice, and a quality gap versus GPT-4; it also warns of inappropriate practical use and legal/ethical risk. Technical achievements, future improvements, research conclusion, and a prominent non-medical-advice disclaimer are shown.",
  "interpretation":"The figure documents a worked prototype rather than clinical validation. It demonstrates structured-data conversion and LLM output, while explicitly recording overconfidence, weak actionability, lack of direct medical validation, potential bias, and prohibition on real-world recommendation.",
  "values":["example age 75 male","risk 72%","waist 85.7→71.8 cm","illustrative output risk 24%","research prototype only","not medical advice"]},
}

def upd(x):
 d=D.get(x.get('object_id'))
 if not d:return
 x.update({'image_path':d['image'],'image_width_px':d['w'],'image_height_px':d['h'],'extraction_method':'original embedded PDF image','extraction_confidence':'verified','vision_required':'N','chatgpt_vision_status':'completed','chatgpt_review_stage':'embedded_original_chatgpt_reread','chatgpt_visible_text':d['visible'],'chatgpt_interpretation':d['interpretation'],'chatgpt_key_values':json.dumps(d['values'],ensure_ascii=False),'chatgpt_uncertainty':'','manual_review_reason':''})

def tab(rel,remove=False,latest=False):
 p=R/rel
 with p.open(encoding='utf-8-sig',newline='') as h: rd=csv.DictReader(h,delimiter='\t'); fs=rd.fieldnames or []; rows=list(rd)
 out=[]
 for x in rows:
  if remove and x.get('object_id') in D:continue
  upd(x); d=D.get(x.get('object_id'))
  if latest and d:x.update({'decode_status':'COMPLETE_AFTER_SOURCE_RECOVERY_CHATGPT_IMAGE_REREAD','crop_recovery_status':'repaired_embedded_original','scientific_interpretation_status':'COMPLETE','chatgpt_image_transcription':d['visible'],'chatgpt_image_interpretation':d['interpretation'],'remaining_uncertainty':'','required_followup':'','latest_review_image':d['image'],'latest_image_kind':'embedded_original_figure'})
  out.append(x)
 with p.open('w',encoding='utf-8-sig',newline='') as h: wr=csv.DictWriter(h,fieldnames=fs,delimiter='\t',lineterminator='\n',extrasaction='ignore');wr.writeheader();wr.writerows(out)

def main():
 sp=R/f'data/study_json/{S}.json'; study=json.loads(sp.read_text())
 for x in study['visual_objects']['items']:
  d=D.get(x.get('object_id'))
  if d:x.update({'image_path':d['image'],'visible_text':d['visible'],'interpretation':d['interpretation'],'key_values':d['values'],'vision_status':'completed','vision_review_stage':'embedded_original_chatgpt_reread','uncertainty':'','manual_review_reason':''})
 sp.write_text(json.dumps(study,ensure_ascii=False,indent=2)+'\n')
 for oid,d in D.items():
  p=R/f'data/visual_object_audit/vision_annotations/{oid}.json'; x=json.loads(p.read_text());x.update({'status':'completed','visible_text':d['visible'],'interpretation':d['interpretation'],'key_values':d['values'],'uncertainty':'','manual_review_reason':'','review_stage':'embedded_original_chatgpt_reread'});p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
 p=R/'data/ALL_REPORT_VISUAL_OBJECTS.jsonl'; rows=[]
 for line in p.read_text().splitlines():
  if line.strip():x=json.loads(line);upd(x);rows.append(x)
 p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
 tab('data/ALL_REPORT_VISUAL_OBJECTS.tsv');tab('data/CHATGPT_VISION_REVIEW_QUEUE.tsv');tab('data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv',remove=True);tab('data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv',latest=True);tab('data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv',remove=True);tab('data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv',remove=True)
 lp=R/'data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv'
 with lp.open(encoding='utf-8-sig',newline='') as h:rd=csv.DictReader(h,delimiter='\t');fs=rd.fieldnames or [];rows=[x for x in rd if x['scientific_interpretation_status']!='SOURCE_RECOVERY_REQUIRED']
 p=R/'data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv'
 with p.open('w',encoding='utf-8-sig',newline='') as h:wr=csv.DictWriter(h,fieldnames=fs,delimiter='\t',lineterminator='\n');wr.writeheader();wr.writerows(rows)
 p=R/'data/STANDARDIZED_STUDY_JSON_INDEX.jsonl';rows=[]
 for line in p.read_text().splitlines():
  if line.strip():x=json.loads(line);rows.append(study if x.get('study_id')==S else x)
 p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
 print('resolved',len(D),'figures')
if __name__=='__main__':main()
