"""Current revision: presentation, exact co-reporting cells and packaged source reconstruction."""
from pathlib import Path
import unittest,json,hashlib,tarfile,re,zipfile,tempfile,subprocess,sys,io
import fitz
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/prompt_086'
class Prompt086(unittest.TestCase):
 def test_A_cells_and_marginals(self):
  rel=json.loads((ROOT/'results/derived/purpose_output_relationships.json').read_text())
  for row,want,marg in zip(rel['relationships'],[[79,4,85,46],[20,1,40,153]],[(83,164),(21,60)]):  # Prompt 106
   cells=[row['counts'][k] for k in ['both','purpose_only','output_only','neither']]
   self.assertEqual(cells,want);self.assertEqual(sum(cells),214);self.assertEqual((cells[0]+cells[1],cells[0]+cells[2]),marg)  # Prompt 106
  for suffix in ['', '_ko']:
   p=fitz.open(ROOT/f'figures/submission/fig3_data_use{suffix}.pdf')[0]
   text=p.get_text();self.assertIn('D.',text)
   for n in ['79','85','46','20','40','153']:self.assertIn(n,text)  # Prompt 106
 def test_C_effective_fonts(self):
  rows=json.loads((OUT/'font_measurements.json').read_text())
  after=[r for r in rows if r['state']=='after'];self.assertEqual({r['figure'] for r in after},set(range(1,13)))
  for r in after:self.assertGreaterEqual(r['min_effective_pt'],7.45 if r['figure'] in (3,9,11) else 6.95,r)
 def test_D_exact_common_rule_removal(self):
  import build_standalone_supplements as b
  captured={};original=b.fixed_width_table_tex
  def capture(title,headers,rows,widths,note='',font_size=7.5):
   captured['rows']=rows;captured['note']=note
   return original(title,headers,rows,widths,note,font_size)
  # Exercise real renderer with output calls redirected to temporary paths.
  with tempfile.TemporaryDirectory(dir=OUT) as tmp:
   old=(b.TEX,b.TABLES,b.compile_tex,b.fixed_width_table_tex)
   b.TEX=b.TABLES=Path(tmp);b.compile_tex=lambda p:None;b.fixed_width_table_tex=capture
   try:
    # Prompt 092: the protocol instrument is Supplementary Table S9 (was S2).
    for n,rows,common,col in [(b.PROTOCOL_TABLE,b.human_protocol_rows(),'Apply the canonical item definition to explicit source evidence; do not infer an unreported value.',5)]:
     b.emit_fixed_table(n,'test','test',list(map(str,range(7))),rows,[1]*7,b.human_protocol_note(),write_workbook=False)
     removed=0
     def expand087(text):
      # Prompt 087 moved shared REP and PROBAST+AI domain text into the S2 note; reverse it losslessly.
      if text.startswith('Common REP rule (see note). '):
       return b.S2_REP_COMMON+' '+text[len('Common REP rule (see note). '):]
      if ' Common PROBAST+AI domain rule (see note).' in text:
       for src_text in [r[col] for r in rows]:
        if b.S2_PROBAST_COMMON_1 in src_text:
         loc,rest=src_text.split(' '+b.S2_PROBAST_COMMON_1+' ',1);dirn,t2=rest.split(' '+b.S2_PROBAST_COMMON_2,1)
         if f"{loc} {dirn} Common PROBAST+AI domain rule (see note).{t2}"==text:return src_text
      return text
     for src,dst in zip(rows,captured['rows']):
      self.assertEqual(src[:col],dst[:col]);self.assertEqual(src[col+1:],dst[col+1:])
      if src[col].startswith(common):
       self.assertEqual(src[col],common+(' '+dst[col] if dst[col] else ''));removed+=1
      else:self.assertEqual(src[col],expand087(dst[col]))
     self.assertGreater(removed,100)
    # Prompt 093: the dictionary is the VARIABLE_DICTIONARY sheet of the Table S5 workbook (cell-identical).
    w=load_workbook(ROOT/'manuscript/bmc_supplementary_data1.xlsx',read_only=True,data_only=True)  # Prompt 097: workbook renamed Additional Data 1
    rows=[list(r) for r in list(w['VARIABLE_DICTIONARY'].values)[1:]];w.close()
    common='Direct/normalised field; see common provenance note.'
    # Prompt 097: the dictionary is no longer a numbered table; the shared-prefix rule is keyed on WORKBOOK_TABLE.
    b.WORKBOOK_TABLE=5
    b.emit_fixed_table(5,'test','test',list(map(str,range(8))),rows,[1]*8,write_workbook=False)
    b.WORKBOOK_TABLE=None
    removed=0
    for src,dst in zip(rows,captured['rows']):
     if src[7]==common:self.assertEqual(dst[7],'');removed+=1
     else:self.assertEqual(src,dst)
    self.assertGreater(removed,120)
   finally:b.TEX,b.TABLES,b.compile_tex,b.fixed_width_table_tex=old
  # Prompt 093: the dictionary and 306-item PDFs were removed; no supplement PDF repeats either common rule.
  for path in (ROOT/'manuscript/supplementary/pdf').glob('Supplementary_Table_*.pdf'):
   text=' '.join(p.get_text() for p in fitz.open(path))
   self.assertLess(text.count('Apply the canonical item definition'),3,path.name)
   self.assertLess(text.count('Direct/normalised field'),3,path.name)
 def test_E_pagination(self):
  data=json.loads((OUT/'supplement_page_fill.json').read_text())
  self.assertLess(len(data['after']),len(data['before']))
  self.assertFalse([r for r in data['after'] if r['page']>1 and r['fill_fraction']<.2],data['after'])
 def test_F_unconfirmed_record(self):
  text=' '.join(p.get_text() for p in fitz.open(ROOT/'manuscript/bmc_supplementary.pdf'))
  self.assertIn('ART003346494',text);self.assertIn('KNHANES use could not be confirmed',' '.join(re.sub(r'[-‑]\s*\n\s*', '', text).split()))  # Prompt 098: record moved to a Table S3 footnote
  flow=json.loads((ROOT/'results/derived/final_selection_flow.json').read_text())
  self.assertEqual(flow['terminology_screen']['partition']['kci_not_advanced'],0)  # Prompt 106
  before=json.loads((OUT/'before_sha256.json').read_text())
  self.assertEqual(json.loads((ROOT/'prompts/implementation_records/prompt_106/artifact_amendments.json').read_text())['results/derived/final_selection_flow.json']['after_sha256'],hashlib.sha256((ROOT/'results/derived/final_selection_flow.json').read_bytes()).hexdigest())  # Prompt 106
 def test_G_fresh_zip(self):
  with tempfile.TemporaryDirectory() as tmp:
   with zipfile.ZipFile(ROOT/'manuscript/reviewer_delivery.zip') as z:z.extractall(tmp)
   r=subprocess.run([sys.executable,str(Path(tmp)/'verify_delivery.py')],capture_output=True,text=True)
   import os;(Path(os.environ.get('KNHANES_TEST086_LOG_DIR',OUT))/'extracted_zip_verification.log').write_text(r.stdout+r.stderr)
   self.assertEqual(r.returncode,0,r.stderr)
   data=json.loads(r.stdout);self.assertTrue(data['figure11_all_panels_reconstructed']);self.assertEqual(data['canonical_protocol_items'],382)
 def test_build_has_no_overflow(self):
  for name in ['manuscript_build.log','supplement_build.log']:
   log=(OUT/name).read_text()
   self.assertNotRegex(log,r'Overfull|Float too large|Fatal error|Emergency stop')
 def test_locked_decisions(self):
  before=json.loads((OUT/'before_sha256.json').read_text())
  with tarfile.open(OUT/'before.tar.gz') as t:
   for name in ['manuscript/bmc_main.tex','manuscript/bmc_main_ko.tex']:
    self.assertEqual(t.extractfile(name.replace('manuscript/','paper/',1)).read().decode().split('\\begin{document}')[0],(ROOT/name).read_text().split('\\begin{document}')[0])
  # After archival the prompt-086 root file lives at its processed path (manifest row 86).
  self.assertEqual(hashlib.sha256((ROOT/'prompts/processed/prompt_086_20260925_135551.txt').read_bytes()).hexdigest(),before['프롬프트.txt'])
  for suffix in ['', '_ko']:
   text=fitz.open(ROOT/f'figures/submission/fig11_methodological_appraisal{suffix}.pdf')[0].get_text()
   self.assertEqual(text.count('N=192 studies'),4)  # Prompt 106
   for n in ['5/65','297','378']:self.assertIn(n,text)  # Prompt 106
  s=(ROOT/'tools/make_streamlined_figures.py').read_text();self.assertRegex(s,r'ax\.plot\(range\(4\),pct,.*zorder=2\)')
if __name__=='__main__':unittest.main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
