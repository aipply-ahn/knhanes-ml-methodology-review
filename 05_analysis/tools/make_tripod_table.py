"""Generate English and Korean TRIPOD+AI manuscript tables from audited records."""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROB = os.path.join(ROOT, "data", "probast")
OUT = os.path.join(ROOT, "manuscript", "submission")
REFS = json.load(open(os.path.join(ROOT, "references", "refs.json"), encoding="utf-8"))
INCLUDED = {r["key"] for r in REFS if r.get("verdict") == "INCLUDE"}

ITEMS = [
    ("Title", "제목", "title_design", "Study design identified in title", "제목에 연구설계 제시"),
    ("Abstract", "초록", "abstract_structured", "Structured abstract", "구조화 초록"),
    ("Introduction", "서론", "background_objective", "Background and objectives stated", "배경과 목적 제시"),
    ("Methods", "방법", "data_source", "Data source and study period stated", "자료원과 연구기간 제시"),
    ("Methods", "방법", "participants_eligibility", "Participant eligibility criteria", "대상자 적격기준"),
    ("Methods", "방법", "outcome_definition", "Outcome defined", "결과변수 정의"),
    ("Methods", "방법", "predictors_description", "Predictors described", "예측변수 설명"),
    ("Methods", "방법", "sample_size_justification", "Sample size justified", "표본크기 근거"),
    ("Methods", "방법", "missing_data", "Missing-data handling described", "결측치 처리 설명"),
    ("Methods", "방법", "model_building", "Model-building procedure described", "모형 구축 절차 설명"),
    ("Methods", "방법", "model_performance_measures", "Performance measures defined", "성능지표 정의"),
    ("Methods", "방법", "model_evaluation", "Model evaluation described", "모형 평가 설명"),
    ("Results", "결과", "results_participants", "Participant flow and characteristics", "대상자 흐름과 특성"),
    ("Results", "결과", "results_performance", "Performance results reported", "성능 결과 보고"),
    ("Discussion", "고찰", "limitations", "Limitations discussed", "제한점 논의"),
    ("Other information", "기타 정보", "funding", "Funding stated", "연구비 제시"),
    ("Open science", "공개과학", "data_availability", "Data availability statement", "자료 이용가능성 문구"),
    ("Open science", "공개과학", "code_availability", "Code availability", "코드 공개"),
    ("Open science", "공개과학", "model_availability", "Final model available for use", "사용 가능한 최종 모형"),
]

records=[]
for p in glob.glob(os.path.join(PROB, "*.json")):
    d=json.load(open(p, encoding="utf-8"))
    # Detailed reporting synthesis is restricted to the final full-report corpus.
    # The three unretrieved reports remain in the retrieval ledger only.
    if d.get("key") in INCLUDED and d.get("source") == "full_text":
        records.append(d)
full=[d for d in records if d.get("source") == "full_text"]

def count(ds, key):
    vals=[(d.get("tripod") or {}).get(key) for d in ds]
    vals=[v for v in vals if v != "NA"]
    yes=sum(v == "Y" for v in vals)
    return yes, len(vals), 100*yes/len(vals) if vals else 0

def make(lang):
    ko=lang=="ko"
    fn="table_tripod_ko.tex" if ko else "table_tripod.tex"
    caption=(f"TRIPOD+AI 보고 충실도. 분모는 비해당 항목을 제외하였다. 원문 확보 열은 원문을 확보한 {len(full)}편으로 제한하였다."
             if ko else f"TRIPOD+AI reporting adherence. Denominators exclude not-applicable items. Full-text columns are restricted to the {len(full)} studies whose full report was obtained.")
    lines=["\\begin{table}[htbp]", "\\centering", f"\\caption{{{caption}}}", "\\label{tab:tripod}", "\\small", "\\begin{tabular}{lrrrr}", "\\toprule",
           (f"항목 & \\multicolumn{{2}}{{c}}{{전체 (n={len(records)})}} & \\multicolumn{{2}}{{c}}{{원문 확보 (n={len(full)})}} \\\\" if ko else f"Item & \\multicolumn{{2}}{{c}}{{All studies (n={len(records)})}} & \\multicolumn{{2}}{{c}}{{Full text (n={len(full)})}} \\\\"),
           "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}", (" & 보고 & \\% & 보고 & \\% \\\\" if ko else " & Reported & \\% & Reported & \\% \\\\"), "\\midrule"]
    previous_group = None
    for group_en,group_ko,key,en,kr in ITEMS:
        group = group_ko if ko else group_en
        if group != previous_group:
            lines.append(f"\\addlinespace[2pt]\\multicolumn{{5}}{{l}}{{\\textit{{{group}}}}} \\\\")
            previous_group = group
        a=count(records,key); f=count(full,key); label=kr if ko else en
        lines.append(f"{label} & {a[0]}/{a[1]} & {a[2]:.1f} & {f[0]}/{f[1]} & {f[2]:.1f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    open(os.path.join(OUT,fn),"w",encoding="utf-8").write("\n".join(lines)+"\n")

make("en"); make("ko")
print(f"TRIPOD tables: all={len(records)}, full={len(full)}")
