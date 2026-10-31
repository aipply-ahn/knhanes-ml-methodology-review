"""벤치마크 리뷰 — raw → 선별 → 판정 배치 → refs/INDEX. 한 파일에 단계별 서브커맨드.

    python tools/bench_pipeline.py screen        # 규칙 선별 + 배치 생성 (results/derived/review/bench_<nn>.json)
    python tools/bench_pipeline.py merge         # review/bench_verdict_*.json → results/derived/bench_verdicts.json
    python tools/bench_pipeline.py refs          # → references/benchmark_reviews.json · BENCHMARK_REVIEWS.md
    python tools/fetch_pdf.py --refs references/benchmark_reviews.json --verdicts INCLUDE,UNCERTAIN
    python tools/bench_pipeline.py md            # PDF → references/md/bench_<key>.md
    python tools/bench_pipeline.py batches       # 구조 추출 배치 → 에이전트 (BENCH_EXTRACT_GUIDE.md)
    python tools/bench_pipeline.py extract_merge # data/bench_extraction/*.json → data/BENCH_EXTRACTION.md
"""
import csv, glob, sys
from collections import Counter
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

BREFS = os.path.join(REF, "benchmark_reviews.json")
BV = os.path.join(DER, "bench_verdicts.json")
DS_RE = re.compile(r"NHANES|KNHANES|UK Biobank|MIMIC|eICU|PhysioNet|KoGES|CHARLS|\bELSA\b|Health and Retirement|Survey of Health, Ageing|Framingham|\bSEER\b|TCGA|ADNI|All of Us|Million Veteran|NHIRD|CPRD|Kadoorie|Taiwan Biobank|Estonian|FinnGen|BioBank Japan|\bHUNT\b|Rotterdam|Whitehall|NHATS|\bMESA\b|\bARIC\b|Optum|MarketScan|Medicare|Veterans|Kaiser|\bN3C\b|PCORnet|OMOP|OHDSI|TriNetX|Flatiron|Community Health Survey|KCHS|National Health Insurance|NHIS|HIRA|Health Panel|KLoSA|CHNS|Demographic and Health Survey|BRFSS|Health Interview Survey|MEPS|JAGES|CLHLS|Global Burden|Nurses' Health|Women's Health Initiative|registers|JMDC", re.I)
GENERIC_DS = re.compile(r"^(Medicare|Veterans|NHIS|registers|Kaiser)$", re.I)
ML_RE = re.compile(r"machine learning|deep learning|artificial intelligence|predictive model|prediction model|data mining|neural network|\bAI\b|\bML\b", re.I)
METHOD_RE = re.compile(r"TRIPOD|PROBAST|reporting|risk of bias|methodolog|quality of|validation|calibration|fairness|\bbias\b|transparen|reproducib|generali[sz]ab|missing data|class imbalance|survey weight", re.I)
SRC_RE = re.compile(r"electronic health|electronic medical|\bEHR|\bEMR|claims|administrative|insurance|biobank|cohort|population-based|national survey|health survey|survey data|complex survey|registr|real-world|tabular|structured data|routinely collected|public health|epidemiolog|longitudinal|panel data|wearable|big data", re.I)
REV_RE = re.compile(r"review|survey of|scoping|systematic|overview|bibliometric|state of the art|state-of-the-art|landscape|meta-analysis|meta-research|umbrella", re.I)


def screen():
    raw = load(sorted(glob.glob(os.path.join(RAW, "bench_epmc_*.json")))[-1])
    rows = []
    for r in raw["records"]:
        t, a = r.get("title") or "", r.get("abstract") or ""
        is_rev = bool(REV_RE.search(t)) or "Review" in " ".join(r.get("pub_type") or [])
        ml_t = bool(ML_RE.search(t))
        ds_t = [m.group(0) for m in DS_RE.finditer(t) if not GENERIC_DS.match(m.group(0))]
        ds_a = Counter(m.group(0).lower() for m in DS_RE.finditer(a) if not GENERIC_DS.match(m.group(0)))
        if not is_rev:
            tier = "--"
        elif ds_t: tier = "T1"                                   # 명명 데이터셋이 제목에 (ML 은 초록에 있으면 됨)
        elif not ml_t: tier = "--"
        elif SRC_RE.search(t): tier = "T2"                        # 자료유형이 제목에
        elif ds_a and max(ds_a.values()) >= 2: tier = "T3"        # 데이터셋이 초록에 2회 이상
        elif METHOD_RE.search(t) and re.search(r"prediction|prognos|clinical|health", t, re.I): tier = "T4"  # 방법·보고품질
        else: tier = "--"
        rows.append(dict(uid=r.get("doi") or f"pmid:{r.get('pmid')}" or r["epmc_id"], tier=tier, layers=r["bench_layers"],
                         datasets_in_ta=sorted(set(m.group(0) for m in DS_RE.finditer(t + " " + a)))[:8],
                         year=r.get("year"), cited=r.get("cited"), journal=r.get("journal"), title=t,
                         abstract=re.sub(r"<[^>]+>", " ", a)[:3500], doi=r.get("doi"), pmid=r.get("pmid"), pmcid=r.get("pmcid"),
                         authors=r.get("authors"), pub_type=r.get("pub_type"), is_oa=r.get("is_oa"), fulltext_urls=r.get("fulltext_urls")))
    cnt = Counter(x["tier"] for x in rows)
    dump(dict(screened_on=time.strftime("%Y-%m-%d"), tiers=dict(cnt), rows=rows), os.path.join(DER, "bench_screen.json"))
    V = load(BV) if os.path.exists(BV) else {}
    todo = [x for x in rows if x["tier"] in ("T1", "T2", "T3", "T4") and x["uid"] not in V]
    seen = set(); todo = [x for x in todo if not (x["uid"] in seen or seen.add(x["uid"]))]
    todo.sort(key=lambda x: (x["tier"], -(x["cited"] or 0)))
    out = os.path.join(DER, "review"); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "bench_batch_*.json")): os.remove(f)
    size = 40
    for i in range(0, len(todo), size):
        json.dump(todo[i:i + size], open(os.path.join(out, f"bench_batch_{i // size + 1:02d}.json"), "w"), ensure_ascii=False, indent=1)
    print(f"  선별 {len(rows)} → {dict(cnt)} · 판정 대상 {len(todo)} → 배치 {(len(todo) + size - 1) // size}")


def merge():
    V = load(BV) if os.path.exists(BV) else {}
    n = 0
    for f in sorted(glob.glob(os.path.join(DER, "review", "bench_verdict_*.json"))):
        for it in load(f):
            if it.get("uid") and it.get("verdict") in ("INCLUDE", "EXCLUDE", "UNCERTAIN"):
                it["source_file"] = os.path.basename(f); V[it["uid"]] = it; n += 1
    dump(V, BV)
    print(f"  항목 {n} · 누적 {len(V)} → {dict(Counter(v['verdict'] for v in V.values()))}")


def refs():
    S = {x["uid"]: x for x in load(os.path.join(DER, "bench_screen.json"))["rows"]}
    V = load(BV)
    old = {r["uid"]: r for r in load(BREFS)} if os.path.exists(BREFS) else {}
    refs, keys = [], Counter()
    for uid, v in V.items():
        if v["verdict"] == "EXCLUDE": continue
        s = S.get(uid)
        if not s: continue
        first = (s.get("authors") or "").split(",")[0]
        key = "bench_" + bibkey(first, s.get("year"), s.get("title"))
        keys[key] += 1
        if keys[key] > 1: key += "abcdefgh"[keys[key] - 2]
        o = old.get(uid, {})
        refs.append(dict(key=key, uid=uid, verdict=v["verdict"], bench_type=v.get("bench_type"), dataset_focus=v.get("dataset_focus"),
                         review_type=v.get("review_type"), n_included=v.get("n_included"), why_benchmark=v.get("why_benchmark"),
                         reason=v.get("reason"), title=s["title"], year=s["year"], journal=s["journal"], authors=s["authors"],
                         cited=s["cited"], doi=s["doi"], pmid=s["pmid"], pmcid=s["pmcid"], abstract=s["abstract"], tier=s["tier"],
                         datasets=s["datasets_in_ta"], is_oa=s["is_oa"], fulltext_urls=s["fulltext_urls"],
                         pdf_file=o.get("pdf_file") if o.get("pdf_file") and os.path.exists(os.path.join(REF, "pdf", o["pdf_file"])) else None,
                         pdf_src=o.get("pdf_src"), pdf_tried=o.get("pdf_tried", False)))
    # 프리프린트/출판본 중복 — 정규화 제목이 같으면 출판본만 센다 (PROTOCOL D11 과 같은 규칙)
    PRE_RE = re.compile(r"research square|medrxiv|biorxiv|preprint|ssrn|arxiv|osf|authorea", re.I)
    groups = {}
    for r in refs:
        if r["verdict"] == "EXCLUDE": continue
        groups.setdefault(norm_title(r.get("title"))[:70], []).append(r)
    for g in groups.values():
        if len(g) < 2: continue
        g.sort(key=lambda r: (bool(PRE_RE.search((r.get("journal") or "") + " " + (r.get("doi") or ""))), not r.get("pmid"), -(r.get("cited") or 0)))
        for d in g[1:]:
            d["duplicate_of"] = g[0]["key"]; d["verdict_orig"] = d["verdict"]; d["verdict"] = "DUPLICATE"
    refs.sort(key=lambda r: (r["verdict"], r.get("bench_type") or "", -(r["cited"] or 0)))
    dump(refs, BREFS)
    inc = [r for r in refs if r["verdict"] == "INCLUDE"]; unc = [r for r in refs if r["verdict"] == "UNCERTAIN"]
    dup = [r for r in refs if r["verdict"] == "DUPLICATE"]
    L = []; A = L.append
    A("# 벤치마크 리뷰 — 바이오헬스 데이터셋 × ML 리뷰 논문 전수조사\n")
    A(f"생성 {time.strftime('%Y-%m-%d')} · `python tools/bench_pipeline.py refs` 자동생성. 판정은 `results/derived/bench_verdicts.json`. PDF 는 `pdf/<key>.pdf`.\n")
    A("| | 건수 | PDF |"); A("|---|---:|---:|")
    for t in ("DATASET", "DATATYPE", "METHOD"):
        g = [r for r in inc if r.get("bench_type") == t]
        A(f"| ✅ {t} | {len(g)} | {sum(1 for r in g if r.get('pdf_file'))} |")
    A(f"| ❓ UNCERTAIN | {len(unc)} | {sum(1 for r in unc if r.get('pdf_file'))} |")
    A(f"| ♻ DUPLICATE (프리프린트 등, 출판본에 합침) | {len(dup)} | |"); A("")
    A("## 요약표 (포함, 피인용순)\n")
    A("| key | 유형 | 자료 초점 | 리뷰 유형 | 포함 연구 수 | 연도 | 저널 | 피인용 | 왜 본보기인가 |"); A("|---|---|---|---|---:|---:|---|---:|---|")
    for r in sorted(inc, key=lambda r: -(r["cited"] or 0)):
        A(f"| `{r['key']}` | {r.get('bench_type')} | {(r.get('dataset_focus') or '')[:40]} | {r.get('review_type') or ''} | {r.get('n_included') or ''} | {r['year']} | {(r['journal'] or '')[:35]} | {r['cited'] or ''} | {(r.get('why_benchmark') or '')[:90]} |")
    A("")
    for title, rows in (("✅ 포함", inc), ("❓ 보류", unc), ("♻ 중복", dup)):
        A(f"## {title} — {len(rows)}건\n")
        for r in sorted(rows, key=lambda r: (r.get("bench_type") or "", -(r["cited"] or 0))):
            pdf = f"[PDF](pdf/{r['pdf_file']})" if r.get("pdf_file") else "_PDF 없음_"
            doi = f"[doi](https://doi.org/{r['doi']})" if r.get("doi") else ""
            A(f"### `{r['key']}` ({r['year']}) {r.get('bench_type') or ''} · {r.get('review_type') or ''}")
            A(f"**{r['title']}**  "); A(f"{(r['authors'] or '')[:100]}  "); A(f"{r['journal'] or ''}{' · 피인용 ' + str(r['cited']) if r.get('cited') else ''}  ")
            A(" · ".join(x for x in (doi, pdf) if x) + "  ")
            A(f"자료 초점: {r.get('dataset_focus') or '?'} · 포함 연구 {r.get('n_included') or '?'}  ")
            if r.get("why_benchmark"): A(f"**왜 본보기인가.** {r['why_benchmark']}  ")
            ab = re.sub(r"\s+", " ", r.get("abstract") or "").strip()
            A(""); A("> " + (ab[:800].rsplit(" ", 1)[0] + " …" if len(ab) > 800 else ab) if ab else "> _초록 없음_"); A("")
    open(os.path.join(REF, "BENCHMARK_REVIEWS.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  BENCHMARK_REVIEWS.md — 포함 {len(inc)} · 보류 {len(unc)} · PDF {sum(1 for r in inc if r.get('pdf_file'))}")


def md():
    """포함 리뷰의 PDF → references/md/<key>.md (make_paper_md 재사용)."""
    import fitz
    from make_paper_md import header
    R = load(BREFS); MD = os.path.join(REF, "md"); os.makedirs(MD, exist_ok=True)
    n = 0
    for r in R:
        if r["verdict"] == "EXCLUDE": continue
        dst = os.path.join(MD, f"{r['key']}.md")
        if os.path.exists(dst):
            head = open(dst, encoding="utf-8").read(600)
            pdf = os.path.join(REF, "pdf", r.get("pdf_file") or "")
            if not ("full_text: false" in head and r.get("pdf_file") and os.path.exists(pdf)):
                continue
        ab = re.sub(r"\s+", " ", r.get("abstract") or "").strip()
        body = f"## Abstract (from index)\n\n{ab or '_초록 없음_'}\n\n"; full = False
        if r.get("pdf_file") and os.path.exists(os.path.join(REF, "pdf", r["pdf_file"])):
            try:
                doc = fitz.open(os.path.join(REF, "pdf", r["pdf_file"]))
                txt = "".join(f"\n\n<!-- page {i} -->\n\n{pg.get_text('text')}" for i, pg in enumerate(doc, 1))
                if len(txt.strip()) > 500: body += "## Full text (PyMuPDF extraction)\n" + txt; full = True
            except Exception as e:
                body += f"\n_PDF 추출 실패: {e}_\n"
        rr = dict(r, category=r.get("bench_type"))
        open(dst, "w", encoding="utf-8").write(header(rr, full) + body); n += 1
    print(f"  md {n} 생성")


def batches():
    """구조 추출 배치 — results/derived/review/bench_extract_<nn>.json"""
    R = load(BREFS); out = os.path.join(DER, "review")
    done = set(f[:-5] for f in os.listdir(os.path.join(PROJ, "data", "bench_extraction"))) if os.path.isdir(os.path.join(PROJ, "data", "bench_extraction")) else set()
    rows = []
    for r in R:
        if r["verdict"] != "INCLUDE" or r["key"] in done: continue  # DUPLICATE 는 자동 제외
        p = os.path.join(REF, "md", f"{r['key']}.md")
        if not os.path.exists(p): continue
        rows.append(dict(key=r["key"], bench_type=r.get("bench_type"), title=r["title"], md=os.path.abspath(p),
                         chars=os.path.getsize(p), full_text="full_text: true" in open(p, encoding="utf-8").read(600)))
    rows.sort(key=lambda x: x["chars"])
    for f in glob.glob(os.path.join(out, "bench_extract_*.json")): os.remove(f)
    bs, cur, size = [], [], 0
    for x in rows:
        if cur and (len(cur) >= 6 or size + x["chars"] > 450_000): bs.append(cur); cur, size = [], 0
        cur.append(x); size += x["chars"]
    if cur: bs.append(cur)
    for i, b in enumerate(bs, 1):
        json.dump(b, open(os.path.join(out, f"bench_extract_{i:02d}.json"), "w"), ensure_ascii=False, indent=1)
    print(f"  추출 대상 {len(rows)} → 배치 {len(bs)}")


def extract_merge():
    R = {r["key"]: r for r in load(BREFS)}
    E = {}
    for f in glob.glob(os.path.join(PROJ, "data", "bench_extraction", "*.json")):
        try: d = load(f); E[d.get("key") or os.path.basename(f)[:-5]] = d
        except Exception as e: print("  !!", f, e)
    rows = sorted(E.values(), key=lambda d: (d.get("bench_type") or "", -(R.get(d["key"], {}).get("cited") or 0)))
    F = ["scope", "research_questions", "review_type", "guideline_followed", "databases", "search_date", "search_string", "flow",
         "inclusion_criteria", "exclusion_criteria", "screening_process", "n_included", "extraction_items", "quality_appraisal",
         "synthesis", "tables_figures", "taxonomy", "key_findings", "reporting_gaps_found", "recommendations", "limitations",
         "template_value", "notes", "source"]
    KO = dict(scope="범위", research_questions="연구질문", review_type="리뷰 유형", guideline_followed="지침·등록", databases="검색 DB",
              search_date="검색일", search_string="검색식", flow="문헌 흐름", inclusion_criteria="포함 기준", exclusion_criteria="제외 기준",
              screening_process="선별 절차", n_included="포함 수", extraction_items="추출 항목", quality_appraisal="품질 평가",
              synthesis="종합 방식", tables_figures="표·그림", taxonomy="분류 체계", key_findings="핵심 발견", reporting_gaps_found="지적된 보고 결함",
              recommendations="권고", limitations="한계", template_value="우리 리뷰에 가져올 것", notes="메모", source="근거")
    def s(v):
        if v is None: return "—"
        if isinstance(v, list): return "; ".join(str(x) for x in v)
        return str(v).replace("\n", " ").replace("|", "／")
    def norm_rev(v):
        t = s(v).lower()
        if "umbrella" in t or "review of review" in t or "리뷰를 대상" in t: return "umbrella (리뷰의 리뷰)"
        if "bibliometric" in t or "계량서지" in t: return "bibliometric"
        if "meta-analysis" in t or "메타분석" in t: return "meta-analysis"
        if "scoping" in t: return "scoping"
        if "systematic" in t: return "systematic"
        if "narrative" in t or "서술" in t: return "narrative"
        return "미기재"

    TOOLS = [("PROBAST-AI", r"probast[ +-]?ai|probast\+ai"), ("PROBAST", r"probast"),
             ("TRIPOD+AI", r"tripod[ +-]?ai|tripod\+ai"), ("TRIPOD", r"tripod"),
             ("CHARMS", r"charms"), ("QUADAS-2", r"quadas"), ("QUIPS", r"quips"),
             ("CONSORT-AI", r"consort"), ("JBI", r"\bjbi\b"), ("NOS", r"newcastle|\bnos\b"),
             ("CASP", r"\bcasp\b"), ("MMAT", r"\bmmat\b"), ("Cochrane RoB", r"cochrane"),
             ("MI-CLAIM", r"mi-?claim"), ("Luo checklist", r"luo"), ("QualSyst", r"qualsyst"),
             ("자체 도구", r"자체|self-|ad hoc|adapted|수정|자체제작")]

    def tools_of(v):
        t = s(v)
        if not t or t == "—": return ["미기재"]
        found, low = [], t.lower()
        for name, pat in TOOLS:
            if re.search(pat, low):
                if name == "PROBAST" and "PROBAST-AI" in found: continue
                if name == "TRIPOD" and "TRIPOD+AI" in found: continue
                found.append(name)
        if found: return found
        if re.search(r"없음|미시행|not (used|performed)|no (formal )?(quality|risk)", low): return ["없음 (평가 안 함)"]
        return ["미기재"]

    def guide_of(v):
        t = s(v).lower(); out = []
        if re.search(r"prisma[ -]?scr|scoping review", t): out.append("PRISMA-ScR")
        elif "prisma" in t: out.append("PRISMA")
        if re.search(r"prospero|crd4|사전등록|registered", t): out.append("사전등록(PROSPERO 등)")
        return out or ["미기재"]

    ITEM_CAT = [("자료원·데이터셋", r"데이터ïì?셋|자료원|data ?(source|set)|dataset|코호트|cohort|자료 ?출처"),
                ("표본 크기·사건 수", r"표본|sample size|\bn\b수|참여자|관측치|event|사건 수|epv"),
                ("입력변수·특징", r"변수|예측변수|predictor|feature|특징|입력"),
                ("변수 선택", r"변수 ?선택|feature selection|선별"),
                ("결측 처리", r"결측|missing|imputation|대치"),
                ("클래스 불균형", r"불균형|imbalance|smote|oversampl|undersampl"),
                ("전처리·정규화", r"전처리|preprocess|정규화|스케일|encoding|표준화"),
                ("알고리즘·모델", r"알고리즘|algorithm|모형|모델|model type|기법"),
                ("하이퍼파라미터·튜닝", r"하이퍼|hyperparam|tuning|튜닝|그리드"),
                ("검증 방식", r"검증|validation|cross-?valid|split|hold-?out|외부"),
                ("성능 지표", r"성능|performance|auc|auroc|정확도|accuracy|c-?index|판별|discrimination"),
                ("보정(calibration)", r"보정|calibration"),
                ("해석가능성·XAI", r"해석|shap|lime|xai|explainab|interpretab|중요도|importance"),
                ("결과변수·과제", r"결과변수|outcome|타겟|target|과제|task|예측 ?대상"),
                ("연구 설계·국가·연도", r"연구 ?설계|study design|국가|country|연도|year|출판"),
                ("코드·데이터 공개", r"코드|code|공개|availab|재현|reproduc|github"),
                ("임상 적용·배포", r"임상|clinical|배포|deploy|implement|의사결정"),
                ("비뚤림·품질 판정", r"비뚤림|bias|품질|quality|probast|tripod"),
                ("공정성·형평", r"공정|fairness|형평|equity|인종|race|성별 편"),
                ("설문 가중치·복합표본설계", r"복합표본|표본\s?가중치|설문\s?가중치|survey weight|sampling weight|design weight|complex (survey|sampling)|svyset|design-based|설계기반"),
                ("모델·클래스 가중치 (설문 가중치 아님)", r"class weight|모델 가중치|모형 가중치|feature weight|attention weight|edge weight|시간 ?가중")]

    def item_cats(x):
        t = str(x).lower(); out = []
        for name, pat in ITEM_CAT:
            if re.search(pat, t): out.append(name)
        return out or ["기타"]

    L = []; A = L.append
    A("# 벤치마크 리뷰 — 구조 추출 정리\n")
    A(f"생성 {time.strftime('%Y-%m-%d')} · `python tools/bench_pipeline.py extract_merge`. 원본 `data/bench_extraction/<key>.json`. 지침 `tools/BENCH_EXTRACT_GUIDE.md`. 후보 목록 `references/BENCHMARK_REVIEWS.md`.\n")
    A(f"총 {len(rows)} 편 · 전문 근거 {sum(1 for d in rows if d.get('source') == 'full_text')} · 초록만 {sum(1 for d in rows if d.get('source') != 'full_text')}\n")
    A("## 집계\n")
    c = Counter(norm_rev(d.get("review_type")) for d in rows)
    A("**리뷰 유형**  "); A("| 유형 | 건수 |"); A("|---|---:|")
    for v, n in c.most_common(): A(f"| {v} | {n} |")
    A("")
    c = Counter(t for d in rows for t in tools_of(d.get("quality_appraisal")))
    A("**품질 평가 도구** (한 리뷰가 여러 도구 사용 가능)  "); A("| 도구 | 리뷰 수 |"); A("|---|---:|")
    for v, n in c.most_common(): A(f"| {v} | {n} |")
    A("")
    c = Counter(t for d in rows for t in guide_of(d.get("guideline_followed")))
    A("**보고 지침·등록**  "); A("| 값 | 리뷰 수 |"); A("|---|---:|")
    for v, n in c.most_common(): A(f"| {v} | {n} |")
    A("")
    c = Counter()
    for d in rows:
        for cat in set(cat for x in (d.get("extraction_items") or []) for cat in item_cats(x)): c[cat] += 1
    A("**추출 항목 — 범주별 (몇 편의 리뷰가 이 항목을 뽑았나)**  "); A("| 추출 항목 범주 | 리뷰 수 |"); A("|---|---:|")
    for v, n in c.most_common(): A(f"| {v} | {n} |")
    A("")
    ns = [d.get("n_included") for d in rows if isinstance(d.get("n_included"), int) and 0 < d["n_included"] < 5000]
    if ns:
        ns.sort()
        A(f"**포함 연구 수 분포** (n={len(ns)}, 5,000 미만): 중앙값 {ns[len(ns)//2]} · 사분위 {ns[len(ns)//4]}–{ns[3*len(ns)//4]} · 범위 {ns[0]}–{ns[-1]}\n")
    A("## 요약표\n"); A("| key | 유형 | 리뷰 유형 | DB | 포함 수 | 품질 평가 | 종합 | 우리 리뷰에 가져올 것 |"); A("|---|---|---|---|---:|---|---|---|")
    for d in rows:
        A(f"| `{d['key']}` | {d.get('bench_type')} | {norm_rev(d.get('review_type'))} | {s(d.get('databases'))[:40]} | {s(d.get('n_included'))} | {', '.join(tools_of(d.get('quality_appraisal')))[:40]} | {s(d.get('synthesis'))[:40]} | {s(d.get('template_value'))[:120]} |")
    A("")
    for t in ("DATASET", "DATATYPE", "METHOD"):
        g = [d for d in rows if d.get("bench_type") == t]
        A(f"# {t} — {len(g)}편\n")
        for d in g:
            r = R.get(d["key"], {})
            A(f"## `{d['key']}` — {r.get('title')}\n")
            A(f"{(r.get('authors') or '')[:100]} · {r.get('journal')} · {r.get('year')} · 피인용 {r.get('cited')} · [md](../references/md/{d['key']}.md)"
              + (f" · [PDF](../references/pdf/{r['pdf_file']})" if r.get("pdf_file") else "") + (f" · [doi](https://doi.org/{r['doi']})" if r.get("doi") else "") + "\n")
            A("| 항목 | 내용 |"); A("|---|---|")
            for k in F: A(f"| {KO[k]} | {s(d.get(k))} |")
            A("")
    open(os.path.join(PROJ, "data", "BENCH_EXTRACTION.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  BENCH_EXTRACTION.md — {len(rows)} 편")


if __name__ == "__main__":
    {"screen": screen, "merge": merge, "refs": refs, "md": md, "batches": batches, "extract_merge": extract_merge}[sys.argv[1]]()
