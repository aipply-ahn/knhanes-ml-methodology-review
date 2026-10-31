#!/usr/bin/env python3
"""Remove paragraph-level cross-reference pseudo-objects from canonical inventories."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
from apply_completed_visual_reviews import ROOT, rewrite_all_tsv

def remove_aliases(study_key: str, aliases: set[str]) -> None:
    p=ROOT/f'data/study_json/{study_key}.json'
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
            rd=csv.DictReader(h,delimiter='\t'); fields=rd.fieldnames or []
            rr=[x for x in rd if x.get('object_id') not in aliases]
        with q.open('w',encoding='utf-8-sig',newline='') as h:
            w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',lineterminator='\n')
            w.writeheader();w.writerows(rr)

    ip=ROOT/'data/STANDARDIZED_STUDY_JSON_INDEX.jsonl'
    out=[]
    for line in ip.read_text().splitlines():
        if line.strip():
            x=json.loads(line);out.append(d if x.get('study_id')==study_key else x)
    ip.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out))

if __name__=='__main__':
    remove_aliases(sys.argv[1],set(sys.argv[2:]))
