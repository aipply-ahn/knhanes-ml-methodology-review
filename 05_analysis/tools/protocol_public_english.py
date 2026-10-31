"""Reviewed English rendering of the Korean canonical human-use items.

IDs and code values are never translated. The full Korean metadata remains in
S7/PROTOCOL_CROSSWALK. Unmapped Korean text fails instead of silently leaking
into the English instrument. These are operational translations, not official
wording of the external appraisal instruments.
"""
import re

QUESTIONS = dict(line.split("|", 1) for line in """
ADM07|Certainty of the judgement
FAM03|Is this the representative report?
FAM04|Do participants or analytic samples overlap?
FAM05|Do KNHANES years or cycles overlap?
FAM06|Are outcomes and analytic objectives identical or part of a continuing analysis?
FAM07|Is the model-development/evaluation pathway the same?
FAM08|Are these a preprint and its subsequent journal publication?
FAM09|Summarise the evidence for linking or separating reports.
FAM10|Final study-family linkage decision
ELG01|Were KNHANES data actually used in the analysis?
ELG02|Was an eligible ML method central to the actual analysis?
ELG03|Can the analytic methods and results be assessed from the full text?
ELG04|Is this included as a unique study?
ELG05|Reason for exclusion or linkage
ELG06|ML-adjacent method
ELG07|Analytic role of this method
TSK01|Task category based on the actual outcome scale and principal analytic objective
TSK02|Task terminology used by the authors
TSK03|Source-based summary of the principal analytic objective
TSK04|Broad health topic
TSK05|Detailed health topic
TSK06|Analytic dataset role of KNHANES
TSK07|Does one report contain multiple analytic tasks?
TSK08|Rationale for selecting the principal task
TSK11|Detailed type of other analytic task
DAT01|KNHANES cycle wording as reported
DAT02|Standardised list of KNHANES cycles
DAT03|Survey-year wording as reported
DAT04|Exact list of analysed years
DAT05|First analysed year
DAT06|Last analysed year
DAT07|Number of years actually used
DAT08|Survey-year span
DAT10|Actual analytic operation applied to multiple years
DAT11|Was a combined-cycle weighting strategy reported?
DAT12|Combined-weight formula or procedure
DAT13|Were the reported combined weights actually applied in the analysis?
DAT14|KNHANES components used
DAT15|Were external data linked to KNHANES participant records using individual, household, or area identifiers?
DAT16|External dataset name and source
DAT17|External-data period or follow-up duration
DAT18|Can the analysed years, cycles, and dataset combination be reproduced?
POP01|Target population
POP02|Description of the analytic population
POP03|Minimum age
POP04|Maximum age
POP05|Sex restriction
POP06|Principal inclusion criteria
POP07|Principal exclusion criteria
POP08|Initial candidate sample size
POP09|Final analytic sample size
POP10|Number excluded
POP11|Reasons and stages of sample exclusion
POP12|Number of events or positive cases
POP13|Number of non-events or negative cases
POP14|Outcome prevalence or event rate
POP15|Can participant flow and the final sample be reconstructed?
POP16|Was a sample-size rationale or justification reported?
POP17|Method of sample-size justification
OUT02|Outcome name
OUT03|Original measurement form of the outcome
OUT04|Source of outcome ascertainment
OUT05|Timing of outcome ascertainment
OUT06|Class names and order
OUT07|Sample size of each class
OUT08|Numerical cut-off or rule used
OUT09|Modelled outcome scale
OUT10|Temporal relationship between predictors and outcome
OUT11|Was a continuous score or measurement categorised?
OUT12|Rationale for the cut-off or categorisation
OUT13|Cited reference or standard supporting the cut-off
OUT14|Is a predictor directly included in the outcome definition?
OUT15|Was outcome assessment blinded to predictor information?
OUT16|Reproducibility of the outcome definition
OUT17|Reliability of the outcome definition
OUT18|Overall appropriateness of outcome construction
PRD01|Description of the candidate predictor set
PRD02|Initial number of candidate/input variables entering the ML pipeline
PRD03|Original label used for the variable count
PRD04|Number of final-model variables
PRD05|Timing of predictor measurement
PRD06|Predictor data domains
PRD07|Are all predictors available at the intended time of use?
PRD08|Are direct components of the outcome included as predictors?
PRD09|Are deterministic derivatives or strong concurrent proxies of the outcome included?
PRD10|Are post-diagnosis or post-outcome-ascertainment variables included?
PRD11|Were predictors defined and measured similarly for all participants?
PRD12|Were predictors measured and processed without outcome information?
PRD13|Reconstructability of the predictor set
PRD14|Target–predictor alignment
PRD15|Overall appropriateness of predictor construction and alignment
PRE01|Principal missing-data strategy
PRE02|All missing-data methods used
PRE03|Variable-specific rules for missing-data exclusion or imputation
PRE04|Missing-data proportion or count
PRE05|Was missing-data handling appropriately performed within the train/test or resampling structure?
PRE06|Were continuous variables scaled or normalised?
PRE07|Were categorical variables encoded?
PRE08|Was outlier handling or winsorisation performed?
PRE09|Were derived variables or feature engineering used?
PRE10|Was dimensionality reduction used in preprocessing?
PRE11|Was supervised feature selection used?
PRE12|Preprocessing method details
PRE13|Timing of feature selection
PRE14|Was all data-driven preprocessing separated from evaluation data?
IMB01|Principal class-imbalance strategy
IMB02|All class-imbalance strategies used
IMB03|Timing of class-imbalance handling
IMB04|Handling of the evaluation/test distribution
IMB05|Can overall and partition-specific class counts and prevalence be reconstructed?
IMB06|Training-data class counts and prevalence
IMB07|Validation/test-data class counts and prevalence
THR01|Decision-threshold selection method
THR02|Applied threshold
THR03|Was the threshold selected independently of the evaluation data?
THR04|Was the model or its predictions recalibrated after class-imbalance adjustment?
MOD02|Algorithm/model families evaluated
MOD03|Number of model families evaluated
MOD04|Baseline or statistical comparator model
MOD05|Final/best model name
MOD06|Final-model hyperparameters
MOD07|Tuning method
MOD08|Tuning search space
MOD09|Software, packages, and versions
MOD10|Random seed
MOD11|Was a simple baseline included?
MOD12|Was hyperparameter tuning performed?
MOD13|Were tuning data separated from final-evaluation data?
MOD14|How completely was the final model specified for application to new observations?
MOD15|Code-availability status
MOD16|Code URL and version/commit
MOD17|Was an interface such as an app, web tool, or calculator provided?
MOD18|Was prospective deployment conducted with repeated application to new observations and evaluation of effects on decisions or outcomes?
VAL02|Validation methods
VAL03|Training:validation:test ratio
VAL04|Number of folds
VAL05|Number of repetitions
VAL06|Were all model-development steps repeated within each resampling iteration?
VAL07|Was evaluation based solely on apparent performance avoided?
VAL08|External or temporal-evaluation dataset name
VAL09|External-data years and cycles
VAL10|Evaluation sample size
VAL11|Number of evaluation events or positive cases
VAL12|Evaluation prevalence
VAL13|Was overlap of the same participants between training and evaluation prevented?
VAL14|Were relevant time, household, or cluster structures considered in splitting?
MET_CI|Were confidence intervals for performance measures reported?
MET_SD|Were standard deviations or distributions across repeated resampling reported?
MET_PAIR|Were paired, DeLong, or same-split comparisons reported?
MET_PAIR_M|Paired-comparison method and results
MET_APPROPRIATE|Were discrimination, calibration, and net benefit assessed as appropriate to the objective?
VI01|Was an explicit model-based variable-importance or explanation method used?
VI02|Variable-importance or explanation methods
VI03|Name of the interpreted model
VI04|Data partition used for interpretation
VI05|Number of input variables in the interpreted model
VI06|Important variable names as reported
VI07|Standardised domains of important variables
VI08|Rule for identifying or selecting important variables
VI09|Number of selected variables
VI10|Was a reduced model subset defined using importance?
VI11|Did ML importance or selection explicitly guide variable choices for subsequent statistical inference?
VI12|Type of subsequent statistical model
VI13|Number of inputs to the subsequent statistical model
VI14|Were the exact ML-selected variables carried forward one-to-one?
VI15|Variables added, removed, or transformed in the subsequent model
VI16|Was importance stability assessed across resampling, survey cycles, or subgroups?
VI17|Were explanation fidelity or robustness assessed quantitatively?
VI18|Was usefulness to experts or users assessed?
VI19|Was subgroup fairness of performance or explanations assessed?
RAT_PERF|Did the Introduction justify ML by expected performance gains over existing methods?
RAT_SCREEN|Did the Introduction justify ML by screening or personalisation?
RAT_COMPLEX|Did the Introduction justify ML by nonlinearity, complexity, or high dimensionality?
RAT_FACTOR|Did the Introduction justify ML by factor discovery or interpretation?
RAT_METHOD|Did the Introduction justify ML by methodological or data-processing problems?
RAT_DEPLOY|Did the Introduction justify ML by dynamic, real-time, electronic-record, or deployment uses?
RAT_NONE|Was there no explicit rationale for using ML?
FUN_PRED|Did the actual analysis perform prediction or classification?
FUN_COMPARE|Did the actual analysis compare algorithms?
FUN_INTERP|Did the actual analysis interpret variables or risk factors?
FUN_PROCESS|Did the actual analysis perform data processing or augmentation?
FUN_TRANSPORT|Did the actual analysis perform external validation or transport evaluation?
FUN_PATTERN|Did the actual analysis discover patterns or features?
FUN_TOOL|Did the actual analysis implement a decision-support tool?
CLM_BETTER|Did the Discussion/Conclusion claim or mention better prediction?
CLM_FACTOR|What variable-related claims were made in the Discussion/Conclusion?
CLM_SCREEN|What individual-application uses were claimed or mentioned in the Discussion/Conclusion?
CLM_NONCAUSAL|Did the Discussion/Conclusion acknowledge cross-sectional or noncausal limitations?
CLM_EXTVAL|Did the Discussion/Conclusion mention the need for external validation or calibration?
CLM_SURVEY|Did the Discussion/Conclusion acknowledge complex-survey-design limitations?
CLM_IMPLEMENT|Did the Discussion/Conclusion claim or mention actual implementation or deployment?
CLM_SUPPORT|Analysis/validation evidence directly matched to each claim
SUR01|Population-interpretation category of the principal analytic objective
SUR02|Explicitly stated target population
SUR03|Explicitly stated estimand
SUR04|Were KNHANES sampling weights mentioned?
SUR05|Were sampling weights used in descriptive statistics?
SUR06|Were sampling weights used in model training?
SUR07|Were sampling weights used in performance evaluation?
SUR08|Were stratification variables reported?
SUR09|Were clusters or primary sampling units reported?
SUR10|Were strata and clusters accounted for in variance/uncertainty estimation?
SUR11|Were combined weights used when pooling multiple survey years?
SUR12|Applicability of complex-survey methods
SUR13|Rationale for the survey-method applicability judgement
SUR14|Overall appropriateness of KNHANES survey-design handling
SUR15|Key evidence for the overall judgement
REP01|Does the title identify a prediction/model/ML study?
REP02|Does the abstract report the objective, data, models, and principal results?
REP03|Are the study objective and intended use clear?
REP04|Are the data source and study design reported?
REP05|Are participant eligibility criteria and selection processes reported?
REP06|Are the outcome definition, timing, and source reported?
REP07|Are predictor definitions and measurement timing reported?
REP08|Are the analysed sample size and event/class counts reported?
REP09|Is a sample-size rationale reported?
REP10|Are missing-data methods reported?
REP11|Are preprocessing, variable selection, and model development reported?
REP12|Are hyperparameters and tuning procedures reported?
REP13|Are internal-validation and resampling procedures reported?
REP14|Are evaluation measures, thresholds, and evaluation data reported?
REP15|Are participant flow and analytic-sample characteristics reported?
REP16|Are performance estimates and their uncertainty reported?
REP17|Is the final model provided in a reusable form?
REP18|Are limitations and generalisability discussed?
REP19|Are registration, protocol, data, and code availability reported?
PD_P1|Were appropriate data sources used?
PD_P2|Was an appropriate study design used?
PD_P3|Did inclusion/exclusion produce representative development data?
PD_R1|Were predictors defined and measured similarly for all participants?
PD_R2|Was predictor preprocessing similar for all participants?
PD_R3|Were predictors assessed without outcome information?
PD_R4|Are predictors available at the intended time of use?
PD_O1|Was the outcome appropriately defined and assessed?
PD_O2|Was the outcome defined and assessed similarly for all participants?
PD_O3|Was the outcome assessed without predictor information?
PD_O4|Was the interval between predictor and outcome assessment appropriate?
PD_A1|Was using apparent performance alone avoided?
PD_A2|Was there evidence that the sample size was reasonable?
PD_A3|Were continuous and categorical predictors handled appropriately?
PD_A4|Were missing and censored data handled appropriately?
PD_A5|Were methods to prevent overfitting appropriate?
PD_D1|Development-quality judgement: participants/data sources
PD_D2|Development-quality judgement: predictors
PD_D3|Development-quality judgement: outcome
PD_D4|Development-quality judgement: analysis
PD_OVERALL|Overall development methodological quality
PE_P1|Were appropriate evaluation data sources used?
PE_P2|Was an appropriate evaluation study design used?
PE_P3|Did inclusion/exclusion produce representative evaluation data?
PE_R1|Were predictors defined and measured similarly for all participants?
PE_R2|Was predictor preprocessing similar for all participants?
PE_R3|Were predictors assessed without outcome information?
PE_R4|Are the evaluated model's predictors available at the intended time of use?
PE_O1|Was the outcome appropriately defined and assessed?
PE_O2|Was the outcome defined and assessed similarly for all participants?
PE_O3|Was the outcome assessed without predictor information?
PE_O4|Was the interval between predictor and outcome assessment appropriate?
PE_A1|Was there evidence that the sample size was reasonable?
PE_A2|Were missing and censored data handled appropriately?
PE_A3|After class-imbalance adjustment, was evaluation performed in the unadjusted distribution?
PE_A4|Was there evidence that leakage was avoided in data splitting?
PE_A5|Were all development steps repeated during resampling evaluation?
PE_A6|Was performance appropriately assessed using calibration, discrimination, net benefit, or other relevant measures?
PE_A7|Were the model, threshold, and evaluation method fixed before inspecting evaluation data?
PE_D1|Evaluation risk-of-bias judgement: participants/data sources
PE_D2|Evaluation risk-of-bias judgement: predictors
PE_D3|Evaluation risk-of-bias judgement: outcome
PE_D4|Evaluation risk-of-bias judgement: analysis
PE_OVERALL|Overall evaluation risk of bias
NC01|Continuous outcome and its units
NC02|Evaluation-data context of reported RMSE/MSE/MAE/R-squared
NC03|Were regression residuals or error distributions assessed?
NC04|Masking or missingness-generation procedure
NC05|Reconstruction error and external comparison
NC06|Method for determining the number of clusters
NC07|Were cluster stability and reproducibility assessed?
NC08|Causal identification assumptions and estimand
NC09|Tasks and measures for evaluating representations
NC10|Principal outputs of the nonclassification task
SUP03|Supplementary filename
SUP04|Supplement URL, access date, and checksum
OBJ02|Object type
OBJ03|Object label
OBJ04|Panel label
OBJ05|PDF page
OBJ05B|Printed page
OBJ06|Caption start anchor
OBJ06B|Caption end anchor
OBJ07|Readability status
OBJ08|Could this affect performance values or model rankings?
OBJ09|Structured extracted/read values
OBJ10|Was the object rechecked at original resolution or as a full page?
OBJ11|Disagreement between text extraction and object evidence, and final decision
""".strip().splitlines())

# Exact whole-cell replacements preserve each original rule rather than
# substituting a generic English instruction for non-English content.
PHRASES = dict(line.split("|", 1) for line in """
C2/C1/C0/CU 규칙 적용 / 판정 이유를 근거와 함께 기록|Apply the C2/C1/C0/CU rules; record the rationale with evidence.
JSON 배열; OTHER 선택 시 설명|JSON array; provide a description when OTHER is selected.
KNHANES 기수의 정수 배열; 문자열 금지|Integer array of KNHANES cycles; do not use strings.
PDF page와 별도 기록|Record separately from the PDF page.
R2/R1/R0 규칙 적용|Apply the R2/R1/R0 rules.
R2/R1/R0 규칙 적용 / 판정 이유를 근거와 함께 기록|Apply the R2/R1/R0 rules; record the rationale with evidence.
R=required_components 모두; P=일부; NR=모두 미보고; UNC=상충·판독불가; NA=비적용|R=all required_components reported; P=some reported; NR=none reported; UNCLEAR=conflicting or unreadable evidence; NA=not applicable.
prediction이라는 용어 또는 train-test split만으로 미래예측으로 분류하지 않음|Do not classify as future prediction based solely on the word prediction or a train–test split.
required; conditionally applicable; not required / 판정 이유를 기록|required; conditionally applicable; not required; record the rationale.
signalling responses와 critical-failure rule에 근거|Base the judgement on signalling responses and the critical-failure rule.
가장 강한 주장을 기준으로 판정 / If OTHER, describe.|Judge using the strongest claim; describe OTHER.
같은 연구 안의 공존은 직접 연결이 아니다. 가능한 경우 같은 model·outcome·evaluation·statistical analysis에 연결한다.|Co-occurrence within a study is not direct linkage. Where recoverable, link to the same model, outcome, evaluation, and statistical analysis.
검색 가능한 8–20단어 권장|Prefer a searchable anchor of 8–20 words.
결과가 여러 개면 outcome_id별 반복|Repeat for each outcome_id when multiple outcomes are present.
공개 링크 보고, 실제 접근 확인, 접근 실패를 구분한다.|Distinguish a reported public link, verified access, and failed access.
공식 PROBAST+AI 도구와 E&E를 기준으로 판정 / 근거와 rationale 필수|Judge using the official PROBAST+AI instrument and Explanation and Elaboration; evidence and rationale are required.
공식 알고리즘 적용|Apply the official algorithm.
근거의 명확성이지 연구 질이 아님|Rate clarity of evidence, not study quality.
다른 RAT_*가 PRESENT이면 반드시 ABSENT; 다른 RAT_*가 모두 ABSENT일 때만 PRESENT|Must be ABSENT if any other RAT_* is PRESENT; PRESENT only if all other RAT_* items are ABSENT.
다중자료 관계는 별도 필드로 기록하며 참가자 단위 연계와 병렬사용을 섞지 않는다. 기존 P1/P2의 PRIMARY/MULTI/EXTVAL/OTHER/UNC는 v1.3 crosswalk로 변환한다.|Record multi-dataset relationships separately; do not conflate participant-level linkage with parallel use. Convert legacy P1/P2 PRIMARY/MULTI/EXTVAL/OTHER/UNC through the v1.3 crosswalk.
독립 데이터셋의 병렬분석·개발/평가 분리·외부타당화는 Y로 코딩하지 않고 v1.3 `multi_dataset_relation`에 기록한다.|Do not code parallel analyses of independent datasets, separate development/evaluation datasets, or external validation as Y; record them in v1.3 multi_dataset_relation.
모델별 반복 가능|May be repeated for each model.
무가중 학습을 자동결함으로 처리하지 않음; 목적·estimand와 대응 / 판정 이유를 기록|Do not automatically treat unweighted training as a defect; assess against the objective and estimand and record the rationale.
변수목록을 세어 input 수를 추정하지 않음|Do not infer the input count by counting entries in a variable list.
보고된 분석단위를 기준으로 기록|Record at the reported analytic unit.
불균형 조정 부재 자체를 결함으로 판정하지 않음 / If OTHER, describe.|Absence of class-imbalance adjustment is not itself a defect; describe OTHER.
불확실·판독불가는 정량값의 단독근거로 사용하지 않음|Do not use uncertain or unreadable objects as the sole evidence for a quantitative value.
비연속 연도는 중간연도로 확장하지 않음|Do not fill intervening years in a nonconsecutive list.
선택은 각 훈련분할 내부에서 재수행되어야 함|Selection must be repeated within each training partition.
세미콜론으로 복수 코드 입력|Separate multiple codes with semicolons.
세미콜론으로 복수 코드 입력 / If OTHER, describe.|Separate multiple codes with semicolons; describe OTHER.
실제 사용연도의 정수 배열; 비연속 연도 보간 금지|Integer array of years actually used; do not interpolate nonconsecutive years.
알고리즘·구조, 입력변수/순서, 전처리/인코딩, hyperparameter, 계수·가중치·절편 또는 저장 객체, 분류역치, 적용방법을 구성요소별로 확인한다. 기존 USED/NOT_USED/NR 값은 v1.3에서 재코딩한다.|Check each component: algorithm/architecture, inputs/order, preprocessing/encoding, hyperparameters, coefficients/weights/intercept or saved object, classification threshold, and application instructions. Recode legacy USED/NOT_USED/NR values in v1.3.
알고리즘명이나 저자 표현이 아니라 실제 분석으로 분류|Classify by the actual analysis, not the algorithm name or authors' terminology.
연도 범위와 통합 여부를 별도 판정|Assess the year span and pooling separately.
의도된 사용시점과 누출·순환성을 함께 고려|Consider intended time of use together with leakage and circularity.
재구성 가능성과 정렬을 수치합산하지 않음|Do not numerically sum reconstructability and alignment.
재현성과 신뢰성을 수치합산하지 않고 판정 / 판정 이유를 근거와 함께 기록|Judge without numerically summing reproducibility and reliability; record the rationale with evidence.
저자 동일만으로 병합하지 않음|Do not merge reports solely because they share authors.
저자 동일만으로 연결하지 않음|Do not link reports solely because they share authors.
접근 가능한 공개 URL 상태를 명시하며 요청제공·부분코드·미제공에는 NA|Specify accessible public-URL status; use NA for on-request, partial-code, or no-code categories.
중요도·SHAP 등 모델 내 기여와 OR/RR/β 등 모집단 연관성 주장을 분리한다. 상세 연결은 v1.3 `claim_evidence_records[]`에 둔다.|Separate within-model contributions such as importance/SHAP from population-association claims such as OR/RR/beta. Preserve detailed links in v1.3 claim_evidence_records[].
활용마다 주장 수준은 v1.3 `proposed_use_records[]`에 별도 기록한다.|Record claim strength separately for each use in v1.3 proposed_use_records[].
훈련분포와 평가분포를 별도로 기록|Record training and evaluation distributions separately.
Multiple choice (복수)|Multiple choice
v1.3 `claim_evidence_records[]` 구조|v1.3 claim_evidence_records[] structure
""".strip().splitlines())

DOMAIN_LABELS = dict(zip(
    'ADM FAM ELG TSK DAT POP OUT PRD PRE IMB THR MOD VAL MET VI RAT FUN CLM SUR REP PD PE NC SUP OBJ'.split(),
    ['Judgement certainty','Study-family linkage','Eligibility','Analytic task','Data sources and years',
     'Participants and sample','Outcomes','Predictors','Preprocessing','Class imbalance','Decision thresholds',
     'Models and tuning','Validation','Performance evaluation','Variable interpretation','Rationale for ML',
     'Actual analytic functions','Claims and evidence','Survey-design handling','Reporting completeness',
     'Development methodological quality','Evaluation risk of bias','Nonclassification tasks','Supplements','Source objects']))

def english(value):
    result = PHRASES.get(value, value)
    if re.search('[가-힣]', result):
        raise ValueError(f'Untranslated public protocol text: {value}')
    return result

def english_item(item):
    out = dict(item)
    out['question'] = english(item['question']) if not re.search('[가-힣]', item['question']) else QUESTIONS[item['item_id']]
    for field in ('decision_rule','required_components','response_type','allowed_values','applicability','primary_unit','required_related_ids'):
        out[field] = english(item[field])
    iid = item['item_id']
    if iid != 'TSK06' and not iid.startswith('REP'):
        for field in ('decision_rule','required_components'):
            out[field] = re.sub(r'(?<![A-Z_])UNC(?![A-Z_])', 'UNCLEAR', out[field])
    out['decision_rule'] = out['decision_rule'].replace('UNCLEAR (current UNCLEAR)', 'UNCLEAR').replace('UNCLEAR=current UNCLEAR', 'UNCLEAR')
    if iid == 'OUT16':
        out['decision_rule'] = ('R2: the target, ascertainment source/instrument, timing and all applicable cutoffs/class/composite rules identify the outcome unambiguously. R1: the target is identifiable but a necessary detail is missing (e.g., scale named without class cutoff). R0: the target definition cannot be recovered beyond a label. Judge recoverability, not validity/leakage or executable-code reproducibility; see OUT17/18 separately. NA means this judgement is structurally inapplicable; original response-status metadata remain separate.')
    elif iid == 'PRD13':
        out['decision_rule'] = ('R2: the candidate inputs and final selected inputs (or an explicit statement that they are the same), with essential definitions/coding and model linkage, can be recovered. R1: only part is recoverable (e.g., a top-10 ranking without the candidate list). R0: neither a usable input set nor its construction can be recovered. A variable count alone is insufficient. Judge input-set reconstruction, not availability at prediction time, leakage or full code reproducibility.')
    elif iid in {'REP06','REP07'}:
        out['decision_rule'] += ' This is a single study-level reporting judgement, distinct from least-recoverable outcome/model summaries of OUT16/PRD13; no equivalence or universal reason for differences is implied. OUT16 also requires source and timing. Retained grades are not retroactively adjudicated.'
    elif iid in {f'{p}_D{i}' for p in ('PD','PE') for i in range(1,5)}:
        domain = int(iid[-1]); dev = iid.startswith('PD')
        tool_page = [4,5,6,7][domain-1] if dev else [9,10,11,12][domain-1]
        ee_pages = ['1-2','2-4','5-6','7-8'][domain-1] if dev else ['9-10','10-12','12-14','14-16'][domain-1]
        direction = ('HIGH=high quality (official low quality concern); LOW=low quality (official high concern).' if dev else 'LOW=low risk of bias; HIGH=high risk of bias.')
        out['decision_rule'] = (f'Moons et al. (2025), official Table S3 p.{tool_page}, domain {domain}; E&E Light Table S4 pp.{ee_pages}. '
            'Y/PY support a favourable domain judgement; N/PN flag a concern, not automatic domain failure. Weigh its material effect and record the source-linked rationale; NI means insufficient information, not confirmed failure. '
            + direction + ' UNCLEAR=insufficient basis for a domain judgement; NA=outside the relevant development/evaluation scope. No numeric score or additional critical-failure algorithm is used.')
    elif iid in {'PD_OVERALL','PE_OVERALL'}:
        rule = ('All applicable domains HIGH => HIGH; any LOW => LOW; otherwise any UNCLEAR => UNCLEAR.' if iid=='PD_OVERALL' else 'All applicable domains LOW => LOW; any HIGH => HIGH; otherwise any UNCLEAR => UNCLEAR.')
        out['decision_rule'] = ('Official Table S3 Step 4, p.13 (Moons et al., 2025), mapped to this review\'s direction-specific labels. '+rule+' All NA => NA (review applicability convention). Preserve unit-level rationale and any justified departure rather than silently overriding domain values. Legacy UNC is displayed as UNCLEAR; original stored values remain in S7.')
        out['decision_rule'] = out['decision_rule'].replace('Legacy UNC is displayed as UNCLEAR;', 'Legacy unclear codes are displayed as UNCLEAR;')
    return out
