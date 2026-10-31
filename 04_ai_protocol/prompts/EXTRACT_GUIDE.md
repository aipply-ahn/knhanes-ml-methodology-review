# 논문별 추출 지침 — 사람·에이전트 공통

입력: `references/md/<key>.md` (PDF 전문 또는 초록만). 출력: `data/extraction/<key>.json` 한 파일.
**본문에 있는 것만 적는다. 없으면 `null` 또는 "미기재".** 추정하지 않는다. 초록만 있는 논문은 `source: "abstract_only"`.

## 출력 JSON 스키마

```json
{
 "key": "...", "source": "full_text | abstract_only",
 "problem": "어떤 문제/결과변수를 다뤘나 (정의 포함, 예: 'T2DM 유병 — 공복혈당≥126 또는 진단/약물')",
 "task": "classification | regression | clustering | survival | imputation | feature_selection | other",
 "ml_usage": "머신러닝을 어떤 식으로 활용했나 — 목적(예측·위험요인 탐색·표현형 군집·변수중요도·비교벤치마크)과 전체 설계 2~4문장",
 "knhanes_waves": "기수·연차 (예: 'KNHANES VII 2016–2018' / '2010–2019 통합')",
 "knhanes_role": "primary | one_of_several | external_validation",
 "other_datasets": "함께 쓴 다른 자료 (없으면 null)",
 "sample_filtering": "포함/제외 기준 순서대로 + 최종 n (예: '≥19세 → 임신 제외 → 결측 제외 → n=12,345')",
 "n_final": 12345,
 "variables": "입력변수 수와 구성 (검진/영양/설문/혈액 등)",
 "variable_selection": "변수 선택 방법 (문헌 기반 · 단변량 p<.05 · LASSO · Boruta · RFE · SHAP 상위 · 없음)",
 "missing_handling": "결측 처리 (완전제거 · 평균/중앙값 대체 · MICE · KNN · 모델 내장 · 미기재)",
 "preprocessing": "그 외 전처리 — 인코딩·표준화·범주화·이상치·불균형(SMOTE/undersampling/class weight)",
 "survey_weights": "yes | no | 미기재  + 어떻게 (가중치를 학습에 반영 / 기술통계에만 / 복합표본설계 무시 명시 등)",
 "models": ["비교한 모델 전부, 원문 표기"],
 "best_model": "최고 성능 모델",
 "hyperparameter_tuning": "그리드/랜덤/베이지안 탐색 여부와 대상 (미기재 가능)",
 "validation": "분할 방식 (train/test 비율 · k-fold · 반복 · 외부검증 자료)",
 "metrics": "주요 지표와 값 (예: 'AUC 0.85 (RF), acc 0.79, F1 0.61')",
 "interpretability": "SHAP · permutation importance · LIME · 없음 — 상위 변수 3~5개",
 "findings": "무엇을 발견하고 보고했나 — 핵심 결과 3~5문장 (중요 변수·성능 비교·임상적 함의)",
 "limitations": "저자가 밝힌 한계 요약 (1~2문장)",
 "code_data_availability": "코드/데이터 공개 여부·링크 (미기재 가능)",
 "notes": "추출자 메모 — 모순·보고 누락·특이점"
}
```

## 원칙
- 한국어로 쓴다. 모델명·지표·변수명은 원문 표기 유지.
- 표·그림 캡션에만 있는 수치도 본문 근거로 인정한다.
- 가중치: "survey design", "complex sampling", "weighted" 를 찾아본다. 언급이 전혀 없으면 "미기재 (언급 없음)".
- 결측: "missing", "imputation", "complete case", "listwise" 를 찾아본다.
- 초록만 있는 경우 채울 수 없는 항목은 null. 억지로 채우지 않는다.
