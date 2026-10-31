#!/usr/bin/env python3
"""Reusable synchronization helper for completed ChatGPT visual reviews."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(rel):
    # Supplementary objects extracted from archives use archive::member paths;
    # provenance hashing is anchored to the immutable archive itself.
    archive = str(rel).split("::", 1)[0]
    return hashlib.sha256((ROOT/archive).read_bytes()).hexdigest()

def ledger_update(x,r):
    x.update({
        'study_key':r['study_key'],'source_scope':r.get('source_scope','main'),'source_path':r['source_path'],
        'source_sha256':sha(r['source_path']),'source_format':Path(r['source_path']).suffix,
        'object_id':r['object_id'],'object_type':r['object_type'],'object_label':r['object_label'],
        'object_number':r['object_number'],'page_or_sheet':str(r['page_or_sheet']),'caption':r['caption'],
        'image_path':r['image_path'],'image_width_px':str(r['width']),'image_height_px':str(r['height']),
        'extraction_method':r.get('extraction_method','original embedded PDF image'),
        'extraction_confidence':'verified','content_domains':r.get('content_domains',x.get('content_domains','')),
        'vision_required':'N','chatgpt_vision_status':'completed','chatgpt_review_stage':r.get('review_stage','embedded_original_chatgpt_reread'),
        'chatgpt_visible_text':r['visible_text'],'chatgpt_interpretation':r['interpretation'],
        'chatgpt_key_values':json.dumps(r['key_values'],ensure_ascii=False),'chatgpt_uncertainty':'','manual_review_reason':''})

def study_object(r):
    return {'object_id':r['object_id'],'type':r['object_type'],'label':r['object_label'],'number':r['object_number'],'scope':r.get('source_scope','main'),'source_path':r['source_path'],'page_or_sheet':str(r['page_or_sheet']),'caption':r['caption'],'native_text':'','structured_table_path':'','image_path':r['image_path'],'content_domains':r.get('content_domains',''),'interpretation':r['interpretation'],'visible_text':r['visible_text'],'key_values':r['key_values'],'vision_status':'completed','vision_review_stage':r.get('review_stage','embedded_original_chatgpt_reread'),'uncertainty':'','manual_review_reason':''}

def apply_reviews(reviews):
    byid={r['object_id']:r for r in reviews}; studies={r['study_key'] for r in reviews}; study_docs={}
    for s in studies:
        p=ROOT/f'data/study_json/{s}.json'; d=json.loads(p.read_text()); existing={x['object_id']:x for x in d['visual_objects']['items']}
        for r in reviews:
            if r['study_key']!=s:continue
            if r['object_id'] not in existing:d['visual_objects']['items'].append(study_object(r));existing[r['object_id']]=d['visual_objects']['items'][-1]
            else: existing[r['object_id']].update(study_object(r))
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');study_docs[s]=d
    for r in reviews:
        p=ROOT/f"data/visual_object_audit/vision_annotations/{r['object_id']}.json"
        d={'object_id':r['object_id']};
        if p.exists():d=json.loads(p.read_text())
        d.update({'status':'completed','visible_text':r['visible_text'],'interpretation':r['interpretation'],'key_values':r['key_values'],'uncertainty':'','manual_review_reason':'','review_stage':r.get('review_stage','embedded_original_chatgpt_reread')});p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    jp=ROOT/'data/ALL_REPORT_VISUAL_OBJECTS.jsonl'; rows=[]; seen=set()
    for line in jp.read_text().splitlines():
        if not line.strip():continue
        x=json.loads(line); r=byid.get(x.get('object_id'))
        if r:ledger_update(x,r);seen.add(x['object_id'])
        rows.append(x)
    for oid,r in byid.items():
        if oid not in seen:
            x={'nearby_context':'','native_text':'','structured_table_path':'','native_interpretation':'','crop_reaudit_status':'repaired_embedded_original','crop_reaudit_method':'embedded_image_reassembly','crop_reaudit_ocr_engine_used':'N'};ledger_update(x,r);rows.append(x)
    jp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    rewrite_all_tsv(rows)
    sync_current_indices(byid)
    ip=ROOT/'data/STANDARDIZED_STUDY_JSON_INDEX.jsonl';out=[]
    for line in ip.read_text().splitlines():
        if line.strip():x=json.loads(line);out.append(study_docs.get(x.get('study_id'),x))
    ip.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out))

def rewrite_all_tsv(rows):
    p=ROOT/'data/ALL_REPORT_VISUAL_OBJECTS.tsv'
    with p.open(encoding='utf-8-sig',newline='') as h:fields=csv.DictReader(h,delimiter='\t').fieldnames or []
    with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows)
    # Full review queue contains all objects with annotation records.
    q=ROOT/'data/CHATGPT_VISION_REVIEW_QUEUE.tsv'
    with q.open(encoding='utf-8-sig',newline='') as h:qfields=csv.DictReader(h,delimiter='\t').fieldnames or []
    qr=[]
    for x in rows:
        ap=ROOT/f"data/visual_object_audit/vision_annotations/{x['object_id']}.json"
        if ap.exists():y=dict(x);y['annotation_path']=str(ap.relative_to(ROOT));qr.append(y)
    with q.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,fieldnames=qfields,delimiter='\t',lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(qr)

def sync_current_indices(byid):
    lp=ROOT/'data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv'
    with lp.open(encoding='utf-8-sig',newline='') as h:rd=csv.DictReader(h,delimiter='\t');fields=rd.fieldnames or [];rows=list(rd)
    pos={x['object_id']:i for i,x in enumerate(rows)}
    for oid,r in byid.items():
        x=rows[pos[oid]] if oid in pos else {k:'' for k in fields}
        x.update({'refreshed_at':r.get('reviewed_at','2026-09-13T23:59:00+09:00'),'study_key':r['study_key'],'object_id':oid,'object_type':r['object_type'],'object_label':r['object_label'],'source_scope':r.get('source_scope','main'),'page_or_sheet':str(r['page_or_sheet']),'caption':r['caption'],'decode_status':'COMPLETE_AFTER_SOURCE_RECOVERY_CHATGPT_IMAGE_REREAD','crop_recovery_status':r.get('crop_recovery_status') or x.get('crop_recovery_status') or 'repaired_embedded_original','scientific_interpretation_status':'COMPLETE','chatgpt_image_transcription':r['visible_text'],'chatgpt_image_interpretation':r['interpretation'],'remaining_uncertainty':'','required_followup':'','latest_review_image':r['image_path'],'latest_image_kind':r.get('latest_image_kind') or x.get('latest_image_kind') or ('table_only_crop' if r['object_type']=='table' else 'recovered_canonical_crop'),'canonical_image':r['image_path'],'source_file':r['source_path'],'ocr_engine_used':'N'})
        if oid not in pos:rows.append(x)
    with lp.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)
    for rel in ('data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv','data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv','data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv'):
        p=ROOT/rel
        with p.open(encoding='utf-8-sig',newline='') as h:rd=csv.DictReader(h,delimiter='\t');fs=rd.fieldnames or [];rr=[x for x in rd if x.get('object_id') not in byid]
        with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,fieldnames=fs,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rr)
    with lp.open(encoding='utf-8-sig',newline='') as h:rd=csv.DictReader(h,delimiter='\t');fs=rd.fieldnames or [];decoded=[x for x in rd if x['scientific_interpretation_status']!='SOURCE_RECOVERY_REQUIRED']
    p=ROOT/'data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv'
    with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,fieldnames=fs,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(decoded)
