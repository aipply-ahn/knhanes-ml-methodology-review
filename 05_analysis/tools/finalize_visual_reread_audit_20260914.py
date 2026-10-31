#!/usr/bin/env python3
"""Finalize provenance/counts for the 424-object direct image-model reread."""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/visual_manual_review/latest_after_recrop'

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))

def write(path,rows,fields=None):
    fields=fields or list(rows[0])
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n',extrasaction='ignore')
        w.writeheader();w.writerows([{k:(v.replace('\0','') if isinstance(v,str) else v) for k,v in r.items()} for r in rows])

latest=read(BASE/'LATEST_VISUAL_REVIEW.tsv')
sheet=read(BASE/'pending_reread_contact_sheets/index.tsv')
audit=read(BASE/'CONTACT_SHEET_REREAD_AUDIT.tsv')
original={r['object_id'] for r in sheet}
assert len(original)==424 and len(sheet)==424
assert len(audit)==417 and len({r['object_id'] for r in audit})==417

# Seven objects were reread separately after their source/page mapping was repaired.
detailed={
 'choi2026development__0001__table_1','kang2019sarcopenia__0007__table_2_recovered',
 'kim2024gender__0002__table_S1','oh2015artificial__0006__table_1_recovered',
 'tran2024explainable__0016__table_2_recovered','ullah2023machine__0004__table_2_recovered',
 'ullah2023machine__0005__table_3_recovered'}
assert detailed <= original and len(detailed)==7
assert {r['object_id'] for r in audit}|detailed==original

byid={r['object_id']:r for r in latest}
for oid in original:
    r=byid[oid]
    assert r['scientific_interpretation_status']=='COMPLETE',oid
    assert r['chatgpt_image_transcription'].strip(),oid
    assert r['chatgpt_image_interpretation'].strip(),oid
    assert r['ocr_engine_used']=='N',oid
    assert (ROOT/r['latest_review_image']).exists(),oid

# Remove NUL source glyphs from current TSV products; JSONL is already clean.
for rel in ['data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv',
            'data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv',
            'data/ALL_REPORT_VISUAL_OBJECTS.tsv','data/CHATGPT_VISION_REVIEW_QUEUE.tsv']:
    p=ROOT/rel
    if p.exists():
        rows=read(p)
        with p.open(encoding='utf-8-sig',newline='') as f: fields=csv.DictReader(f,delimiter='\t').fieldnames
        write(p,rows,fields)

counts=Counter(r['scientific_interpretation_status'] for r in latest)
summary={
 'completed_at':'2026-09-14T03:22:00+09:00','original_pending_objects':424,
 'contact_sheet_direct_rereads':417,'separate_source_mapping_repairs_and_rereads':7,
 'remaining_reinterpretation_required':counts.get('REINTERPRETATION_REQUIRED_FOR_NEWLY_EXPOSED_CONTENT',0),
 'complete_objects_total':counts.get('COMPLETE',0),
 'source_recovery_required_outside_424':counts.get('SOURCE_RECOVERY_REQUIRED',0),
 'publisher_source_resolution_user_review_outside_424':counts.get('MANUAL_REVIEW_REQUIRED_SOURCE_RESOLUTION',0),
 'ocr_engines_used':0,
 'quality_control_note':'All 424 recovered objects were directly inspected with the ChatGPT image model in 48 indexed contact sheets; seven mapping exceptions and five obvious crop/orientation exceptions were separately repaired and reread. Historical transcription wording may describe the pre-recovery crop; current-image completion decisions are recorded in CONTACT_SHEET_REREAD_AUDIT.tsv and the object ledger.',
}
(BASE/'REREAD_424_COMPLETION_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
