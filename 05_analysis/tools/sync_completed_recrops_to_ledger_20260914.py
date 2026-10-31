#!/usr/bin/env python3
"""Propagate four earlier completed recrops that were left stale in the master ledger."""
import csv,json
from pathlib import Path
from PIL import Image
from apply_completed_visual_reviews import apply_reviews,ROOT
IDS={"ahn2025machine__0001__figure_1","anon2025improving__0003__figure_2","anon2026partial__0002__figure_1","anon2026partial__0005__figure_4"}
with (ROOT/'data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv').open(encoding='utf-8-sig',newline='') as h:latest={x['object_id']:x for x in csv.DictReader(h,delimiter='\t') if x['object_id'] in IDS}
ledger={}
for line in (ROOT/'data/ALL_REPORT_VISUAL_OBJECTS.jsonl').read_text().splitlines():
 if line.strip():x=json.loads(line);ledger[x['object_id']]=x
reviews=[]
for oid in IDS:
 x=latest[oid]; old=ledger[oid]; im=Image.open(ROOT/x['latest_review_image'])
 ap=ROOT/f'data/visual_object_audit/vision_annotations/{oid}.json';ann=json.loads(ap.read_text()) if ap.exists() else {}
 label=x['object_label']; number=label.split(':',1)[1] if ':' in label else label
 reviews.append({'reviewed_at':'2026-09-14T06:45:00+09:00','study_key':x['study_key'],'object_id':oid,'object_type':x['object_type'],'object_label':label,'object_number':number,'source_scope':x['source_scope'],'source_path':x['source_file'],'page_or_sheet':x['page_or_sheet'],'caption':x['caption'],'image_path':x['latest_review_image'],'width':im.width,'height':im.height,'extraction_method':'verified high-resolution manual recrop from source PDF','content_domains':old.get('content_domains',''),'visible_text':x['chatgpt_image_transcription'],'interpretation':x['chatgpt_image_interpretation'],'key_values':ann.get('key_values',[])})
apply_reviews(reviews)
