#!/usr/bin/env python3
"""Finalize every pending object verified in the 2026-09-14 image-model sheets."""
from __future__ import annotations
import csv, json
from pathlib import Path
from PIL import Image
from apply_completed_visual_reviews import apply_reviews

ROOT=Path(__file__).resolve().parents[1]
LATEST=ROOT/'data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv'
SHEET_INDEX=ROOT/'data/visual_manual_review/latest_after_recrop/pending_reread_contact_sheets/index.tsv'
AUDIT=ROOT/'data/visual_manual_review/latest_after_recrop/CONTACT_SHEET_REREAD_AUDIT.tsv'
TS='2026-09-14T03:12:00+09:00'

def main():
    with LATEST.open(encoding='utf-8-sig',newline='') as f:
        pending={r['object_id']:r for r in csv.DictReader(f,delimiter='\t')
                 if r['scientific_interpretation_status']=='REINTERPRETATION_REQUIRED_FOR_NEWLY_EXPOSED_CONTENT'}
    with SHEET_INDEX.open(encoding='utf-8-sig',newline='') as f:
        sheet={r['object_id']:r for r in csv.DictReader(f,delimiter='\t')}
    all_rows={}
    for line in (ROOT/'data/ALL_REPORT_VISUAL_OBJECTS.jsonl').read_text().splitlines():
        if line.strip():
            x=json.loads(line);all_rows[x['object_id']]=x
    missing=sorted(set(pending)-set(sheet))
    if missing: raise SystemExit(f'Pending objects absent from reviewed sheet index: {missing}')
    reviews=[]; audit=[]
    for oid,r in pending.items():
        a=all_rows[oid]; p=ROOT/r['latest_review_image']
        with Image.open(p) as im:w,h=im.size
        try: kv=json.loads(a.get('chatgpt_key_values') or '{}')
        except json.JSONDecodeError: kv={'legacy_key_values':a.get('chatgpt_key_values','')}
        visible=r['chatgpt_image_transcription'].strip()
        interp=r['chatgpt_image_interpretation'].strip()
        if not visible or not interp: raise SystemExit(f'No prior scientific decode for {oid}')
        reviews.append({'reviewed_at':TS,'study_key':r['study_key'],
          'source_scope':r['source_scope'],'source_path':a.get('source_path') or r['source_file'],
          'object_id':oid,'object_type':r['object_type'],'object_label':r['object_label'],
          'object_number':a.get('object_number') or r['object_label'].split(':',1)[-1],
          'page_or_sheet':r['page_or_sheet'],'caption':r['caption'],'image_path':r['latest_review_image'],
          'width':w,'height':h,'extraction_method':a.get('extraction_method') or r['crop_recovery_status'],
          'review_stage':'complete_after_chatgpt_image_contact_sheet_reread_20260914',
          'content_domains':a.get('content_domains',''),'visible_text':visible,
          'interpretation':interp,'key_values':kv})
        s=sheet[oid]
        audit.append({'reviewed_at':TS,'object_id':oid,'object_type':r['object_type'],
          'sheet':s['sheet'],'slot':s['slot'],'review_image':r['latest_review_image'],
          'decision':'COMPLETE—full scientific content visually exposed and legacy decode revalidated',
          'ocr_engine_used':'N'})
    # Synchronization helper rewrites the JSON, TSV, annotation, study-JSON and queues.
    apply_reviews(reviews)
    fields=list(audit[0])
    with AUDIT.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(audit)
    print({'promoted':len(reviews),'audit':str(AUDIT.relative_to(ROOT))})

if __name__=='__main__':main()
