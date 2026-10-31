"""Check the actual release: canonical preservation, readable results and rendered pages."""
from pathlib import Path
import re,json,hashlib
from collections import Counter
import fitz
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/cycle_081'

def items(text):
    return {c[1].strip('`'):c for l in text.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*`',l)
            for c in [[s.strip() for s in l.strip('|').split('|')]]}

def main():
    checks={};details={}
    protocol=(ROOT/'KNHANES_ML_study_audit_protocol.md').read_text()
    old=items((ROOT/'prompts/implementation_records/cycle_080/protocol_before_ko.md').read_text());new=items(protocol)
    checks['canonical_entirely_english']=not re.search('[가-힣]',protocol)
    checks['382_item_ids_and_order_preserved']=list(old)==list(new) and len(new)==382
    errors=[]
    for k,row in old.items():
        if len(new[k])!=17:errors.append([k,'column_count'])
        for i,c in enumerate(row):
            # English-only technical cells are immutable, including response atoms,
            # unit/linkage/applicability, mappings, official IDs and components.
            if i!=8 and not re.search('[가-힣]',c) and c!=new[k][i]:
                from protocol_metadata_corrections import declared_change
                if not declared_change(k,i,c,new[k][i]): errors.append([k,i,c,new[k][i]])
    checks['nontranslated_metadata_unchanged']=not errors;details['metadata_differences']=errors
    from p2_item_spec import codes
    checks['translated_choice_codes_preserved']=all(codes(row[10])==codes(new[k][10]) for k,row in old.items())
    checks['boundary_and_official_rules_retained']=all(t in protocol for t in ['R2','R1','R0','critical-failure rule','not automatic domain failure','SOURCE_REVIEWED','PENDING/null','class weights are not sampling weights','BMJ 2025;388:e082505','HIGH means high quality'])
    baseline=ROOT/'project_archive/submission_versions/v079_before_cycle_20260924_090253/manifest.json'
    b=json.loads(baseline.read_text()); changed=[];count=0
    for r in b['files']:
        if r['path'].startswith(('data/protocol_v1_2/P1/','data/protocol_v1_2/P2_blinded/','data/protocol_v1_2/final/')):
            count+=1
            if hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']:changed.append(r['path'])
    checks['baseline_P1_P2_final_files_unchanged']=count>=666 and not changed
    details['locked_files_compared']=count;details['changed_locked_files']=changed
    s=(ROOT/'manuscript/bmc_supplementary.tex').read_text()
    sequence=re.findall(r'bfseries Supplementary (Table|Figure) S(\d+)\.',s)
    # S9 is one numbered table with three continued panels.
    unique=[]
    for x in sequence:
        if not unique or unique[-1]!=x:unique.append(x)
    expected=[('Table','1'),('Table','3'),('Table','4'),('Table','5'),('Table','6'),('Table','8'),('Figure','1'),('Table','2'),('Table','9')]
    checks['combined_order_protocol_then_results_last']=unique==expected;details['combined_order']=unique
    checks['public_only_tables_and_figures']=not re.search(r'Supplementary (Document|Data)\s+S\d',s)
    checks['no_long_supplement_prose_sections']=not re.search(r'\\(?:sub)*section\{',s)
    w=load_workbook(ROOT/'manuscript/supplementary/tables/Supplementary_Table_S09_Study_protocol_audit_results.xlsx',read_only=True,data_only=True)
    master=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
    h,*records=list(master['STUDIES'].values);byid={r[0]:dict(zip(h,r)) for r in records}
    checks['24_lossless_workbook_sheets']=len(master.sheetnames)==24
    from study_audit_table import responses,readable,participant_count
    real_errors=[];coverage={}
    for sheet in w:
        if sheet.title=='Panel D':continue
        rows=list(sheet.values);ids=[]
        for row in rows[1:]:
            sid=str(row[0]).split(';')[0];ids.append(sid)
            d=json.loads((ROOT/f'data/protocol_v1_2/final/{sid}_final.json').read_text())
            if sheet.title=='Panel A':
                if row[2]!=participant_count(byid[sid]['D_final_sample']) or row[3]!=responses(d,'OUT10'):real_errors.append([sid,'A'])
            elif sheet.title=='Panel B':
                if row[1]!=responses(d,'VAL02') or row[3]!=responses(d,'SUR10'):real_errors.append([sid,'B'])
            elif sheet.title=='Panel C':
                if responses(d,'PD_OVERALL') not in row[1] or responses(d,'PE_OVERALL') not in row[2]:real_errors.append([sid,'C'])
        coverage[sheet.title]=len(ids)
        if set(ids)!=set(byid) or len(ids)!=220:real_errors.append([sheet.title,'coverage'])
    checks['audit_panels_cover_all_220_and_real_values']=not real_errors and len(coverage)==3
    audit_pdf=fitz.open(ROOT/'manuscript/supplementary/pdf/Supplementary_Table_S09_Study_protocol_audit_results.pdf')
    printed=' '.join(p.get_text() for p in audit_pdf)
    counts=Counter(re.findall(r'KHM\d{3}(?=;)',printed))
    checks['printed_audit_has_every_study_in_all_three_panels']=set(counts)==set(byid) and all(n==3 for n in counts.values())
    checks['public_audit_english_explanations']=not re.search('[가-힣]',printed)
    details['printed_audit_studies']=len(counts)
    details['audit_panel_coverage']=coverage;details['audit_value_errors']=real_errors
    w.close();master.close()
    bounds=[];pages={};font_stats={};missing_figures=[]
    for name in ['bmc_main','bmc_main_ko','bmc_supplementary']:
        doc=fitz.open(ROOT/f'manuscript/{name}.pdf');pages[name]=len(doc)
        for i,page in enumerate(doc):
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        x0,y0,x1,y1=span['bbox']
                        if x0<-.5 or y0<-.5 or x1>page.cropbox.width+.5 or y1>page.cropbox.height+.5:bounds.append([name,i+1,span['text'],span['bbox']])
        if name=='bmc_supplementary':continue
        tex='\n'.join(re.split(r'(?<!\\)%',l)[0] for l in (ROOT/f'manuscript/{name}.tex').read_text().splitlines())
        for f in re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',tex):
            fig=fitz.open(ROOT/'manuscript'/f)[0]
            texts=[sp for b in fig.get_text('dict')['blocks'] for l in b.get('lines',[]) for sp in l['spans'] if len(sp['text'].strip())>3]
            anchor=max(texts,key=lambda t:len(t['text']))['text'].strip()
            found=[(i,p) for i,p in enumerate(doc) if anchor in p.get_text()]
            if not found:missing_figures.append([name,f,anchor]);continue
            i,page=found[0]
            source=next(sp for sp in texts if sp['text'].strip()==anchor)
            target=next(sp for b in page.get_text('dict')['blocks'] for l in b.get('lines',[]) for sp in l['spans'] if sp['text'].strip()==anchor)
            ratio=target['size']/source['size']
            minsize=min(sp['size'] for sp in texts if sp['text'].strip() not in ('dev','eval'))*ratio
            font_stats[name+'/'+Path(f).stem]={'page':i+1,'minimum_text_pt':round(minsize,2),'scale':round(ratio,4)}
    checks['pdf_text_inside_page']=not bounds
    checks['all_24_active_figures_found_in_actual_manuscripts']=len(font_stats)==24 and not missing_figures
    checks['final_main_figure_font_floor_6_5pt']=all(v['minimum_text_pt']>=6.5 for v in font_stats.values())
    details.update(pdf_pages=pages,out_of_page_text=bounds,rendered_figure_fonts=font_stats,missing_figures=missing_figures)
    for name in ['bmc_main','bmc_main_ko','bmc_supplementary']:
        log=(ROOT/f'build/submission/{name}.log').read_text()
        checks[name+'_no_overflow_or_missing_glyphs']=not re.search(r'Overfull \\[hv]box|Missing character:|undefined references|undefined citations',log)
    report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'details':details}
    (OUT/'verification_081.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],json.dumps(checks,indent=2));assert all(checks.values())
if __name__=='__main__':main()
