# 01_search: the search

Role: how the records were found. The search was run on 2 November 2026 in PubMed, Europe PMC, OpenAlex, KCI and the
KDCA publication list (Supplementary Table S3 of the article).

| File | Content |
|---|---|
| `queries.txt` | The query strings sent to Europe PMC, PubMed and OpenAlex, as printed by `query.py`. KCI was searched with each Korean survey name combined with each machine-learning term, and the KDCA KNHANES publication list was filtered with the same terms (both in `run_search.py`) |
| `query.py` | The search terms (survey names, machine-learning terms; the Korean terms are the exact terms searched) |
| `run_search.py` | Retrieval and deduplication code |
| `flow.json` | Records per source, after deduplication and after the type filters (the top of the PRISMA flow) |
| `PRISMA-S_checklist.md` | The completed PRISMA-S checklist: where the article reports each search-reporting item (published here only) |
| `dedup_rule_merges.tsv` | Database records merged with an included article as documented deduplication exceptions (bibliographic fields only) |
