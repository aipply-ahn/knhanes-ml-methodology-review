"""Render actual final-page evidence; this records locations, not a visual PASS."""
from pathlib import Path
import fitz,json,re
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_081/rendered'
OUT.mkdir(exist_ok=True)
assert not list(OUT.glob('*.png')),'Preserve previous renders; choose a new evidence directory.'
index={};figures=[]
for name in ['bmc_main','bmc_main_ko']:
 doc=fitz.open(ROOT/f'manuscript/{name}.pdf')
 tex='\n'.join(re.split(r'(?<!\\)%',line)[0] for line in (ROOT/f'manuscript/{name}.tex').read_text().splitlines())
 pages=set()
 for path in re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',tex):
  source=fitz.open(ROOT/'manuscript'/path)[0]
  spans=[s for b in source.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if len(s['text'].strip())>3]
  anchor=max(spans,key=lambda s:len(s['text']))['text'].strip()
  hits=[i for i,p in enumerate(doc) if anchor in p.get_text()];assert hits,(path,anchor)
  i=hits[0];pages.add(i+1)
  figures.append({'manuscript':name,'figure':Path(path).stem,'page':i+1,'image':str((OUT/f'{name}_{i+1:03}.png').relative_to(ROOT)),'inspection':'PENDING'})
 for number in sorted(pages):doc[number-1].get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(OUT/f'{name}_{number:03}.png')
 index[name]={'total_pages':len(doc),'rendered_pages':sorted(pages)}
# Locate supplement boundaries and actual combined pages from each standalone S2/S9.
combined=fitz.open(ROOT/'manuscript/bmc_supplementary.pdf');pages={1,len(combined)}
starts=[i+1 for i,p in enumerate(combined) if re.search(r'Supplementary (?:Table|Figure) S\d+\.',p.get_text())]
pages.update(starts);pages.update(min(len(combined),p+1) for p in starts)
for num,slug in [('02','Operational_definitions_coding_rules'),('09','Study_protocol_audit_results')]:
 doc=fitz.open(ROOT/f'manuscript/supplementary/pdf/Supplementary_Table_S{num}_{slug}.pdf')
 # For S9 retain each panel first/continued page and last page of study results.
 selected={1,2,len(doc)}
 if num=='09':
  for i,p in enumerate(doc):
   text=p.get_text()
   if re.search(r'— [ABCD]\. ',text):selected.update([i+1,min(len(doc),i+2)])
  selected.add(len(doc)-1)
 else:selected.update([len(doc)//2])
 for number in sorted(selected):
  doc[number-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f'S{num}_{number:03}.png')
 index['S'+num]={'total_pages':len(doc),'rendered_pages':sorted(selected)}
for number in sorted(pages):combined[number-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(OUT/f'bmc_supplementary_{number:03}.png')
index['bmc_supplementary']={'total_pages':len(combined),'rendered_pages':sorted(pages)}
for name in ['bmc_main','bmc_main_ko']:
 paths=[OUT/f'{name}_{n:03}.png' for n in index[name]['rendered_pages']]
 for offset in range(0,len(paths),4):
  canvas=Image.new('RGB',(1600,2200),'#dddddd');draw=ImageDraw.Draw(canvas)
  for j,p in enumerate(paths[offset:offset+4]):
   im=Image.open(p);im.thumbnail((795,1050));x=(j%2)*800;y=(j//2)*1100
   canvas.paste(im,(x,y+25));draw.text((x+8,y+5),p.stem,fill='black')
  canvas.save(OUT/f'{name}_contact_{offset//4+1}.png')
(OUT/'page_index.json').write_text(json.dumps(index,indent=2)+'\n')
(OUT/'figure_inventory.json').write_text(json.dumps(figures,indent=2)+'\n')
print(json.dumps(index,indent=2))
