"""Independent reconstruction from public scalar sheets, not raw JSON or shared reducer."""
from pathlib import Path
from collections import defaultdict, Counter
import json, re
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/cycle_083'

def reconstruct():
    w=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
    def rows(name):
        it=iter(w[name].values);h=next(it)
        for row in it:yield dict(zip(h,row))
    study={r['A_study_id']:r for r in rows('STUDIES')}
    ids=sorted(s for s,r in study.items() if r['B_core_health_classification']=='Y')
    units={(r['study_id'],r['evaluation_id']):r for r in rows('EVALUATIONS')}
    continuations=defaultdict(list)
    for r in rows('TEXT_CONTINUATIONS'):continuations[r['cell_ref']].append((r['part_index'],r['text']))
    def restore(v):
        m=re.search(r'cell_ref=([^\]]+)\]',str(v or ''))
        return ''.join(t for _,t in sorted(continuations[m[1]])) if m else v
    items=defaultdict(lambda:defaultdict(list))
    wanted={'THR01','THR03','IMB05','VAL10','IMB04','PRE01','IMB01','VAL02','MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R'}
    for r in rows('ITEM_RESPONSES'):
        if r['item_id'] in wanted:
            r={k:restore(v) for k,v in r.items()};items[r['study_id']][r['item_id']].append(r)
    positive={'FIXED05','YOUDEN','VAL_OOF','F1','CLINICAL','OTHER'}
    def state(rs,yes,partial=set(),no={'NR','N','NOT_USED'}):
        vals={r['final_value'] for r in rs}
        if vals & yes:return 'Y'
        if vals & partial:return 'P'
        if not vals or vals-yes-partial-no-{'NA'}:return 'UNCLEAR'
        return 'NR' if vals & no else 'NA'
    def links(r):
        return dict(line.split(': ',1) for line in str(r.get('related_ids','')).splitlines() if ': ' in line)
    by={};all_flags={}
    for sid,its in items.items():
        all_flags[sid]={'Y':'Y','NR':'N','UNCLEAR':'UNCLEAR','NA':'NA'}[state(its['THR01'],positive)]
        if sid not in ids:continue
        linked=[]
        for r in its['THR03']:
            uid=r['unit_id'];u=units.get((sid,uid))
            if r['final_value']!='USED' or not u or r['primary_unit']!='Evaluation':continue
            for t in its['THR01']:
                if t['unit_id']!=uid or t['final_value'] not in positive or t['primary_unit']!='Evaluation':continue
                anchors=[u,links(r),links(t)]
                if all(len({a[k] for a in anchors if a.get(k) and a[k] not in ('NR','(null)')})<=1 for k in ['model_id','outcome_id','dataset_id']):linked.append(uid)
        ns=[r['final_value'] for r in its['VAL10']]
        n_ok=any(re.fullmatch(r'[0-9]+(?:\.0+)?',str(v)) and float(v)>0 for v in ns)
        by[sid]={'decision_rule':state(its['THR01'],positive),'independent_units':sorted(set(linked)),
                 'class_distribution':state(its['IMB05'],{'R'},{'P'}),'sample_size':bool(n_ok),
                 'original_prevalence':state(its['IMB04'],{'ORIGINAL'},no={'ALTERED','NR'})}
    members={k:[] for k in ['threshold_reported','threshold_independent','class_distribution','sample_size','original_prevalence']}
    for sid,r in by.items():
        flags=[r['decision_rule']=='Y',bool(r['independent_units']),r['class_distribution']=='Y',r['sample_size'],r['original_prevalence']=='Y']
        for k,flag in zip(members,flags):
            if flag:members[k].append(sid)
    members={k:sorted(v) for k,v in members.items()}
    denominators={k:ids for k in members};denominators['threshold_independent']=members['threshold_reported']
    fig=json.loads((ROOT/'results/derived/study_reporting_summary.json').read_text())
    assert by==fig['by_study'] and members==fig['members'] and denominators==fig['denominators']
    assert all(study[s]['H_threshold_reported']==v for s,v in all_flags.items())
    # Co-occurrence of Figure 11 components, deliberately no evaluation join.
    codes={'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}
    eligible=[s for s in ids if {v.strip() for v in str(study[s]['B_proposed_uses']).split('|')} & codes]
    def vals(s,k):return {v for r in items[s][k] for v in str(r['final_value']).splitlines()}
    components={s:[bool(vals(s,'VAL02') & {'EXTERNAL','TEMPORAL'}),any('R' in vals(s,k) for k in ['MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R']),bool(vals(s,'THR01') & positive)] for s in eligible}
    counts=[sum(v[i] for v in components.values()) for i in range(3)]
    all_three=sorted(s for s,v in components.items() if all(v))
    assert len(eligible)==48 and counts==[18,9,23] and all_three==['KHM002','KHM033','KHM087','KHM089','KHM178']
    report={'status':'PASS','source':'Public S7 STUDIES, ITEM_RESPONSES, EVALUATIONS, TEXT_CONTINUATIONS only; no SOURCE_JSON/raw records/shared reporting helper.',
            'by_study':by,'members':members,'denominators':denominators,'decision_states':dict(Counter(r['decision_rule'] for r in by.values())),
            'all_220_threshold_flags':all_flags,'figure11':{'eligible_ids':sorted(eligible),'components':counts,'all_three_ids':all_three}}
    (OUT/'public_reconstruction.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS public reconstruction', {k:len(v) for k,v in members.items()})
    return report
if __name__=='__main__':reconstruct()
