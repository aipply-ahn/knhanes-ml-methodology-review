# RC48 — Survey design in descriptive statistics and population estimates

Coded 2026-10-31 from the full texts of all 193 studies (`study_list.tsv`); row-level output in `rc48_descriptive_design.tsv`.
SUR05_raw was used only as a hint; NOT_USED codes that the earlier coder had inferred from n/N arithmetic were not counted as an author report.

## Counts

| RC48 | n |
|---|---|
| 1 (met) | 37 |
| 0 (not met) | 144 |
| NA (no descriptive statistics/population estimates) | 12 |

| POPEST | n |
|---|---|
| Y | 39 |
| N | 150 |
| UNC | 4 |

RC48 x POPEST: 1/Y 35, 1/N 2 (KHM047, KHM086: explicitly unweighted), 0/Y 4 (KHM063, KHM178, KHM220, KHM089), 0/UNC 4 (KHM011, KHM138, KHM168, KHM231), 0/N 136, NA/N 12.

## Cross-tab RC48 x SUR05_raw

| RC48 \ SUR05_raw | USED | NOT_USED | NR | UNC | total |
|---|---|---|---|---|---|
| 1 | 33 | 2 | 1 | 1 | 37 |
| 0 | 3 | 5 | 134 | 2 | 144 |
| NA | 0 | 0 | 12 | 0 | 12 |
| total | 36 | 7 | 147 | 3 | 193 |

- USED → 0 (3): KHM063 (claims "weighted characteristics" but names no weight or survey procedure), KHM011 (blanket "procedures employed weighted data"; Table 1 n (%) not identified), KHM001 (weighting stated for the logistic regression only).
- NOT_USED → 1 (2): KHM047 and KHM086 state explicitly that sampling weights / complex-sample analysis were not applied.
- NOT_USED → 0 (5): KHM020, KHM005, KHM015, KHM023 and KHM218 never state the weighting status; the earlier NOT_USED came from n/N arithmetic.
- NR → 1 (1): KHM033 (descriptive statistics weighted with NHANES MEC weights).
- UNC → 1 (1): KHM084 (weighted frequencies, % and means with "complex sample weights").
- UNC → 0 (2): KHM180 (blanket claim; descriptive tables in Python/SciPy give mean ± SD), KHM245 (only the p-values are from complex-sample tests).

## Decision conventions applied

- Rule (a) needs both: an explicit statement that the descriptive statistics are weighted, and some identification of the weight or design, such as KNHANES sampling/complex-survey weights, strata/cluster/weights, a named weight variable, Rao-Scott with weighted %, or a survey procedure.
- A weighting statement that covers only regression or ML, or a blanket "analyses considered the design", gives 0 when nothing indicates the descriptive tables used it.
- "mean ± SE" in a table with no weighting statement gives 0 (KHM039, KHM064, KHM202, KHM204, KHM162).
- NA applies only when the paper gives nothing beyond sample/split counts: no percentages, means or prevalence of any characteristic or of the outcome.
- An outcome class distribution with % counts as a descriptive statistic, so these papers get 0 (see the borderline list).

## Hard / borderline cases

1. **KHM086 (1)**: the "not performed" statement says complex-sample analysis "fully reflecting" weights, strata and clusters (완전하게 반영한) was not done. I read this as no design-based analysis, so Table 1 is unweighted; it could be read as partial weighting.
2. **KHM047 (1)**: "sampling weights were not applied" is a study-wide statement, not specific to Table 1. It was taken to cover the descriptive statistics.
3. **KHM084 (1) / KHM003 (1) vs KHM063 (0)**: KHM084 and KHM003 name "complex sample weights" / "complex-survey-design weights" without a variable name, strata or cluster, and were scored 1. KHM063 says only "weighted characteristics" with mean ± SE, so it is 0 under the "claims weighting but nothing identifies how" clause.
4. **KHM019 (1)**: descriptive statistics come from a dataset resampled/expanded with the itvex weight, with no design-based variance. Scored 1 because the weight is named and the weighted population is described.
5. **KHM224 (1)**: SUDAAN plus expansion of records by health-examination weights; weighted chi-square tables. Strata and cluster are not stated, but the weight and the software are.
6. **KHM095 (1)**: the Methods describe weighted means (SE) and Rao-Scott with SAS PROC SURVEY, but the Table 1 note says "mean ± SD or number (%)". The text was followed.
7. **KHM002 (1), KHM033 (1)**: the weighting refers to NHANES (development data). The KNHANES external-validation descriptives are not stated as weighted. Scored 1 on the literal "any of" rule; the score could go to 0 if RC48 is restricted to the KNHANES component.
8. **KHM004 (NA)**: the KNHANES component has only n=460 and the split sizes. The population-weighted ASIRs are GBD country aggregates (out of scope), so NA rather than 1.
9. **KHM169, KHM164, KHM110, KHM139, KHM132, KHM087, KHM001, KHM056, KHM180, KHM079, KHM245 (0)**: weights are used in regression/ML, or stated as a blanket, but the descriptive tables are not identified as weighted or unweighted. KHM087 says ML analyses were unweighted but says nothing on the descriptives. KHM056's prevalence equals n/N despite the complex-sampling statement.
10. **Outcome-distribution-only papers scored 0 (not NA)**: KHM111, KHM124, KHM122, KHM218, KHM123, KHM132, KHM191. Their only descriptive statistic is the outcome n (%). Under a stricter NA convention ("no participant characteristics") these would be NA.
11. **Counts-only papers scored NA**: KHM160, KHM080, KHM017, KHM106, KHM050, KHM104, KHM041, KHM163, KHM029, KHM032, KHM210. KHM163 and KHM032 list variable value ranges [min,max] in a definitions table, which was not treated as descriptive statistics.
12. **POPEST borderline**:
    - Y without design handling: KHM178 ("estimated OP prevalence among Korean adults ≥50 years"), KHM220 (prevalence of allergic disease "in Korean children"), KHM089 (regional prevalence disparities across Korea), KHM063.
    - UNC: KHM231 (sample prevalence compared with other countries' general-population rates), KHM138 (KNHANES prevalence used for QALY gains per 100,000 persons), KHM011, KHM168.
    - Plain "prevalence was X% in this study" statements were coded N.
