"""Render the current missing list. Run with /usr/bin/python3 (ReportLab and Nanum fonts)."""
from pathlib import Path
import subprocess,html,hashlib,sys
from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Preformatted
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'data/PDF_MISSING.md'
before=hashlib.sha256(p.read_bytes()).hexdigest()
for name,file in [('Nanum','NanumGothic.ttf'),('NanumBold','NanumGothicBold.ttf')]:pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/nanum/'+file))
pdfmetrics.registerFontFamily('Nanum',normal='Nanum',bold='NanumBold',italic='Nanum',boldItalic='NanumBold')
z=subprocess.run(['/home/ahnbi/.conda/envs/myclaude/bin/pandoc',str(p),'-f','gfm','-t','html5'],capture_output=True,text=True,check=True).stdout
soup=BeautifulSoup(z,'html.parser')
for div in soup.find_all('div'):div.unwrap()
for c in soup.find_all('code'):c.name='font';c.attrs={'name':'Nanum'}
for a in soup.find_all('a'):a.attrs={'href':a.get('href',''),'color':'#155ca5'}
styles={
'p':ParagraphStyle('p',fontName='Nanum',fontSize=10,leading=15,spaceAfter=7),
'h1':ParagraphStyle('h1',fontName='NanumBold',fontSize=21,leading=28,spaceAfter=14,keepWithNext=True),
'h2':ParagraphStyle('h2',fontName='NanumBold',fontSize=13,leading=18,spaceBefore=12,spaceAfter=8,keepWithNext=True),
'cell':ParagraphStyle('cell',fontName='Nanum',fontSize=8.5,leading=12,splitLongWords=True),
'code':ParagraphStyle('code',fontName='Nanum',fontSize=9,leading=14,spaceAfter=10,backColor=colors.HexColor('#f3f5f7'))}
def inside(n):return ''.join(str(x) for x in n.contents)
W,H=landscape(A4);width=W-26*mm;story=[]
for node in soup.children:
 if not getattr(node,'name',None):continue
 if node.name in ('h1','h2','p'):story.append(Paragraph(inside(node),styles[node.name]))
 elif node.name=='pre':story.append(Preformatted(node.get_text(),styles['code']))
 elif node.name=='table':
  rows=[]
  for tr in node.find_all('tr'):
   rows.append([Paragraph(('<b>'+inside(c)+'</b>') if c.name=='th' else inside(c),styles['cell']) for c in tr.find_all(['td','th'])])
  fractions={8:[.18,.05,.11,.05,.13,.30,.08,.10],5:[.06,.48,.12,.08,.26],3:[.47,.09,.44]}.get(len(rows[0]),[1/len(rows[0])]*len(rows[0]))
  tab=Table(rows,colWidths=[width*f for f in fractions],repeatRows=1,hAlign='LEFT')
  tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#bdc7d0')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
  story.extend([tab,Spacer(1,9)])
def footer(canvas,doc):
 canvas.saveState();canvas.setFont('Nanum',8);canvas.setFillColor(colors.HexColor('#666666'));canvas.drawRightString(W-13*mm,8*mm,str(doc.page));canvas.restoreState()
out=p.with_suffix('.pdf');doc=SimpleDocTemplate(str(out),pagesize=(W,H),rightMargin=13*mm,leftMargin=13*mm,topMargin=14*mm,bottomMargin=15*mm,title=soup.h1.get_text(),author='');doc.build(story,onFirstPage=footer,onLaterPages=footer)
assert hashlib.sha256(p.read_bytes()).hexdigest()==before
print(out)
