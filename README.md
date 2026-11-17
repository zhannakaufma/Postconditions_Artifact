# Replication package: Programmers Are Poor and Overconfident Judges of LLM-Generated Postcondition Assertions

This repo contains everything needed to run our analyses and read our paper results.

```
Survey.pdf,                                survey intro, structure and demographics Q's
stimuli.zip, stimuli_py.zip                stimuli shown in the survey's loop & merge
data/                                      the longtables used in our analyses
analysis/                                  our R analyses (as Rmds + rendered PDFs)
pipeline/                                  scripts to build data/ from raw sources 
```

## Survey and stimuli

* `Survey.pdf` -- the Qualtrics questionnaire of the controlled experiment (Study 1): introduction, consent, tutorial and the questions asked for every stimulus. Each participant saw 10 stimuli from the counterbalanced set, so the stimuli themselves are not in the PDF.
* `stimuli.zip` -- the stimuli as shown (PNG), one file per function × postcondition × comment condition. 
* `stimuli_py.zip` -- the same stimuli as Python source.

## analysis/

* `Quant_Analysis.Rmd` / `.pdf` -- Main Study analysis (RQ1 to RQ3, Section VI-A to VI-C). 
* `Qual_Analysis.Rmd` / `.pdf` -- Think-Aloud analysis (RQ4, Section VI-D); produces `Perception_Sankeys.pdf`. 
* `Contextualization_Analysis.Rmd` / `.pdf` -- Corpus Contextualization analysis (Section III-A3). 
| `postcondition_samples.pdf` | Our mapping rules to Shevrin and Maoz's formula model, with 50 color-coded examples per source. 

Render any report from inside `analysis/` with `Rscript -e 'rmarkdown::render("<file>.Rmd")'`.
R packages: `tidyverse`, `lme4`, `lmerTest`, `car`, `MASS`, `emmeans`, `effsize`, `mediation`, `psych`, `lavaan`, `simr`, `knitr`, `rmarkdown`, `networkD3`, `htmlwidgets`, `webshot` (run `webshot::install_phantomjs()` once). PDF output needs a LaTeX installation.

## data/

*  `quant_longtable.csv` -- Main Study Longtable: The responses of our 86 participants: demographics, stimulus seen, response, confidence, time, and the complexity metrics of each postcondition and function. 
* `qual_longtable.csv` -- Think-Aloud Longtable: ground truth, assessment, mental model and reasoning strategy flow. 
* `qual_participants.csv` -- Think-aloud participant data. 
* `postcondition_corpora.csv` -- The 28,311 postconditions used in our Corpus Contextualization analysis, with their Boolean propositional formula (`SM_Formula`), Shevrin and Maoz's 11 formula properties and reading-complexity score (`SM_Score`), and, for Python rows, cyclomatic complexity, cognitive complexity and Halstead difficulty. 
* `function_metrics.csv` -- Size and complexity of all 164 HumanEval functions and the 210 Python methods of PostCondBench. 

## pipeline/
Reproduces the files in in `data/`. Requires Python 3 with `pandas`, `radon`, `complexipy`,`tree_sitter`, `tree_sitter_java`, and a Java JDK (Shevrin and Maoz's scoring jar is called from Python). Run from inside `pipeline/`:

```
sh all_longtable.sh                 # Qualtrics export -> ../data/quant_longtable.csv    
python3 compare_functions.py        # -> ../data/function_metrics.csv
python3 compare_postconditions.py   # -> ../data/postcondition_corpora.csv
python3 make_samples_pdf.py         # -> ../analysis/postcondition_samples.pdf (needs pdflatex)
```

### Complexity metrics

Cyclomatic complexity, cognitive complexity and Halstead difficulty are computed by
`libs/complexity_metrics.py` (via `radon` and `complexipy`) for every Python postcondition and function.

### Shevrin and Maoz's reading-complexity score

Shevrin and Maoz (TOSEM 2025) define 11 syntactic properties of propositional Boolean formulas and a reading-complexity score fitted to human comprehension data. 

Clone their jar into `pipeline/libs/boolean-comprehension-materials` (use `git clone https://github.com/iliashevrin/boolean-comprehension-materials`), and call via `libs/sm_java/SMMetrics.java`
(`javac -cp libs/boolean-comprehension-materials/jars/formula_score_calculator.jar -d libs/sm_java libs/sm_java/SMMetrics.java`).

### Corpora

`external_datasets/` holds each corpus as extracted from its public source (one JSON file plus
the script that extracted it). `compare_postconditions.py` parses, maps and scores them all.

| Dataset | Description | Source |
|---|---|---|
| `study` | the 52 postconditions shown in the survey | `libs/postconditions_info.py` |
| `nl2postcond_py` | GPT-4 postconditions for HumanEval (4,113 distinct) | nl2postcond artifact, Endres et al. FSE 2024 |
| `nl2postcond_java` | GPT-4 postconditions for Defects4J methods (17,480 distinct) | nl2postcond artifact |
| `postcondbench_py`, `postcondbench_java` | LLM-generated, expert-refined postconditions for 420 real-world methods | <https://github.com/zhang-ge-hao/postcond-bench> |
| `dafnybench` | every `ensures` clause in DafnyBench's 782 programs (3,085) | <https://github.com/sun-wendy/DafnyBench> |
| `jdk_jml` | every `ensures` clause in OpenJML's JML specs of the Java standard library (1,729) | <https://github.com/OpenJML/Specs> |

The nl2postcond artifact is at
<https://github.com/microsoft/intent-formalization/tree/main/nl2postcondition-fse2024/GeneratedPostconditions>.

The JML and Dafny harnesses must be built:

```
curl -L -o tools/jmltk-cli-1.0.0-all.jar https://github.com/jmltoolkit/jmltk/releases/download/JMLtk-v1.0.0/cli-1.0.0-all.jar
javac -cp tools/jmltk-cli-1.0.0-all.jar -d sm_jml sm_jml/SMJml.java
dotnet build -c Release sm_dafny        # .NET 8 SDK; fetches DafnyCore 4.11.0 from NuGet
```
