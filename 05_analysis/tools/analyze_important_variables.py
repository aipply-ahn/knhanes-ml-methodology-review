"""Standardise variable domains named in the current explicit-importance reports."""
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOMAINS={
 'Age':r'\bage\b|aging|연령|나이',
 'Adiposity/body size':r'\bBMI\b|obes|adipos|waist|weight|body fat|body mass|WHtR|WHR|비만|체중|허리둘레|체지방|신장|키',
 'Sex':r'\bsex\b|\bgender\b|female|male|성별|여성|남성',
 'Blood pressure/hypertension':r'blood pressure|hypertension|\bSBP\b|\bDBP\b|수축기|이완기|혈압|고혈압',
 'Glycaemia/diabetes/insulin':r'diabet|glucose|glyc|HbA1c|insulin|HOMA|TyG|당뇨|혈당|인슐린',
 'Lipids':r'cholesterol|triglycer|\bHDL\b|\bLDL\b|\bTG\b|lipid|콜레스테롤|중성지방|지질',
 'Kidney/urine':r'kidney|renal|eGFR|creatinine|albuminuria|urine|proteinuria|콩팥|신장질환|요단백|요혈|소변|크레아티닌',
 'Mental/subjective health':r'stress|depress|anxiety|suicid|self.?rated health|subjective health|quality of life|QoL|EQ-?5D|sleep|스트레스|우울|불안|자살|주관적 건강|삶의 질|수면',
 'Socioeconomic/context':r'income|education|occupation|employment|insurance|marital|residen|household|region|소득|교육|직업|경제활동|보험|결혼|거주|지역|가구',
 'Diet/nutrients':r'diet|nutrition|sodium|potassium|protein intake|energy intake|omega|food|water intake|식이|영양|나트륨|칼륨|단백질 섭취|에너지 섭취|오메가|식품|물 섭취',
 'Physical activity/function':r'physical activ|exercise|sedent|walking|mobility|grip|근력|신체활동|운동|좌식|보행|이동|악력',
 'Smoking':r'smok|tobacco|흡연',
 'Alcohol':r'alcohol|drink|AUDIT|음주|알코올',
 'Pain/musculoskeletal':r'pain|low back|joint|hip|knee|arthritis|통증|요통|관절|고관절|무릎',
 'Work/clinical history':r'working hours|work hours|past event|prior event|history of|근로시간|과거 악화|과거력|병력',
}
TOPICS={'mental_health':'Mental health','diabetes':'Diabetes','cvd':'Cardiovascular/HTN',
 'osteoporosis_sarcopenia':'Bone/muscle','metabolic_syndrome':'Metabolic syndrome',
 'obesity':'Obesity/body composition','oral_health':'Oral health','nutrition_diet':'Nutrition/diet',
 'ckd':'Kidney disease','qol_health_behavior':'QoL/health behaviour','hearing_vision':'Hearing/vision',
 'liver':'Liver','respiratory':'Respiratory','dyslipidemia':'Dyslipidaemia',
 'multimorbidity_general':'Multimorbidity','other':'Other'}

def main():
 with open(ROOT/'data/VARIABLE_IMPORTANCE_DETAILS.tsv',encoding='utf-8-sig') as f:
  src=list(csv.DictReader(f,delimiter='\t'))
 rows=[]
 for r in src:
  text=r['importance_result'].strip()
  generic=text.lower() in {'shap','feature importance','variable importance','lime','pdp'}
  hits=[d for d,p in DOMAINS.items() if re.search(p,text,re.I)] if not generic else []
  rows.append({'key':r['key'],'year':r['year'],'topic':r['topic'],'topic_label':TOPICS[r['topic']],
               'outcome':r['outcome'],'detail_recoverable':int(bool(hits)),
               'variable_domains':'; '.join(hits),'importance_result':text})
 with open(ROOT/'data/IMPORTANT_VARIABLE_DOMAINS.tsv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0],delimiter='\t'); w.writeheader(); w.writerows(rows)
 overall=Counter(); by=defaultdict(Counter); den=Counter(); explicit=Counter()
 for r in rows:
  explicit[r['topic_label']]+=1
  if r['detail_recoverable']:
   den[r['topic_label']]+=1
   for d in r['variable_domains'].split('; '): overall[d]+=1; by[r['topic_label']][d]+=1
 summary={'n':len(rows),'n_with_codable_variable_domains':sum(x['detail_recoverable'] for x in rows),
          'overall':dict(overall),'topic_explicit_n':dict(explicit),'topic_codable_n':dict(den),
          'by_topic':{t:dict(c) for t,c in by.items()}}
 (ROOT/'results/derived/important_variable_domains.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 lines=["# 변수 중요도 결과의 표준 변수군 코딩", "",
        f"명시적 중요도 방법을 사용한 {len(rows)}편을 대상으로 원문에 이름이 제시된 변수를 15개 넓은 변수군으로 코딩했다. 한 연구는 여러 변수군에 포함될 수 있으며, 방법명만 있거나 구체적 변수명이 없으면 미확인으로 남겼다.", "",
        "| 연구 | 연도 | 주제 | 목적변수 | 변수명 코딩 | 표준 변수군 | 중요도 결과 근거문 |",
        "|---|---:|---|---|---:|---|---|"]
 for r in rows:
  vals=[r['key'],r['year'],r['topic_label'],r['outcome'],r['detail_recoverable'],r['variable_domains'] or 'NR',r['importance_result']]
  lines.append('| '+' | '.join(str(v).replace('|','/') for v in vals)+' |')
 (ROOT/'manuscript/submission/appendices/appendix9b_important_variable_domains.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
