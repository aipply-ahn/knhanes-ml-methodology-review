# Rules r5 (2026-10-31): new item RC47 Data availability (TRIPOD+AI 18e) — published as C35 in Table 1

Source of truth for the criterion: TRIPOD+AI item 18e "Provide details of the availability of the study data"
(references/guidelines/TRIPOD_AI_checklist.pdf). Distinct from 5a (sources of data: which data and why).

Met (1): the report gives details of the availability of the study data, in a data availability statement or anywhere
in the text, e.g.
- KNHANES data are publicly available / can be downloaded from the KNHANES (KDCA) website, with or without the link;
- the access procedure (user registration, approval of use on the KNHANES homepage, data use agreement with KDCA);
- a repository or DOI for processed data;
- availability on request from the authors (with or without conditions);
- why sharing is restricted and how access can be obtained (e.g., restricted by law, obtainable through the KDCA).
Not met (0): no such details; KNHANES named only as the data source (5a); mention only in references or
acknowledgements; "not applicable"; "data are contained within the article"; a statement about code or another survey only.
Applies to all 193 core studies (no NA).

Current judgements and basis: rc47_data_availability.tsv (Claude Code, full-text reading; 113 met).
Full texts: references/md/<key>.md (study list: prompts/implementation_records/v15_recode/batch_*_input.json).

## Added to round 7 (2026-10-31): official TRIPOD+AI items 20b and 16
Current values and basis: new_items_20261031/t20b_t16.tsv (columns T20b, T16 with basis and quote).
- T20b (all 193): 1 if characteristics of the analysed participants (demographics and key predictors) are reported
  together with the sample size and the number or % with the outcome, overall or by outcome group (table or text);
  with several data sources (e.g., development and external data), for each source. Amount of missing data is judged
  by another item (ignore here). Characteristics only in a supplement not available in references/md are 0 (flag it).
- T16 (only studies that evaluate on separate data: temporal, other year/cycle or other source; others NA):
  1 if the paper states how the evaluation data differ from, or are the same as, the development data in setting or
  period, eligibility, outcome definition or predictors (text or comparison table); 0 if the evaluation data are only named.

## Added to round 7: RC48 Survey design in descriptive statistics and population estimates (KNHANES-specific)
Current values: new_items_20261031/rc48_descriptive_design.tsv (RC48 scored; POPEST recorded, not scored).
Judged on the KNHANES data of the study (statements about NHANES or other surveys only do not count).
- 1: descriptive statistics stated to be weighted AND the weight or design is identifiable (named weight variable,
  complex-sample analysis with strata/cluster/weights, PROC SURVEY*, SPSS Complex Samples, weighted %/mean±SE notes);
  or the authors explicitly state that descriptive statistics are unweighted / complex-sample analysis was not applied;
  or population estimates are presented with the design handling described.
- 0: descriptive statistics (including only the outcome n (%)) presented but weighted vs unweighted cannot be
  determined from the authors' text (blanket "weighted data were used", weighting stated only for regression or ML,
  unweighted status inferred only from n/N arithmetic); or population-level statistics without design handling.
- NA: nothing beyond sample or split counts.
- POPEST: Y if any statistic is presented as a population-level estimate (weighted, or worded as a population
  figure); N if only the analytic sample is described; UNC if unclear.
