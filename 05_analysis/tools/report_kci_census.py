"""Build the separate KCI acquisition inventory; never change review verdicts."""
import collections
import csv
import hashlib
import json
import pathlib
import re
import unicodedata
import fitz

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / 'references/_logs/kci_20260905'
RAW = ROOT / 'results/raw/kci_20260905'


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC', s or '').lower() if c.isalnum())


def dump(obj, path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def build():
    census = json.loads((RAW / 'census.json').read_text())
    decisions = json.loads((LOG / 'screening_decisions.json').read_text())
    main = json.loads((ROOT / 'references/refs.json').read_text())
    corpus = json.loads((ROOT / 'results/derived/corpus.json').read_text())['records']
    doi_map = {norm(r.get('doi')): r for r in corpus if r.get('doi')}
    title_map = {norm(r.get('title')): r for r in corpus if r.get('title')}
    rows = []
    for hit in census['records']:
        r = json.loads((LOG / (hit['kci_id'] + '.json')).read_text())
        r['search_matches'] = hit['search_matches']
        decision = decisions.get(r['kci_id'])
        if decision is None:
            decision = {'status': 'NO_ML_EVIDENCE_IN_ABSTRACT',
                        'note': '검색 결과에는 등장하나 제목·초록 점검에서 실제 ML 적용 근거를 확인하지 못함. 최종 리뷰 제외 판정과 별개인 검색 정리 상태.'}
        r['acquisition_screening'] = decision
        match = doi_map.get(norm(r.get('doi'))) if r.get('doi') else None
        match_type = 'DOI' if match else None
        if match is None:
            match = title_map.get(norm(r['title'])) or title_map.get(norm(r.get('title_en')))
            if match: match_type = 'NORMALIZED_EXACT_TITLE'
        r['corpus_match'] = {'uid': match['uid'], 'by': match_type} if match else None
        r['body_language'] = 'UNVERIFIED_NO_PDF'
        if r.get('pdf_file'):
            p = ROOT / 'references/pdf' / r['pdf_file']
            data = p.read_bytes()
            assert data.startswith(b'%PDF-'), p
            doc = fitz.open(stream=data, filetype='pdf')
            assert len(doc) > 0, p
            digest = hashlib.sha256(data).hexdigest()
            if r.get('sha256'): assert r['sha256'] == digest, p
            r.update(sha256=digest, pdf_pages=len(doc), pdf_bytes=len(data))
            body = ''.join(pg.get_text() for pg in list(doc)[1:5])
            letters = len(re.findall(r'[a-zA-Z가-힣]', body))
            hangul = len(re.findall(r'[가-힣]', body))
            r['body_hangul_ratio'] = round(hangul / max(1, letters), 4)
            r['body_language'] = ('UNVERIFIED_TEXT_SPARSE' if letters < 200 else
                                  'ko' if hangul >= 100 and hangul / letters >= .1 else 'en')
            r['body_language_basis'] = 'PDF pages 2–5 extracted letters; Korean >=100 and ratio>=0.10; heuristic, not KCI language metadata'
            if decision['status'].startswith('CANDIDATE') or decision['status'] == 'RECHECK_FULLTEXT':
                folder = ROOT / 'references/kci_pdf'
                folder.mkdir(exist_ok=True)
                link = folder / (r['kci_id'] + '_' + r['pdf_file'])
                target = pathlib.Path('../pdf') / r['pdf_file']
                if not link.exists(): link.symlink_to(target)
                assert link.resolve() == p.resolve()
            r['missing_reason'] = ''
        else:
            attempts = r.get('attempts', [])
            errors = [a.get('error', '') for a in attempts if a.get('error')]
            codes = sorted({a['status'] for a in attempts if a.get('status', 0) >= 400})
            if any('NameResolution' in x for x in errors): reason = '공개 경로 확인, 현재 환경에서 호스트 이름 해석 실패'
            elif any('RemoteDisconnected' in x or 'reset by peer' in x for x in errors): reason = '출판사 연결 종료/차단으로 다운로드 실패'
            elif any('timed out' in x for x in errors): reason = '출판사/원문 경로 응답 시간 초과'
            elif codes: reason = '접근 실패 HTTP ' + ', '.join(map(str, codes))
            else: reason = '접근한 KCI/출판사 경로에서 검증 가능한 공개 PDF를 찾지 못함'
            if r.get('related_version_file'):
                reason = '같은 제목의 학위논문 별도 확보; 이 KCI 학술지판은 미확보. ' + r['related_version_file']
            r['missing_reason'] = reason
        rows.append(r)
    rows.sort(key=lambda r: (-(r.get('year') or 0), r['kci_id']))
    assert len(rows) == census['n_unique'] == len({r['kci_id'] for r in rows})
    dump(rows, ROOT / 'references/kci_refs.json')
    candidates = [r for r in rows if r['acquisition_screening']['status'].startswith('CANDIDATE')]
    recheck = [r for r in rows if r['acquisition_screening']['status'] == 'RECHECK_FULLTEXT']
    missing = [r for r in candidates if not r.get('pdf_file')]
    acquired = [r for r in candidates if r.get('acquisition') == 'DOWNLOADED']
    present = [r for r in candidates if r.get('acquisition') == 'ALREADY_PRESENT']
    counts = dict(search_queries=census['query_count'], search_hits=len(rows),
                  candidates=len(candidates), recheck=len(recheck),
                  candidate_pdf_new=len(acquired), candidate_pdf_existing=len(present),
                  candidate_pdf_missing=len(missing),
                  new_pdf_language=dict(collections.Counter(r['body_language'] for r in acquired)),
                  candidate_kci_status=dict(collections.Counter(r.get('kci_status') for r in candidates)),
                  candidate_corpus_unmatched=sum(not r.get('corpus_match') for r in candidates),
                  candidate_refs_unmatched=sum(not r.get('existing_key') for r in candidates),
                  all_downloaded_files=sum(r.get('acquisition') == 'DOWNLOADED' for r in rows),
                  screening_counts=dict(collections.Counter(r['acquisition_screening']['status'] for r in rows)))
    assert len(candidates) == len(acquired) + len(present) + len(missing), counts
    dump(counts, LOG / 'summary.json')
    columns = ['kci_id', 'year', 'title', 'title_en', 'authors', 'journal', 'kci_status',
               'doi', 'screening', 'screening_note', 'body_language', 'existing_key',
               'existing_verdict', 'corpus_uid', 'acquisition', 'pdf_file', 'pdf_pages',
               'pdf_src', 'sha256', 'missing_reason', 'related_version_file', 'url']
    def flat(r):
        z = dict(r, screening=r['acquisition_screening']['status'],
                 screening_note=r['acquisition_screening']['note'],
                 corpus_uid=(r.get('corpus_match') or {}).get('uid', ''))
        z['authors'] = '; '.join(r.get('authors') or [])
        return {k: z.get(k, '') for k in columns}
    for name, data in [('KCI_CENSUS', rows), ('KCI_CANDIDATES', candidates), ('KCI_PDF_MISSING', missing)]:
        with (ROOT / 'data' / (name + '.tsv')).open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, columns, delimiter='\t', extrasaction='ignore')
            w.writeheader(); w.writerows(flat(r) for r in data)
    labels = {'CANDIDATE_CORE': '핵심 ML 후보', 'CANDIDATE_ADJACENT': '인접 방법 후보', 'RECHECK_FULLTEXT': '범위 재검토'}
    def table(data, missing_only=False):
        out = ['|연도|논문 / KCI|분류|원문|비고|', '|---|---|---|---|---|']
        for r in data:
            title = r['title'].replace('|', '/').replace('\n', ' ')
            pdf = ('[PDF](../references/pdf/' + r['pdf_file'] + ')') if r.get('pdf_file') else '미확보'
            note = r['missing_reason'] if missing_only else ('기존 보유' if r['acquisition'] == 'ALREADY_PRESENT' else '이번 확보' if r.get('pdf_file') else r['missing_reason'])
            out.append(f"|{r.get('year')}|[{title}]({r['url']})|{labels.get(r['acquisition_screening']['status'], r['acquisition_screening']['status'])}|{pdf}|{note}|")
        return '\n'.join(out)
    report = f'''# KCI KNHANES × ML 보완 검색·PDF 확보 — 2026-09-05

프로젝트는 KNHANES에 ML을 실제 적용한 연구의 방법·보고 품질·복합표본설계 처리를 검토한다. 이번 작업은 한국어 및 KCI 수록 문헌 검색과 전문 확보를 보완한 것이다. **아래 후보 수는 최종 리뷰 포함 편수가 아니다.**

- KCI 검색 {census['query_count']}개 조합, 중복 제거 {len(rows)}개 KCI 레코드. 검색 오류 {len(census['failed_queries'])}건.
- 확보·검토 후보 **{len(candidates)}건**: 이번 PDF **{len(acquired)}편**, 기존 보유 **{len(present)}편**, 미확보 **{len(missing)}편**.
- 별도 범위 재검토 **{len(recheck)}건**. 나머지 검색 결과는 실제 ML/KNHANES 적용 근거가 없거나 불명확하다.
- 이번 확보 후보 PDF의 본문 언어 추정: {dict(collections.Counter(r['body_language'] for r in acquired))}. KCI의 `kr` 메타데이터와 실제 본문 언어가 다른 사례가 있어 PDF 2–5쪽 텍스트로 구분했다. 미확보 논문 언어는 확정하지 않았다.
- 후보 중 기존 통합 검색 말뭉치와 DOI/정규화 정확 제목으로 매칭되지 않은 레코드 {counts['candidate_corpus_unmatched']}건. 이는 새 연구임이 확정된 수가 아니며, 한·영 제목 및 출판본 중복 확인이 필요하다.

[후보 TSV](KCI_CANDIDATES.tsv) · [검색 전건 TSV](KCI_CENSUS.tsv) · [미확보 목록](KCI_PDF_MISSING.md) · [PDF 모음](../references/kci_pdf/) · [전체 서지 JSON](../references/kci_refs.json)

## 검색·선별 방법

[KCI 논문 검색](https://www.kci.go.kr/kciportal/po/search/poArtiSearList.kci)의 KEYALL 검색에 자료원 AND 방법을 적용했다. 연도·언어 제한 없이 각 검색의 모든 결과 페이지를 수집했고, 실제 수집 건수와 KCI 표시 건수가 일치하는지 확인했다. KCI ID로 중복 제거했다. **이 검색식으로 회수된 결과의 전수 점검이며, KCI 전체 관련 논문의 완전한 회수를 보장하는 수는 아니다.**

자료원 검색어: {', '.join(census['datasets'])}.

방법 검색어: {', '.join(census['methods'])}.

검색 결과 전건에 제목·초록·키워드 규칙 선별을 적용하고, 후보와 경계 사례는 제목·초록을 수동 점검했으며 일부는 전문을 확인했다. 단순 회귀, 집락표본추출의 cluster, 위험인자 동반 발생의 clustering, 미국 NHANES만 사용한 연구를 ML 적용 후보와 구분했다. 단독 트리·벌점회귀·군집·LCA/LPA 및 연관규칙은 인접 방법 후보로 따로 표시했다. 최종 포함과 tier는 [프로토콜](../planning/PROTOCOL.md)에 따른 전문 심사가 필요하다.

KCI 상태는 수집 시점 표시를 보존했다: {counts['candidate_kci_status']}. KCI 검색 수록과 KCI 등재를 동일하게 취급하지 않는다.

## 확보·검증

KCI가 제공한 원문, 학회·출판사 PDF, 공개 기관 저장소를 이용했다. PDF signature, 파서 열기, 페이지 수, 첫 3쪽 제목 또는 DOI 일치로 파일 정체성을 확인하고 SHA-256을 기록했다. 본문 텍스트는 `references/md/`에 저장했다. 오류 응답·목차·다른 논문 PDF는 확보 성공으로 집계하지 않았다. 미확보는 접근한 공개 경로에서의 결과이며 유료 논문이라는 뜻은 아니다.

조사 초기 확보 후 범위 밖으로 분류된 파일도 감사 추적을 위해 보존했다. 전체 신규 PDF 파일 {counts['all_downloaded_files']}개와 위의 관련 후보 신규 PDF {len(acquired)}개는 다른 집계다. `references/kci_pdf/`에는 후보 및 재검토 문헌의 파일 링크만 모았다.

## 후속 검토에 필요한 발견

- 2009년 「데이터 마이닝을 이용한 당뇨환자의 관리요인에 관한 연구」에서 KNHANES 2005 자료에 신경망·트리·로지스틱 비교가 확인됐다. 프로토콜 D5의 ‘사실상 2010년대 후반부터’라는 설명은 문헌 통합 후 수정 검토가 필요하다.
- 군집이라는 단어를 쓴 기존 포함 논문 중 실제 분석이 요인분석 또는 관측/기대 유병비인 사례가 있어 재검토로 표시했다. 기존 `verdicts.json` 판정은 바꾸지 않았다.
- 새 후보에 대한 포함 확정, 중복 adjudication, 추출표, PROBAST/TRIPOD 및 원고 수치 갱신은 이번 확보 목록에 포함하지 않는다. 기존 서지 레코드와 일치하는 경우에는 PDF 위치·출처 정보만 동기화한다.

## 후보 목록

{table(candidates)}

## 범위 재검토

{table(recheck)}

''' + '\n'.join(f"- **{r['kci_id']}**: {r['acquisition_screening']['note']}" for r in recheck) + '''

## 재현 자료

- `tools/census_kci.py search`: 검색 결과 HTML·쿼리·회수 건수 저장.
- `tools/census_kci.py fetch`: KCI 세부 서지 및 공개 PDF 수집, 성공/실패 로그 저장.
- `tools/kci_fetch_urls.py <URL-map.json>`: 학회·저장소 보완 확보, 제목/DOI 검증.
- `tools/report_kci_census.py`: 수동 검색 정리 기록과 확보 로그로 이 목록/TSV/JSON 재생성.
- `results/raw/kci_20260905/`: 검색 원문 및 검색 조합별 결과.
- `references/_logs/kci_20260905/`: 논문별 URL·응답·검증, 수동 정리 기록, 집계.
'''
    (ROOT / 'data/KCI_CENSUS.md').write_text(report)
    (ROOT / 'data/KCI_PDF_MISSING.md').write_text(f'# KCI 관련 후보 PDF 미확보 — {len(missing)}편\n\n2026-09-07 현재. 접근 실패와 공개 PDF 링크 미발견을 구분했다. 최종 제외가 아니다. 상세 시도는 `references/_logs/kci_20260905/ART*.json` 참조.\n\n[TSV](KCI_PDF_MISSING.tsv) · [전체 조사 결과](KCI_CENSUS.md)\n\n' + table(missing, True) + '\n')
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
