#!/usr/bin/env python3
"""Validate final consensus -> derived JSON -> TeX -> rendered PDF propagation."""
import json, re, subprocess
import fitz
from openpyxl import load_workbook
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NUM=ROOT/"results/derived/protocol_v1_2_manuscript_numbers.json"; CONS=ROOT/"results/derived/protocol_v1_2_consensus_results.json"
MACRO=ROOT/"manuscript/protocol_v1_2_numbers.tex"; TEX=ROOT/"manuscript/bmc_main.tex"; PDF=ROOT/"manuscript/bmc_main.pdf"
OUT=ROOT/"data/protocol_v1_2/MANUSCRIPT_PROPAGATION_AUDIT.json"
SUPP=ROOT/"manuscript/supplementary"
nums=json.loads(NUM.read_text())["numbers"]; cons=json.loads(CONS.read_text())
macros={k:int(v.replace(",","")) for k,v in re.findall(r"\\newcommand\{\\(\w+)\}\{([\d,]+)\}",MACRO.read_text())}
expected={"ScreenedReportN":"reports_screened_final","StudyN":"studies","HealthN":"health","MethodN":"method","ClassN":"classification","AllClassN":"all_classification","HealthClassN":"health_classification","ContinuousN":"continuous","OtherN":"other","PredictionN":"prediction","ProtocolItemN":"protocol_items","DevelopmentN":"development_units","EvaluationN":"evaluation_units","VisualN":"visual_objects","VisualContainerN":"visual_containers","VisualPanelN":"visual_panels","MainFigureN":"main_figures","MainTableN":"main_tables","SuppFigureN":"supplement_figures","SuppTableN":"supplement_tables","FigureObjectN":"figure_objects","ImageInterpretedN":"image_interpreted","ImageCompleteN":"image_complete","ImageUnavailableN":"image_source_unavailable","ImageManualN":"image_manual_resolution","MetricFigureN":"metric_sensitive_figures","SupplementFileN":"supplement_files","SupplementStudyN":"supplement_studies","EvidenceRecordN":"evidence_records","PerformanceRecordN":"performance_metric_records","BestSelectionN":"best_model_selections","RetractedN":"retracted_corpus_history","ExternalOnlyN":"external_validation_only"}
checks=[]
def check(name,ok,detail): checks.append({"check":name,"status":"pass" if ok else "fail","detail":detail})
p2=list((ROOT/"data/protocol_v1_2/P2_blinded").glob("KHM*_P2.json")); consensus=list((ROOT/"data/protocol_v1_2/final_consensus").glob("KHM*_CON.json")); finals=list((ROOT/"data/protocol_v1_2/final").glob("KHM*_final.json"))
check("record_census",len(p2)==256 and len(consensus)==len(finals)==255,f"P2={len(p2)}, consensus={len(consensus)}, final={len(finals)}")  # prompt 106
adj=json.loads((ROOT/"data/protocol_v1_2/ADJUDICATION_SUMMARY.json").read_text())
check("adjudication_complete",adj.get("status")=="COMPLETE" and adj.get("final_records")==222,str(adj.get("status")))
check("derived_status",cons.get("status")=="PASS",cons.get("review_status"))
check("denominators",cons["denominators"]=={"reports":255,"studies":250,"prediction":238,"classification":222,"continuous":16,"other":12},str(cons["denominators"]))  # prompt 106
final_records=[json.loads(p.read_text()) for p in finals]
reason_records=[r for r in final_records if r.get("corpus_status",{}).get("include",r.get("protocol_items",{}).get("ELG04",[{}])[0].get("value")=="Y") and r.get("protocol_items",{}).get("TSK01",[{}])[0].get("value")=="CLS"]
reason_codes={c for r in reason_records for x in r.get("adjudication",{}).get("classification_reason_codes",[]) for c in x.get("reason_codes",[])}
check("classification_reason_codes",len(reason_records)==222 and all(r.get("adjudication",{}).get("classification_reason_codes") for r in reason_records) and {"outcome_rule_not_reconstructable","cutoff_basis_not_reported","predictor_set_not_reconstructable","target_component_used_as_predictor","post_outcome_predictor","insufficient_evidence"} <= reason_codes,f"records={len(reason_records)}; codes={len(reason_codes)}")  # prompt 106
expanded=[r.get("adjudication",{}).get("expanded_model_task_audit") for r in final_records if r.get("corpus_status",{}).get("include",r.get("protocol_items",{}).get("ELG04",[{}])[0].get("value")=="Y")]
check("expanded_model_task_audit",len(expanded)==250 and all(expanded) and all(x.get("algorithm_development",{}).get("evidence_location") is not None for x in expanded),f"included expanded records={len(expanded)}")  # prompt 106
flow=[r.get("adjudication",{}).get("analytic_flow") for r in final_records]
required_flow_fields={"source_population_size_reported","eligibility_criteria_reported","exclusion_numbers_reported","exclusion_reasons_reported","final_analytic_sample_reported","outcome_cases_or_prevalence_reported","complete_cohort_traceability"}
check("analytic_flow",len(flow)==255 and all(x is not None for x in flow) and sum(x.get("applicability")=="INCLUDED" for x in flow)==250 and all(len(x.get("fields",{}))==34 and required_flow_fields <= set(x.get("fields",{})) for x in flow if x.get("applicability")=="INCLUDED"),"255 rows; 250 included records with 34 stage-specific fields")  # prompt 106
restriction_dims=[r.get("adjudication",{}).get("selection_restriction_dimensions",{}) for r in final_records if r.get("corpus_status",{}).get("include",r.get("protocol_items",{}).get("ELG04",[{}])[0].get("value")=="Y")]
check("selection_restriction_dimensions",len(restriction_dims)==250 and all(set(x.get("fields",{}))=={"age_restriction","sex_restriction","disease_or_risk_restriction","measurement_or_data_availability_restriction"} for x in restriction_dims),"220 records; four nonexclusive evidence-linked dimensions")  # prompt 106
continuous_audits=[r.get("adjudication",{}).get("continuous_interpretation_audit") for r in final_records if r.get("protocol_items",{}).get("TSK01",[{}])[0].get("value")=="CONT" and r.get("corpus_status",{}).get("include",True)]
check("continuous_interpretation_audit",len(continuous_audits)==16 and all(continuous_audits) and sum(x.get("status","").startswith("USED") for x in continuous_audits)==11,"16 full-text audits; 11 explicit model-based importance/interpretation")  # prompt 106
purpose=json.loads((ROOT/"results/derived/study_purpose_audit.json").read_text())
purpose_records=[r.get("adjudication",{}).get("study_category_and_dataset_use") for r in final_records if r.get("corpus_status",{}).get("include",r.get("protocol_items",{}).get("ELG04",[{}])[0].get("value")=="Y")]
check("study_category_audit",purpose["summary"]["denominator"]==250 and purpose["summary"]["study_category"]=={"HEALTH_ANALYSIS":214,"METHOD_RESEARCH":36} and purpose["summary"]["method_research_category"]=={"METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT":26,"EXISTING_METHODS_COMPARISON_OR_EVALUATION":10} and purpose["summary"]["health_analysis_purpose"]=={"HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION":120,"VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION":21,"POPULATION_ASSOCIATION_ANALYSIS":14,"HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY":3,"CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION":4,"MULTIPLE_CO_PRIMARY_PURPOSES":52} and purpose["summary"]["health_analysis_purpose_components"]=={"HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION":204,"VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION":83,"POPULATION_ASSOCIATION_ANALYSIS":21,"HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY":3,"CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION":4} and len(purpose_records)==250 and all(x and x.get("evidence") and x.get("purpose_judgement_basis") for x in purpose_records),"250 evidence-linked records; exclusive health purpose 120/21/14/3/4/52; method 26/10")  # prompt 106
v13=json.loads((ROOT/"data/protocol_v1_3/purpose_evidence_addendum.json").read_text())
v13_records=[r.get("adjudication",{}).get("purpose_evidence_v1_3") for r in final_records if r.get("corpus_status",{}).get("include",r.get("protocol_items",{}).get("ELG04",[{}])[0].get("value")=="Y")]
check("purpose_evidence_v1_3",v13["summary"]["denominator"]==250 and v13["summary"]["primary_orientation"]=={"HEALTH_FOCUSED":214,"METHOD_FOCUSED":36} and v13["summary"]["task_denominators"]=={"D_CLS":222,"D_HEALTH_CLS":192} and v13["summary"]["association_audit"]["any_association_estimate_reported"]=={"Y":63,"N":187} and v13["summary"]["health_focused_association_audit"]["any_association_estimate_reported"]=={"Y":60,"N":154} and v13["summary"]["association_audit"]["association_was_substantive_output"]=={"Y":20,"N":230} and v13["summary"]["association_audit"]["population_association_was_survey_aware"]=={"N":246,"Y":4} and len(v13_records)==250 and all(x for x in v13_records) and v13["summary"]["independent_human_review_complete"] is False,"250 v1.3 records; all/health association outputs=63/60; substantive/survey-aware=20/4; human review not fabricated")  # prompt 106
sf=json.loads((ROOT/"results/derived/final_selection_flow.json").read_text()); s=sf["sources"]; f=sf["flow"]
selection_closed=(sum(s[k] for k in ("europe_pmc_unique","openalex_unique","pubmed_unique_beyond_europe_pmc","korean_citation_index","kdca_publication_list"))==s["total_before_cross_source_deduplication"] and f["duplicates_removed"]+f["unique_records_screened"]==s["total_before_cross_source_deduplication"] and f["terminology_exclusions"]+f["records_assessed_against_eligibility"]==f["unique_records_screened"] and f["reports_excluded_total"]+f["eligible_reports_entering_family_linkage"]==f["records_assessed_against_eligibility"] and sum(f["report_exclusion_reasons"].values())==f["reports_excluded_total"] and f["ineligible_reports"]+f["ml_adjacent_reports_catalogued"]==f["reports_excluded_total"] and f["additional_or_companion_reports_linked"]+f["unique_full_report_studies_included"]==f["eligible_reports_entering_family_linkage"])
check("selection_flow_closure",selection_closed and s["korean_citation_index"]==339 and f["eligible_reports_not_retrieved"] is None and all(sf["full_text_retrieval"][k] is None for k in ("reports_sought","reports_not_retrieved","reports_assessed")),"18,516 -> 11,077 -> 1,499 -> 245 -> 220+25")
bad={m:{"macro":macros.get(m),"json":nums.get(k)} for m,k in expected.items() if macros.get(m)!=nums.get(k)}
check("tex_macro_values",not bad,str(bad)); tex=TEX.read_text(); check("generated_constants_input",r"\input{protocol_v1_2_numbers.tex}" in tex,"present")
# Prompt 090: claim-ordered Results state the importance denominator in words ("129 of the 165").
# Prompt 093 (review v31 section 6.1) rewrote the prespecification sentence and the Study Groups sentence.
# Prompt 094 (review v32): Results restate the 129 and 184/36 denominators in the new wording.
for token in ("were written down before each stage began","192 core studies, 154 produced an importance ranking","192 classified a health outcome, 22 analysed health with another task"):  # prompt 106  # Prompt 107
    check("manuscript_"+re.sub(r"\W+","_",token).strip("_"),token in tex,token)
stale=["222 unique full-report studies","206 categorical-outcome classification","2,095 visual objects","203 development units","11,525 evidence-registry","126/31/7/3","independent duplicate assessment",
       "180 and 126 studies","robust in 49, limited in 105","126 reported an explicit importance","Only one study explicitly predicted a future","162/\\ClassN{} were current-state","51/58 classification","Only 9/\\ClassN{}","A final model was usable in 28","await duplicate review"]
check("no_known_stale_prose",not any(x in tex for x in stale),str([x for x in stale if x in tex]))
figrefs=re.findall(r"\\includegraphics(?:\[[^]]*\])?\{figs/([^}]+)\}",tex)
# Prompt 093: five claim-ordered main figures (review v31 section 4.2).
# Prompt 094 (review v32): six practice figures.
# Prompt 097 (review v35): literature map and rankings figure; the methods testbed moved to Supplementary Figure S6.
expected_figrefs={"fig1_prisma.pdf","fig2_literature_map.pdf","fig3_analysis_workflow.pdf","fig4_variable_importance.pdf","fig5_rankings_named.pdf","fig6_maturing_practice.pdf","fig7_next_steps.pdf"}  # Prompt 107: Figure 2 split into data (2) and analysis (3); Prompt 112: new Figure 5
check("adjudicated_figure_set",set(figrefs)==expected_figrefs,str(figrefs))
active_table_inputs=set(re.findall(r"\\input\{generated_tables/([^}]+)\}",tex))
check("one_conceptual_main_table",not active_table_inputs and tex.count(r"\begin{table}")==1 and not re.search(r"\\input\{table_[^}]+\}",tex),f"generated inputs={len(active_table_inputs)}; inline tables={tex.count(r'\begin{table}')}")
manifest=list(__import__('csv').DictReader((SUPP/"supplementary_manifest.tsv").open(),delimiter="\t"))
manifest_groups=__import__('collections').Counter(row["Item"].rsplit(" S",1)[0] for row in manifest)
# Prompt 093: 8 tables (S5 is the workbook, Additional file 2) + 8 figures.
# Prompt 094 (review v32): 8 tables + 6 figures.
# Prompt 096 (review v34): Supplementary Table S9 (study-level summary) added as the last table.
# Prompt 097 (review v35): Tables S1-S8, Figures S1-S7 and Additional Data 1 (workbook).
check("standalone_supplement_manifest",len(manifest)==17 and manifest_groups=={"Supplementary Table":8,"Supplementary Figure":8,"Additional Data 1":1},str(manifest_groups))  # Prompt 099: Figure S7 added
check("standalone_supplement_pdfs",len(list((SUPP/"pdf").glob("*.pdf")))==16 and not list((SUPP/"pdf").glob("Supplementary_Data_1*.pdf")) and not list((SUPP/"pdf").glob("*.aux")) and not list((SUPP/"pdf").glob("*.log")),"Tables S1--S8 and Figures S1--S8; Additional Data 1 is XLSX only; no TeX build debris")  # Prompt 099: eight figures
check("standalone_supplement_tables",len(list((SUPP/"tables").glob("*.xlsx")))==9,"nine XLSX tables S1--S9; the dictionary and 306-item protocol are sheets of the S5 study-level workbook")
reaudit_path=SUPP/"data/Supplementary_Table_S06_noncore_health_reaudit.json"
reaudit=json.loads(reaudit_path.read_text()) if reaudit_path.exists() else {}
check("standalone_supplement_data",len(list((SUPP/"data").iterdir()))==1 and reaudit.get("n")==22 and reaudit.get("group_counts")=={"continuous_or_ordered":14,"other_task_specific":8},"one provenance file records the 22-study S5 task audit; raw 1:N records are delivered in S7 and mirrored in the repository")  # Prompt 107
combined_tex=ROOT/"manuscript/bmc_supplementary.tex"
combined_pdf=ROOT/"manuscript/bmc_supplementary.pdf"
combined_source=combined_tex.read_text() if combined_tex.exists() else ""
check("combined_and_individual_submission_supplements",combined_tex.exists() and combined_pdf.exists() and
      not re.search(r"\\(?:input|include)\{",combined_source) and
      all(f"Supplementary Table S{i}." in combined_source for i in range(1,9)) and
      "Supplementary Table S9." not in combined_source and
      all(f"Supplementary Figure S{i}." in combined_source for i in range(1,9)) and "Supplementary Figure S9." not in combined_source,
      "self-contained combined TeX/PDF and 16 separately maintained submission items are present")  # Prompt 099: Figures S1-S8
# Prompt 093 (review v31 section 3.1): BMC takes the supplement as two Additional files (PDF and the Table S5 workbook).
check("no_additional_file_bundles","Additional file 1" in tex and "Additional file 2" in tex and "Additional file 3" not in tex and "appendices/pdf/appendix" not in tex,"Additional file 1 = supplement PDF, Additional file 2 = Table S5 workbook; item-specific citations in the text")
def pdf_text(path): return re.sub(r"\s+"," ",subprocess.run(["pdftotext",str(path),"-"],capture_output=True,text=True,check=True).stdout)
prisma=pdf_text(SUPP/"pdf/Supplementary_Table_S01_PRISMA_2020_checklist.pdf")
check("prisma_locations_current","Figure 1" in prisma and "Supplementary Table S3" in prisma and "Additional file" not in prisma,"PRISMA 2020 checklist points to the current manuscript and supplement")
prisma_s=load_workbook(SUPP/"tables/Supplementary_Table_S02_PRISMA_S_checklist.xlsx",read_only=True).active  # prompt 092: PRISMA-S is S2
check("prisma_s_checklist",prisma_s.max_row==17 and prisma_s.max_column==5,"completed 16-item PRISMA-S checklist is present")
search_xlsx=load_workbook(SUPP/"tables/Supplementary_Table_S03_Search_strategies_and_yields.xlsx",read_only=True).active
search_rows=list(search_xlsx.iter_rows(values_only=True))
search_header=list(search_rows[0]); source_col=search_header.index("Source"); contribution_col=search_header.index("Retrieval and PRISMA contribution")
contribution={row[source_col]:str(row[contribution_col]) for row in search_rows[1:]}
check("search_prisma_alignment",all(token in " ".join(contribution.values()) for token in ("6,046","52","9,998","339","2,079")),"current source-preprocessed database/index contributions close to 16,435; raw OpenAlex 10,000 is separately retained in S3 and the derived-view provenance")
f11=pdf_text(ROOT/"manuscript/figs/fig12_temporal_changes.pdf")
# Prompt 088: panel A shows importance outputs, so its title is "Importance and stability" (purpose/output distinction).
check("figure12_temporal_content",all(x in f11 for x in ("Importance and stability","Model-based importance","Algorithm-family use","Validation evidence","Reproducibility and survey-design reporting","Tree-based boosting","Later/external validation","Candidate/final sets recoverable","Tuning/evaluation","separated","model fully specified","Survey weights","reported","≤2019","2025–26","period n=45, 35, 59, 53")) and "Health-topic composition" not in f11 and "Method-research type" not in f11,"four enlarged period panels with line-broken year ranges and direct labels, thin visual-guide lines, and denominators in the figure header and caption; health topics remain in Figure S1")  # prompt 106
temporal=json.loads((ROOT/"results/derived/exploratory_temporal_practice_analysis.json").read_text())
nn=temporal["health_focused_classification"]["algorithm_families"]["Neural networks"]
nn_counts=[nn[p]["n"] for p in temporal["periods"]]
check("figure12_neural_network_total",nn_counts==[14,14,18,9] and sum(nn_counts)==55,f"period counts={nn_counts}; total={sum(nn_counts)} agrees with Figure 8 DNN/MLP n=54")  # prompt 106
f2=pdf_text(ROOT/"manuscript/figs/fig2_landscape.pdf")
check("figure2_category_and_data_use",all(x in f2 for x in ("Publication growth","Role of KNHANES","Primary analysis dataset","One of multiple primary datasets","External/transportability evaluation","Application/ test dataset","Survey-year scope","KNHANES components","Health interview","163","33","2026: 27","through Sep","Laboratory data","Oral examination")) and "2026*" not in f2 and "├" not in f2 and "└" not in f2,"four concise panels covering orientation-specific growth, observed 2026 publications through September without projection notation, and vector-drawn component hierarchy")  # prompt 106
# Preserve PDF drawing-object order for wrapped labels; pdftotext can insert
# a bar's numeric annotation between the two halves of an intact label.
def drawing_text(path):
    with fitz.open(path) as doc:
        return " ".join(" ".join(p.get_text() for p in doc).split())
f3=drawing_text(ROOT/"manuscript/figs/fig3_data_use.pdf")
check("figure3_category_specific_detail",all(x in f3 for x in ("Stated scientific purposes","Proposed subsequent uses","Analytic outputs","Health-state / value estimation","Variable interpretation","Variable importance or ranking","Population-level association analysis","Association estimate","Purpose–output pairing","204 (95.3%)","83 (38.8%)","21 (9.8%)","200 (93.5%)","164 (76.6%)","60 (28.0%)")) and "Multiple co-primary purposes" not in f3,"four panels with standardised purpose, output, and proposed-use terminology and n (%) labels")  # prompt 106
f4=pdf_text(ROOT/"manuscript/figs/fig4_populations.pdf")
check("figure4_populations",all(x in f4 for x in ("Leading health topics","Remaining topic categories","19","Age restriction","Disease/risk restriction","Final sample-size distribution (N=214)","Not reported = 3","Participant-flow reporting","214","211","155")),"top eight plus a 17-study residual union close the 184-study topic denominator; selection, sample-size, and flow panels remain present")  # prompt 106
f7=pdf_text(ROOT/"manuscript/figs/fig7_predictor_training.pdf")
# Prompt 089: outside-training preprocessing (NOT_USED) is now counted as before split, so missing-handling NA is 86 (was 116).
check("figure7_model_development",all(x in f7 for x in ("A. Reported initial","predictor counts (N=192)","B. Candidate/final predictor-set","recoverability (N=192)","Not reported = 104","Initial predictors (log scale)","Missing-data strategies","Data-dependent timing","Fully specified","Partly specified","39","150","Insufficiently specified","3","Within training","Before split","Not applied / NA","104","102")),"panel-swapped predictor-count histogram with dispersed study points, three-row candidate-definition completeness, missing data, and four N=165 timing rows including NA")  # prompt 106
input_count_audit=json.loads((ROOT/"results/derived/initial_candidate_input_count_audit.json").read_text())
check("initial_candidate_input_count_audit",input_count_audit["reporting_studies"]==74 and input_count_audit["summary"]=={"median":22.5,"q1":13.25,"q3":43.0,"minimum":6.0,"maximum":968.0} and len(input_count_audit["records"])==74,"one explicit pipeline-entry count per study; no variable-list counting")  # prompt 106
f8dev=pdf_text(ROOT/"manuscript/figs/fig8_model_development.pdf")
check("figure8_model_development",all(x in f8dev for x in ("Algorithm families evaluated","Hyperparameter-tuning methods","Separation of tuning from final evaluation","Author-designated final models","Random forest","XGBoost","DNN/MLP","Clearly separated","No designation recoverable","13")),"evaluation, tuning, separation, author-designated model families, and the 13-study no-designation group")
best_family=json.loads((ROOT/"results/derived/author_designated_model_family_audit.json").read_text())
check("author_designated_model_family_audit",best_family["studies_with_author_designated_selection"]==179 and best_family["single_model_studies"]==32 and best_family["designation_not_recoverable"]==13 and best_family["family_counts"].get("XGBoost")==31 and best_family["family_counts"].get("DNN/MLP")==26,"study-level, same-family deduplicated; multi-family selections permitted")  # prompt 106
f8=pdf_text(ROOT/"manuscript/figs/fig9_validation_evaluation.pdf")
# Cycle083 reporting existence and same-evaluation independence replace the
# first-stored policy. Counts are derived; separate public reconstruction verifies them.
reporting=json.loads((ROOT/"results/derived/study_reporting_summary.json").read_text())
independent_label=f"{len(reporting['members']['threshold_independent'])}/{len(reporting['denominators']['threshold_independent'])}"
reporting_labels=[str(n) for n in reporting['decision_states'].values() if n]
check("figure9_evaluation",all(x in f8 for x in ("Internal evaluation methods","Single train–test split","Beyond development data","Neither","Later period only","External dataset only","Both","Beyond development: 38/192","Reporting in at least one","evaluated unit (N=192)","Sample size","Class distribution","44","125","127",independent_label,"Performance measures reported","AUROC","Calibration","Decision-curve analysis",*reporting_labels)),"four mutually exclusive beyond-development bars; order-invariant reporting states and same-evaluation independent-selection numerator over threshold-reporting studies; selected metrics")  # prompt 106
f9eval=drawing_text(ROOT/"manuscript/figs/fig10_variable_interpretation.pdf")
check("figure10_variable_interpretation",all(x in f9eval for x in ("Use of model-based variable importance","Explicit importance reported","Not reported","154/192","38/192","Variable-importance methods (eligible N=154)","field-specific denominators","SHAP","Model-native","Permutation","Importance-stability","Importance-guided","Subsequent","Exact variable","25/154","25/192","12/192","5/12")),"methods use eligible N=154 and all stability/downstream rows print their field-specific denominators")  # prompt 106
f10=pdf_text(ROOT/"manuscript/figs/fig11_methodological_appraisal.pdf")
# The 2026-09-24 spacing revision shortened only the REP19 conjunction/wrapping.
# Normalise this equivalent wording before applying the existing content checks.
# Prompt 088: reader-facing labels drop internal item codes (REP06/REP07/REP19); survey rows carry "used n".
check("figure11_methodological_appraisal",all(x in f10 for x in ("Selected TRIPOD+AI-derived reporting indicators (N=192 studies)","Outcome definition","timing and source","Predictor definition","and timing","class counts","Missing-data","Hyperparameters","Internal validation","Final-model","Registration; data/code","availability","(used 7)","(used 13)","Complete","Partial","Insufficient / NR / unclear","Survey design (N=192 studies)","Used","Not used","Not reported","Not applicable","Unclear","Reported checks (N=192 studies)","Importance","stability","Association: linked","survey-aware","Individual use:","3 co-reported checks","Policy: survey","design reported","4/19","5/65","15/48","PROBAST+AI model-level appraisal","Development models (n=297)","Methodological quality","Evaluations (n=378)","Risk of bias","270/297 (91%)","375/378 (99%)","High quality","Low quality","Low risk","High risk","297","378")) and f10.count("(N=192 studies)")==4 and "field-specific eligible denominators" not in f10 and "Participants/data sources" not in f10,"requested concise C/D titles, denominator-closing survey-design statuses, row-specific evidence ratios, and model-unit PROBAST+AI labels")  # prompt 106
figure11_audit=json.loads((ROOT/"results/derived/figure11_reporting_probast_domain_audit.json").read_text())
check("figure11_reporting_probast_domain_audit",len(figure11_audit["reporting"]["items"])==19 and all(x["complete"]+x["partial"]+x["not_reported_or_unclear"]==x["denominator"] for x in figure11_audit["reporting"]["items"]) and figure11_audit["probast_ai"]["development"]["unit_n"]==297 and figure11_audit["probast_ai"]["evaluation"]["unit_n"]==378 and figure11_audit["probast_ai"]["development"]["rows"]["Overall"]=={"high_quality":15,"unclear":12,"low_quality":270} and figure11_audit["probast_ai"]["evaluation"]["rows"]["Overall"]=={"low_risk":2,"unclear":1,"high_risk":375},"core-cohort reporting rows close to denominators; model-unit overall judgements use U_dev=297 and U_eval=378")  # prompt 106
# Prompt 093: the study-level workbook is Table S5; its VARIABLE_DICTIONARY sheet is the former S5 dictionary.
noncore_xlsx=SUPP/"tables/Supplementary_Table_S05_Noncore_health_analysis_studies.xlsx"  # Prompt 097: renumbered
master_xlsx=SUPP/"tables/Supplementary_Data_1_Study_level_dataset.xlsx"  # Prompt 097: Additional Data 1
dict_ws=load_workbook(master_xlsx,read_only=True)["VARIABLE_DICTIONARY"]
master_wb=load_workbook(master_xlsx,read_only=True)
master_ws=master_wb["STUDIES"]
technical_dict_ws=master_wb["DATA_DICTIONARY"]
dict_names=[row[0] for row in dict_ws.iter_rows(min_row=2,values_only=True)]
master_names=[cell.value for cell in next(master_ws.iter_rows(min_row=1,max_row=1))]
noncore_ws=load_workbook(noncore_xlsx,read_only=True).active
check("supplement_noncore_health_studies",noncore_ws.max_row==25 and noncore_ws.max_column==11,"S5 has 22 study rows, two reader group headers, and eleven one-value columns (prompt 111)")  # prompt 106
required_s7={"README","STUDIES","REPORTS","DATASETS","OUTCOMES","MODELS","DEVELOPMENTS","EVALUATIONS","PERFORMANCE_METRICS","EVIDENCE_ANCHORS","AI_DISAGREEMENTS","FINAL_ADJUDICATION","DATA_DICTIONARY","PROTOCOL_CROSSWALK","ITEM_RESPONSES","MODEL_SELECTIONS","ANALYSIS_FIELDS","SOURCE_PACKAGE","VISUAL_DETAILS","SOURCE_JSON","TEXT_CONTINUATIONS","RECORD_DETAILS","RECORD_EVIDENCE"}
check("supplement_variable_dictionary",dict_ws.max_row==master_ws.max_column+1 and dict_ws.max_column==8 and dict_names==master_names and technical_dict_ws.max_column==14,f"S5 has 8 reader columns and defines all {master_ws.max_column} S7/STUDIES columns in identical order; S7/DATA_DICTIONARY retains 14 technical columns")
check("supplement_master_dataset",master_ws.max_row==251 and master_ws.max_column>=150 and required_s7.issubset(master_wb.sheetnames),f"S7 has 250 studies, {master_ws.max_column} fields, and all 14 relational sheets")  # prompt 106
check("supplement_relational_long_tables",master_wb["DEVELOPMENTS"].max_row==364 and master_wb["EVALUATIONS"].max_row==448 and master_wb["PERFORMANCE_METRICS"].max_row>1 and master_wb["EVIDENCE_ANCHORS"].max_row>1,"S7 preserves all 363 development units and 447 evaluation units across every included task, plus metrics and evidence anchors; the prediction-only release subset is 355/435")  # prompt 106
check("supplement_protocol_crosswalk",master_wb["PROTOCOL_CROSSWALK"].max_row==395 and master_wb["DATA_DICTIONARY"].max_row==159,"S7 contains the 382 canonical items plus 12 public classification addenda and a 158-variable public dictionary")
# Validate S7 values against the S7/DATA_DICTIONARY storage grammar. Missing-state codes are
# allowed globally, while scalar categorical fields may not silently contain
# pipe-delimited multiple values.
dict_rows=list(technical_dict_ws.iter_rows(min_row=2,values_only=True))
master_rows=list(master_ws.iter_rows(min_row=2,values_only=True))
master_index={name:i for i,name in enumerate(master_names)}
missing_codes={"NR","NA","UNC","UNCLEAR"}; schema_errors=[]
numeric_types={"Non-negative integer","Pipe-delimited non-negative integer(s)","Numeric proportion","Pipe-delimited numeric proportion(s)","Numeric performance metric"}
for drow in dict_rows:
    name,data_type,allowed=drow[0],drow[5],str(drow[6])
    values=[str(row[master_index[name]]).strip() for row in master_rows if row[master_index[name]] not in (None,"")]
    if data_type in {"Controlled categorical","Controlled multi-select","Boolean flag"}:
        permitted={token.strip() for token in allowed.split(" | ")} | missing_codes
        tokens={token.strip() for value in values for token in value.split(" | ")}
        unknown=sorted(tokens-permitted)
        if unknown or (data_type != "Controlled multi-select" and any(" | " in value for value in values)):
            schema_errors.append({"field":name,"unknown":unknown,"scalar_multivalue":data_type != "Controlled multi-select" and any(" | " in value for value in values)})
    if data_type in numeric_types:
        for token in (part.strip() for value in values for part in value.split(" | ")):
            if token in missing_codes: continue
            try: number=float(token)
            except ValueError:
                schema_errors.append({"field":name,"invalid_numeric":token}); continue
            if "integer" in data_type.lower() and (number < 0 or not number.is_integer()):
                schema_errors.append({"field":name,"invalid_integer":token})
            if ("proportion" in data_type.lower() or "performance" in data_type.lower()) and not 0 <= number <= 1:
                schema_errors.append({"field":name,"out_of_range":token})
check("supplement_s5_s7_code_and_range_validation",not schema_errors,f"errors={schema_errors[:10]}; controlled codes exact; integers >=0; proportions/performance in [0,1]")
release_dir=ROOT/"data/repository_release"
dev_units=list(__import__('csv').DictReader((release_dir/"PROBAST_AI_development_units.tsv").open(),delimiter="\t"))
eval_units=list(__import__('csv').DictReader((release_dir/"PROBAST_AI_evaluation_units.tsv").open(),delimiter="\t"))
check("repository_release_staging",len(dev_units)==355 and len(eval_units)==435 and (release_dir/"performance_metrics_long.tsv").exists() and (release_dir/"RELEASE_MANIFEST.tsv").exists(),"local release bundle has 355 development and 435 evaluation units plus metrics and manifest")  # prompt 106
protocol_text=(ROOT/"KNHANES_ML_study_audit_protocol.md").read_text()
check("dual_ai_human_adjudication_workflow",all(x in protocol_text for x in ("AI_A_BLINDED","AI_B_BLINDED","HUMAN_ADJUDICATION","FINAL_CONSENSUS")) and "Do not call this independent review by two humans or human Cohen's kappa" in protocol_text,"canonical protocol specifies blinded dual-AI extraction, human source adjudication, validation, and final consensus without claiming duplicate-human review")
for path in (ROOT/"data/INTEGRATED_STUDY_AUDIT.tsv",ROOT/"data/INTEGRATED_STUDY_AUDIT.xlsx",master_xlsx):
    check("exists_"+path.name,path.exists() and path.stat().st_size>1000,f"bytes={path.stat().st_size if path.exists() else 0}")
# Prompt 090: eight main figures instead of twelve, so the PDF is smaller.
check("pdf_exists",PDF.exists() and PDF.stat().st_size>300_000,f"bytes={PDF.stat().st_size if PDF.exists() else 0}")
if PDF.exists():
    raw_text=subprocess.run(["pdftotext",str(PDF),"-"],capture_output=True,text=True,check=True).stdout
    # Page/line-number-only lines can interrupt prose across a page break.
    # Normalise the extraction, never remove manuscript line numbering.
    text=re.sub(r"\s+"," ",re.sub(r"(?m)^[ \t\f]*\d+[ \t]*$", "", raw_text))
    # Prompt 090 rewrote Results in claim order; the rendered anchors follow the new wording.
    # Prompt 091: participant flow on the 165-study core cohort (117) and the 0-of-120 headline.
    rendered={"flow":r"276 reports of 250 unique studies were included","category":r"192 classi(?:f|ﬁ)i?ed a health outcome, 22 analysed health with another task","tasks":r"core cohort of 192 health-focused classi(?:f|ﬁ)i?cation studies","development":r"297 model developments","evaluation":r"evaluation units","importance":r"Of the 192 core studies, 154 produced an importance ranking","timing":r"health state measured in the same survey in 190 of the 192 core studies","evidence_alignment":r"Code sharing rose in every period, from 1 of 45 through 2019 to 8 of 53","reporting":r"AUROC reported Calibration reported Validation beyond the development data Variable importance","publication":r"Fig\. 2 The literature and its data","cohort_traceability":r"Outcome rebuildable from the reportb? Predictor set rebuildable from the reportb?","analysis_ready":r"Variable Importance as the Main Product (?:\d+ )*Once (?:fi|ﬁ)tted and evaluated, the models were used","integrated_ledger":r"Study-level values and their source locations for all 250 studies are given in Supplementary Data"}  # Prompt 099: Figure 2 caption renamed (bridge figure); timing sentence now counts the 165 core studies (Figure 2E)  # Prompt 100: straight storyline (Figure 2 caption, importance heading, forward maturing and next-step sentences)  # Prompt 101: reporting counts anchored in Table 1; section opens from Figure 2G  # prompt 106: 250-study values  # Prompt 107: fixed denominators (192) and Figure 2/3 split  # Prompt 107  # Prompt 107  # prompt 109
    # Prompt 094 (review v32): claim-evidence anchors (evidence alignment, cohort traceability, analysis-ready headline) were replaced
    # by the practice findings in the same Results positions.
    # Prompt 095 (review v33): boosting moved to How ML Was Used; the reporting-completeness detail sentence moved to Figure S5, and
    # the rendered anchor now checks the little-changed reporting practices stated in Results.
    for label,pattern in rendered.items(): check("rendered_"+label,re.search(pattern,text) is not None,pattern)
    s2d=" ".join(" ".join(pg.get_text() for pg in fitz.open(SUPP/"pdf/Supplementary_Figure_S04_Participants_and_sample_size.pdf")).split()).replace("\u2011","-")  # Prompt 097: renamed  # Prompt 102: renumbered S4
    check("supplement_participant_flow_117",re.search(r"Every selection step.*?140 \(73%\)",s2d) is not None and "the last row requires all five" in s2d,"Figure S4B: every participant-selection step in 140 of 192 core studies (prompts 093, 097; prompt 106 values)")  # Prompt 107: panel B
    rendered_stale=["combined-weight and explicit-importance analyses used 180 and 126","five continuous-outcome prediction studies","206-study classification cohort","Outcome construction was robust in 49","126 reported an explicit importance method","162/196 were current-state","51/58 classification studies","Only 9/196 classification studies","A final model was usable in 28","await duplicate review"]
    check("rendered_no_known_stale_claims",not any(x in text for x in rendered_stale),str([x for x in rendered_stale if x in text]))
log=(ROOT/"build/submission/bmc_main.log").read_text(errors="ignore") if (ROOT/"build/submission/bmc_main.log").exists() else ""
check("latex_no_fatal","Fatal error" not in log and "Emergency stop" not in log,"compile log"); check("latex_refs_defined","undefined references" not in log.lower() and "undefined citations" not in log.lower(),"compile log")
check("latex_no_overfull","Overfull" not in log,"main PDF has no overflowing boxes")
status="PASS" if all(x["status"]=="pass" for x in checks) else "FAIL"
result={"schema":"protocol_v1_2_v1_3_manuscript_propagation_audit","date":date.today().isoformat(),"status":status,"checks":checks,"summary":{"pass":sum(x["status"]=="pass" for x in checks),"fail":sum(x["status"]=="fail" for x in checks)}}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n"); print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(status!="PASS")
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
