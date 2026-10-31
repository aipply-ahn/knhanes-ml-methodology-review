import pathlib,json,requests,fitz,hashlib,unicodedata,concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parents[1];LOG=ROOT/'references/_logs/kci_20260905'
def norm(t):return ''.join(c for c in unicodedata.normalize('NFKC',t or '').lower() if c.isalnum())
def download(aid,url):
 p=LOG/(aid+'.json')
 if not p.exists():return
 r=json.load(open(p))
 if r.get('pdf_file'):return
 try:
  z=requests.get(url,timeout=25,verify=False if 'e-jnh.org/' in url else True);a={'url':url,'status':z.status_code,'bytes':len(z.content),'stage':'publisher_followup','tls_certificate_verified':'e-jnh.org/' not in url};r['attempts'].append(a)
  if z.content.startswith(b'%PDF-'):
   d=fitz.open(stream=z.content,filetype='pdf');t=''.join(pg.get_text() for pg in list(d)[:3]);ok=(r.get('doi') and norm(r['doi']) in norm(t)) or any(len(norm(s))>20 and norm(s)[:60] in norm(t) for s in [r['title'],r.get('title_en')])
   if ok:
    dst=ROOT/'references/pdf'/(r['key']+'.pdf');dst.write_bytes(z.content);r.update(pdf_file=dst.name,pdf_src=url,pdf_pages=len(d),pdf_bytes=len(z.content),sha256=hashlib.sha256(z.content).hexdigest(),acquisition='DOWNLOADED',identity_validation={'publisher_followup':True})
    (ROOT/'references/md'/(r['key']+'.md')).write_text(f"---\nkey: {r['key']}\nkci_id: {aid}\nverdict: CANDIDATE\nfull_text: true\n---\n\n# {r['title']}\n\nSource: {url}\n"+''.join(f'\n\n<!-- page {i} -->\n\n'+pg.get_text() for i,pg in enumerate(d,1)))
   else:a['validation']='PDF_IDENTITY_UNCONFIRMED'
  p.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(aid,r['acquisition'],flush=True)
 except Exception as e:
  r['attempts'].append({'url':url,'error':str(e),'stage':'publisher_followup'});p.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(aid,str(e),flush=True)
if __name__=='__main__':
 xs=json.load(open(__import__('sys').argv[1]))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(lambda x:download(*x),xs.items()))
