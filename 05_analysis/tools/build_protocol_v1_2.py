#!/usr/bin/env python3
"""Rebuild the historical v1.2 core component and study JSON template.

The canonical human-readable protocol is the integrated v1.3 file. This
historical generator must not overwrite it.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/archive/protocol_legacy_v1_0_v1_1/KNHANES_ML_study_audit_protocol_v1.1.md"
OUT_MD = ROOT / "build/KNHANES_ML_study_audit_protocol_v1.2_core_generated.md"
OUT_JSON = ROOT / "KNHANES_ML_study_audit_template_v1.2.json"

DROP = {f"MET_{m}_V" for m in ("ACC", "BACC", "AUROC", "AUPRC", "SENS", "SPEC", "PPV", "NPV", "F1", "MCC", "KAPPA", "BRIER", "LOGLOSS", "CALSLOPE", "CALINT", "CALPLOT", "DCA", "RMSE", "MSE", "MAE", "R2")}
SYSTEM_IDS = {"ADM01", "ADM02", "ADM03", "ADM04", "ADM05", "ADM06", "ADM08", "FAM01", "OUT01", "MOD01", "VAL01", "OBJ01", "DAT00"}
DERIVED_IDS = {"FAM02", "TSK09", "TSK10", "SUP01"} | {f"MED{i:02d}" for i in range(1, 16)} | {f"MET_{m}_R" for m in ("ACC", "BACC", "AUROC", "AUPRC", "SENS", "SPEC", "PPV", "NPV", "F1", "MCC", "KAPPA", "BRIER", "LOGLOSS", "CALSLOPE", "CALINT", "CALPLOT", "DCA", "RMSE", "MSE", "MAE", "R2")}
AUTO_IDS = {f"QA{i:02d}" for i in range(1, 12)} | {"BEST01", "BEST02", "BEST03"}
CONTENT_PREFIXES = ("RAT_", "FUN_", "CLM_")
METHOD_PREFIXES = ("PRE", "IMB", "THR", "MOD", "VAL", "VI", "INF", "SUR")

MISSING_ALLOWED = {
    "ELG05": "DUPLICATE_RETRIEVAL; COMPANION_REPORT; ML_ADJACENT; NO_KNHANES_ANALYSIS; NO_ELIGIBLE_ML; ABSTRACT_ONLY; OTHER",
    "ELG06": "CLUSTERING; LATENT_CLASS_PROFILE; PCA_FACTOR; PENALISED_REGRESSION; ASSOCIATION_RULES; OTHER",
    "ELG07": "PRIMARY; PREPROCESSING; ANCILLARY; UNC",
    "DAT14": "EXAMINATION; HEALTH_INTERVIEW; NUTRITION; ORAL_HEALTH; LABORATORY; ACCELEROMETRY; OTHER",
    "VI02": "SHAP; MODEL_NATIVE; PERMUTATION; PDP; ALE; ICE; LIME; PERTURBATION_ABLATION; COEFFICIENT_STATISTIC; TREE_RULE; NETWORK_SPECIFIC; NA; OTHER",
    "VI07": "AGE; ADIPOSITY_BODY_SIZE; SEX; BLOOD_PRESSURE; GLYCAEMIA_DIABETES; LIPIDS; KIDNEY_URINE; MENTAL_SUBJECTIVE_HEALTH; SOCIOECONOMIC; DIET; PHYSICAL_ACTIVITY_FUNCTION; SMOKING; ALCOHOL; PAIN_MUSCULOSKELETAL; WORK_CLINICAL_HISTORY; NA; OTHER",
    "VI08": "RANKING_ONLY; FIXED_TOP_K; RECURSIVE_WRAPPER; THRESHOLD; CROSS_MODEL_CONSENSUS; PENALISED_STATISTICAL_FILTER; EXPERT_JUDGEMENT; AVAILABILITY_MISSINGNESS; NR; NA; OTHER",
    "SUR12": "REQUIRED; CONDITIONAL; NOT_REQUIRED; UNC",
    "SUP02": "Availability and review status are stored separately in source_package.supplement_files[]",
}

REP_COMPONENTS = {
    "REP01": "prediction/model/ML identification",
    "REP02": "objective; data source; model(s); principal result(s)",
    "REP03": "objective; intended use; target population",
    "REP04": "data source; study design; setting; dates",
    "REP05": "eligibility criteria; selection process; exclusions",
    "REP06": "outcome definition; assessment timing; source/assessor",
    "REP07": "predictor definition; measurement timing; availability at intended use",
    "REP08": "analysed sample size; event/non-event or class counts",
    "REP09": "sample-size rationale or calculation",
    "REP10": "missingness amount; handling method; analysis stage",
    "REP11": "preprocessing; variable selection; model development",
    "REP12": "hyperparameters; tuning method; tuning/evaluation separation",
    "REP13": "internal-validation method; resampling details; nesting of development steps",
    "REP14": "evaluation dataset; performance metrics; threshold where applicable",
    "REP15": "participant flow; exclusions; analysed participant characteristics",
    "REP16": "performance estimate; uncertainty or resampling distribution",
    "REP17": "complete model specification or executable artefact; use instructions",
    "REP18": "limitations; generalisability; applicability",
    "REP19": "registration/protocol; data availability; code/model availability",
}


def parse_source():
    text = SOURCE.read_text(encoding="utf-8")
    start, end = text.index("## 11. 표준 문항"), text.index("## 12. 공식 기준문서")
    section = ""; items = []
    for line in text[start:end].splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) != 13:
            continue
        items.append({"id": c[1].strip("`"), "section": section, "subsection": c[2], "scope": c[3], "nature": c[4], "condition": c[5], "question": c[6], "format": c[7], "allowed": c[8], "evidence": c[9], "rule": c[10], "json_key": c[11].strip("`"), "output": c[12]})
    return items


def new_item(qid, section, subsection, scope, nature, condition, question, fmt, allowed, evidence, rule, key, output):
    return {"id": qid, "section": section, "subsection": subsection, "scope": scope, "nature": nature, "condition": condition, "question": question, "format": fmt, "allowed": allowed, "evidence": evidence, "rule": rule, "json_key": key, "output": output}


def insert_items(items):
    additions = {
        "FAM09": [new_item("FAM10", "C. 연구군·적격성", "연결 판정", "Study", "Judgement", "Linked-report candidate", "연구군 연결 최종판정", "Single choice", "MERGE; SPLIT; UNC", "필수", "저자 동일만으로 병합하지 않음", "linkage_decision", "AF2/AF8 linkage")],
        "TSK10": [new_item("TSK11", "D. 분석과제", "기타 과제 분기", "Study", "Judgement", "TSK01=OTHER", "기타 분석과제의 세부 유형", "Multiple choice (복수)", "IMPUTATION; CLUSTERING; CAUSAL; REPRESENTATION; DATA_PROCESSING; OTHER", "필수", "JSON 배열; OTHER 선택 시 설명", "other_task_subtype", "AF3/AF8 task-neutral")],
        "OBJ03": [new_item("OBJ03B", "U. 보충자료·멀티미디어", "객체원장", "Visual object", "System metadata", "inventory_level=PANEL", "parent visual object ID", "Identifier", "", "필수", "panel은 container parent 필수", "parent_object_id", "visual_objects[]")],
        "OBJ05": [new_item("OBJ05B", "U. 보충자료·멀티미디어", "객체원장", "Visual object", "Direct extraction", "Every object", "인쇄 페이지", "Text", "", "선택", "PDF page와 별도 기록", "printed_page", "visual_objects[]")],
        "OBJ06": [new_item("OBJ06B", "U. 보충자료·멀티미디어", "객체원장", "Visual object", "Direct extraction", "Every object", "caption 끝 anchor", "Text", "", "필수", "검색 가능한 8–20단어 권장", "caption_end_anchor", "visual_objects[]")],
    }
    result = []
    for q in items:
        if q["id"] in DROP:
            continue
        if q["id"] == "DAT01":
            result.append(new_item("DAT00", "E. KNHANES 자료", "자료 식별", "Dataset", "System metadata", "Every dataset", "dataset ID", "Identifier", "KHM001-DS01 형식", "필수", "모든 development/evaluation은 dataset_id 연결", "dataset_id", "units.datasets[]"))
        result.append(q)
        result.extend(additions.get(q["id"], []))
    return result


def role(q):
    qid = q["id"]
    if qid in SYSTEM_IDS or q["nature"] in {"Administrative", "Metadata", "System metadata"}:
        return "system_metadata"
    if qid in DERIVED_IDS or q["nature"] == "Derived":
        return "derived"
    if qid in AUTO_IDS or q["nature"] == "Audit check":
        return "automated_validation"
    if q["nature"] == "Official appraisal":
        return "appraisal_judgement"
    return "reviewer_entered"


def units(q):
    qid, scope = q["id"], q["scope"]
    if qid in {"POP12", "POP13", "POP14"}:
        return "Outcome", "evaluation_id (if evaluation-specific)"
    if qid == "ELG04":
        return "Study", "family_id; report_id"
    if qid.startswith("PRE"):
        return "Development", "model_id; dataset_id"
    if qid.startswith(("MET_", "PE_")):
        return "Evaluation", "model_id; outcome_id; dataset_id"
    if qid.startswith("PD_"):
        return "Development", "model_id; outcome_id; dataset_id"
    if qid.startswith("VI"):
        return "Model", "outcome_id"
    if "Evaluation" in scope:
        return "Evaluation", "model_id; outcome_id; dataset_id"
    if "Development" in scope:
        return "Development", "model_id; outcome_id; dataset_id"
    if "Visual object" in scope:
        return "VisualObject", "report_id; parent_object_id if panel"
    if "Supplement file" in scope:
        return "SupplementFile", "report_id"
    if "Model" in scope:
        return "Model", "outcome_id if applicable"
    if "Outcome" in scope:
        return "Outcome", "evaluation_id if applicable"
    if "Report" in scope:
        return "Report", "study_id; family_id if applicable"
    if "Dataset" in scope:
        return "Dataset", "study_id"
    return "Study", ""


def official_id(qid):
    if not qid.startswith(("PD_", "PE_")):
        return ""
    phase = "DEV" if qid.startswith("PD_") else "EVAL"; code = qid.split("_", 1)[1]
    if code == "OVERALL": return f"{phase}.OVERALL"
    if code.startswith("D"): return f"{phase}.DOMAIN.{code[1:]}"
    domain = {"P": "PDS", "R": "PRED", "O": "OUT", "A": "ANA"}[code[0]]
    return f"{phase}.{domain}.{code[1:]}"


def revise(items):
    generic = "Y=Yes / reported / present; N=No / absent; NR=Not reported; UNC=Unclear / not recoverable; NA=Not applicable; OTH=Other"
    for q in items:
        qid = q["id"]
        q["item_role"] = role(q)
        q["primary_unit"], q["related_ids"] = units(q)
        q["required_components"] = REP_COMPONENTS.get(qid, "")
        q["official_item_id"] = official_id(qid)
        if qid in MISSING_ALLOWED: q["allowed"] = MISSING_ALLOWED[qid]
        q["allowed"] = re.sub(r"\bOTH\b", "OTHER", q["allowed"])
        q["rule"] = re.sub(r"\bOTH\b", "OTHER", q["rule"]).replace("If other", "If OTHER")
        if q["allowed"] == generic or "Y=Yes / reported / present" in q["allowed"]:
            if qid.startswith(CONTENT_PREFIXES):
                q["allowed"] = "PRESENT; ABSENT; UNC; NA"
            elif qid.startswith(METHOD_PREFIXES) and q["item_role"] == "reviewer_entered":
                q["allowed"] = "USED; NOT_USED; NR; UNC; NA"
            else:
                q["allowed"] = "Y; N; UNC; NA"
            q["rule"] = re.sub(r"If OTHER, describe\.?", "", q["rule"]).strip()
        if qid.startswith("REP"):
            q["condition"] = "D_PROB"
            q["allowed"] = "R; P; NR; UNC; NA"
            q["rule"] = "R=required_components 모두; P=일부; NR=모두 미보고; UNC=상충·판독불가; NA=비적용"
        if qid in DERIVED_IDS:
            q["evidence"] = "자동"
            if qid.startswith("MET_") and qid.endswith("_R"):
                q["question"] = q["question"].replace("보고되었는가?", "performance_metrics[]에서 보고 상태가 어떻게 파생되는가?")
                q["allowed"] = "R; NR; NA; UNC"
                q["rule"] = "metric 배열과 source-package 검색상태에서 자동 산출; 수동 이중입력 금지"
        if qid == "SUP02":
            q["item_role"] = "system_metadata"
            q["nature"] = "System metadata"
            q["question"] = "보충자료 파일별 확보상태와 검토상태"
            q["format"] = "Object array"
            q["allowed"] = "availability=ACQUIRED/NOT_ACQUIRED/BLOCKED/NOT_IDENTIFIED; review_status=NOT_STARTED/IN_PROGRESS/COMPLETE/NOT_APPLICABLE"
            q["evidence"] = "자동/필수 provenance"
            q["rule"] = "availability와 review_status를 서로 다른 필드로 저장"
            q["json_key"] = "source_package.supplement_files"
        if qid in {"BEST01", "BEST02", "BEST03"}:
            replacement = {
                "BEST01": ("selection 배열에 선택기준이 기록되었는가?", "selection_criterion_complete"),
                "BEST02": ("selection 배열에 선택모델과 metric ID 연결이 완전한가?", "selection_model_metric_complete"),
                "BEST03": ("selection 배열에 평가맥락과 근거가 완전한가?", "selection_context_evidence_complete"),
            }[qid]
            q["nature"] = "Audit check"; q["question"], q["json_key"] = replacement; q["format"] = "Single choice"
            q["allowed"] = "Y; N; UNC; NA"; q["evidence"] = "자동"; q["rule"] = "best_model_selections[] validator에서 자동 산출"
            q["primary_unit"] = "Study"; q["related_ids"] = "outcome_id"
        if qid == "DAT02":
            q["format"] = "Integer array"; q["rule"] = "KNHANES 기수의 정수 배열; 문자열 금지"
        if qid == "DAT04":
            q["format"] = "Integer array"; q["rule"] = "실제 사용연도의 정수 배열; 비연속 연도 보간 금지"
        branch = {"NC04": "TSK11 contains IMPUTATION", "NC05": "TSK11 contains IMPUTATION or REPRESENTATION", "NC06": "TSK11 contains CLUSTERING", "NC07": "TSK11 contains CLUSTERING", "NC08": "TSK11 contains CAUSAL", "NC09": "TSK11 contains REPRESENTATION"}
        if qid in branch: q["condition"] = branch[qid]
        visual = {
            "OBJ03": ("object label", "object_label", "Text"),
            "OBJ05": ("PDF page", "pdf_page", "Integer"),
            "OBJ06": ("caption 시작 anchor", "caption_start_anchor", "Text"),
            "OBJ09": ("구조화된 추출·판독값", "extracted_values", "Object array"),
        }
        if qid in visual: q["question"], q["json_key"], q["format"] = visual[qid]
        if qid.startswith(("PD_", "PE_")) and q["subsection"] == "공식 signalling question":
            q["subsection"] = "운용 번역·요약"
        for old, new in {"높은 성능 기대을":"높은 성능에 대한 기대를", "선별·개인화을":"선별·개인화를", "방법론·자료처리 문제을":"방법론·자료처리 문제를", "동적·실시간·전자기록·배치을":"동적·실시간·전자기록·배치를", "외부검증·보정 필요 제시을":"외부검증·보정의 필요성을", "실제 구현·배치 보고을":"실제 구현·배치를 보고했다고"}.items():
            q["question"] = q["question"].replace(old, new)
    # Logical invariant for mutually exclusive rationale code.
    for q in items:
        if q["id"] == "RAT_NONE": q["rule"] = "다른 RAT_*가 PRESENT이면 반드시 ABSENT; 다른 RAT_*가 모두 ABSENT일 때만 PRESENT"
    return items


def render_tables(items):
    cols = ["No.", "ID", "하위섹션", "item_role", "primary_unit", "required_related_ids", "성격", "적용조건", "질문/항목", "형식", "허용응답", "근거", "판정·예외 규칙", "JSON key", "산출물", "official_item_id", "required_components"]
    out = [f"## 15. 전체 protocol items {len(items)}개", "", "`reviewer_entered`와 `appraisal_judgement`만 검토자가 입력한다. `system_metadata`, `derived`, `automated_validation`은 같은 연구 JSON 안에서 시스템이 채우거나 계산한다.", ""]
    last = None
    for n, q in enumerate(items, 1):
        if q["section"] != last:
            last = q["section"]; out += [f"### {last}", "", "| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
        values = [n, f"`{q['id']}`", q["subsection"], q["item_role"], q["primary_unit"], q["related_ids"], q["nature"], q["condition"], q["question"], q["format"], q["allowed"], q["evidence"], q["rule"], f"`{q['json_key']}`", q["output"], q["official_item_id"], q["required_components"]]
        out.append("| " + " | ".join(str(x).replace("|", "/") for x in values) + " |")
    return "\n".join(out) + "\n"


INTRO = """# KNHANES ML 연구 표준 분석 설문 및 근거감사 프로토콜

- Protocol version: 1.2 draft (전수조사 전 10편 구조 파일럿 대상)
- Canonical instrument: **이 Markdown 파일 하나**
- Review work file: **연구 × 검토단계당 JSON 하나**
- Full-study ledger: 최종 JSON을 한 줄씩 자동 병합한 JSONL(파생물; 수동 입력 금지)

## v1.2 동기화 원칙

문항·허용응답·분기·단위·근거·JSON key는 이 문서에 전부 들어 있다. 별도 CSV/TSV/schema/choice-set 파일은 조사자가 참조하지 않는다. P1, P2, final은 각각 `KHM001_P1.json`, `KHM001_P2.json`, `KHM001_final.json`으로 분리한다. 최종 JSON들을 자동 병합해 `KNHANES_studies_v1.2.jsonl`을 만들 수 있지만 JSONL은 별도 조사 입력물이 아니다.

## 1. 독립검토 파일 규칙

- P1은 P1 전용 JSON, P2는 P2 전용 JSON에 입력한다.
- P2 완료 전 P1 파일과 값을 P2에게 노출하지 않는다.
- P1의 기존자료 이관은 `migration_validation`, 원문 신규 판독은 `independent_review`로 구분한다.
- CON 존재 → CON 사용; CON 없음 + P1=P2 → 일치값; P1≠P2 + CON 없음 → `UNRESOLVED`; P1만 존재 → `PROVISIONAL`.
- `KHM001_final.json`에는 P1/P2 원본값, 비교 결과, CON과 최종값을 모두 보존한다.

## 2. 단일 연구 JSON 최상위 구조

```json
{
  "protocol_version": "1.2",
  "study_id": "KHM001",
  "file_role": "P1",
  "review_mode": "independent_review",
  "metadata": {},
  "source_package": {"main_text": {}, "supplement_files": [], "appendix": {}, "repository": {}},
  "units": {"reports": [], "datasets": [], "outcomes": [], "models": [], "developments": [], "evaluations": []},
  "evidence_registry": [],
  "protocol_items": {},
  "performance_metrics": [],
  "best_model_selections": [],
  "visual_objects": [],
  "review_record": {},
  "adjudication": {}
}
```

각 protocol item은 `item_role`, `primary_unit`, `unit_id`, `related_ids`, `value`, `value_status`, `evidence_ids`, `reviewer_id`, `review_stage`, `status`, `rationale`을 가진다. 반복단위는 같은 item ID 아래 배열로 저장한다.

## 3. 단위와 ID

- Study `KHM001`; Report `KHM001-R01`; Dataset `KHM001-DS01`; Outcome `KHM001-O01`; Model `KHM001-M01`; Development `KHM001-D01`; Evaluation `KHM001-E01`; Visual `KHM001-V0001`; Supplement `KHM001-S01`.
- 실제 응답의 `primary_unit`은 하나만 허용한다. 필요한 연결은 `related_ids`에 둔다.
- Evaluation은 최소 `model_id`, `outcome_id`, `dataset_id`를 연결한다. Development도 model과 dataset을 연결한다.

## 4. 근거와 source package

근거는 같은 JSON의 `evidence_registry`에 한 번 저장하고 각 항목은 `evidence_ids`로 연결한다. 근거에는 source file/type, section/subsection, PDF/인쇄 page, object/panel/table 좌표, start/end anchor, excerpt, interpretation status를 기록한다.

Source package는 확보와 검토를 분리한다: `availability=ACQUIRED/NOT_ACQUIRED/BLOCKED/NOT_IDENTIFIED`, `review_status=NOT_STARTED/IN_PROGRESS/COMPLETE/NOT_APPLICABLE`, access date, sha256, notes. Supplement는 `source_package.supplement_files[]`에 파일별로 저장한다. NR은 접근 가능한 package 검토가 완료된 뒤에만 사용하며 가상 인용문을 만들지 않는다.

## 5. 응답코드

- 방법 수행: `USED/NOT_USED/NR/UNC/NA`
- 내용코드: `PRESENT/ABSENT/UNC/NA`
- 보고완전성: `R/P/NR/UNC/NA`
- 단순 논리판정: `Y/N/UNC/NA`
- PROBAST+AI: `Y/PY/PN/N/NI/NA`

단일 Y 코드에 수행·보고·존재 의미를 섞지 않는다. `OTHER`로 통일하며 다중응답은 JSON 배열이다.

## 6. 성능·최고모델

21개 `MET_*_V` 값 문항은 삭제했다. 실제 값은 `performance_metrics[]`에만 evaluation/model/outcome/dataset/class/threshold/split별로 저장한다. `MET_*_R`은 배열과 source-package에서 자동 파생한다. BEST01–03은 수동 값 입력이 아니라 `best_model_selections[]` 완결성 자동검사다.

`performance_metrics`, `best_model_selections`, `visual_objects`의 모든 원소에는 `reviewer_id`, `review_stage`, `status`, `rationale`, `evidence_ids`가 필수다.

## 7. 보고완전성과 기타 분석

REP01–19는 D_PROB에만 적용하며 각 문항의 `required_components`를 모두 충족하면 R, 일부면 P, 모두 미보고면 NR이다. 기타 11편은 REP 평가에서 제외하고 핵심 특성과 TSK11/NC 문항으로 기술한다; 별도 generic reporting score를 만들지 않는다.

## 8. PROBAST+AI

PD/PE 한국어는 운용 요약이며 표의 `official_item_id`로 공식 항목을 연결한다. 모든 applicable development domain HIGH→HIGH; 하나라도 LOW→LOW; LOW 없이 UNC→UNC; 모두 NA→NA. 평가도 모든 applicable domain LOW→LOW; 하나라도 HIGH→HIGH; HIGH 없이 UNC→UNC; 모두 NA→NA. 공식 원문과 E&E가 최종 기준이다.

## 9. Visual

object label/parent, PDF/인쇄 page, caption start/end anchor를 별도 필드로 저장한다. 판독값은 `extracted_values[]`이다. Container와 panel을 구분하고 panel은 기존 container 분모에 더하지 않는다.

## 10. 분모

고정 연구 분모는 D_ALL=222, D_CLS=206, D_CONT=5, D_OTHER=11, D_PROB=211이다. D_DEV, D_EVAL, D_MULTIYEAR, D_VI, D_SUBSET, D_INF와 visual 수는 포함규칙만 고정하고 JSON에서 자동 산출한다.

## 11. JSONL과 분석표

`KHM*_final.json` 한 편을 JSONL 한 줄로 자동 병합한다. Excel/CSV는 JSONL 내부 배열을 분석 시점에 펼쳐 만든 파생물이며 수동 수정하지 않는다. 현재 활성 조사 산출물은 이 Markdown과 연구 JSON 템플릿뿐이다.

## 12. 10편 구조 파일럿

파일럿은 문항 누락, 분기, 단위/관계 ID, P1/P2 독립성, metric/selection/visual reviewer 필드, source-package NR 규칙을 확인한다. 파일럿과 validator 통과 후에만 222편 전수조사를 시작한다.

## 13. 완료 조건

모든 적용 reviewer item, 근거, 단위관계, source-package, P1/P2/CON, metric/selection, visual parent와 자동 derived/QA 검사를 한 final JSON 안에서 복원할 수 있어야 한다.

## 14. 문항표 읽는 법

`item_role`이 reviewer_entered/appraisal_judgement이면 검토자가 입력하고, system_metadata/derived/automated_validation이면 시스템이 같은 JSON에 기록한다. `primary_unit`은 실제 저장단위이며 `required_related_ids`는 필수 연결이다.
"""


def blank_source():
    return {"availability": "NOT_IDENTIFIED", "review_status": "NOT_STARTED", "access_date": None, "sha256": None, "files": [], "notes": None}


def make_template(items):
    entries = {}
    for q in items:
        entries[q["id"]] = [{"item_role": q["item_role"], "primary_unit": q["primary_unit"], "unit_id": None, "related_ids": {}, "json_key": q["json_key"], "value": None, "value_status": "PENDING", "evidence_ids": [], "reviewer_id": None, "review_stage": "P1", "status": "NOT_STARTED", "rationale": None}]
    reviewer = {"reviewer_id": None, "review_stage": "P1", "status": "NOT_STARTED", "rationale": None, "evidence_ids": []}
    return {
        "protocol_version": "1.2", "study_id": None, "file_role": "P1", "review_mode": "independent_review",
        "metadata": {"title": None, "publication_year": None, "authors": [], "journal": None, "doi": None, "language": None},
        "source_package": {"main_text": blank_source(), "supplement_files": [{"supplement_id": None, "filename": None, **blank_source()}], "appendix": blank_source(), "repository": blank_source()},
        "units": {"reports": [], "datasets": [{"dataset_id": None, "label": None, "role": None}], "outcomes": [], "models": [], "developments": [], "evaluations": []},
        "evidence_registry": [{"evidence_id": None, "source_file": None, "source_type": None, "section": None, "subsection": None, "pdf_page": None, "printed_page": None, "object_label": None, "panel_label": None, "table_row": None, "table_column": None, "start_anchor": None, "end_anchor": None, "excerpt": None, "interpretation_status": "PENDING"}],
        "protocol_items": entries,
        "performance_metrics": [{"metric_id": None, "evaluation_id": None, "model_id": None, "outcome_id": None, "dataset_id": None, "metric": None, "estimate": None, "lower_ci": None, "upper_ci": None, "sd": None, "class_label": None, "threshold": None, "split_label": None, "summary_type": None, "reported_text": None, "author_designated_best": False, **reviewer}],
        "best_model_selections": [{"selection_id": None, "outcome_id": None, "evaluation_ids": [], "selected_model_ids": [], "selected_metric_ids": [], "criterion": None, "tie_status": None, "author_designated": None, **reviewer}],
        "visual_objects": [{"object_id": None, "object_type": None, "inventory_level": "CONTAINER", "parent_object_id": None, "object_label": None, "panel_label": None, "source_file": None, "pdf_page": None, "printed_page": None, "caption_start_anchor": None, "caption_end_anchor": None, "interpretation_status": "PENDING", "visible_text": None, "interpretation": None, "extracted_values": [], **reviewer}],
        "review_record": {"reviewer_id": None, "review_stage": "P1", "review_mode": "independent_review", "date": None, "status": "NOT_STARTED", "blind_to_other_reviewer": True},
        "adjudication": {"status": "NOT_APPLICABLE", "P1_file": None, "P2_file": None, "consensus_entries": [], "unresolved": [], "final_value_rule": "CON > AGREEMENT > UNRESOLVED; P1-only=PROVISIONAL"},
    }


def main():
    source = parse_source()
    items = revise(insert_items(source))
    ids = [q["id"] for q in items]
    assert len(source) == 397 and len(DROP) == 21
    assert len(ids) == len(set(ids)) == 382
    assert not (set(ids) & DROP)
    md = INTRO.rstrip() + "\n\n" + render_tables(items) + "\n## 16. 공식 기준문서\n\n- PROBAST+AI: BMJ 2025;388:e082505 및 공식 도구·Explanation & Elaboration\n- TRIPOD+AI: EQUATOR Network 공식 checklist\n"
    OUT_MD.write_text(md, encoding="utf-8")
    template = make_template(items)
    OUT_JSON.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({"source_items": len(source), "removed_metric_value_items": len(DROP), "final_protocol_items": len(items), "roles": dict(Counter(q["item_role"] for q in items)), "json_item_keys": len(template["protocol_items"])})


if __name__ == "__main__":
    main()
