#!/usr/bin/env python3
"""Retrieve publisher-hosted supplementary files for every included report.

Sources:
1) Europe PMC full-text XML + supplementaryFiles ZIP for PMCID records.
2) Publisher landing pages, discovering links explicitly labelled as supplementary,
   supporting information, additional files, or multimedia appendices.

All downloads are stored by study key with a SHA-256 manifest. The script is
resumable and never treats the review's own "supplementary-search addition"
label as evidence of article supplementary material.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,mimetypes,re,sys,time,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.parse import urljoin,urlparse,unquote
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'references'/'supplements'
MANIFEST=OUT/'manifest.tsv'
STUDIES=OUT/'study_status.tsv'
UA='KNHANES-ML-systematic-review supplementary-material audit (contact: repository maintainer)'
TEXT_SUPP_RE=re.compile(
    r'(?i)^\s*(?:download\s+)?(?:supplementary|supplemental)\s*[_-]?\s*'
    r'(?:material|information|data|files?|tables?|figures?|methods?|appendi(?:x|ces)|results?)\b'
    r'|^\s*supporting\s+information\b|^\s*additional\s+(?:files?|data)\b'
    r'|^\s*multimedia\s+appendi(?:x|ces)\b|^\s*electronic\s+supplement\b'
)
HREF_SUPP_RE=re.compile(
    r'(?i)(?:supplement(?:ary|al)?|supporting[-_/ ]?(?:information|data|file)'
    r'|additional[-_/ ]?file|multimedia[-_/ ]?appendix|MOESM\d*'
    r'|[._-]s\d{3}(?:[._-]|$)|esm(?:[._-]|$)|/mmc\d+)'
)
BAD_RE=re.compile(r'(?i)(policy|guideline|instructions?-for-authors|submit|advertis|cookie|privacy|terms|supplements?\-journal)')
FILE_EXT={'.pdf','.zip','.doc','.docx','.xls','.xlsx','.csv','.tsv','.txt','.sav','.r','.py','.ipynb','.jpg','.jpeg','.png','.tif','.tiff','.gif','.mp4','.mov','.xml'}
FIELDS=['key','year','title','doi','pmcid','landing_url','source_checked','disclosure_status','candidate_links','downloaded_files','status','notes']
MFIELDS=['key','source','source_url','final_url','local_path','filename','content_type','bytes','sha256','retrieved_on']

def session():
    s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}); return s

def safe_name(name,default='supplement'):
    name=unquote(name).split('?')[0].split('#')[0]
    name=re.sub(r'[^A-Za-z0-9._()\-]+','_',name).strip('._')
    return (name or default)[:180]

def fname(resp,url,idx=1):
    cd=resp.headers.get('content-disposition','')
    m=re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)",cd,re.I)
    if m: return safe_name(m.group(1))
    n=Path(urlparse(resp.url or url).path).name
    n=safe_name(n,f'supplement_{idx}')
    ct=(resp.headers.get('content-type') or '').split(';')[0].lower()
    if Path(n).suffix.lower() not in FILE_EXT:
        ext=mimetypes.guess_extension(ct) or ''
        if ct=='application/vnd.openxmlformats-officedocument.wordprocessingml.document': ext='.docx'
        if ct=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ext='.xlsx'
        n+=ext
    return n

def write_file(key,source,url,resp,idx):
    data=resp.content
    if not data: return None
    n=fname(resp,url,idx)
    d=OUT/key; d.mkdir(parents=True,exist_ok=True)
    p=d/n
    if p.exists() and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(data).digest(): pass
    else:
        base=p.stem; ext=p.suffix; j=2
        while p.exists(): p=d/f'{base}_{j}{ext}'; j+=1
        p.write_bytes(data)
    return {'key':key,'source':source,'source_url':url,'final_url':resp.url,'local_path':str(p.relative_to(ROOT)),
            'filename':p.name,'content_type':resp.headers.get('content-type',''),'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'retrieved_on':time.strftime('%Y-%m-%d')}

def pmc_one(r):
    key=r['key']; pmc=r.get('pmcid') or ''
    base=dict(key=key,year=r.get('year'),title=r.get('title'),doi=r.get('doi'),pmcid=pmc,
              landing_url=r.get('landing') or '',source_checked='Europe PMC fullTextXML',candidate_links=0,downloaded_files=0)
    if not pmc:
        return [],{**base,'disclosure_status':'not_applicable','status':'no_pmcid','notes':''}
    s=session(); xu=f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML'
    try:
        x=s.get(xu,timeout=45); x.raise_for_status()
        soup=BeautifulSoup(x.content,'xml')
        names=[]
        for sm in soup.find_all('supplementary-material'):
            for tag in sm.find_all(['media','graphic']):
                h=tag.get('xlink:href') or tag.get('href')
                if h and Path(urlparse(h).path).name not in names: names.append(Path(urlparse(h).path).name)
        if not names:
            return [],{**base,'disclosure_status':'none_in_pmc_xml','status':'checked_no_supplement','notes':''}
        zu=f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/supplementaryFiles'
        zresp=s.get(zu,timeout=90); zresp.raise_for_status(); z=zipfile.ZipFile(io.BytesIO(zresp.content))
        members={Path(n).name:n for n in z.namelist() if not n.endswith('/')}
        saved=[]
        for i,n in enumerate(names,1):
            member=members.get(n)
            if not member: continue
            data=z.read(member)
            fake=requests.Response(); fake.status_code=200; fake._content=data; fake.url=zu+'#'+n
            fake.headers['content-type']=mimetypes.guess_type(n)[0] or 'application/octet-stream'
            fake.headers['content-disposition']=f'attachment; filename="{n}"'
            item=write_file(key,'Europe PMC',zu+'#'+n,fake,i)
            if item:saved.append(item)
        return saved,{**base,'disclosure_status':'supplement_disclosed','candidate_links':len(names),'downloaded_files':len(saved),
                      'status':'downloaded' if len(saved)==len(names) else 'partial','notes':' | '.join(n for n in names if n not in members)}
    except Exception as e:
        return [],{**base,'disclosure_status':'unknown','status':'error','notes':f'{type(e).__name__}: {e}'[:400]}

def is_candidate(href,text):
    return bool(HREF_SUPP_RE.search(href) or TEXT_SUPP_RE.search(text)) and not BAD_RE.search(href+' '+text)

def content_is_file(resp,explicit=True):
    ct=(resp.headers.get('content-type') or '').lower().split(';')[0]
    ext=Path(urlparse(resp.url).path).suffix.lower()
    if ext in FILE_EXT:return True
    if ct.startswith(('application/pdf','application/zip','application/msword','application/word','application/xls','application/vnd.','text/csv','text/tab-separated')):return True
    if 'attachment' in (resp.headers.get('content-disposition') or '').lower():return True
    if explicit and ct.startswith('image/'):return True
    return False

def publisher_one(r):
    key=r['key']; start=r.get('landing') or (f"https://doi.org/{r['doi']}" if r.get('doi') else '')
    base=dict(key=key,year=r.get('year'),title=r.get('title'),doi=r.get('doi'),pmcid=r.get('pmcid') or '',
              landing_url=start,source_checked='publisher landing page',candidate_links=0,downloaded_files=0)
    if not start:return [],{**base,'disclosure_status':'unknown','status':'no_landing_identifier','notes':''}
    s=session()
    try:
        pg=s.get(start,timeout=45,allow_redirects=True)
        if pg.status_code>=400:
            return [],{**base,'disclosure_status':'unknown','status':f'landing_http_{pg.status_code}','notes':pg.url}
        soup=BeautifulSoup(pg.content,'html.parser')
        cand=[]
        for a in soup.find_all('a',href=True):
            h=urljoin(pg.url,a['href']); text=' '.join(a.get_text(' ',strip=True).split())
            if is_candidate(h,text): cand.append((h,text))
        for tag in soup.find_all(['link','meta']):
            h=tag.get('href') or tag.get('content') or ''
            label=' '.join(str(tag.get(k,'')) for k in ['rel','name','property','title'])
            if h and is_candidate(h,label): cand.append((urljoin(pg.url,h),label))
        uniq=[]; seen=set()
        for h,t in cand:
            h=h.replace('&amp;','&')
            if h not in seen and h!=pg.url: seen.add(h); uniq.append((h,t))
        if len(uniq) > 50:
            uniq = uniq[:50]
        saved=[]; errors=[]
        for i,(u,label) in enumerate(uniq,1):
            try:
                rr=s.get(u,timeout=75,allow_redirects=True)
                if rr.status_code>=400: errors.append(f'{rr.status_code}:{u}'); continue
                if content_is_file(rr):
                    item=write_file(key,'publisher',u,rr,i)
                    if item:saved.append(item)
                elif 'html' in (rr.headers.get('content-type') or '').lower():
                    # One-level supplement landing page.
                    sp=BeautifulSoup(rr.content,'html.parser')
                    nested = sp.find_all('a',href=True)[:50]
                    for j,a in enumerate(nested,1):
                        h=urljoin(rr.url,a['href']); tx=' '.join(a.get_text(' ',strip=True).split())
                        ext=Path(urlparse(h).path).suffix.lower()
                        if (is_candidate(h,tx) or ext in FILE_EXT) and not BAD_RE.search(h+' '+tx):
                            try:
                                fr=s.get(h,timeout=75,allow_redirects=True)
                                if fr.status_code<400 and content_is_file(fr):
                                    item=write_file(key,'publisher',h,fr,i*100+j)
                                    if item:saved.append(item)
                            except Exception as e: errors.append(f'{type(e).__name__}:{h}')
            except Exception as e: errors.append(f'{type(e).__name__}:{u}')
        # Deduplicate manifest entries by hash while retaining one local file.
        ded=[]; hashes=set()
        for x in saved:
            if x['sha256'] not in hashes: hashes.add(x['sha256']); ded.append(x)
        return ded,{**base,'disclosure_status':('supplement_disclosed' if uniq else 'none_found_on_landing'),
                    'candidate_links':len(uniq),'downloaded_files':len(ded),
                    'status':('downloaded' if ded else 'candidate_not_downloaded' if uniq else 'checked_no_supplement'),
                    'notes':' | '.join(errors)[:1000]}
    except Exception as e:
        return [],{**base,'disclosure_status':'unknown','status':'error','notes':f'{type(e).__name__}: {e}'[:400]}

def load_refs():
    return [r for r in json.loads((ROOT/'references/refs.json').read_text()) if r.get('verdict')=='INCLUDE']

def write_tsv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',choices=['pmc','publisher','all'],default='all');ap.add_argument('--workers',type=int,default=6);ap.add_argument('--limit',type=int); args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True); refs=load_refs();
    if args.limit:refs=refs[:args.limit]
    allfiles=[]; statuses=[]
    oldfiles=[]; oldstatus=[]
    if MANIFEST.exists():
        with MANIFEST.open() as f:oldfiles=list(csv.DictReader(f,delimiter='\t'))
    if STUDIES.exists():
        with STUDIES.open() as f:oldstatus=list(csv.DictReader(f,delimiter='\t'))

    def checkpoint():
        filemap={(x['key'],x['sha256']):x for x in oldfiles+allfiles}
        stmap={(x['key'],x['source_checked']):x for x in oldstatus+statuses}
        write_tsv(MANIFEST,sorted(filemap.values(),key=lambda x:(x['key'],x['filename'])),MFIELDS)
        write_tsv(STUDIES,sorted(stmap.values(),key=lambda x:(x['key'],x['source_checked'])),FIELDS)
        return filemap,stmap
    phases=[]
    if args.source in ('pmc','all'):
        phases.append(('pmc',pmc_one,[r for r in refs if len(str(r.get('pmcid') or '')) > 3]))
    if args.source in ('publisher','all'):phases.append(('publisher',publisher_one,refs))
    for label,fn,items in phases:
        print(f'{label}: checking {len(items)} studies',flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs={ex.submit(fn,r):r for r in items}
            done=0
            for fut in as_completed(futs):
                files,st=fut.result();allfiles.extend(files);statuses.append(st);done+=1
                if done%20==0 or done==len(items):
                    checkpoint()
                    print(f'{label}: {done}/{len(items)}',flush=True)
    filemap,stmap=checkpoint()
    print(f'manifest files={len(filemap)} statuses={len(stmap)}',flush=True)
if __name__=='__main__':main()
