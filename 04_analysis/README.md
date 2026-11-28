# 04_analysis: from codings to the reported numbers

Role: how the settled codings became the study-level variables, the numbers, the figures and the tables
of the article and of Additional Data 1 and 2.

| Path | Content |
|---|---|
| `code/coding_derive.py`, `code/coding_classify.py` | Derivation of the study-level variables and the study groups from the settled codings. Variables of this earlier derivation that describe a concept already given by a reader or `fig_*` column of Additional Data 1 under another rule (e.g. `weights_fitting`, `auc_reported`, `scope_*`, `val_*`, `fam_*`) are not in Additional Data 1; the analysis values are the reader and `fig_*` columns (list in the Additional Data 1 README) |
| `code/legacy_numbers.py`, `code/legacy_figdata.py`, `code/legacy_figures.py`, `code/legacy_supplement.py`, `code/oct_supplement.py` | Numbers, figure data, figures and supplementary tables |
| `code/make_main_figures.py`, `code/make_supplementary_figures.py`, `code/checklist_v15.py`, `code/checklist_desc.py` | Figure drawing and the reporting checklist |
| `code/build_excel.py` | The study-level Excel file |
| `code/req_macros.py` | Numbers for the 52 individual TRIPOD+AI requirements |
| `code/recount_from_additional_data.py` | Run this to recount the article's aggregates from Additional Data 1–2 and `probast_units.csv`: it reads only `Additional_Data_1.xlsx`, `Additional_Data_2.xlsx` and `probast_units.csv` (all in `04_analysis/`; the PROBAST+AI unit totals and domain counts are recounted from `04_analysis/probast_units.csv`), compares each count with the number in `numbers/` and prints OK or FAIL, and lists the few reported counts that these files cannot give (process counts of selection and coding). From the repository root: `python 04_analysis/code/recount_from_additional_data.py` (needs openpyxl; numpy for one p-value). `validate_counts.py` runs it as its last check |
| `probast_units.csv` | Unit-level PROBAST+AI judgements of the 217 classification studies, for recounting the unit totals and the domain counts: one row per study (`study_id` of Additional Data 1), assessment (`development` or `evaluation`), unit, and field (`overall` or a domain: `PD_D1`–`PD_D4`, `PE_D1`–`PE_D4`, domains 1–4 = participants, predictors, outcome, analysis), with the judgement as coded (`LOW`, `HIGH`, `UNC` = unclear, `NA` = not assessed). `unit_label` is the coders' short model and data-set descriptor that pairs a unit's domain and overall judgements; where a descriptor repeated report wording or was written in Korean it was replaced by `unit N` (same replacement within a study; `label_neutralised` = yes). A domain count takes the evaluation units with an overall judgement and their judgement in that domain, matched by label (a study with one unit judged overall and one judged in the domain pairs the two). Made by `code/export_probast_units.py` |
| `numbers/oct_numbers.tex`, `numbers/legacy_numbers.tex`, `numbers/req_numbers.tex` | The numbers cited in the article, as LaTeX macros (`req_numbers.tex`: the 52 individual TRIPOD+AI requirements) |
| `Additional_Data_1.xlsx`, `Additional_Data_2.xlsx` | Copies of Additional Data 1 (study-level dataset) and 2 (reporting assessment of the classification studies); the report-level reporting status is in `03_coding/reporting_status.csv` |

The code runs on the author's full coding files, which also hold the verbatim excerpts from the reports; the final
structured codings it uses are published as Additional Data 1 and 2 and `03_coding/reporting_status.csv`, and these copies and the numbers let a reader check
the reported aggregates. Additional Data 1 and 2 are also published with the article.
