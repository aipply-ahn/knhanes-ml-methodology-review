# Suspected errors in source reports (internal audit record, S13)

Not coding errors and not an analysis variable; kept so that judgements depending on them can be traced.

| Study | Issue | Effect on coding |
|---|---|---|
| KHM220 | The ML section describes a cohort of 198,964 "stratified across four clusters", apparently copied from KHM259 (choi2025phenotypic); the asthma modelling sample is unclear | RC09 = 0, RC13 = 0 (counts describe another sample) |
| KHM259 | Flow chart incoherent: 313,027 "2019 cycle" respondents from 513,044; final 198,964 unchanged after further exclusions | RC09 = 0 |
| KHM171 | Table 2 labelled n = 11,781 (whole sample) with true positives (5,220) exceeding all cases (3,280); Fig. 1 describes a test-set evaluation | RC30 = 1 on the Table 2 footnote (10-fold CV) |
| KHM040 | Group sizes do not add up to the stated 33,265 | RC09 = 0 |
| KHM182 | Eligibility contradictory (Methods "aged 19-64" vs aim 40-64) | RC09 = 0 |
| KHM089 | Methods name LASSO while the RF top-30 ranking carries variables into the model | RC45 judged on the RF ranking |
| KHM185 | Only the medRxiv preprint is available; the 2024 journal version was not obtained | all judgements provisional |
