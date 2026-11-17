"""
Calc complexity and sloc metrics for functions in HumanEvalProblems (including study) and PostCondBench

Usage:  python3 compare_functions.py
Writes: ../data/function_metrics.csv
"""
import os, sys, json, textwrap, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '.')
from libs.complexity_metrics import function_metrics
from libs.postconditions_info import EVAL_ROWS

rows = []
BASE = 'libs/HumanEvalProblems'
for n in sorted((d for d in os.listdir(BASE) if d.isdigit()), key=int):
    src = open(f'{BASE}/{n}/stub_with_reference_{n}.py').read()
    rows.append(dict(source='humaneval', id=f'HumanEval/{n}', used=f'HumanEval/{n}' in EVAL_ROWS, **function_metrics(src)))
for m in json.load(open('external_datasets/postcondbench_methods.json')):
    if m['language'] == 'python':
        rows.append(dict(source='postcondbench', id=m['id'], used=False, **function_metrics(textwrap.dedent(m['source']))))

df = pd.DataFrame(rows)
df.to_csv('../data/function_metrics.csv', index=False)
print('wrote ../data/function_metrics.csv', df.shape, '| humaneval:', (df.source == 'humaneval').sum(), ' postcondbench:', (df.source == 'postcondbench').sum(), ' used:', df.used.sum())
