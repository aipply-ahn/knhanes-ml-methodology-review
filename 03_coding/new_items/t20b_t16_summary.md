# T20b / T16 coding summary (2026-10-31)

Source: full-text markdown of the 193 studies listed in `study_list.tsv`. Output: `t20b_t16.tsv`.
Coding was done in 13 parallel batches using one written brief, followed by a consistency pass across batches.

## Counts

| Item | 1 | 0 | NA | Total |
|---|---|---|---|---|
| T20b (all studies) | 137 (71.0%) | 56 | - | 193 |
| T16 (FUN_TRANSPORT = PRESENT, n = 34) | 27 (79.4%) | 7 | 159 (all ABSENT) | 193 |
| T16 after addendum (34 PRESENT + 5 discrepancies) | 32 (82.1%) | 7 | 154 | 193 |

- T20b by FUN_TRANSPORT: PRESENT 12/34 = 1; ABSENT 125/159 = 1. Studies with separate evaluation data mostly fail because the evaluation source has no characteristics of its own.
- On reading, none of the 34 PRESENT studies turned out to lack separate evaluation data, so none was recoded to NA.
- T16 = 0 (7): KHM004, KHM014, KHM032, KHM037, KHM121, KHM184, KHM192.

## Rules applied consistently

- **Separate sources.** A held-out survey year, another survey, another country or a hospital is a separate data source, and it needs its own characteristics for T20b = 1. A random train/test split of the same pooled KNHANES data is not a separate source.
- **Pooled tables.** A table pooling development and temporal evaluation years counts as 0 for T20b. This applies to KHM014, KHM020, KHM037, KHM181, KHM184, KHM192 and KHM235.
- **Text instead of a table.** A short in-text description of an evaluation source counts if it gives numeric demographics plus N and outcome prevalence, e.g. KHM002 (age, % female, BMI, prevalence). A verbal comparison with the numbers only in a supplement does not count, e.g. KHM089.
- **Supplement-only characteristics.** If the characteristics appear only in a supplement that is not in the md, the study is coded 0. This applies to KHM001, KHM006, KHM033, KHM044, KHM089, KHM094, KHM168 and KHM182.
- **Characteristics without the outcome.** Characteristics with no number or % with the outcome are coded 0. This applies to KHM013, KHM098, KHM099, KHM117, KHM142, KHM152 and KHM221.
- **Variable dictionaries.** A variable list or dictionary without distributions is coded 0. This applies to KHM032, KHM111, KHM124, KHM125, KHM132, KHM160 and KHM163.
- **T16 sameness statements.** An explicit statement that the evaluation data used the same criteria or process counts as 1. Examples are KHM063 ("same flow chart"), KHM064 ("A similar process was used"), KHM181 and KHM257 ("same inclusion and exclusion criteria"). So does a statement about predictor harmonisation or availability across years or surveys, as in KHM087, KHM182 and KHM235. A year that is only named, or eligibility that is only implied by a shared flowchart, is coded 0. A text search of the T16 = 0 papers for such statements found none.

## Borderline cases (author may wish to review)

### T20b

- **KHM020 (oh2022machinea): changed from the batch's 1 to 0 in the consistency pass.** The paper trains on 2016–2018 and tests on the 2019 KNHANES year, but its tables pool 2016–2019. It is flagged FUN_TRANSPORT = ABSENT, so T16 = NA.
- **KHM002: coded 1.** The external KNHANES set is described only in text: median age, % female, BMI and prevalence. The full table is in S1 Table.
- **KHM085, KHM096, KHM175 and KHM217: coded 1 from text descriptions.** For KHM085 this is the second source. In each case the full tables are in the supplement.
- **KHM077, KHM101, KHM130, KHM204, KHM220, KHM233, KHM248 and KHM052: coded 1, but the table is not stratified by outcome.** These tables are split by sex, exposure or another grouping, or are overall only. The outcome count is given elsewhere in the text or in another table.
- **KHM016, KHM118, KHM200 and KHM238: coded 1.** The characteristics are survey-weighted counts or % by outcome group, and the unweighted N is given in the text.
- **Coded 1 despite inconsistent Ns:** KHM009 (the table describes the cohort before exclusions), KHM040, KHM046 and KHM220 (the table N differs from the analysed N).
- **KHM021: coded 0.** This is a letter that reports only N, mean age and stroke prevalence.
- **KHM149: coded 0.** The outcome distribution is shown only in a figure panel, with no number.
- **KHM155: coded 0.** It gives predictor distributions but no N and no outcome %.
- **KHM191: coded 0.** The Taiwan and KNHANES datasets are characterised, but the third dataset (China) is not.
- **KHM221: coded 0.** Both cohorts are characterised, but there is no count or % with the exacerbation outcome.

### T16

- **KHM087 and KHM235: coded 1 on predictor-availability or harmonisation statements only.** Coding them 0 would also be defensible.
- **KHM051: coded 1 on Table 1.** Table 1 compares the 2014–2018 and 2019–2020 sets side by side. There is no explicit sentence saying the definitions are the same.
- **KHM014 and KHM184: coded 0.** Eligibility is implied by pooled curation or a shared flowchart, but the paper never states it.
- **KHM121: coded 0.** The paper notes only a difference in the prevalence of suicidal ideation (SI). It says nothing on eligibility, outcome or predictors.
- **KHM004: coded 0.** The origin of the "independent external validation set" (n = 50) is unclear. NA would also be defensible.

## Possible FUN_TRANSPORT flag errors (not recoded; T16 left NA per the instructions)

These studies are flagged ABSENT, but on reading they evaluate on separate data:

- **KHM013:** 2020 temporal validation cohort.
- **KHM020:** 2019 hold-out test year.
- **KHM058:** develops on 2013–2015 and validates on 2016. It says variables were kept only if measured the same way across years, so T16 would likely be 1.
- **KHM137:** develops on CHARLS and validates on KNHANES, UK Biobank and NHANES.
- **KHM195:** trains on KNHANES V-1 (2010) and tests on V-2 (2011). Table 1 compares the two, so T16 would likely be 1.

KHM133 is a counterexample. It has a hospital (YSH) source, but that source was pooled into training, so it has no separate evaluation data, and ABSENT is correct.

### Addendum: T16 coded for these five (FUN_TRANSPORT raw-code discrepancies)

On the coordinator's request, T16 was coded for these five under the same rule. All five are 1, and each T16_basis is tagged "FUN_TRANSPORT raw-code discrepancy".

| Study | T16 | Basis |
|---|---|---|
| KHM013 | 1 | Table 1 and the text compare the training (2016–2019) and validation (2020) cohorts. |
| KHM020 | 1 | **Borderline.** It states only that predictors were the same: the variables were limited to those surveyed in common across 2016–2019. This follows the KHM235 precedent. |
| KHM058 | 1 | Variables were kept only if their measurement was unchanged across 2013–2016, and Table 1 compares development and validation. |
| KHM137 | 1 | Table 2 compares the CHARLS, KNHANES, UK Biobank and NHANES cohorts, and the outcome uses waist cut-offs specific to each population. |
| KHM195 | 1 | Table 1 compares the training (V-1) and test (V-2) sets with p values. |

Updated T16 counts (n = 193): 32 coded 1, 7 coded 0, 154 coded NA. Of the 39 studies with separate evaluation data (34 flagged PRESENT plus these 5), 32 are 1 (82.1%).

These five remain FUN_TRANSPORT = ABSENT in the raw coding. Following the record-raw-schema rule, the flag correction is logged here as a proposal only, for the author to decide.
