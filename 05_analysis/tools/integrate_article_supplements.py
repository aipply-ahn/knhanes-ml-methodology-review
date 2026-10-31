#!/usr/bin/env python3
"""Record supplement provenance and apply manually verified extraction upgrades."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "references" / "supplements" / "manifest.tsv"
EXT = ROOT / "data" / "extraction"
ROB = ROOT / "data" / "probast"
ROB_AI = ROOT / "data" / "probast_ai_reassessment" / "records"

UPDATES = {
    "ahn2025machine": {
        "problem": "성인 당뇨병 환자의 건강관련 삶의 질(HRQoL) — EQ-5D index <0.678 위험군 대 ≥0.678 안정군 이진 분류",
        "variables": "상황특이이론에 따라 사전 지정한 45개 예측변수: 인구학, 당뇨 관련 장벽, 혈액·소변 검사, 동반질환, 가구 자원, 주관적 건강, 심리사회 및 건강증진 행동(Supplementary Table S1에 변수명·KNHANES 코드·코딩 제시).",
        "missing_handling": "25개 입력변수에서 각 <5%의 결측을 확인하고 범주형은 최빈값, 연속형은 중앙값으로 단일 대체.",
        "preprocessing": "무작위 7:3 훈련/시험 분할; 심한 클래스 불균형(위험:안정 약 1:15)은 SMOTENC로 처리; StandardScaler로 표준화. SMOTENC·대체·표준화가 분할 후 훈련자료에만 적합됐는지는 명확하지 않음.",
        "survey_weights": "yes — 기술통계와 집단 비교에서 복합표본설계, 가중 백분율, Rao–Scott 카이제곱 및 복합표본 t 검정을 사용. ML 적합·튜닝·시험셋 성능에는 조사 가중치·층화·집락 적용이 보고되지 않음.",
        "hyperparameter_tuning": "훈련자료에서 GridSearchCV와 10-fold stratified cross-validation. 최종값: LR C=0.1/L2; NB var_smoothing=1e-6; RF 100 trees, depth 20, min split 2, min leaf 1, log2 features; SVM C=100, gamma=0.001, RBF; XGBoost colsample 0.6, learning rate 0.2, depth 5, min child weight 1, 300 trees, subsample 0.9 (Supplementary Table S2).",
        "validation": "7:3 무작위 분할의 독립 시험셋 내부검증; 훈련자료 내 GridSearchCV+10-fold stratified CV로 튜닝. 외부·시간적 검증 없음. EQ-5D 절단값 0.766과 0.803에서 전체 파이프라인 반복 민감도 분석.",
        "notes": "EQ-5D 위험군 절단값은 임상적 근거로 제시한 0.678이며 위험군 209명, 안정군 2,292명. self-rated health가 HRQoL과 개념적으로 밀접해 AUC 0.984의 해석에 주의가 필요함. Full text acquired and the reporting fields were refreshed on 2026-09-06.",
    },
    "bhak2024machine": {
        "missing_handling": "결측 대체 — 범주형은 단변량 대체, 연속형은 scikit-learn IterativeImputer를 이용한 다변량 대체(Supplementary Methods). 반복 횟수와 다중대체 통합은 미보고.",
    },
    "choi2026development": {
        "n_final": 20035,
        "survey_weights": "yes — 보조표에서 survey-weighted 학습과 weighted AUC 평가를 명시하고, 비가중 학습과의 민감도 분석도 제시(Table 7). 층화·집락을 재표집 또는 교차검증에 반영했는지는 미보고.",
        "validation": "단일 train/test 분할과 5-fold 교차검증을 비교하고, 17개 시·도 leave-one-region-out 분석을 수행(Supplementary Tables 9–10). 외부자료 검증은 없음.",
        "interpretability": "SHAP(mean absolute SHAP; 개별 및 환경변수 군집 합산), 환경변수 leave-one-out 성능 비교. 전체 상위는 성별, 연령, 교육; 환경변수 중 PM10, NO2, PM2.5, 녹지 순(Supplementary Tables 2, 4, 6).",
    },
    "dashdondov2026assessing": {
        "n_final": 5462,
    },
    "jang2026psychological": {
        "variables": "Boruta 후보 24개: 성, 연령, 지역, 소득, 교육, 결혼, 가구세대구성, 공공부조, 활동제한, 고용, 주당 근로시간, 체형인지, 1년 체중변화, 음주, 흡연, 신체활동, 고혈압·이상지질혈증·당뇨·심근경색/협심증·천식·만성콩팥병·우울증 진단.",
        "variable_selection": "암 생존자 자료의 무작위 5% 부분표본에 Boruta를 적용해 12개를 Confirmed로 선정: 성, 연령, 소득, 결혼, 공공부조, 활동제한, 고용, 근로시간, 체형인지, 흡연, 심근경색/협심증, 우울증. 이 집합을 최종 다변량 모형에 사용(Supplementary Table S1).",
    },
    "jang2023machine": {
        "hyperparameter_tuning": "TPOT 0.11.6(세대 100, population size 100, AUC 목적; RAPIDS cuML/DMLC XGBoost 가속)으로 XGBClassifier 1.3.0의 n_estimators, learning_rate, max_depth, min_child_weight, gamma, subsample, colsample_bytree, reg_alpha, reg_lambda를 최적화. scale_pos_weight는 음성/양성 수 비율로 고정.",
        "validation": "개발자료 9:1 연령군·결과 층화 분할 → SCHPC 독립 외부검증 → KNHANES 독립 외부검증. 결과에 대해 층화 복원추출을 10,000회 시행해 percentile 95% CI 산출; KNHANES 성능에는 sample_weight 적용. 역치는 Youden index 또는 Index of Union.",
        "survey_weights": "yes — KNHANES 평가의 AUC·민감도·특이도에 표본가중치를 적용. 모집단 기술통계에는 R survey/jtools로 PSU=psu, 2차 단위=ID_fam, 층=kstrata, 12개 연도 통합가중치=wt_tot/12를 지정. 성능 CI의 부트스트랩은 결과 층화만 보고되어 층·집락 반영 여부는 불명확.",
        "notes": "KNHANES n이 초록·Table 1에서는 62,945, 결과 본문에서는 62,845로 불일치. KNHANES는 학습에 사용되지 않고 외부검증·SHAP 설명·하위군 분석에만 사용됨.",
    },
    "jo2023development": {
        "hyperparameter_tuning": "BayesSearchCV, 5-fold CV, random_state=42로 모형별 탐색. 예: RF n_estimators 100/150/200, max_depth None/5/10/15, min_samples_split 5/10, min_samples_leaf 4/8; 보조자료의 실행 코드에 탐색공간과 선택 절차 제시.",
    },
    "lee2019deep": {
        "code_data_availability": "보조 MethodsX 파일에 TensorFlow 1.x 기반 전체 학습·추론 소스코드가 본문 형태로 공개됨. 입력 데이터는 KNHANES에서 준비해야 하며 학습된 가중치·독립 실행 모형 파일은 제공되지 않음.",
    },
    "kim2026sleep": {
        "variables": "보조표에 사회인구학·생활습관·임상 특성과 각 범주를 제시하며 분석표본은 ERM 1,461명과 non-ERM 13,779명(총 15,240명).",
    },
    "you2025related": {
        "n_final": 858,
    },
}


def dump(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8"), delimiter="\t"))
    by_key = {}
    for row in rows:
        by_key.setdefault(row["key"], []).append(row)

    for key, items in by_key.items():
        p = EXT / f"{key}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        rec["supplementary_materials"] = {
            "reviewed": True,
            "files": len(items),
            "manifest": "references/supplements/manifest.tsv",
            "searchable_text": f"references/supplements_text/{key}.md",
            "sources": sorted(set(x["source"] for x in items)),
        }
        if key in UPDATES:
            rec.update(UPDATES[key])
            review_note = "Supplementary files were re-reviewed on 2026-09-06; verified fields were updated."
            if review_note not in (rec.get("notes") or ""):
                rec["notes"] = ((rec.get("notes") or "").rstrip() + " " + review_note).strip()
        dump(p, rec)

        rp = ROB / f"{key}.json"
        if rp.exists():
            rob = json.loads(rp.read_text(encoding="utf-8"))
            rob["supplementary_materials_reviewed"] = True
            rob["supplementary_file_count"] = len(items)
            if key == "lee2019deep":
                rob["tripod"]["code_availability"] = "Y"
            if key == "choi2026development":
                rob["tripod"]["model_evaluation"] = "Y"
                rob["probast"]["D4"]["S1"] = "Y"
                rob["probast"]["D4"]["note"] = (
                    "Supplementary Table 7 documents survey-weighted training and weighted AUC evaluation, "
                    "and Tables 9–10 report 5-fold cross-validation and leave-one-region-out analyses. "
                    "Strata and PSU handling and pooled-cycle weight construction remain unreported; calibration is absent."
                )
            rob["tripod_n_yes"] = sum(v == "Y" for v in rob["tripod"].values())
            rob["tripod_n_applicable"] = sum(v != "NA" for v in rob["tripod"].values())
            dump(rp, rob)

        rp_ai = ROB_AI / f"{key}.json"
        if rp_ai.exists():
            rob_ai = json.loads(rp_ai.read_text(encoding="utf-8"))
            rob_ai["supplementary_materials"] = {
                "reviewed": True,
                "files": len(items),
                "manifest": "references/supplements/manifest.tsv",
                "searchable_text": f"references/supplements_text/{key}.md",
                "note": "Use as primary evidence during manual PROBAST+AI model-level reassessment; no legacy judgement was carried forward.",
            }
            dump(rp_ai, rob_ai)

    print(f"supplement provenance added to {len(by_key)} studies; verified extraction upgrades={len(UPDATES)}")


if __name__ == "__main__":
    main()
