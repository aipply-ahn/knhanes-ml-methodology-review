# PROBAST + TRIPOD+AI 평가 지침 (KNHANES 확장판)

입력 `references/md/<key>.md` · 출력 `data/probast/<key>.json`. **본문에 있는 것만.** 초록만이면 대부분 NI.

## 판정값
각 신호질문: `Y`(예) · `PY`(아마 예) · `PN`(아마 아니오) · `N`(아니오) · `NI`(정보 없음) · `NA`(해당 없음)
영역 판정: `low` · `high` · `unclear` — **신호질문 하나라도 N/PN 이면 high**, NI 가 있고 N/PN 이 없으면 unclear

## PROBAST 4영역

### D1 Participants
- 1.1 자료원이 적절한가 · 1.2 포함·제외 기준이 적절한가

### D2 Predictors
- 2.1 예측변수가 모든 대상에게 동일하게 정의·측정되었는가
- 2.2 예측변수 측정 시 결과를 몰랐는가 (단면연구는 대개 PN — 동시 측정)
- 2.3 예측변수를 실제 사용 시점에 얻을 수 있는가

### D3 Outcome
- 3.1 결과 정의가 적절한가 · 3.2 사전 정의되었는가 · 3.3 예측변수를 결과 정의에서 배제했는가
- 3.4 모든 대상에게 동일하게 정의되었는가 · 3.5 결과 판정 시 예측변수를 몰랐는가
- 3.6 예측변수~결과 시간간격이 적절한가 (단면은 대개 PN/N)

### D4 Analysis — 가장 중요
- 4.1 표본 크기가 충분한가 (미보고면 NI) · 4.2 결측 처리가 적절한가 (완전제거만이면 대개 PN)
- 4.3 연속·범주 예측변수 처리 · 4.4 결과 기반 단변량 변수선택을 피했는가 (단변량 p 선택이면 N)
- 4.5 자료 복잡성(**표본설계** 포함)을 고려했는가 · 4.6 성능지표가 적절한가 (보정 없으면 PN)
- 4.7 과적합·낙관성 보정 (검증 없거나 단일분할만이면 PN/N) · 4.8 최종 모형 보고 일치 (ML 은 대개 NA/NI)
- 4.9 모델 업데이트 절차 (해당 없으면 NA)

## KNHANES 확장 신호질문 (본 리뷰의 방법론적 기여) — D4 에 부가
- **S1** 표본가중치를 모형 적합에 반영했는가, 또는 미반영 근거를 밝혔는가
- **S2** 층화·집락 구조를 성능 추정(분할·교차검증)에서 고려했는가
- **S3** 여러 조사연차를 **하나의 분석자료로 합쳤다면** 통합 가중치 산출 방식을 밝혔는가
  - `NA` 는 두 경우뿐이다 — (1) 단일 연차만 사용, (2) 여러 연차를 쓰되 합치지 않고 연차별로 개발·검증에 나누어 사용
  - 같은 기수 안의 연차를 합친 경우도 적용 대상이다. 질병관리청 지침은 기수 내·기수 간을 가리지 않고 복수 연차 통합에 통합가중치 산출을 요구한다
  - (2026-09-04 정정: 이전 문구 '단일 기수면 NA' 는 같은 기수 안의 연차 통합을 잘못 면제해 판정이 엇갈렸다)

## TRIPOD+AI 항목 (`Y`/`N`/`NA`)
`title_design` · `abstract_structured` · `background_objective` · `data_source` ·
`participants_eligibility` · `outcome_definition` · `predictors_description` ·
`sample_size_justification` · `missing_data` · `model_building` · `model_performance_measures` ·
`model_evaluation` · `results_participants` · `results_performance` · `limitations` ·
`data_availability` · `code_availability` · `funding` · `model_availability`

## 출력 스키마
```json
{"key":"...", "source":"full_text|abstract_only",
 "probast":{"D1":{"1.1":"Y","1.2":"Y","judgment":"low","note":"..."},
            "D2":{"2.1":"Y","2.2":"PN","2.3":"Y","judgment":"high","note":"..."},
            "D3":{"3.1":"Y","3.2":"Y","3.3":"Y","3.4":"Y","3.5":"NI","3.6":"PN","judgment":"high","note":"..."},
            "D4":{"4.1":"NI","4.2":"PN","4.3":"Y","4.4":"N","4.5":"N","4.6":"PN","4.7":"PN","4.8":"NI","4.9":"NA",
                  "S1":"N","S2":"N","S3":"NA","judgment":"high","note":"..."}},
 "overall_rob":"high|low|unclear", "applicability":"low|high|unclear",
 "tripod":{"title_design":"N","abstract_structured":"Y","...":"..."},
 "tripod_n_yes":0,"tripod_n_applicable":0,
 "notes":"판정 근거·특이사항"}
```
