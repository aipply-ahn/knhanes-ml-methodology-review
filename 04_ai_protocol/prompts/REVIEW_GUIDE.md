# 초록 판정 지침 — 사람·에이전트 공통

입력: `results/derived/review/batch_<tier>_<nn>.json`. 출력: 같은 폴더에 `verdict_<tier>_<nn>.json` (JSON 배열).

## 판정값

| verdict | 조건 |
|---|---|
| **INCLUDE** | KNHANES(어느 연차든, 연계자료 포함)를 **분석 자료로 사용** + ML/AI 방법(PROTOCOL D2)을 **실제로 적용**. 여러 자료 중 하나여도, 외부검증용이어도 포함 |
| **INCLUDE_ADJACENT** | KNHANES 사용 + ML 인접 방법만 (LASSO/EN 단독 · k-means 등 군집 단독 · CART 단독 · PCA 단독). ML 본류 방법 없음 |
| **EXCLUDE** | 아래 사유 중 하나 |
| **UNCERTAIN** | 초록만으로 못 정함 (초록 없음 · 방법 미기재 · "prediction model" 이라고만 씀) |

## 제외 사유 코드 (reason 에 앞부분에 쓴다)

`NOT_KNHANES` KNHANES 를 비교·인용으로만 언급, 분석 자료 아님 (미국 NHANES 만 쓴 경우 포함)
`NO_ML` 통계 모형만 (logistic/Cox/선형회귀·GEE·구조방정식). "prediction model" 이어도 회귀만이면 여기
`REVIEW` 리뷰·논평·프로토콜·편집자 서한
`ABBREV_FP` 약어 오탐 (AI=Adequate Intake, ML=mL, DL=dL, RF=radiofrequency, CNN≠convolutional 등)
`OTHER` 기타 (사유 서술)

## 함께 적는 필드 (INCLUDE · INCLUDE_ADJACENT 에서 가능한 한 채운다)

```
category      결과변수 영역 한 단어: diabetes / hypertension / cvd / metabolic_syndrome / obesity / dyslipidemia /
              ckd / liver / thyroid / cancer / osteoporosis_sarcopenia / mental_health / sleep / oral_health /
              hearing_vision / respiratory / nutrition_diet / physical_activity / qol_health_behavior / mortality /
              multimorbidity_general / methodology (결측대체·가중치·합성데이터 등) / other
ml_methods    초록에 쓰인 알고리즘 목록 (원문 표기)
task          classification / regression / clustering / survival / imputation / synthesis / feature_selection / other
knhanes_role  primary / one_of_several / external_validation
outcome       결과변수 짧게 (예 "type 2 diabetes", "depression (PHQ-9)")
```

## 원칙

- 초록에 있는 것만 근거로. 추정하지 않는다. 애매하면 UNCERTAIN.
- 규칙선별 용어(`terms`)는 힌트일 뿐이다. 약어 오탐이 많다.
- 한국어 제목만 있는 KDCA 단독 레코드는 제목·키워드로 판단하되, 확신 없으면 UNCERTAIN.
