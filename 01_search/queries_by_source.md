# Search queries by source

Baseline searches: 3-5 September 2026, no date or language limits. Exact code: scripts/ (census_*.py).
An update re-running the same queries was started on 31 October 2026 (see search_updates.csv).

| Source | Query | Script |
|---|---|---|
| Europe PMC | Layer A: TITLE_ABS contains KNHANES, "Korea National Health and Nutrition Examination Survey" or "Korean National Health and Nutrition Examination Survey" (all records). Layer B: full text contains a KNHANES term AND an ML term (list in census_epmc.py) | scripts/census_epmc.py |
| PubMed | KNHANES[tiab] OR "Korea National Health and Nutrition Examination Survey"[tiab] OR "Korean National Health and Nutrition Examination Survey"[tiab] OR "Korea National Health and Nutrition Examination Survey"[mh]; records not in Europe PMC added | scripts/census_pubmed.py |
| OpenAlex | title_and_abstract.search: "KNHANES"; "Korea National Health and Nutrition Examination Survey" | scripts/census_openalex.py |
| Korean Citation Index | KEYALL: 7 survey names x 43 ML terms (301 queries; lists in census_kci.py) | scripts/census_kci.py |
| KDCA KNHANES publication list | complete author-registered publication list (not a keyword search) | scripts/census_kdca.py, census_kdca_match.py |

Deduplication: DOI, then PubMed ID, then normalised title (deduplication.py). Title/abstract screening: deterministic
dictionary of ML and prediction terms (keyword_filter.py; tiers T1 ML/AI method, T2 ML-adjacent, T3 prediction model
without ML term; records with no term are excluded at this stage).
