"""Idempotent, source-anchored revision of post-core analysis fields only."""
import hashlib
import json
import re
from pathlib import Path
from protocol_record_schema import normalise_analysis_records

ROOT = Path(__file__).resolve().parents[1]
# Exact lines personally checked in the retained full text; not title inference.
RANGES = {'KHM011':[(115,132)], 'KHM036':[(69,88)], 'KHM045':[(130,138)],
          'KHM053':[(36,44),(201,212)], 'KHM081':[(178,205)], 'KHM082':[(160,170)],
          'KHM093':[(328,343)], 'KHM136':[(90,98),(356,369),(1525,1538)],
          'KHM204':[(142,161),(258,268),(299,318)], 'KHM210':[(153,170),(186,193)]}

def main():
    changes = []
    addpath = ROOT/'data/protocol_v1_3/purpose_evidence_addendum.json'
    add = json.loads(addpath.read_text())
    addby = {r['study_id']:r for r in add['records']}
    for path in sorted((ROOT/'data/protocol_v1_2/final').glob('*_final.json')):
        d = json.loads(path.read_text()); sid=d['study_id']
        record=d.get('adjudication',{}).get('purpose_evidence_v1_3')
        if not record or not record.get('statistical_analysis_records'): continue
        before = json.dumps(d['protocol_items'],ensure_ascii=False,sort_keys=True)
        if sid in RANGES:
            source = ROOT/f"references/md/{d['canonical_key']}.md"
            lines=source.read_text().splitlines(); start,end=RANGES[sid][0]
            excerpt='\n[...]\n'.join('\n'.join(lines[a-1:b]) for a,b in RANGES[sid])
            pages=re.findall(r'<!-- page (\d+) -->','\n'.join(lines[:start]))
            ev={'evidence_id':sid+'-EV980','source_file':str(source.relative_to(ROOT)),
                'source_type':'MAIN_TEXT','section':'Population and analysis scope (P079 source reread)',
                'pdf_page':int(pages[-1]) if pages else None,'printed_page':None,'object_label':None,
                'start_anchor':excerpt[:120],'end_anchor':excerpt[-120:],'excerpt':excerpt,
                'source_lines':[start,end],'source_line_ranges':[list(pair) for pair in RANGES[sid]],
                'interpretation_status':'NATIVE'}
            prior=next((e for e in d['evidence_registry'] if e['evidence_id']==ev['evidence_id']),None)
            assert prior is None or prior==ev, f'Anchor collision: {sid}'
            if prior is None:d['evidence_registry'].append(ev)
        old=json.dumps(record,ensure_ascii=False,sort_keys=True)
        if sid == 'KHM011':
            ev={'evidence_id':sid+'-EV981','source_file':'references/pdf/kim2024neural.pdf',
                'source_type':'MAIN_TEXT','section':'Results / Table 2','pdf_page':4,
                'printed_page':'339','object_label':'Table 2','table_row':'Model 2',
                'table_column':'Tertile 3 (>1.25 micrograms/L)',
                'start_anchor':'Model 2','end_anchor':'1.62 (1.38-1.92)',
                'excerpt':'Model 2: Tertile 1 1.00 (Reference); Tertile 2 1.32 (1.13-1.55); Tertile 3 1.62 (1.38-1.92); p for trend <0.001. The prose immediately above Table 2 instead reports OR 1.82 (95% CI 1.17-2.83).',
                'interpretation_status':'COMPLETE',
                'note':'Values and conflict directly checked on the rendered PDF page; original prose anchor EV036 retained.'}
            prior=next((e for e in d['evidence_registry'] if e['evidence_id']==ev['evidence_id']),None)
            assert prior is None or prior==ev
            if prior is None:d['evidence_registry'].append(ev)
        normalise_analysis_records(record)
        assert before==json.dumps(d['protocol_items'],ensure_ascii=False,sort_keys=True)
        if old!=json.dumps(record,ensure_ascii=False,sort_keys=True):changes.append(sid)
        path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
        addby[sid].update(record)
    addpath.write_text(json.dumps(add,ensure_ascii=False,indent=2)+'\n')
    merged=ROOT/'data/protocol_v1_2/KNHANES_studies_v1.2.jsonl'
    with merged.open('w') as handle:
        for path in sorted((ROOT/'data/protocol_v1_2/final').glob('*_final.json')):
            handle.write(json.dumps(json.loads(path.read_text()),ensure_ascii=False)+'\n')
    print('Post-core records updated:', ', '.join(changes))

if __name__=='__main__':main()
