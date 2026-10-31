"""Retrieve the author's official tool/E&E from the article's PMC deposit."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
def main():
    url='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11931409/supplementaryFiles'
    r=requests.get(url,timeout=60);r.raise_for_status()
    z=zipfile.ZipFile(io.BytesIO(r.content))
    records=[]
    for member,name in [('mook082505.ww2.pdf','PROBAST_AI_official_tool_2025.pdf'),
                        ('mook082505.ww3.pdf','PROBAST_AI_EE_Light_2025.pdf')]:
        data=z.read(member);assert data.startswith(b'%PDF')
        p=ROOT/'references/guidelines'/name
        assert not p.exists() or p.read_bytes()==data
        p.write_bytes(data)
        records.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),
                        'source':url,'article':'https://doi.org/10.1136/bmj-2024-082505',
                        'deposited_file':member,'access_date':'2026-09-24'})
    p=ROOT/'prompts/implementation_records/prompt_079';p.mkdir(exist_ok=True)
    (p/'official_sources.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))
if __name__=='__main__':main()
