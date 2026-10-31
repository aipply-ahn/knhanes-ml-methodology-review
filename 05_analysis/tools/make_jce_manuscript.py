#!/usr/bin/env python3
"""Port the BMC Medical Research Methodology manuscript (manuscript/bmc_main.tex) to the Journal of Clinical
Epidemiology template (Elsevier elsarticle) in paper/src/jce_main.tex. One-time port (2026-10-24): after it,
paper/src/jce_main.tex is the working file for the JCE submission; the BMC version is backed up in
submissions/BMC_MRM_backup_20261024/.

JCE Original Research (guide for authors as summarised 2026-10-24): structured abstract <= 350 words with
Background (objective), Methods, Results and Discussion (conclusion); 1-7 keywords; 3-5 highlights; a "What is new?"
box below the abstract; numbered sections; main text <= 3,000 words; <= 5 figures, <= 5 tables, <= 100 references;
superscript numbered citations; generative-AI declaration before the references; cover letter.

    python tools/make_jce_manuscript.py [--force]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "manuscript"
OUT = ROOT / "paper/src"  # moved 2026-10-24 (was manuscript_jce/)
TEX = OUT / "jce_main.tex"

PREAMBLE = r"""%% Journal of Clinical Epidemiology submission (Elsevier elsarticle). Ported from manuscript/bmc_main.tex on
%% 2026-10-24 by tools/make_jce_manuscript.py; this file is now edited directly.
\documentclass[preprint,review,12pt,number,sort&compress]{elsarticle}
\usepackage{graphicx}
\usepackage{float}
\usepackage{placeins}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{array}
\usepackage{ragged2e}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{lineno}
\usepackage{framed}
\usepackage[hidelinks]{hyperref}
\biboptions{super,sort&compress}
\newcommand{\supptab}[1]{Supplementary Table~S#1}
\newcommand{\suppfig}[1]{Supplementary Figure~S#1}
\input{../../manuscript/protocol_v1_2_numbers.tex}
\graphicspath{{../../manuscript/}}  % figures and numbers stay generated in manuscript/
\journal{Journal of Clinical Epidemiology}
\renewcommand{\floatpagefraction}{.70}

\begin{document}
\begin{frontmatter}
\title{From Classification to Explanation: A Systematic Methodological Review of Supervised Machine Learning in a
National Health Survey}

\author[suwon1,suwon2]{Hongryul Ahn\corref{cor1}}
\ead{hrahn@suwon.ac.kr}
\cortext[cor1]{Corresponding author. Division of AI and Data Science, The University of Suwon, Hwaseong-si 18323,
Republic of Korea. ORCID: 0000-0002-5941-9784.}
\affiliation[suwon1]{organization={Division of AI and Data Science, The University of Suwon},
            city={Hwaseong-si}, postcode={18323}, country={Republic of Korea}}
\affiliation[suwon2]{organization={DS\&ML Center, The University of Suwon},
            city={Hwaseong-si}, postcode={18323}, country={Republic of Korea}}

\begin{abstract}
%ABSTRACT%
\end{abstract}

\begin{highlights}
\item Supervised ML with a national health survey mostly classified current health states
\item Variable-importance rankings became the main output, in 50 of 53 recent studies
\item Rankings most often named age, socioeconomic position and body size
\item Few studies checked ranking stability or used survey weights in model fitting
\item Explanation standards should complement prediction-model reporting guidance
\end{highlights}

\begin{keyword}
Machine learning \sep Variable importance \sep SHAP \sep National health survey \sep KNHANES \sep
Complex survey design \sep Systematic review
\end{keyword}
\end{frontmatter}

\linenumbers

\begin{framed}
\noindent\textbf{What is new?}

\smallskip\noindent\textit{Key findings}
\begin{itemize}[leftmargin=1.2em,itemsep=1pt,topsep=1pt]
\item Of 254 studies applying supervised machine learning (ML) to the Korea National Health and Nutrition Examination
Survey, 193 classified a health state, nearly all measured in the same survey.
\item Model-based variable-importance rankings became a main product, rising from 28 of 46 studies published through
2019 to 50 of 53 in 2025--2026.
\end{itemize}
\textit{What this adds to what was known}
\begin{itemize}[leftmargin=1.2em,itemsep=1pt,topsep=1pt]
\item Prediction-model standards assume prediction in new individuals, but in this survey literature ML was used mainly
to explain: few studies checked whether rankings were stable (26 of 193) or used the survey design in model fitting
(9 of 193).
\end{itemize}
\textit{What is the implication and what should change now?}
\begin{itemize}[leftmargin=1.2em,itemsep=1pt,topsep=1pt]
\item ML studies of probability-sampled health surveys should report whether their rankings are stable and represent
the surveyed population, alongside the items of prediction-model standards.
\end{itemize}
\end{framed}

"""

BACK = r"""
\section*{CRediT authorship contribution statement}
\textbf{Hongryul Ahn:} Conceptualization, Methodology, Data curation, Formal analysis, Investigation, Visualization,
Writing -- original draft, Writing -- review \& editing.

\section*{Declaration of competing interest}
The author declares that he has no known competing financial interests or personal relationships that could have
appeared to influence the work reported in this paper.

\section*{Funding}
This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit
sectors.

\section*{Ethics}
Not applicable. This systematic review used published reports and did not involve the collection or analysis of
individual participant data.

\section*{Data availability}
%DATA%

\section*{Declaration of generative AI and AI-assisted technologies in the manuscript preparation process}
%% AUTHOR TO CONFIRM: wording follows the Elsevier template statement; adjust the uses listed to what was actually done.
During the preparation of this work the author used Claude (Anthropic) for the AI-assisted data extraction and
appraisal described in the Methods, for analysis code, and for language editing of the manuscript. After using this
tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the
publication.

\section*{Acknowledgements}
None.

\section*{Abbreviations}
%ABBREV%

\section*{Appendix A. Supplementary data}
\begin{description}[leftmargin=0pt,itemsep=2pt]
\item[Supplementary material 1] KNHANES\_ML\_review\_Supplementary.pdf (PDF). Supplementary Tables S1--S8 and
Supplementary Figures S1--S8.
\item[Supplementary material 2] KNHANES\_ML\_review\_Additional\_Data\_1.xlsx (XLSX). %DATA1%
\end{description}

\bibliographystyle{elsarticle-num}
\bibliography{references,supporting_refs}  % symlinks to ../../manuscript/*.bib
\end{document}
"""


def between(s, a, b):
    i = s.index(a) + len(a)
    return s[i:s.index(b, i)]


def main():
    if TEX.exists() and "--force" not in sys.argv:
        sys.exit(f"{TEX} exists; it is the working file now (use --force to overwrite)")
    OUT.mkdir(exist_ok=True)
    s = (SRC / "bmc_main.tex").read_text()
    abstract = between(s, r"\abstract{", r"\keywords{").strip()
    assert abstract.endswith("}")
    abstract = abstract[:-1].strip()
    abstract = abstract.replace(r"\textbf{Conclusions:}", r"\textbf{Discussion:}")
    abstract = abstract.replace("How ML is used with such surveys has not been examined.",
                                "We examined how supervised ML has been used with KNHANES.")
    body = r"\section{Introduction}" + between(s, r"\section{Background}", r"\section*{Abbreviations}")
    abbrev = between(s, r"\section*{Abbreviations}", "%====")
    data = between(s, r"\subsection*{Availability of data and materials}", r"\subsection*{Competing interests}").strip()
    data = data.replace("Additional Data~1 (Additional file 2)", "Additional Data~1 (Supplementary material 2)")
    data1 = between(s, r"\item[Additional file 2] KNHANES\_ML\_review\_Additional\_Data\_1.xlsx (XLSX).", r"\end{description}").strip()
    tex = PREAMBLE.replace("%ABSTRACT%", abstract) + body.strip() + "\n" + \
        BACK.replace("%DATA%", data).replace("%ABBREV%", abbrev.strip()).replace("%DATA1%", data1)
    tex = tex.replace("\\begin{table}[!t]", "\\begin{table}[p]\\renewcommand{\\baselinestretch}{1}\\selectfont", 1)  # single-spaced table on its own page
    tex = tex.replace("(Additional file 1)", "(Supplementary material 1)").replace("(Additional file 2)", "(Supplementary material 2)")
    TEX.write_text(tex)
    print(TEX, len(tex))


if __name__ == "__main__":
    main()
