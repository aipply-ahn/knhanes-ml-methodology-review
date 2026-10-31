"""KCI native search census and public PDF retrieval for KNHANES × ML.
Run: python tools/census_kci.py search | fetch
Uses KCI KEYALL searches, no date or language restrictions.
Stores a separate audit corpus; does not change the main review decisions.
"""
import concurrent.futures as cf, datetime, hashlib, json, math, pathlib, re, sys, time
import requests
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'results/raw/kci_20260905'; RAW.mkdir(exist_ok=True)
LOG=ROOT/'references/_logs/kci_20260905'; LOG.mkdir(exist_ok=True)
BASE='https://www.kci.go.kr'
SEARCH=BASE+'/kciportal/po/search/poArtiSearList.kci'
DATASETS=['국민건강영양조사','KNHANES','국민건강 영양조사','National Health and Nutrition Examination Survey','국건영','국민건강·영양조사','KNHNAES']
METHODS=['머신러닝','기계학습','기계 학습','machine learning','딥러닝','deep learning','데이터마이닝','data mining','신경망','neural network','인공지능','artificial intelligence','랜덤 포레스트','random forest','XGBoost','부스팅','서포트 벡터','support vector','의사결정나무','의사결정트리','decision tree','군집','clustering','잠재계층','잠재프로파일','LASSO','elastic net','AutoML','SHAP','머신 러닝','딥 러닝','인공 신경망','SVM','LightGBM','AdaBoost','CatBoost','k-means','KNN','CHAID','CART','다층 퍼셉트론','연관규칙','association rule']
def dump(x,p):p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
def get(session,u,**kw):
 for n in range(2):
  try:
   r=session.get(u,timeout=30,**kw);r.raise_for_status();return r
  except Exception:
   if n:raise
   time.sleep(1)
def search_one(pair):
 dataset,method=pair;slug=hashlib.sha256((dataset+' AND '+method).encode()).hexdigest()[:16]
 p={'poSearchBean.conditionList':'KEYALL','poSearchBean.keywordList':dataset,'poSearchBean.refineOperationList':'AND','poSearchBean.refineConditionList':'KEYALL','poSearchBean.refineKeywordList':method,'poSearchBean.docsCount':'50','poSearchBean.startPg':'1'}
 result={'dataset':dataset,'method':method,'params':p.copy(),'records':[],'pages':[]};s=requests.Session()
 try:
  page=1;total=None
  while total is None or page<=math.ceil(total/50):
   p['poSearchBean.startPg']=str(page);file=RAW/f'search_{slug}_{page}.html'
   if file.exists():html=file.read_text()
   else:
    html=get(s,SEARCH,params=p).text;file.write_text(html)
   soup=BeautifulSoup(html,'html.parser');count=soup.find('input',{'name':'allCnt'})
   if count is None:raise ValueError('No result count (unexpected search response)')
   total=int(count['value']);result['total_reported']=total
   if total>2000:raise ValueError('Unexpected broad query: check AND parameters')
   found=[]
   for a in soup.select('a.subject'):
    tr=a.find_parent('tr');fields={x.get('name'):x.get('value','') for x in tr.find_all('input')};aid=re.search(r'ART\d+',a['href']).group()
    found.append({'kci_id':aid,'title':fields.get('R_INDE_TITL') or a.get_text(' ',strip=True),'author':fields.get('b','').removeprefix('저자 : '),'journal':fields.get('R_SERE_NM'),'pub_ym':fields.get('R_PUBI_DT'),'volume':fields.get('R_VOL'),'issue':fields.get('R_ISSE'),'pages':fields.get('f'),'kci_status':tr.select_one('.s-state-type-ico').get_text(strip=True) if tr.select_one('.s-state-type-ico') else None,'url':BASE+a['href']})
   result['records']+=found;result['pages'].append({'page':page,'n':len(found),'html':str(file.relative_to(ROOT))})
   if total and not found:raise ValueError('Empty page before advertised end')
   page+=1
  assert len(result['records'])==total,(len(result['records']),total)
 except Exception as e:result['error']=str(e)
 dump(result,RAW/f'query_{slug}.json');print(dataset,method,result.get('total_reported'),result.get('error',''),flush=True);return result

def search():
 with cf.ThreadPoolExecutor(max_workers=3) as ex:queries=list(ex.map(search_one,[(d,m) for d in DATASETS for m in METHODS]))
 records={}
 for q in queries:
  for r in q['records']:
   records.setdefault(r['kci_id'],dict(r,search_matches=[]))['search_matches'].append({'dataset':q['dataset'],'method':q['method']})
 dump({'searched_on':datetime.datetime.now().isoformat(),'endpoint':SEARCH,'datasets':DATASETS,'methods':METHODS,'query_count':len(queries),'failed_queries':[{'dataset':q['dataset'],'method':q['method'],'error':q['error']} for q in queries if q.get('error')],'n_unique':len(records),'records':list(records.values())},RAW/'census.json')
 print('Unique',len(records),'failed',sum('error' in q for q in queries),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='search':search()


def detail_one(row):
 aid=row['kci_id'];fp=RAW/(aid+'.html');s=requests.Session();r=dict(row);r['attempts']=[]
 def fetch_url(u,referer=None):
  try:
   z=get(s,u,headers={'Referer':referer} if referer else {});r['attempts'].append({'url':u,'status':z.status_code,'final_url':z.url,'bytes':len(z.content)});return z
  except Exception as e:r['attempts'].append({'url':u,'error':str(e)});return None
 z=fetch_url(r['url'])
 if z is None:r['error']='KCI detail retrieval failed';dump(r,LOG/(aid+'.json'));return r
 fp.write_text(z.text);soup=BeautifulSoup(z.text,'html.parser')
 def meta(name):
  tag=soup.find('meta',{'name':name});return tag.get('content') if tag else None
 def node(sel):
  t=soup.select_one(sel);return t.get_text(' ',strip=True) if t else ''
 r.update(title_en=meta('citation_title'),doi=meta('citation_doi'),language=meta('citation_language'),authors=[x.get('content') for x in soup.find_all('meta',{'name':'citation_author'})],abstract_ko=node('#korAbst'),abstract_en=node('#engAbst'),keywords=meta('citation_keywords'))
 if r.get('doi'):r['doi']=re.sub(r'^https?://(?:dx\.)?doi\.org/','',r['doi'],flags=re.I).lower()
 r['year']=int(meta('citation_publication_date')[:4]) if (meta('citation_publication_date') or '')[:4].isdigit() else None
 import unicodedata
 def norm(t):return ''.join(c for c in unicodedata.normalize('NFKC',t or '').lower() if c.isalnum())
 main=json.loads((ROOT/'references/refs.json').read_text());match=next((x for x in main if r.get('doi') and (x.get('doi') or '').lower()==r['doi']),None)
 if match is None:match=next((x for x in main if len(norm(x.get('title')))>25 and norm(x.get('title')) in [norm(r['title']),norm(r.get('title_en'))]),None)
 r['existing_key']=match['key'] if match else None;r['existing_verdict']=match.get('verdict') if match else None
 if match:r['key']=match['key']
 else:
  from common import bibkey
  r['key']=bibkey((r.get('authors') or ['anon'])[0],r.get('year'),r.get('title_en') or r['title'])
  if r['key'].startswith('anon') or r['key'].endswith('manuscript') or any(x['key']==r['key'] for x in main):r['key']='kci'+str(r.get('year') or 'nd')+aid.lower()
 # Acquisition-stage candidates: preserve all search hits, and do not treat this as final eligibility.
 r['screening_status']='CANDIDATE'
 text=' '.join(r.get(k) or '' for k in ['title','title_en','abstract_ko','abstract_en','keywords'])
 r['knhanes_evidence']=bool(re.search(r'국민[\s·⋅]*건강[\s·⋅]*영양[\s·⋅]*조사|국건영|KNHANES|KNHNAES|Korea[n]? National Health|Korea Disease Control|Survey in Korea',text,re.I))
 if row.get('scope_override'):r['knhanes_evidence']=True;r['scope_override']=row['scope_override']
 if not r['knhanes_evidence']:r['screening_status']='DATASET_UNCONFIRMED'
 r['ml_term_evidence']=bool(re.search(r'머신\s*러닝|기계\s*학습|딥\s*러닝|데이터\s*마이닝|인공\s*지능|신경망|랜덤\s*포레스트|서포트\s*벡터|의사\s*결정\s*(?:나무|트리)|군집\s*분석|잠재\s*(?:계층|프로파일)|연관\s*규칙|machine[ -]learning|deep[ -]learning|data[ -]mining|neural[ -]network|random[ -]forest|boost|support[ -]vector|decision[ -]tree|cluster(?:ing)?[ -]analysis|latent[ -](?:class|profile)|lasso|elastic[ -]net|AutoML|SHAP|CatBoost|XGBoost|association[ -]rules?|k[ -]means|\b(?:CART|CHAID|SVM|KNN)\b',text,re.I))
 r['pdf_file']=None
 if match and match.get('pdf_file') and (ROOT/'references/pdf'/match['pdf_file']).exists():
  r.update(pdf_file=match['pdf_file'],pdf_src=match.get('pdf_src'),acquisition='ALREADY_PRESENT');dump(r,LOG/(aid+'.json'));print(aid,'existing',r['key'],flush=True);return r
 if not r['knhanes_evidence'] or not r['ml_term_evidence']:
  r['screening_status']='DATASET_UNCONFIRMED' if not r['knhanes_evidence'] else 'NO_ML_IN_TITLE_ABSTRACT'
  r['acquisition']='NOT_ATTEMPTED_SCOPE_UNCONFIRMED';dump(r,LOG/(aid+'.json'));return r
 candidates=[]
 for a in soup.find_all('a'):
  onclick=a.get('onclick','');m=re.search(r"fncDown\('([^']+)'",onclick)
  if m:
   candidates.append(BASE+'/kciportal/ci/sereArticleSearch/ciSereArtiOrteServHistIFrame.kci?sereArticleSearchBean.artiId='+aid+'&sereArticleSearchBean.orteFileId='+m.group(1))
 if r.get('doi'):candidates.append('https://doi.org/'+r['doi'])
 # Publisher/full text links exposed by KCI, excluding references and citation export.
 for a in soup.select('.report-detail-right a, .report-detail-left a'):
  h=a.get('href','')
  if h.startswith('http') and not any(x in h for x in ['kci.go.kr','orcid.org']):candidates.append(h)
 seen=set()
 import fitz,urllib.parse
 for u in candidates:
  if not u or u in seen or len(seen)>=12:continue
  seen.add(u);z=fetch_url(u,r['url'])
  if z is None:continue
  if z.content.startswith(b'%PDF-'):
   try:
    doc=fitz.open(stream=z.content,filetype='pdf');first=''.join(pg.get_text() for pg in list(doc)[:3]);full=''.join(pg.get_text() for pg in doc)
    title_ok=any(len(norm(t))>20 and norm(t)[:60] in norm(first) for t in [r['title'],r.get('title_en')])
    doi_ok=bool(r.get('doi') and norm(r['doi']) in norm(first))
    if not (title_ok or doi_ok):
     r['attempts'][-1]['validation']='PDF_IDENTITY_UNCONFIRMED';(LOG/(aid+'_unconfirmed.pdf')).write_bytes(z.content);continue
    dst=ROOT/'references/pdf'/(r['key']+'.pdf')
    if dst.exists():
     if dst.read_bytes()!=z.content:r['key']+='_'+aid.lower();dst=ROOT/'references/pdf'/(r['key']+'.pdf')
    dst.write_bytes(z.content);r.update(pdf_file=dst.name,pdf_src=z.url,pdf_pages=len(doc),pdf_bytes=len(z.content),sha256=hashlib.sha256(z.content).hexdigest(),acquisition='DOWNLOADED',identity_validation={'title':title_ok,'doi':doi_ok})
    # A plainly labeled candidate full text, separate from established extraction judgments.
    md=ROOT/'references/md'/(r['key']+'.md')
    if not md.exists():md.write_text('---\nkey: '+r['key']+'\nkci_id: '+aid+'\nverdict: CANDIDATE\nfull_text: true\n---\n\n# '+r['title']+'\n\n'+f"KCI: {r['url']}\nPDF source: {r['pdf_src']}\n\n"+''.join(f'\n\n<!-- page {i} -->\n\n'+pg.get_text() for i,pg in enumerate(doc,1)))
    break
   except Exception as e:r['attempts'][-1]['validation_error']=str(e)
  elif 'html' in z.headers.get('content-type','').lower():
   html=BeautifulSoup(z.text,'html.parser')
   tag=html.find('meta',{'name':'citation_pdf_url'})
   if tag:candidates.append(urllib.parse.urljoin(z.url,tag.get('content','')))
   for a in html.find_all('a',href=True):
    h=a['href'];label=a.get_text(' ',strip=True)
    if re.search(r'\.pdf(?:\?|$)|download_pdf|articlePdf',h,re.I) and not re.search('supp|appendix|copyright|윤리|투고|심사',h+' '+label,re.I):candidates.append(urllib.parse.urljoin(z.url,h))
 if not r['pdf_file']:r['acquisition']='UNAVAILABLE_AFTER_ATTEMPTS'
 dump(r,LOG/(aid+'.json'));print(aid,r['acquisition'],r['key'],flush=True);return r

def fetch():
 rows=json.loads((RAW/'census.json').read_text())['records'];result=[]
 with cf.ThreadPoolExecutor(max_workers=4) as ex:
  futures=[]
  for r in rows:
   p=LOG/(r['kci_id']+'.json')
   if p.exists():result.append(json.loads(p.read_text()))
   else:futures.append(ex.submit(detail_one,r))
  for f in cf.as_completed(futures):
   try:result.append(f.result())
   except Exception as e:print('WORKER ERROR',e,flush=True)
 dump(sorted(result,key=lambda r:(-(r.get('year') or 0),r['kci_id'])),ROOT/'references/kci_refs.json')
 print('Records',len(result),'Downloaded',sum(r.get('acquisition')=='DOWNLOADED' for r in result),flush=True)

if __name__=='__main__' and sys.argv[1]=='fetch':fetch()
