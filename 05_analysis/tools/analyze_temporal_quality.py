"""Analyse publication growth and methodological quality over publication periods."""
import glob,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from analyze_extraction import metric_depth,posthoc,validation,weights
from canonical_data import included_extractions
ROOT=Path(__file__).resolve().parents[1]
PERIODS=['≤2019','2020–2022','2023–2024','2025–2026']
def period(y):return '≤2019' if y<=2019 else '2020–2022' if y<=2022 else '2023–2024' if y<=2024 else '2025–2026'
def main():
 refs={r['key']:r for r in json.load(open(ROOT/'references/refs.json'))}
 prob=[]
 for p in glob.glob(str(ROOT/'data/probast/*.json')):
  d=json.load(open(p)); r=refs.get(d.get('key'))
  if r and r.get('verdict')=='INCLUDE':prob.append(d)
 ext=included_extractions()
 px=defaultdict(list); ex=defaultdict(list)
 for d in prob:px[period(int(refs[d['key']]['year']))].append(d)
 for d in ext:ex[period(int(refs[d['key']]['year']))].append(d)
 out={}; years=[];scores=[];years_ft=[];scores_ft=[]
 for p in PERIODS:
  ds=px[p]; es=ex[p]
  def score(d):
   v=list(d['tripod'].values());return 100*sum(x=='Y' for x in v)/sum(x!='NA' for x in v)
  sc=[score(d) for d in ds]; ft=[score(d) for d in ds if d['source']=='full_text']
  hd=[sum(d['probast'][x]['judgment']=='high' for x in ('D1','D2','D3','D4')) for d in ds]
  cal=external=wfit=0
  for d in es:
   t=' '.join(str(d.get(k) or '') for k in ('metrics','validation','findings','interpretability','notes'))
   cal+=metric_depth(d.get('metrics'))=='판별력 + 보정' or '보정 평가' in posthoc(t)
   external+='외부검증' in validation(d.get('validation'))
   wfit+=weights(d.get('survey_weights'))=='학습에 반영'
  item={}
  for name in ('missing_data','model_evaluation','limitations','code_availability','model_availability','sample_size_justification'):
   yes=sum(d['tripod'].get(name)=='Y' for d in ds); app=sum(d['tripod'].get(name)!='NA' for d in ds)
   item[name]={'yes':yes,'applicable':app,'pct':100*yes/app}
  out[p]={'n':len(ds),'n_fulltext':len(ft),
   'general_median':float(np.median(sc)),'general_q1':float(np.percentile(sc,25)),'general_q3':float(np.percentile(sc,75)),
   'fulltext_median':float(np.median(ft)),'fulltext_q1':float(np.percentile(ft,25)),'fulltext_q3':float(np.percentile(ft,75)),
   'high_domain_distribution':dict(Counter(map(str,hd))),
   'high_domains_median':float(np.median(hd)),'calibration_n':int(cal),'calibration_pct':100*cal/len(es),
   'external_n':int(external),'external_pct':100*external/len(es),'weights_fitting_n':int(wfit),'weights_fitting_pct':100*wfit/len(es),
   'items':item}
 for d in prob:
  y=int(refs[d['key']]['year']);v=list(d['tripod'].values());s=100*sum(x=='Y' for x in v)/sum(x!='NA' for x in v)
  years.append(y);scores.append(s)
  if d['source']=='full_text':years_ft.append(y);scores_ft.append(s)
 rho,pv=spearmanr(years,scores);rhoft,pft=spearmanr(years_ft,scores_ft)
 result={'periods':out,'spearman_all':{'rho':rho,'p':pv},'spearman_fulltext':{'rho':rhoft,'p':pft}}
 (ROOT/'results/derived/temporal_quality.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
