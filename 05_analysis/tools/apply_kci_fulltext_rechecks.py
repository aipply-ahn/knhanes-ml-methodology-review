"""Apply explicit source-based rechecks as an overlay; never rewrite raw screening."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def build():
    entries=[]
    for uid,key,reason,pages,rationale in [
        ('ART002908025','kim2022classification','EXCLUDE_NO_DIRECT_KNHANES_ANALYSIS',[4,5],'Methods pp54-55, Figure 2 and Table 4: 1,192 food items from the 2010 food exchange table and national standard food composition table; decision-tree food classification. KNHANES is background to food-list development, not the directly analysed survey dataset.'),
        ('ART003146879','wonshik2024cbfam','EXCLUDE_NO_ELIGIBLE_ML',[2,3,4],'Full text pp39-41, sections 3.2-4.2 and Figures 1-3: KNHANES 2020/2021 rows are integrated with COVID-19 counts using conditional alignment in pandas/numpy. Evaluation is Cronbach alpha (0.573 versus 0.514), not a fitted or evaluated eligible ML model; future epidemiological analysis is proposed, not performed.')]:
        path=f'references/pdf/{key}.pdf'
        entries.append(dict(uid='kci:'+uid,previous_status='RECHECK_FULLTEXT',current_status=reason,source_pdf=path,source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),pdf_pages=pages,rationale=rationale,review_scope='AI-assisted full-text and source-page review; no independent human adjudication claimed'))
    report=dict(schema='kci_fulltext_rechecks_v1',records=entries,scope='Two historical non-advanced records resolved by current full-text review; historical screening partitions and the 1,499-candidate denominator are unchanged. This does not establish exhaustive screening or all-candidate retrieval totals.')
    (ROOT/'results/derived/kci_fulltext_rechecks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'results/derived/final_selection_flow.json';f=json.loads(p.read_text());t=f['terminology_screen']
    t['unresolved_fulltext_recheck_uids']=[];t['resolved_fulltext_rechecks']=entries
    t['interpretation']=report['scope'];t['current_recheck_source']='results/derived/kci_fulltext_rechecks.json'
    p.write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n')
    return report
if __name__=='__main__':build()
