"""Readable scientific study assessments; detailed source records remain in S7."""
from collections import Counter
import json
import re

LABELS = {
 'HEALTH_FOCUSED':'Health-focused', 'METHOD_FOCUSED':'Method-focused',
 'CLASSIFICATION':'Classification', 'CONTINUOUS_OR_ORDERED_ESTIMATION':'Continuous/ordered estimation',
 'SPLIT':'Train/test split','CV':'Cross-validation','EXTERNAL':'External validation','TEMPORAL':'Later-period validation','BOOT':'Bootstrap','APPARENT':'Apparent evaluation','NONE_NR':'None/not reported unresolved',
 'CURRENT':'Current health state','CONCURRENT':'Current health state','FUTURE':'Future outcome',
 'UNC':'Unclear','UNCLEAR':'Unclear','NA':'Not applicable','NR':'Not reported',
 'USED':'Used','NOT_USED':'Not used','Y':'Yes','N':'No (recorded)',
 'R2':'Fully recoverable','R1':'Partly recoverable','R0':'Not recoverable',
}

def readable(value):
    if value is None:return 'Unextracted/null'
    if isinstance(value,list):return ' + '.join(readable(v) for v in value) if value else 'Empty response list'
    if isinstance(value,dict):return json.dumps(value,ensure_ascii=False)
    return '; '.join(LABELS.get(v.strip(),v.strip().replace('_',' ').capitalize()) for v in str(value).split('|'))

def support_label(value):
    return {'Y':'Criterion documented as met','N':'Criterion not documented as met'}.get(value,readable(value))

def participant_count(value):
    if value is None:return 'Unextracted/null'
    def atom(x):
        try:
            n=float(x)
            if n.is_integer():return f"{int(n):,}"
        except (ValueError,TypeError):pass
        return readable(x)
    return '; '.join(atom(x.strip()) for x in str(value).split('|'))

def response_unit(doc,item,records):
    spec={'OUT10':('outcomes','outcome_id','outcome'), 'OUT16':('outcomes','outcome_id','outcome'),
          'PRD13':('models','model_id','model'), 'PD_OVERALL':('developments','development_id','development unit'),
          'PE_OVERALL':('evaluations','evaluation_id','evaluation unit')}.get(item)
    if not spec:return 'response record'
    key,field,label=spec
    ids=[r.get('unit_id') for r in records]
    known={u.get(field) for u in doc.get('units',{}).get(key,[])}
    if all(ids) and len(ids)==len(set(ids)) and set(ids)<=known:return label
    return 'response record'

def responses(doc, item):
    records=doc.get('protocol_items',{}).get(item,[])
    if not records:return 'No response record (not extracted)'
    counts=Counter((json.dumps(r.get('value'),sort_keys=True),str(r.get('value_status'))) for r in records)
    unit=response_unit(doc,item,records)
    output=[]
    for (v,status),n in sorted(counts.items()):
        value=json.loads(v);label=readable(value)
        if item=='PD_OVERALL' and value in ('LOW','HIGH'):label=value.capitalize()+' quality'
        if item=='PE_OVERALL' and value in ('LOW','HIGH'):label=value.capitalize()+' risk'
        # ANSWERED is only a completion wrapper. Other states remain explicit.
        state='' if status in ('ANSWERED','REPORTED') else f' (status: {readable(status)})'
        output.append(f'{label}{state}: {n} {unit}{"s" if n!=1 else ""}')
    return '; '.join(output)

def evidence_ids(doc, items):
    return sorted({eid for item in items for r in doc.get('protocol_items',{}).get(item,[]) for eid in r.get('evidence_ids',[])})

def build_study_audit_table(docs, headers, rows, emit):
    master={r[0]:dict(zip(headers,r)) for r in rows}
    panels=[]
    groups=[
        ('A. Study scope and recoverability', ['Study / short citation','Orientation and task','Final cohort n (participants)','Outcome timing (OUT10)','Outcome / predictor recovery','Evidence and detailed records']),
        ('B. Validation, survey design and interpretation', ['Study / short citation','Validation design (VAL02)','Sampling weights: fitting / evaluation','Design uncertainty (SUR10)','Importance / stability (VI01 / VI16)','Evidence and detailed records']),
        ('C. Unit-specific appraisal and supporting evidence', ['Study / short citation','Development quality (PD_OVERALL)','Evaluation bias risk (PE_OVERALL)','Support: importance / association','Support: individual use / policy','Evidence and detailed records']),
    ]
    for panel,header in groups:
        result=[]
        for doc in sorted(docs,key=lambda d:d['study_id']):
            sid=doc['study_id'];m=master[sid]
            authors=doc.get('metadata',{}).get('authors','Not reported')
            first=(authors[0] if isinstance(authors,list) else str(authors).split(';')[0].split(',')[0])
            if re.search('[가-힣]',str(first)):
                first='DOI '+str(m['A_DOI']) if m['A_DOI'] not in (None,'NR') else {'KHM072':'Decision-tree study of sleep problems in cancer survivors'}.get(sid, 'Report '+sid)
            label=f"{sid}; {first} ({m['A_publication_year']})"
            if panel.startswith('A.'):
                items=['OUT10','OUT16','PRD13','POP09']
                vals=[f"{readable(m['B_primary_orientation'])}; {readable(m['B_analytic_task'])}",participant_count(m['D_final_sample']),responses(doc,'OUT10'),f"Outcomes: {responses(doc,'OUT16')}. Predictor sets: {responses(doc,'PRD13')}"]
            elif panel.startswith('B.'):
                items=['VAL02','SUR06','SUR07','SUR10','VI01','VI16']
                vals=[responses(doc,'VAL02'),f"Fitting: {responses(doc,'SUR06')}. Evaluation: {responses(doc,'SUR07')}",responses(doc,'SUR10'),f"Importance: {responses(doc,'VI01')}. Stability: {responses(doc,'VI16')}"]
            else:
                items=['PD_OVERALL','PE_OVERALL','VI16','SUR10','VAL02','MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R','THR01','SUR04','SUR08','SUR09']
                vals=[responses(doc,'PD_OVERALL'),responses(doc,'PE_OVERALL'),f"Importance: {support_label(m['M_importance_stability_support_criteria_met'])}. Association: {support_label(m['M_population_association_support_criteria_met'])}",f"Individual use: {support_label(m['M_individual_application_support_criteria_met'])}. Policy: {support_label(m['M_surveillance_policy_support_criteria_met'])}"]
            ids=[]
            for item in items:
                candidates=evidence_ids(doc,[item])
                if candidates:ids.append((item,candidates[0]))
            # A few locators provide a readable entry point, never a substitute for full evidence.
            loc='; '.join(f'{item}: {eid}' for item,eid in ids[:3]) if ids else 'No evidence ID in these item responses'
            detail=loc

            result.append([label,*vals,detail])
        panels.append((panel,header,result))
    from protocol_reader_keys import S9_NOTE
    note = S9_NOTE
    from make_streamlined_figures import CLS, reduce_recoverability, flat_values
    cross=[]
    for unit_item,study_item in [('OUT16','REP06'),('PRD13','REP07')]:
        tab=Counter((reduce_recoverability(d,unit_item),flat_values(d,study_item)[0]) for d in CLS)
        for grade in ['FULL','PART','NO']:
            ns=[tab[(grade,v)] for v in ['R','P','NR']]
            cross.append([f'{unit_item} / {study_item}',
                          {'FULL':'Fully recoverable','PART':'Partly recoverable','NO':'Not recoverable'}[grade],
                          *ns,sum(ns)])
    panels.append(('D. Descriptive comparison of distinct constructs (core cohort)',
                   ['Unit item / study item','Least recoverable observed outcome/model','Study: reported completely','Study: partially reported','Study: not reported','Studies in row'],cross))

    from pathlib import Path
    reassessment=json.loads((Path(__file__).resolve().parents[1]/'data/protocol_v1_3/judgement_reassessment.json').read_text())
    panels.append(('E. Bounded source checks and unresolved judgements',reassessment['columns'],reassessment['rows']))
    emit(8,'Study_protocol_audit_results','Recorded protocol-based assessments of the included studies',
         panels,[40,47,39,44,61,45],note,font_size=8.5)
