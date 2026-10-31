"""Create readable PDF/XLSX audit artifacts for all variable-importance studies."""
import csv, re, subprocess
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'manuscript/submission/appendices'

def read(path):
 with open(path,encoding='utf-8-sig') as f:return list(csv.DictReader(f,delimiter='\t'))

def esc(x):
 x=str(x or '')
 return (x.replace('\\',r'\textbackslash{}').replace('&',r'\&').replace('%',r'\%')
   .replace('$',r'\$').replace('#',r'\#').replace('_',r'\_').replace('{',r'\{').replace('}',r'\}')
   .replace('~',r'\textasciitilde{}').replace('^',r'\textasciicircum{}').replace('\n',' '))

def main():
 detail=read(ROOT/'data/VARIABLE_IMPORTANCE_DETAILS.tsv')
 domains={r['key']:r for r in read(ROOT/'data/IMPORTANT_VARIABLE_DOMAINS.tsv')}
 assert detail and len(detail)==len(domains)
 n_studies=len(detail)
 rows=[]
 for r in detail:
  d=domains[r['key']]
  rows.append({
   '연구키':r['key'],'연도':r['year'],'주제':d['topic_label'],'목적변수':r['outcome'],
   '입력 변수 수':r['n_input_variables'],'변수 중요도 방법':r['importance_methods'],
   '표준 변수군':d['variable_domains'] or 'NR','중요변수 선정 상태':r['importance_selection_status'],
   '선정 규칙':r['selection_strategies'],'변수 중요도 결과':r['importance_result'],
   '후속 통계추론':('예' if r['importance_guided_inference']=='1' else '아니오'),
   '선택 변수 수':r['selected_n'] or 'NR','추론 변수 수':r['inferential_n'] or 'NR',
   '입력 변수 근거문':r['input_variables_source_text'],'선정 규칙 근거문':r['selection_rule_source_text']})

 # Filterable workbook: full text without page-width constraints.
 wb=Workbook(); ws=wb.active; ws.title=f'{n_studies}편 전체 감사표'
 headers=list(rows[0]); ws.append(headers)
 for row in rows: ws.append([row[h] for h in headers])
 ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
 widths=[25,8,20,34,13,24,42,30,42,80,14,13,13,80,80]
 for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
 for c in ws[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='315B7D'); c.alignment=Alignment(wrap_text=True,vertical='center')
 for row in ws.iter_rows(min_row=2):
  for c in row: c.alignment=Alignment(wrap_text=True,vertical='top')
  row[0].font=Font(bold=True)
 for i in range(2,ws.max_row+1): ws.row_dimensions[i].height=72
 ws.sheet_view.showGridLines=False
 xlsx=OUT/'appendix9_variable_importance_full_ko.xlsx'; wb.save(xlsx)

 # Landscape, multipage PDF. Detailed evidence remains readable at 7 pt.
 tex=OUT/'appendix9_variable_importance_full_ko.tex'
 head=r'''\documentclass[10pt]{article}
\usepackage[a4paper,landscape,margin=10mm]{geometry}
\usepackage{fontspec}\usepackage{kotex}\usepackage{xetexko}
\setmainfont{NanumMyeongjo}\setsansfont{NanumSquare}
\usepackage{longtable,booktabs,array,xcolor,hyperref}
\hypersetup{hidelinks}\pagestyle{plain}\setlength{\parindent}{0pt}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\begin{document}
{\LARGE\bfseries 보조자료 9: 변수 중요도 연구 __N__편 전체 검토표}\par\medskip
명시적 모형 변수 중요도 방법을 사용한 __N__편의 주제, 목적변수, 입력 수, 변수 중요도 방법, 표준 변수군,
선정 규칙과 후속 통계추론을 연구별로 연결하였다. 표준 변수군은 원문 변수 중요도 결과에 구체적인
변수명이 있을 때만 코딩했으며, 방법명만 제시된 경우 NR로 남겼다.\par\medskip
\footnotesize
\setlength{\tabcolsep}{2.5pt}\renewcommand{\arraystretch}{1.12}
\begin{longtable}{P{2.7cm}P{2.7cm}P{1.0cm}P{2.4cm}P{3.2cm}P{3.5cm}P{8.0cm}}
\caption{명시적 변수 중요도 연구 __N__편의 전체 감사표.}\label{tab:fullimportance}\\
\toprule 연구·연도·주제 & 목적변수 & 입력 수 & 변수 중요도 방법 & 표준 변수군 & 선정 규칙·후속 추론 & 변수 중요도 결과 \\\midrule
\endfirsthead
\multicolumn{7}{l}{\small 표 1 계속}\\\toprule 연구·연도·주제 & 목적변수 & 입력 수 & 변수 중요도 방법 & 표준 변수군 & 선정 규칙·후속 추론 & 변수 중요도 결과 \\\midrule
\endhead
\midrule\multicolumn{7}{r}{다음 페이지에 계속}\\\bottomrule\endfoot
\bottomrule\endlastfoot
'''
 body=[]
 for r in rows:
  sel=f"{r['중요변수 선정 상태']}; {r['선정 규칙']}; 후속 추론: {r['후속 통계추론']}"
  body.append(' & '.join([esc(f"{r['연구키']} ({r['연도']}); {r['주제']}"),esc(r['목적변수']),esc(r['입력 변수 수']),esc(r['변수 중요도 방법']),esc(r['표준 변수군']),esc(sel),esc(r['변수 중요도 결과'])])+r' \\')
 tex.write_text(head.replace('__N__',str(n_studies))+'\n'.join(body)+'\n\\end{longtable}\n\\end{document}\n')
 subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',tex.name],cwd=OUT,check=True,stdout=subprocess.DEVNULL)
 print(xlsx); print(tex.with_suffix('.pdf'))

if __name__=='__main__':main()
