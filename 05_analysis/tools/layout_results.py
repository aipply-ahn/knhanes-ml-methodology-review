"""Keep each Results analysis unit with its supporting visual in both manuscripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def move_figure(s, filename, heading, message, width_from=None, width_to=None):
    marker = f"{{figs/{filename}}}"
    pos = s.index(marker)
    start = s.rindex(r"\begin{figure}[H]", 0, pos)
    end = s.index(r"\end{figure}", pos) + len(r"\end{figure}")
    block = s[start:end]
    if width_from and width_to:
        block = block.replace(width_from, width_to, 1)
    s = s[:start] + s[end:]
    insertion = heading + "\n" + message + "\n\n" + block + "\n"
    if heading not in s:
        raise ValueError(f"heading not found: {heading}")
    return s.replace(heading + "\n", insertion, 1)


def move_input(s, command, heading, message):
    if command not in s:
        raise ValueError(command)
    s = s.replace(command + "\n", "", 1)
    return s.replace(heading + "\n", heading + "\n" + message + "\n\n" + command + "\n", 1)


def move_table_by_caption(s, caption_start, heading, message):
    cap = s.index(caption_start)
    start = s.rindex(r"\begin{table}[H]", 0, cap)
    end = s.index(r"\end{table}", cap) + len(r"\end{table}")
    block = s[start:end]
    s = s[:start] + s[end:]
    return s.replace(heading + "\n", heading + "\n" + message + "\n\n" + block + "\n", 1)


def prepare(path, korean=False):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    marker = "% RESULTS_LAYOUT_LOCKED"
    if marker in s:
        return
    s = s.replace(r"\begin{figure}[htbp]", r"\begin{figure}[H]")
    s = s.replace(r"\begin{table}[htbp]", r"\begin{table}[H]")
    s = s.replace("\\begin{table}[H]\\centering\n",
                  "\\begin{table}[H]\\centering\n\\singlespacing\n")

    if korean:
        parent_heads = [r"\section{결과}", r"\subsection{분석방법 수준 메타연구 분석}", r"\subsection{평가방법론에 따른 분석}"]
        child_heads = [
            r"\subsubsection{연구 주제, 분석 과제와 분석 코호트}",
            r"\subsubsection{전처리와 복합표본설계}", r"\subsubsection{모형 개발}",
            r"\subsubsection{회귀와 기타 비분류 머신러닝}", r"\subsubsection{검증, 성능과 모형 비교}",
            r"\subsubsection{머신러닝의 정당화, 실제 기능과 해석}",
            r"\subsubsection{중요변수로 제시된 결과와 선정 규칙}",
            r"\subsubsection{높고 낮은 평가점수의 연구 사례}", r"\subsubsection{시간에 따른 변화}",
            r"\subsubsection{선행 방법론 리뷰와의 맥락 비교}",
        ]
        for h in parent_heads + child_heads:
            s = s.replace(h, "\\clearpage\n" + h, 1)
        s = move_figure(s, "fig1_prisma.pdf", r"\subsubsection{문헌 선정과 출판 지형}",
                        "최종 포함 문헌은 224편이었고 2019년 이후 출판이 빠르게 증가했다.",
                        r"width=0.86\textwidth", r"width=0.68\textwidth")
        s = move_figure(s, "fig8_interpretation_ko.pdf", r"\subsubsection{머신러닝의 정당화, 실제 기능과 해석}",
                        "머신러닝은 주로 예측·선별 방법으로 정당화됐지만 실제로는 후향적 모형 비교와 변수 해석에 머물렀다.",
                        r"width=\textwidth", r"width=0.82\textwidth")
        s = move_input(s, r"\input{table_importance_examples_ko}",
                       r"\subsubsection{중요변수로 제시된 결과와 선정 규칙}",
                       "‘중요변수’의 의미는 순위 보고, 고정 Top-k, 성능 기반 축소, 임계값, 모형 간 합의와 전문가 판단에 따라 달랐다.")
        s = move_figure(s, "fig9_quality_ko.pdf", r"\subsubsection{비뚤림 위험과 보고 완결성}",
                        "모든 연구의 전반 비뚤림 위험이 높았고 조사설계 보고는 일반 보고항목보다 현저히 부족했다.",
                        r"width=\textwidth", r"width=0.82\textwidth")
        s = move_table_by_caption(s, r"\caption{선별한 방법론 리뷰와의 맥락 비교.",
                        r"\subsubsection{선행 방법론 리뷰와의 맥락 비교}",
                        "KNHANES 연구는 비뚤림 위험, 표본크기 근거와 보정에서 비교 문헌보다 열세였고 복합표본설계는 고유한 추가 약점이었다.")
        s = s.replace(r"\subsubsection{회귀와 기타 비분류 머신러닝}" + "\n",
                      r"\subsubsection{회귀와 기타 비분류 머신러닝}" + "\n"
                      "회귀 표지 11편 중 실제 연속형 예측은 5편뿐이었고, 나머지 비분류 연구에는 과제별 평가기준이 필요했다.\n\n"
                      r"\input{table_nonclassification_ko}" + "\n", 1)
        s = s.replace(r"\subsubsection{높고 낮은 평가점수의 연구 사례}" + "\n",
                      r"\subsubsection{높고 낮은 평가점수의 연구 사례}" + "\n"
                      "높은 보고점수는 낮은 비뚤림 위험을 보장하지 않았으며, 두 평가를 연구별로 함께 읽어야 했다.\n\n"
                      r"\input{table_quality_vignettes_ko}" + "\n", 1)
        time_text = """\\begin{table}[H]\\centering
\\singlespacing
\\caption{출판시기별 방법론 관행. 분모는 포함 연구 224편이다.}
\\label{tab:time-ko}
\\small
\\begin{tabular}{lrrrrrr}\\toprule
시기 & 연구 & 가중치 & 완전사례 & 외부검증 & 해석 & 코드\\\\
\\midrule
2019년까지 & 47 & 0 & 16 & 4 & 16 & 4\\\\
2020--2022 & 48 & 1 & 18 & 3 & 27 & 11\\\\
2023--2024 & 63 & 0 & 28 & 10 & 44 & 13\\\\
2025--2026 & 66 & 0 & 33 & 17 & 54 & 19\\\\
\\midrule 합계 & 224 & 1 & 95 & 34 & 141 & 47\\\\
\\bottomrule\\end{tabular}
\\end{table}"""
        next_head = r"\subsubsection{선행 방법론 리뷰와의 맥락 비교}"
        s = s.replace("\n\\clearpage\n" + next_head, "\n\n" + time_text + "\n\n\\clearpage\n" + next_head, 1)
    else:
        parent_heads = [r"\section{Results}", r"\subsection{Meta-Research of the Analytic Workflow}", r"\subsection{Methodological Appraisal}"]
        child_heads = [
            r"\subsubsection{Research Topics, Analytic Tasks, and Analysis Cohorts}",
            r"\subsubsection{Preprocessing and Complex-Survey Design}", r"\subsubsection{Model Development}",
            r"\subsubsection{Regression and Other Nonclassification Uses}",
            r"\subsubsection{Validation, Performance, and Model Comparison}",
            r"\subsubsection{ML Rationale, Analytic Function, and Interpretation}",
            r"\subsubsection{Variables Identified as Important and How They Were Selected}",
            r"\subsubsection{Study Vignettes Behind High and Low Appraisal Scores}",
            r"\subsubsection{Change Over Time}", r"\subsubsection{Contextual Comparison With Methodological Reviews}",
        ]
        for h in parent_heads + child_heads:
            s = s.replace(h, "\\clearpage\n" + h, 1)
        s = move_figure(s, "fig1_prisma.pdf", r"\subsubsection{Study Selection and Publication Profile}",
                        "The review identified 224 included studies, with rapid growth after 2019.",
                        r"width=0.86\textwidth", r"width=0.68\textwidth")
        s = move_figure(s, "fig8_interpretation.pdf", r"\subsubsection{ML Rationale, Analytic Function, and Interpretation}",
                        "ML was usually justified for prediction or screening but functioned chiefly as retrospective comparison and variable interpretation.",
                        r"width=\textwidth", r"width=0.82\textwidth")
        s = move_input(s, r"\input{table_importance_examples}",
                       r"\subsubsection{Variables Identified as Important and How They Were Selected}",
                       "The meaning of an important variable differed across rankings, fixed top-$k$ sets, performance-guided reduction, thresholds, model consensus, and expert judgement.")
        s = move_figure(s, "fig9_quality.pdf", r"\subsubsection{Risk of Bias and Reporting Completeness}",
                        "All studies had high overall risk of bias, and survey-design reporting was markedly weaker than general reporting.",
                        r"width=\textwidth", r"width=0.82\textwidth")
        s = move_table_by_caption(s, r"\caption{Contextual comparison with selected methodological reviews.",
                        r"\subsubsection{Contextual Comparison With Methodological Reviews}",
                        "KNHANES studies compared unfavourably on risk of bias, sample-size justification, and calibration, with complex-survey design as an additional dataset-specific weakness.")
        s = s.replace(r"\subsubsection{Regression and Other Nonclassification Uses}" + "\n",
                      r"\subsubsection{Regression and Other Nonclassification Uses}" + "\n"
                      "Only 5 of 11 regression-labelled studies predicted a continuous outcome, and other nonclassification functions required task-specific evaluation.\n\n"
                      r"\input{table_nonclassification}" + "\n", 1)
        s = s.replace(r"\subsubsection{Study Vignettes Behind High and Low Appraisal Scores}" + "\n",
                      r"\subsubsection{Study Vignettes Behind High and Low Appraisal Scores}" + "\n"
                      "High reporting completeness did not guarantee low risk of bias, so both assessments must be read at study level.\n\n"
                      r"\input{table_quality_vignettes}" + "\n", 1)
    p.write_text(marker + "\n" + s, encoding="utf-8")


if __name__ == "__main__":
    prepare("manuscript/submission/main.tex")
    prepare("manuscript/submission/main_ko.tex", korean=True)
