"""Detect text collisions in Figure12 vector output, complementing actual-page review."""
from pathlib import Path
import fitz
import re,json,itertools
ROOT=Path(__file__).resolve().parents[1]

# Author-preserved presentation decision: Figure 12 series remain connected
# across ordered periods. A later prose-edit prompt must not silently remove
# this visual structure again.
source=(ROOT/'tools/make_streamlined_figures.py').read_text()
assert re.search(r"ax\.plot\(range\(4\),pct,.*zorder=2\)",source), 'Figure 12 period connectors removed from generator'
assert 'Thin lines connect observations across the ordered publication periods' in (ROOT/'manuscript/bmc_main.tex').read_text()
assert '가는 선은 순서가 있는 출판 시기의 관측값을 시각적으로 연결' in (ROOT/'manuscript/bmc_main_ko.tex').read_text()
# Keep current regression output separate from immutable historical cycle081 evidence.
OUT=ROOT/'prompts/implementation_records/figure12_current_check';OUT.mkdir(parents=True,exist_ok=True)
results=[]
for lang in ['en','ko']:
 path=ROOT/'manuscript/figs'/('fig12_temporal_changes'+('_ko' if lang=='ko' else '')+'.pdf')
 page=fitz.open(path)[0]
 spans=[s for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if s['text'].strip()]
 conflicts=[]
 for a,b in itertools.combinations(spans,2):
  ra,rb=fitz.Rect(a['bbox']),fitz.Rect(b['bbox']);intersection=ra&rb
  if intersection.is_empty:continue
  # PDF glyph bboxes can touch by subpixel rounding; require material overlap.
  if intersection.width>1 and intersection.height>1:
   conflicts.append({'a':a['text'],'b':b['text'],'intersection':list(intersection)})
 results.append({'language':lang,'text_spans':len(spans),'material_text_intersections':conflicts})
(OUT/'figure12_text_geometry.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
assert all(not r['material_text_intersections'] for r in results)
