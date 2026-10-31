"""Save actual final manuscript/supplement page evidence for visual review."""
from pathlib import Path
import fitz,json,re,unicodedata
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_080'
report=json.loads((OUT/'verification_080.json').read_text())
dest=OUT/'rendered';dest.mkdir(exist_ok=True)
for p in dest.glob('*.png'):p.unlink()  # only this cycle's derived review images
index={}
for name in ['bmc_main','bmc_main_ko','bmc_supplementary']:
    doc=fitz.open(ROOT/f'manuscript/{name}.pdf')
    if name=='bmc_supplementary':
        starts=[i+1 for i,p in enumerate(doc) if re.search(r'Supplementary (?:Table|Figure) S\d+\.',p.get_text())]
        pages=sorted(set([1,len(doc),*starts,*[min(len(doc),i+1) for i in starts],70,85,104]))
    else:
        pages=sorted({v['page'] for k,v in report['details']['rendered_figure_fonts'].items() if k.startswith(name+'/')})
        # Include actual main conceptual table and the revised Discussion pages.
        pages=sorted(set(pages+[i+1 for i,p in enumerate(doc) if ('Proposed purpose-matched evidence framework' in p.get_text() or '목적별근거틀제안' in re.sub(r'\s+', '', unicodedata.normalize('NFC',p.get_text())))]))
    paths=[]
    for number in pages:
        path=dest/f'{name}_{number:03}.png';doc[number-1].get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(path);paths.append(path)
    index[name]={'pages':len(doc),'reviewed_pages':pages}
    for offset in range(0,len(paths),6):
        sheet=Image.new('RGB',(1500,1800),'#dddddd');draw=ImageDraw.Draw(sheet)
        for k,p in enumerate(paths[offset:offset+6]):
            im=Image.open(p);im.thumbnail((740,560));x=(k%2)*750;y=(k//2)*600;sheet.paste(im,(x,y+25));draw.text((x+8,y+5),p.stem,fill='black')
        sheet.save(dest/f'{name}_contact_{offset//6+1}.png')
(dest/'page_index.json').write_text(json.dumps(index,indent=2)+'\n')
print(index)
