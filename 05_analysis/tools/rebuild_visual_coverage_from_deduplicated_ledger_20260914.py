#!/usr/bin/env python3
"""Rebuild coverage/workbook/performance counts from the deduplicated object ledger."""
from collections import Counter, defaultdict
import csv
from pathlib import Path
import openpyxl
import re

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def write(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows)

objects=read(DATA/'ALL_REPORT_VISUAL_OBJECTS.tsv'); by=defaultdict(list)
for x in objects:by[x['study_key']].append(x)

cp=DATA/'ALL_REPORT_VISUAL_COVERAGE.tsv'; coverage=read(cp)
with cp.open(encoding='utf-8-sig',newline='') as f:cfields=csv.DictReader(f,delimiter='\t').fieldnames
for r in coverage:
 xs=by.get(r['study_key'],[]); status=Counter(x['chatgpt_vision_status'] for x in xs)
 main=[x for x in xs if x['source_scope']=='main']; supp=[x for x in xs if x['source_scope']!='main']
 r.update(objects_total=str(len(xs)),main_figures=str(sum(x['object_type']=='figure' for x in main)),
  main_tables=str(sum(x['object_type']=='table' for x in main)),supplement_figures=str(sum(x['object_type']=='figure' for x in supp)),
  supplement_tables=str(sum(x['object_type']=='table' for x in supp)),
  vision_required=str(sum(x['chatgpt_vision_status']!='not_required_native_table' for x in xs)),
  chatgpt_vision_pending=str(status.get('pending',0)),chatgpt_completed=str(status.get('completed',0)),
  chatgpt_uncertain=str(status.get('uncertain',0)),chatgpt_unreadable=str(status.get('unreadable',0)+status.get('manual_review_required_source_resolution',0)),
  audit_status=('complete_with_flagged_visual_uncertainty' if status.get('unreadable',0)+status.get('manual_review_required_source_resolution',0) else 'complete'))
write(cp,coverage,cfields)

# Keep the filterable one-sheet workbook byte-for-byte aligned in row content.
wb=openpyxl.Workbook();ws=wb.active;ws.title='Visual objects';fields=list(objects[0]);ws.append(fields)
clean=lambda v:re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',' ',str(v or ''))
for x in objects:ws.append([clean(x.get(k,'')) for k in fields])
ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;wb.save(DATA/'ALL_REPORT_VISUAL_OBJECTS.xlsx')

# The performance-screening denominator follows deduplicated figure containers.
pp=DATA/'FIGURE_PERFORMANCE_CANDIDATES.tsv'; perf=read(pp); pc=Counter(x['manuscript'] for x in perf)
pa=DATA/'FIGURE_PERFORMANCE_AUDIT.tsv'; audits=read(pa)
with pa.open(encoding='utf-8-sig',newline='') as f:afields=csv.DictReader(f,delimiter='\t').fieldnames
for r in audits:
 r['catalogued_figures_screened']=str(sum(x['object_type']=='figure' for x in by.get(r['key'],[])))
 r['performance_figure_candidates']=str(pc.get(r['key'],0))
write(pa,audits,afields)

print({'objects':len(objects),'main_figures':sum(x['source_scope']=='main' and x['object_type']=='figure' for x in objects),
 'main_tables':sum(x['source_scope']=='main' and x['object_type']=='table' for x in objects),
 'supplement_figures':sum(x['source_scope']!='main' and x['object_type']=='figure' for x in objects),
 'supplement_tables':sum(x['source_scope']!='main' and x['object_type']=='table' for x in objects),
 'image_interpreted':sum(x['chatgpt_vision_status']!='not_required_native_table' for x in objects),
 'performance_figures':sum(int(x['catalogued_figures_screened']) for x in audits),'performance_candidates':len(perf)})
