"""
Cross-check (not a dependency of the pipeline): confirm that the study's older
annotated pool file, ../../Original_Postconditions_All_With_Complexities.csv, is
the same nl2postcond run as the SimplePromptNoRef rows of nl2postcond_python_gpt4.json
(EvalPlus / GPT-4 / SimplePromptNoRef), row for row: same (task, response) keys,
same assert text, same correctness label, same mutation-kill counts.

Usage:  python3 check_nl2postcond_python_pool.py
"""
import json, os, sys, re, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ex = pd.DataFrame(json.load(open('nl2postcond_python_gpt4.json')))
ex = ex[ex.ablation == 'SimplePromptNoRef']
pool = pd.read_csv('../../Original_Postconditions_All_With_Complexities.csv')
m = pool.merge(ex, left_on=['Problem', 'r_num'], right_on=['task_id', 'response_num'], how='outer', indicator=True)
assert (m._merge == 'both').all(), f'row keys differ: {m._merge.value_counts().to_dict()}'
norm = lambda s: re.sub(r'\s+', ' ', str(s)).strip()
def strip_msg(s):
    """The pool CSV keeps the assert's optional failure message; the JSON does not.
    Cut at the first top-level comma that is followed by a string literal."""
    depth, q = 0, None
    for i, c in enumerate(s):
        if q:
            if c == '\\': continue
            if c == q: q = None
        elif c in '"\'': q = c
        elif c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0 and s[i+1:].lstrip()[:1] in ('"', "'"): return s[:i]
    return s
same_text = (m.Assertonly.str.replace(r'^\s*assert\s+', '', regex=True).map(strip_msg).map(norm) == m.postcondition.map(norm))
same_label = (m.test_set_correct_x.astype(str).str.lower() == m.test_set_correct_y.astype(str).str.lower())
same_kill = (m.num_bopi_killed_x.fillna(-1) == m.num_bopi_killed_y.fillna(-1))
print(f'rows: {len(m)}   same (task, response) keys: all')
print(f'identical assert text (whitespace-normalised): {int(same_text.sum())}/{len(m)}')
print(f'identical correctness label:                   {int(same_label.sum())}/{len(m)}')
print(f'identical mutation-kill counts:                {int(same_kill.sum())}/{len(m)}')
for _, r in m[~same_text].iterrows():
    print('  text differs:', r.Problem, 'r', r.r_num)
sys.exit(0 if (same_text.all() and same_label.all() and same_kill.all()) else 1)
