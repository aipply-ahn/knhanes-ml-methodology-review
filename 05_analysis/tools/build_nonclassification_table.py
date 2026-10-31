#!/usr/bin/env python3
"""Build the main nonclassification table from adjudicated final JSON."""
import json, re, unicodedata
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"manuscript/submission/table_nonclassification.tex"
OUT_CONT=ROOT/"manuscript/submission/table_continuous_prediction.tex"
OUT_OTHER=ROOT/"manuscript/submission/table_other_tasks.tex"
def one(r,k): return r['protocol_items'][k][0]['value']
def flat(values):
    out=[]
    for x in values: out.extend(x if isinstance(x,list) else [x])
    return out
def ascii_text(x):
    x=unicodedata.normalize('NFKD',str(x)).encode('ascii','ignore').decode()
    x=re.sub(r'\s+',' ',x).strip()
    return x
def esc(x):
    x=ascii_text(x)
    for a,b in [('\\',r'\textbackslash{}'),('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#'),('$',r'\$'),('{',r'\{'),('}',r'\}')]: x=x.replace(a,b)
    return x
def compact(xs,n=4):
    xs=list(dict.fromkeys(esc(x) for x in xs if x and x!='NA'))
    return '; '.join(xs[:n])+((f'; +{len(xs)-n} more') if len(xs)>n else '') or 'Not reported'
records=[]
for p in sorted((ROOT/'data/protocol_v1_2/final').glob('KHM*_final.json')):
    r=json.loads(p.read_text()); inc=r.get('corpus_status',{}).get('include',one(r,'ELG04')=='Y')
    if inc and one(r,'TSK01') in ('CONT','OTHER'): records.append(r)
cont=[r for r in records if one(r,'TSK01')=='CONT']; other=[r for r in records if one(r,'TSK01')=='OTHER']
lines=[r'\begingroup',r'\scriptsize',r'\setstretch{1.0}',r'\setlength{\tabcolsep}{2pt}',
       r'\begin{longtable}{>{\RaggedRight\arraybackslash}p{0.12\textwidth}>{\RaggedRight\arraybackslash}p{0.22\textwidth}>{\RaggedRight\arraybackslash}p{0.30\textwidth}>{\RaggedRight\arraybackslash}p{0.28\textwidth}}',
       r'\caption{Task-specific synthesis of the 24 studies outside the primary classification cohort: 12 continuous-outcome prediction and 12 other primary tasks. Ancillary classifiers did not change primary-task assignment.}\label{tab:nonclassification}\\',
       r'\toprule',r'Study & Outcome or primary task & Models and validation & Evaluation and interpretation \\',r'\midrule',r'\endfirsthead',
       r'\multicolumn{4}{l}{\tablename\ \thetable\ (continued)}\\',r'\toprule',r'Study & Outcome or primary task & Models and validation & Evaluation and interpretation \\',r'\midrule',r'\endhead',
       r'\midrule\multicolumn{4}{r}{Continued on next page}\\',r'\endfoot',r'\bottomrule',r'\endlastfoot',
       r'\multicolumn{4}{l}{\textbf{Panel A. Continuous-outcome prediction ($n=12$)}}\\']
cont_rows=[]
for r in cont:
    models=compact([x.get('label') for x in r['units']['models']],3)
    validations=compact(flat([x['value'] for x in r['protocol_items']['VAL02']]),4)
    outcomes=compact([x.get('label') for x in r['units']['outcomes']],2)
    metrics=compact([x.get('metric') for x in r['performance_metrics']],8)
    imp='; explicit variable importance' if any(x['value']=='USED' for x in r['protocol_items']['VI01']) else ''
    retract='; retracted---corpus history only' if r.get('corpus_status',{}).get('exclude_from_valid_evidence') else ''
    study=f"{r['study_id']} ({r['metadata']['publication_year']})"
    row=f"{esc(study)} & {outcomes} & {models}; validation: {validations} & Metrics: {metrics}{imp}{retract} \\\\"
    cont_rows.append(row); lines.append(row)
lines += [r'\midrule',r'\multicolumn{4}{l}{\textbf{Panel B. Other primary analytic tasks ($n=12$)}}\\']
cats=Counter()
for r in other:
    codes=flat([x['value'] for x in r['protocol_items']['TSK11']])
    if 'IMPUTATION' in codes: cats['Missing-data imputation']+=1
    elif 'CLUSTERING' in codes or 'DATA_PROCESSING' in codes: cats['Clustering or topic discovery']+=1
    else: cats['Structural, causal, or representation learning']+=1
desc={
 'Missing-data imputation':('Reconstruction of actigraphy or survey responses','Masking design, reconstruction error, distribution preservation, and transport'),
 'Clustering or topic discovery':('Participant subgroup or dietary-pattern discovery','Stability, separation, sensitivity to specification, and replication'),
 'Structural, causal, or representation learning':('Dependence structure, causal meta-learning, or ordered representation','Identification assumptions, balance/overlap, structural stability, or representation validity')}
other_rows=[]
for cat in ('Missing-data imputation','Clustering or topic discovery','Structural, causal, or representation learning'):
    a,b=desc[cat]; row=f"{esc(cat)} & n={cats[cat]} & {esc(a)} & {esc(b)} \\\\"
    other_rows.append(row); lines.append(row)
lines += [r'\end{longtable}',r'\endgroup']
assert len(cont)==12 and len(other)==12 and sum(cats.values())==12
OUT.write_text('\n'.join(lines)+'\n')
def standalone(caption,label,headers,rows):
    return '\n'.join([r'\begingroup',r'\scriptsize',r'\setstretch{1.0}',r'\setlength{\tabcolsep}{2pt}',
      r'\begin{longtable}{>{\RaggedRight\arraybackslash}p{0.12\textwidth}>{\RaggedRight\arraybackslash}p{0.22\textwidth}>{\RaggedRight\arraybackslash}p{0.30\textwidth}>{\RaggedRight\arraybackslash}p{0.28\textwidth}}',
      f'\\caption{{{caption}}}\\label{{{label}}}\\\\',r'\toprule',headers+r' \\',r'\midrule',r'\endfirsthead',
      r'\multicolumn{4}{l}{\tablename\ \thetable\ (continued)}\\',r'\toprule',headers+r' \\',r'\midrule',r'\endhead',
      r'\midrule\multicolumn{4}{r}{Continued on next page}\\',r'\endfoot',r'\bottomrule',r'\endlastfoot']+rows+[r'\end{longtable}',r'\endgroup'])+'\n'
OUT_CONT.write_text(standalone('Continuous-outcome prediction studies ($n=12$). Retracted work is retained only as corpus history and excluded from valid performance evidence.','tab:continuous-prediction',r'Study & Outcome & Models and validation & Evaluation and interpretation',cont_rows))
OUT_OTHER.write_text(standalone('Other primary analytic tasks ($n=12$), summarised using task-appropriate evaluation criteria.','tab:other-tasks',r'Task group & Studies & Analytic purpose & Appropriate evaluation',other_rows))
print(f'Wrote split nonclassification tables: CONT={len(cont)}, OTHER={len(other)}')
