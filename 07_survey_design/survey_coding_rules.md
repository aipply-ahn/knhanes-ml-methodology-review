# Survey-design coding rules

KNHANES is a stratified, clustered probability sample with sampling weights. Each analysis stage is coded
separately; "used", "explicitly not used", "not reported" and "unclear" are kept apart, and use is not equated with
methodological validity.

| Stage | Raw code | Question |
|---|---|---|
| Weights mentioned | SUR04 | Were KNHANES sampling weights mentioned? |
| Descriptive statistics and population estimates | SUR05; RC48 | Were descriptive statistics weighted? RC48 (reporting item): whether descriptive statistics and population estimates were weighted, with the method, or identified as unweighted sample summaries; POPEST records whether population-level estimates were presented |
| Model fitting | SUR06; C22 | Were weights used in model fitting (and is it reported how, or why not)? |
| Performance evaluation | SUR07; C30 | Were performance measures weighted? |
| Uncertainty | SUR10; C33 | Were strata and PSUs used for variance estimation? |
| Combined years | SUR11; C04 | Were weights adjusted when pooling survey years? |
| Importance aggregation | C40 | When participant-level importance (SHAP, LIME) was aggregated, were weights used? |

Full definitions: 03_coding/raw_coding_protocol.md (SUR01-SUR15) and 06_reporting_checklist/core_checklist.csv.
