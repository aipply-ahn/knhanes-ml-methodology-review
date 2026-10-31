"""v13: LaTeX for Table 1 from tools/checklist_v13.py (one row per TRIPOD+AI component or checklist item)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import checklist_v13 as CK

NOTE = {"K": ("유지", "Retained"), "R": ("세분화", "Refined"), "RS": ("세분화(특화)", "Refined (KNHANES)"), "N": ("신설", "New"), "NS": ("신설(특화)", "New (KNHANES)")}


class _MS:  # build() only needs the callables, not the data
    first = staticmethod(lambda d, k: None); has = staticmethod(lambda d, k, v: False); flat_values = staticmethod(lambda d, k: [])


def rows():
    return CK.build(_MS)


def table(ko, numbered=False):
    j = 0 if ko else 1
    L, last = [], None
    for it in rows():
        key, cko, cen, oko, oen, note, stage, met, app = it
        if key != last and last is not None:
            L.append("\\addlinespace[1pt]")
            if isinstance(key, str) and isinstance(last, int):
                L.append("\\midrule")
        if isinstance(key, int):
            head = f"{key}. {CK.TRIPOD[key - 1][j]}" if key != last else ""
            comp = cko if ko else cen
        else:
            head = (("{}(해당 없음) " if ko else "{}(None) ") + CK.GROUPS[key][j]) if key != last else ""
            comp = "--" if key != last else ""
        item = (oko if ko else oen) if oko else "\\centering{}''"  # same as the component: ditto mark
        if met is None and note != "K":
            item += "$^{\\S}$"
        if numbered:
            item = f"{len([x for x in L if ' & ' in x]) + 1}. " + item
        L.append(f"{head} & {comp} & {item} & {CK.STAGE[stage][j] if stage else ''} & \\mbox{{{NOTE[note][j]}}} \\\\")
        last = key
    head = ("\\textbf{TRIPOD+AI 유래 보고 평가 요소} & \\textbf{본 검토에서 정의한 평가 구성요소} & \\textbf{KNHANES ML 분류 연구의 세부 보고 항목} & \\textbf{재현 단계} & \\textbf{유형}" if ko else
            "\\textbf{TRIPOD+AI-derived reporting element} & \\textbf{Component defined in this review} & \\textbf{Detailed reporting item for KNHANES ML classification studies} & \\textbf{Repro\\-duction stage} & \\textbf{Type}")
    cap = ("KNHANES 기반 머신러닝 분류 연구의 재현성을 위한 TRIPOD+AI 기반 세부 보고 체크리스트" if ko else "TRIPOD+AI-aligned reporting checklist for reproducible machine learning classification studies using KNHANES")
    foot = ("{\\fontsize{6.4}{7.4}\\selectfont 왼쪽 두 열은 공식 TRIPOD+AI 항목이 아니라, 이 검토에서 보고 완전성을 판정하려고 TRIPOD+AI 항목을 재구성한 19개 평가 요소와 각 요소의 판정 구성요소이다. 세부 보고 항목은 한 행에 관찰 가능한 정보 한 가지만 담도록 구성요소를 나눈 것이며, ''는 구성요소와 같은 항목이다. 재현 단계: 자료(같은 원자료로 분석자료 재구성), 모형(모형과 성능 수치 재현), 중요도(변수중요도 결과 재현); 빈칸은 해석에 필요한 항목이다. 재현 단계는 그 정보가 재현에 필요하다는 뜻이며, 그것만으로 재현이 보장된다는 뜻은 아니다. 유형: 유지(구성요소를 그대로 씀), 세분화(구성요소를 나누거나 구체화함), 신설(대응 구성요소가 없음), (특화)(KNHANES의 반복 횡단면 확률표본조사 특성 때문에 필요함). 점수(그림~\\ref{fig:refined})는 각 항목을 보고, 미보고, 해당 없음으로 판정해 적용 가능한 항목 중 보고한 비율로 계산했고, 판정 불가는 미보고로 셌다. 조건부 항목(예: 통합 연도 가중치는 여러 해를 결합한 연구, 탐색 공간은 튜닝한 연구, 중요도 항목은 순위를 보고한 연구)은 해당하는 연구의 분모에만 넣었다. 이 점수는 재현에 필요한 정보의 보고 완전성을 나타내는 기술적 지표이며, 분석을 실제로 재수행해 확인한 재현 가능성이나 검증된 질 점수가 아니다. 저자가 이 검토의 결과와 기존 보고 지침을 바탕으로 제안한 체크리스트로, TRIPOD+AI와 PROBAST+AI를 대체하지 않고 보완한다. $^{\\S}$ 이 검토에서 코딩하지 않아 점수에 넣지 않음. AUROC, 수신자 조작 특성 곡선 아래 면적; PSU, 일차표본추출단위.\\par}" if ko else
            "{\\fontsize{6.4}{7.4}\\selectfont The first two columns are not official TRIPOD+AI items: they are the 19 elements into which this review reorganised TRIPOD+AI to judge reporting completeness, and the components used to judge each element. Detailed reporting items split the components so that each row holds one observable piece of information; '' marks an item identical to the component. Reproduction stage: Data (rebuilding the analysis dataset from the same raw data), Model (reproducing the model and performance estimates), Importance (reproducing the variable-importance results); blank, needed for interpretation. A stage means that the information is needed for reproduction, not that it guarantees reproduction. Type: Retained (component used as it is), Refined (component divided or made specific), New (no corresponding component), (KNHANES) (needed because KNHANES is a repeated cross-sectional probability survey). For the score (Figure~\\ref{fig:refined}) each item was judged reported, not reported or not applicable, and the score is the percentage of applicable items reported; unclear was counted as not reported. Conditional items (for example, combined-year weights for studies combining years, the search space for studies that tuned, importance items for studies with a ranking) entered only the denominators of the studies to which they applied. The score is a descriptive measure of the completeness of the information needed for reproduction, not reproducibility verified by re-running the analysis or a validated quality score. The checklist was proposed by the author from the findings of this review and existing reporting guidance and complements rather than replaces TRIPOD+AI and PROBAST+AI. $^{\\S}$ Not coded in this review and not scored. AUROC, area under the receiver operating characteristic curve; PSU, primary sampling unit.\\par}")
    W = (">{\\RaggedRight\\arraybackslash}p{0.18\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.17\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.355\\textwidth}"
         ">{\\centering\\arraybackslash}p{0.06\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.16\\textwidth}")
    hdr = "\\toprule\n" + head + " \\\\\n\\midrule\n"
    return ("\\begingroup\\renewcommand{\\baselinestretch}{1}\\fontsize{6.6}{7.6}\\selectfont\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{longtable}{@{}" + W + "@{}}\n\\caption{" + cap + "}\\label{tab:checklist}\\\\\n" + hdr + "\\endfirsthead\n" + hdr + "\\endhead\n\\bottomrule\n\\endlastfoot\n"
            + "\n".join(L).replace("\\midrule\n{}", "\\midrule\n{}") + "\n\\end{longtable}\n" + foot + "\n\\endgroup\n")


if __name__ == "__main__":
    R = rows()
    from collections import Counter
    print(Counter(r[5] for r in R), "repro", sum(bool(r[6]) for r in R), "scored", sum(r[7] is not None for r in R),
          "refined TRIPOD items", sorted({r[0] for r in R if r[5] in ("R", "RS")}))
