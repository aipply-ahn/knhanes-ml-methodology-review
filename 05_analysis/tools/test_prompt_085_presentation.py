"""Guard the revised scientific labels and actual Korean PRISMA glyph rendering."""
from pathlib import Path
import unittest
import fitz
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

class PresentationTests(unittest.TestCase):
 def test_korean_prisma_glyphs_are_visible(self):
  page=fitz.open(ROOT/'figures/submission/fig1_prisma_ko.pdf')[0]
  words=[w for w in page.get_text('words') if any('\uac00'<=c<='\ud7a3' for c in w[4])]
  self.assertGreater(len(words),50)
  for word in words:
   pix=page.get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(word[:4]))
   rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3]
   self.assertGreater(int((rgb.min(axis=2)<100).sum()),40,word[4])
 def test_revised_titles_and_publication(self):
  # Prompt 092: manuscript/bmc_main.pdf carries the supplement; main-text checks read the manuscript-only build.
  text=' '.join(p.get_text() for p in fitz.open(ROOT/'build/submission/bmc_main.pdf'))
  compact=' '.join(text.split())
  # Prompt 090: outcome-definition and period panels moved to Supplementary Figures S5 and S12.
  supp=' '.join(' '.join(p.get_text() for p in fitz.open(ROOT/'manuscript/bmc_supplementary.pdf')).split())
  # Prompt 093: outcome-definition grades are drawn in main Figure 3A; Figure S3 points readers there.
  # Prompt 094 (review v32): outcome/predictor rebuild grades moved to main Figure 6C; Figure S3 points readers there.
  # Prompt 096 (review v34): former Figure 6C moved to Supplementary Figure S3E and Figure 4B.
  self.assertIn('(B) Outcome alone, predictor set alone, and outcome, predictor set and tuning separation together, fully rebuildable',' '.join(supp.replace('pre‑ dictor','predictor').replace('pre- dictor','predictor').split()))  # Prompt 099: outcome-source panel moved to Figure 2E  # Prompt 103: predictor-set bar added to S2D  # Prompt 104: panel B  # prompt 109
  # Prompt 088 removed internal item codes (OUT16) from reader-facing figure titles.
  self.assertNotIn('OUT16',compact)
  self.assertIn('Differences by publication period',supp)
  self.assertIn('198–220',compact)
  self.assertIn('333',compact)
  self.assertNotIn('SaML preprint',compact)
  # Prompt 093: Table 1 names the stronger column "Recommended standard (stronger)", proposed for future studies.
  # Prompt 094 (review v32): Table 1 became the recommended-practice table in the Discussion.
  self.assertIn('Methodological practices reported in the 192 core classi',compact.replace('ﬁ','fi'))  # Prompt 096 (review v34): Table 1 is a checklist  # prompt 109

if __name__=='__main__':unittest.main()
