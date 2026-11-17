"""
Builds ../data/postcondition_corpora.csv from:
  study              the 52 postconditions shown in the survey (../libs/postconditions_info.py)
  nl2postcond_py     every distinct GPT-4 Python postcondition for EvalPlus/HumanEval in nl2postcond
  nl2postcond_java   every distinct GPT-4 Java postcondition for Defects4J in nl2postcond
                     (external_datasets/nl2postcond_java_gpt4.json)
                     nl2postcond sampled each method ten times per prompt; identical samples for the
                     same method and prompt are one postcondition, so they are kept once.
  dafnybench         every `ensures` clause in DafnyBench's ground-truth programs
                     (external_datasets/dafnybench_ensures.json)
  jdk_jml            every `ensures` clause in OpenJML's JML specifications
                     (external_datasets/openjml_jdk_ensures.json)
  postcondbench_py   ground-truth icontract Python postconditions for PostCondBench
                     (external_datasets/postcondbench_python.json)
  postcondbench_java ground-truth Java postconditions for PostCondBench
                     (external_datasets/postcondbench_java.json)

Usage:  python3 compare_postconditions.py
"""
import warnings
import os, re, sys, json, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
from libs.shevrin_maoz_metrics import parse as parse_python, to_formula, artifact_metrics, PROPERTIES
from libs.complexity_metrics import classic_metrics
from sm_java import parse_java
from sm_jml import parse_jml_many
from sm_dafny import parse_dafny_many
warnings.filterwarnings('ignore', category=SyntaxWarning)   # GPT-4 regexes

def parse_each(parser, postconditions):
    """One Formula per expression, or the exception the parser raised."""
    out = []
    for e in postconditions:
        try: out.append(parser(e))
        except Exception as ex: out.append(ex)
    return out

def collect(dataset, language, ids, postconditions, trees, **columns):
    out = []
    for i, (id, postcondition, tree) in enumerate(zip(ids, postconditions, trees)):
        if isinstance(tree, Exception):   # the parser rejected it: report it and leave it out
            if dataset == 'jdk_jml':
                print(f'  unparseable: {" ".join(postcondition.split())[:90]}   ({type(tree).__name__}: {str(tree)[:60]})')
        else:
            out.append({'dataset': dataset, 'language': language, 'id': id, 'postcondition': postcondition, 'SM_Formula': to_formula(tree),
                        **{name: values[i] for name, values in columns.items()}})
    print(f'{dataset}: {len(out)} of {len(ids)} postconditions parsed')
    return out

rows = []
from libs import postconditions_info as pi                       # the 52 study postconditions, incorrect then correct
study_ids = [f'{p}#{c}' for c in (0, 1) for p in pi.EVAL_ROWS]
study_postconditions = pi.WRONG_POSTCONDITIONS + pi.RIGHT_POSTCONDITIONS
rows += collect('study', 'python', study_ids, study_postconditions, parse_each(parse_python, study_postconditions))
def distinct(rows, unit):
    """Drop rows whose (unit, ablation, postcondition) repeats an earlier row: nl2postcond's repeated samples."""
    seen, out = set(), []
    for row in rows:
        key = (unit(row), row['ablation'], ' '.join(row['postcondition'].split()))
        if key not in seen: seen.add(key); out.append(row)
    print(f'  {len(out)} distinct of {len(rows)} sampled')
    return out

nl2postcond_py = distinct(json.load(open('external_datasets/nl2postcond_python_gpt4.json')), lambda row: row['task_id'])
postconditions = [row['postcondition'] for row in nl2postcond_py]
rows += collect('nl2postcond_py', 'python', [f"{row['task_id']}#{row['response_num']}" for row in nl2postcond_py], postconditions,
                parse_each(parse_python, postconditions),                                     # nl2postcond's labels, for RQ1's pool comparison
                ablation=[row['ablation'] for row in nl2postcond_py], correct=[row['test_set_correct'] for row in nl2postcond_py])

nl2postcond_java = distinct(json.load(open('external_datasets/nl2postcond_java_gpt4.json')),
                            lambda row: re.sub(r'_postcondition_\d+\.java$', '', row['file']))   # the method the sample was generated for
postconditions = [row['postcondition'] for row in nl2postcond_java]
rows += collect('nl2postcond_java', 'java', [row['method'] + '/' + row['file'] for row in nl2postcond_java], postconditions,
                parse_each(parse_java, postconditions))

dafny = json.load(open('external_datasets/dafnybench_ensures.json'))
postconditions = [row['postcondition'] for row in dafny]
rows += collect('dafnybench', 'dafny', [row['test_file'] for row in dafny], postconditions, parse_dafny_many(postconditions))

jdk = json.load(open('external_datasets/openjml_jdk_ensures.json'))
postconditions = [row['postcondition'] for row in jdk]
rows += collect('jdk_jml', 'jml', [row['file'] for row in jdk], postconditions, parse_jml_many(postconditions))

postcondbench_py = json.load(open('external_datasets/postcondbench_python.json'))
postconditions = [row['postcondition'] for row in postcondbench_py]
rows += collect('postcondbench_py', 'python', [row['id'] for row in postcondbench_py], postconditions, parse_each(parse_python, postconditions))

postcondbench_java = json.load(open('external_datasets/postcondbench_java.json'))
postconditions = [row['postcondition'] for row in postcondbench_java]
rows += collect('postcondbench_java', 'jml', [row['id'] for row in postcondbench_java], postconditions, parse_jml_many(postconditions))

df = pd.DataFrame(rows)
df[PROPERTIES] = artifact_metrics(df.SM_Formula)[PROPERTIES].values
print('Shevrin & Maoz columns computed by the artifact for', int(df.SM_Score.notna().sum()), 'formulas')

def classic_or_nan(postcondition, language):   # the three classic metrics exist only for valid Python
    try: return classic_metrics(postcondition) if language == 'python' else {}
    except Exception: return {}
classic = pd.DataFrame([classic_or_nan(p, l) for p, l in zip(df.postcondition, df.language)])
for k in classic.columns: df[k] = classic[k].values
df.to_csv('../data/postcondition_corpora.csv', index=False)
print('wrote ../data/postcondition_corpora.csv', df.shape)

print('\nsummary by dataset:')
g = df.groupby('dataset')
summ = pd.DataFrame({'n': g.size(), 'score_median': g.SM_Score.median(), 'score_mean': g.SM_Score.mean(),
                     'ops_median': g.OperatorCount.median(), 'nesting_median': g.OperatorNesting.median(),
                     'neg_mean': g.NegationCount.mean(), 'atomic_share': g.OperatorCount.apply(lambda s: (s == 0).mean())})
print(summ.round(2).to_string())
