"""Separate survey-year span from the operation performed on multiple years."""
import csv, glob, json, re
from collections import Counter
from pathlib import Path
from canonical_data import included_extractions

ROOT=Path(__file__).resolve().parents[1]
REF={r['key']:r for r in json.load(open(ROOT/'references/refs.json'))}

SEPARATED={
    'chung2014screening': 'KNHANES 2010 was used for development/internal validation and 2011 only for evaluation.',
    'kim2024predictiona': 'KNHANES 2015 was used for development; 2010 and 2011 were retained as separate validation sets.',
    'shim2020application': 'KNHANES 2010 was used for training and 2011 only for testing.',
}

def years(v):
    return sorted({int(x) for x in re.findall(r'(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)',str(v or '')) if 1998<=int(x)<=2026})

def cycle(y):
    for a,b,n in [(1998,2000,1),(2001,2004,2),(2005,2006,3),(2007,2009,4),(2010,2012,5),(2013,2015,6),(2016,2018,7),(2019,2021,8),(2022,2024,9),(2025,2027,10)]:
        if a<=y<=b:return n

def span(d):
    ys=years(d.get('knhanes_waves'))
    if not ys:return 'Unclear'
    if len(ys)==1:return 'Single year'
    return 'Multiple years, same cycle' if len({cycle(y) for y in ys})==1 else 'Multiple years, across cycles'

def weight(d):
    s=' '.join(str(d.get(k) or '') for k in ['survey_weights','notes'])
    if re.search(r'integrated weight|combined weight|통합가중|연도.*가중.{0,20}(나누|조정)|가중치.{0,30}(통합|결합)',s,re.I):
        return 'Described'
    return 'Not described'

def main():
    rows=[]
    for d in included_extractions():
        key=d['key']
        sp=span(d)
        if sp=='Single year': op='Not applicable'; basis='One survey year stated'; cw='Not applicable'
        elif sp=='Unclear': op='Unclear'; basis='Survey years were not recoverable'; cw='Not applicable'
        elif key in SEPARATED: op='Development/evaluation separation'; basis=SEPARATED[key]; cw='Not applicable'
        else:
            op='Actual pooled multi-year analysis'
            basis='Evidence-assisted inference: one analytic cohort was constructed across the stated survey years; no year-exclusive development/evaluation allocation was reported.'
            cw=weight(d)
        rows.append({'key':key,'survey_years_reported':d.get('knhanes_waves') or '',
                     'survey_year_span':sp,'pooling_operation':op,
                     'pooling_basis':basis,'combined_weight_reporting':cw,
                     'weight_evidence':d.get('survey_weights') or ''})
    rows.sort(key=lambda x:x['key'])
    with open(ROOT/'data/POOLING_OPERATION_AUDIT.tsv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
    c1=Counter(r['survey_year_span'] for r in rows);c2=Counter(r['pooling_operation'] for r in rows)
    pooled=[r for r in rows if r['pooling_operation']=='Actual pooled multi-year analysis']
    c3=Counter(r['combined_weight_reporting'] for r in pooled)
    result={'n_included':len(rows),'survey_year_span':dict(c1),'pooling_operation':dict(c2),
            'combined_weight_reporting_among_actual_pooled':dict(c3),
            'n_actual_pooled':len(pooled),
            'definition':'Actual pooling denotes construction of at least one analytic cohort from multiple survey years. Year-exclusive development/evaluation use is separated. Inference-based codes require independent verification.'}
    (ROOT/'results/derived/pooling_operations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
