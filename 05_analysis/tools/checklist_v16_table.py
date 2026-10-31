"""v16: Table 1 (core checklist RC01-RC46 with criteria) from tools/checklist_v16.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import checklist_v16 as CK
from checklist_v12 import TRIPOD


class _MS:
    first = staticmethod(lambda d, k: None); has = staticmethod(lambda d, k, v: False); flat_values = staticmethod(lambda d, k: [])


def ordered():
    R = CK.items(_MS)
    key = lambda r: (r[1] if isinstance(r[1], int) else 100 + list(CK.GROUPS).index(r[1]), r[0])
    return sorted(R, key=key)


def table(ko):
    j = 0 if ko else 1
    L, last = [], None
    for it in ordered():
        rid, el, iko, ien, cko, cen, st, ty, src, met, app = it
        if last is not None and el != last:
            L.append("\\addlinespace[1.5pt]")
            if isinstance(el, str) and isinstance(last, int):
                L.append("\\midrule")
        head = (f"{el}. {TRIPOD[el - 1][j]}" if isinstance(el, int) else (("{}(해당 없음) " if ko else "{}(None) ") + CK.GROUPS[el][j])) if el != last else ""
        L.append(f"{head} & {rid} & {iko if ko else ien} & {cko if ko else cen} & {CK.STAGE[st][j]} & \\mbox{{{CK.TYPE[ty][j]}}} \\\\")
        last = el
    head = ("\\textbf{TRIPOD+AI 유래 평가 요소} & \\textbf{ID} & \\textbf{핵심 평가항목} & \\textbf{충족(1) 판정 기준} & \\textbf{재현 단계} & \\textbf{유형}" if ko else
            "\\textbf{TRIPOD+AI-derived element} & \\textbf{ID} & \\textbf{Core item} & \\textbf{Criterion for meeting the item (1)} & \\textbf{Stage} & \\textbf{Type}")
    cap = ("KNHANES 기반 머신러닝 분류 연구의 재현성을 위한 TRIPOD+AI 기반 핵심 보고 체크리스트" if ko else
           "TRIPOD+AI-aligned core reporting checklist for reproducible machine learning classification studies using KNHANES")
    foot = ("{\\fontsize{6.4}{7.4}\\selectfont 왼쪽 열은 공식 TRIPOD+AI 항목이 아니라 이 검토에서 TRIPOD+AI 항목을 재구성한 19개 평가 요소이다. 각 핵심 평가항목은 하나의 보고 요구사항이며 충족(1), 미충족(0), 해당 없음(NA)으로 판정한다. 미충족은 정보가 전혀 없다는 뜻이 아니라 요구사항을 충족하기에 불충분하다는 뜻이다. 항목은 관행이 아니라 보고를 판정한다(예: 가중치는 사용 여부와 방법 또는 쓰지 않은 이유를 보고했는지). 재현 단계: 자료(같은 원자료로 분석자료 재구성), 모형(모형과 성능 수치 재현), 중요도(변수중요도 결과 재현), 보고·해석(결과의 해석과 평가에 필요함). 유형: 구체화(TRIPOD+AI 유래 요소를 구체화함), 신설(대응 요소가 없음), (특화)(KNHANES의 반복 횡단면 확률표본조사 특성 때문에 필요함). 46개 항목 모두를 핵심 연구 193편에 적용했다. ID는 항목을 추가하거나 나눈 순서이다. 항목별 상세 보고 명세는 부록 표~\\ref{tab:spec}에 있다. 점수는 적용 가능한 항목 중 충족한 비율로, 재현에 필요한 정보의 보고 완전성을 나타내는 기술적 지표이며 실제 재현 가능성이나 검증된 질 점수가 아니다. 저자가 이 검토의 결과와 기존 보고 지침을 바탕으로 제안한 체크리스트로, TRIPOD+AI와 PROBAST+AI를 대체하지 않고 보완한다. PSU, 일차표본추출단위.\\par}" if ko else
            "{\\fontsize{6.4}{7.4}\\selectfont The left column lists the 19 elements into which this review reorganised TRIPOD+AI, not official TRIPOD+AI items. Each core item is one reporting requirement judged met (1), not met (0) or not applicable (NA); not met means insufficient to meet the requirement, not that no information was given. Items judge reporting, not practice (for weights, whether and how they were used or why not). Stage: Data (rebuilding the analysis dataset from the same raw data), Model (reproducing the model and performance estimates), Importance (reproducing the variable-importance results), Reporting (needed to interpret or appraise the results). Type: Specified (specifies a TRIPOD+AI-derived element), New (no corresponding element), (KNHANES) (needed because KNHANES is a repeated cross-sectional probability survey). All 46 items were applied to the 193 core studies. IDs follow the order in which items were added or split. The detailed specification is in Appendix Table~\\ref{tab:spec}. The score is the percentage of applicable items met; it is a descriptive measure of the completeness of the information needed for reproduction, not verified reproducibility or a validated quality score. The checklist was proposed by the author from the findings of this review and existing reporting guidance and complements rather than replaces TRIPOD+AI and PROBAST+AI. PSU, primary sampling unit.\\par}")
    W = (">{\\RaggedRight\\arraybackslash}p{0.15\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.045\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.17\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.37\\textwidth}"
         ">{\\RaggedRight\\arraybackslash}p{0.085\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.12\\textwidth}")
    hdr = "\\toprule\n" + head + " \\\\\n\\midrule\n"
    return ("\\begingroup\\renewcommand{\\baselinestretch}{1}\\fontsize{6.6}{7.6}\\selectfont\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{longtable}{@{}" + W + "@{}}\n\\caption{" + cap + "}\\label{tab:checklist}\\\\\n" + hdr + "\\endfirsthead\n" + hdr + "\\endhead\n\\bottomrule\n\\endlastfoot\n"
            + "\n".join(L) + "\n\\end{longtable}\n" + foot + "\n\\endgroup\n")
