# Analysis code

tools/ holds the project scripts as used for the manuscript (copied without change except that the API contact
e-mail is read from the CONTACT_EMAIL environment variable). Main entry points:

- figures: make_main_figures.py (Figures 1-5 and appendix figures)
- core checklist: checklist_v22.py (scores), checklist_v22_table.py (Table 1), add_checklist_columns_v22.py (Additional Data 1)
- Additional Data 1 workbook: build_data1_workbook.py
- supplements: build_standalone_supplements.py

These scripts currently expect the project layout (protocol JSON records under data/protocol_v1_2/final, which hold
per-study evidence quotes and are not published here). reproduce_all.py documents the order of the steps. A standalone
pipeline that regenerates all tables and figures from the public coded data (03_coding/study_level_data.xlsx) is in
preparation and will be released with the submission tag.
