"""Audit outcome construction and class structure in classifier-process studies."""
import csv,json,re,subprocess
from collections import Counter
from pathlib import Path
from canonical_data import included_extraction_index

ROOT=Path(__file__).resolve().parents[1]
REF={r['key']:r for r in json.load(open(ROOT/'references/refs.json'))}
MR=json.load(open(ROOT/'results/derived/ml_rationale.json'))['per_study']

BOTH={'zhang2026online','kim2021deepa','lee2025deep'}
MULTI_K={'dashdondov2023deep':'3','byeon2024predicting':'NR','vallathan2025feature':'3'}
# Studies with clearly separate yes/no endpoints rather than a single multiclass target.
MULTIPLE_BINARY={'zhang2024machine','park2025development','jung2024four','kim2021classification',
                 'seo2025contribution','lee2021risk','choi2024explainable','yoo2016simple',
                 'heo2018prediction','choi2024application','choi2025automated','joo2022misperception',
                 'choi2021identification','kim2025employing'}

CLINICAL=r'WHO|IOM|Institute of Medicine|AWGS|NCEP|ATP\s*III|ACC/AHA|pooled cohort|대한(?:당뇨|신장)|한국비만학회|KDCA|CKD-EPI|FNIH|ETDRS|Kellgren|K-L|CPI|community periodontal|clinical|임상|진단 기준|지침|권고|AHA/NHLBI|ADA'
SCALE=r'PHQ-?9|AUDIT|EQ-?5D|HINT-?8|GAD-?7|CIDI|도구|척도|instrument|questionnaire score'
REFERENCE=r'백분위|percentile|reference population|참고치|선행연구|문헌|Eriksen|published cutoff'
DATA_DRIVEN=r'상위\s*(?:1/3|1/4|삼분|사분)|quartile|tertile|median split|sample median|Youden|ROC.{0,30}(?:cut|threshold)|optimal cut|자료.{0,20}(?:분포|백분위)'
THRESH=r'(?:≥|≤|>|<|=)\s*-?\d|\d\s*(?:점|mg/dL|mmHg|kg/m²|kg/m2|cm|%|백분위)|cut.?off\s*-?\d|컷오프\s*-?\d|threshold|절단점|기준'
CONT=r'BMI|PHQ|AUDIT|EQ-?5D|HINT-?8|HbA1c|공복혈|FPG|glucose|SBP|DBP|혈압|25\s*\(?OH\)?D3?|vitamin\s*D|비타민\s*D|T-score|BMD|DXA|ASM|ASMI|악력|eGFR|uACR|albumin/creatinine|HOMA|TyG|AIP|cholesterol|콜레스테롤|TG|HDL|LDL|허리둘레|waist|dft|CPI|Kellgren|stress|스트레스|삶의 질|QoL|quality of life|ASCVD|위험점수|risk score'


def compact(x): return re.sub(r'\s+',' ',str(x or '')).strip()

def titlelike(text,title):
 return compact(text).lower().rstrip(',.')==compact(title).lower().rstrip(',.') or (not re.search('[가-힣]',text) and len(text)<180)

def best_pdf_excerpt(key,title):
 pdf=ROOT/'references/pdf'/f'{key}.pdf'
 if not pdf.exists(): return ''
 txt=subprocess.run(['pdftotext','-layout',str(pdf),'-'],capture_output=True,text=True).stdout
 chunks=[compact(x) for x in re.split(r'\n\s*\n',txt) if compact(x)]
 words=[w for w in re.findall(r'[A-Za-z가-힣]{4,}',title) if w.lower() not in {'using','machine','learning','model','analysis','prediction','based','korean','national','health'}]
 cues=re.compile(r'dependent variable|primary outcome|target variable|response variable|was defined as|were defined as|cut.?off|threshold|종속변수|결과변수|목적변수|로 정의|진단기준|유무|여부',re.I)
 def score(c):
  return 4*bool(cues.search(c))+3*bool(re.search(THRESH,c,re.I))+sum(w.lower() in c.lower() for w in words[:8])-0.001*len(c)
 cand=sorted((c for c in chunks if not re.search(r'\bReferences\b|참고문헌',c,re.I)),key=score,reverse=True)
 return compact(cand[0])[:1000] if cand and cues.search(cand[0]) and score(cand[0])>=6 else ''

def main():
 rows=[]
 ext_index=included_extraction_index()
 for rec in MR:
  key=rec['key']
  if key not in ext_index: continue
  x=ext_index[key]
  if x.get('task')!='classification': continue
  ref=REF[key]
  af=(rec.get('analytic_function') or {}).get('prediction_or_classification')
  source=compact(af or x.get('problem'))
  tl=titlelike(source,ref['title'])
  pdf_excerpt=best_pdf_excerpt(key,ref['title']) if rec['full_text'] and tl else ''
  evidence=source if not tl else (pdf_excerpt or source)
  low=evidence.lower()
  explicitly_missing=bool(re.search(r'정의.{0,20}미기재|기준.{0,20}미기재|세부 정의 미기재|not reported|unreported',evidence,re.I)) or key=='byeon2024predicting'

  if re.search(r'4범주|5단계|Zone I|normal\s*/\s*pre|정상/골감소증|극단군|ordinal categor',evidence,re.I): construction='Ordinal categories collapsed or retained'
  elif re.search(r'중 하나|하나 이상|\d+개 이상|동시에 충족|복합|composite|AND| OR | 또는 ',evidence,re.I) and re.search(CONT,evidence,re.I): construction='Composite clinical rule'
  elif re.search(CONT,evidence,re.I) and re.search(THRESH,evidence,re.I): construction='Continuous/score variable discretised'
  elif re.search(r"자가보고|의사진단|설문|yes.?/?.?no|예.?/?.?아니오|에\s*['\"]?예['\"]?|유무|여부|판독|diagnos|\bICD-?10\b|\bcase\b.{0,20}\bcontrol\b|경험자|시도자|대조군|\d+회 이상|로 분류",evidence,re.I): construction='Existing categorical response/diagnosis'
  else: construction='Construction not recoverable'

  definition='Recoverable' if construction!='Construction not recoverable' and not explicitly_missing else 'Not recoverable'
  if key in BOTH: scheme='Both binary and multiclass'; k='2 and 3' if key=='zhang2026online' else '2 and 4'
  elif key in MULTI_K: scheme='Multiclass only'; k=MULTI_K[key]
  elif key in MULTIPLE_BINARY: scheme='Multiple binary endpoints'; k='2 per endpoint'
  elif re.search(r'이분|binary|yes.?/?.?no|예.?/?.?아니오|유무|여부| vs |0\s*=|1\s*=|있음|없음|초과|미만|이상|이하|유병|판별|고위험|저위험',evidence,re.I): scheme='Binary only'; k='2'
  elif definition=='Recoverable' and construction in {'Continuous/score variable discretised','Composite clinical rule','Existing categorical response/diagnosis'}: scheme='Binary only'; k='2'
  else: scheme='Class count not recoverable'; k='NR'

  if construction in {'Continuous/score variable discretised','Composite clinical rule','Ordinal categories collapsed or retained'}:
   cutoff='Reported' if re.search(THRESH,evidence,re.I) and not explicitly_missing else 'Not recoverable'
   if re.search(CLINICAL,evidence,re.I): basis='Clinical guideline/diagnostic standard'
   elif re.search(SCALE,evidence,re.I): basis='Validated scale or instrument convention'
   elif re.search(REFERENCE,evidence,re.I): basis='Reference population or prior literature'
   elif re.search(DATA_DRIVEN,evidence,re.I): basis='Data-driven distribution or optimisation'
   elif cutoff=='Reported': basis='Numeric rule reported; rationale not stated'
   else: basis='Basis not recoverable'
  else:
   cutoff='Not applicable' if construction=='Existing categorical response/diagnosis' else 'Not recoverable'
   basis='Survey/clinical categorical ascertainment' if construction=='Existing categorical response/diagnosis' else 'Basis not recoverable'

  # The stress paper names three score ranges (low/moderate/high) but leaves both
  # thresholds as symbolic T1/T2 and never defines the underlying stress score.
  # Generic keyword rules otherwise mistake the words "threshold" and "clinical"
  # for a reported, clinically justified binary cutoff.
  if key == 'vallathan2025feature':
   evidence=source
   definition='Not recoverable'
   construction='Continuous/score variable discretised'
   cutoff='Not recoverable'
   basis='Basis not recoverable'
   scheme='Multiclass only'
   k='3'

  # Manually adjudicated edge cases newly entering the classifier-process cohort.
  # These overrides preserve the distinction between a fitted classifier and a
  # sufficiently reported clinical outcome definition.
  if key == 'anon2018hybrid':
   evidence=source
   definition='Recoverable'
   construction='Existing categorical response/diagnosis'
   cutoff='Not applicable'
   basis='Survey/clinical categorical ascertainment'
   scheme='Binary only'
   k='2'
  elif key in {'kim2020optimized','shon2022machine'}:
   evidence=source
   definition='Not recoverable'
   construction='Existing categorical response/diagnosis'
   cutoff='Not applicable'
   basis='Survey/clinical categorical ascertainment'
   scheme='Binary only'
   k='2'
  elif key == 'son2022performance':
   evidence=source
   definition='Recoverable'
   construction='Ordinal categories collapsed or retained'
   cutoff='Not applicable'
   basis='Survey/clinical categorical ascertainment'
   scheme='Multiclass only'
   k='5'
  elif key == 'lee2025deep':
   evidence=source
   definition='Recoverable'
   construction='Ordinal categories collapsed or retained'
   cutoff='Not applicable'
   basis='Clinical guideline/diagnostic standard'
   scheme='Both binary and multiclass'
   k='2 and 4'
  elif key == 'dashdondov2021mahalanobis':
   evidence=source
   definition='Recoverable'
   construction='Composite clinical rule'
   cutoff='Reported'
   basis='Numeric rule reported; rationale not stated'
   scheme='Multiclass only'
   k='3'
  elif key == 'amarbayasgalan2022variational':
   evidence=source
   definition='Recoverable'
   construction='Composite clinical rule'
   cutoff='Reported'
   basis='Reference population or prior literature'
   scheme='Binary only'
   k='2'

  outcome=compact(ref.get('outcome') or ref['title'])
  rows.append(dict(key=key,year=ref['year'],topic=ref.get('category',''),outcome=outcome,
                   outcome_definition=evidence,full_text=rec['full_text'],definition_status=definition,
                   outcome_construction=construction,cutoff_reported=cutoff,cutoff_basis=basis,
                   classification_scheme=scheme,n_classes=k,source_text=source,
                   pdf_excerpt_used=bool(pdf_excerpt)))

 rows.sort(key=lambda r:(r['topic'],-int(r['year']),r['key']))
 out=ROOT/'data/TARGET_DEFINITION_AUDIT.tsv'
 with out.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys(),delimiter='\t');w.writeheader();w.writerows(rows)
 counters={name:Counter(r[name] for r in rows) for name in ['definition_status','outcome_construction','cutoff_reported','cutoff_basis','classification_scheme']}
 cont=[r for r in rows if r['outcome_construction'] in {'Continuous/score variable discretised','Composite clinical rule','Ordinal categories collapsed or retained'}]
 summary={'n':len(rows),'n_threshold_relevant':len(cont),'counters':{k:dict(v) for k,v in counters.items()},'threshold_basis':dict(Counter(r['cutoff_basis'] for r in cont))}
 (ROOT/'results/derived/target_definition_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 md=['# 분류 연구 목적변수·이산화·클래스 감사','',f'분류 연구 {len(rows)}편. 연속 측정값, 점수, 복합 임상기준 또는 순서범주를 분류 결과로 변환한 연구는 {len(cont)}편이었다.','', '## 집계','']
 for name,c in counters.items():
  md.append(f'### {name}');md.extend(f'- {k}: {v}' for k,v in c.items());md.append('')
 md += ['## 연구별 상세','', '| 연구 | 주제 | 목적변수 | 구성 | 절단값 | 근거 | 분류형태 | 클래스 | 근거문 |','|---|---|---|---|---|---|---|---:|---|']
 for r in rows:
  ev=r['outcome_definition'][:280].replace('|','/');md.append(f"| {r['key']} ({r['year']}) | {r['topic']} | {r['outcome'][:80]} | {r['outcome_construction']} | {r['cutoff_reported']} | {r['cutoff_basis']} | {r['classification_scheme']} | {r['n_classes']} | {ev} |")
 rendered='\n'.join(md)+'\n'
 (ROOT/'data/TARGET_DEFINITION_AUDIT.md').write_text(rendered)
 (ROOT/'manuscript/submission/appendices/appendix10_target_definitions.md').write_text(rendered)
 print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
