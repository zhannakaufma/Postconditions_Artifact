"""
Extract every GPT-4 Python postcondition for EvalPlus/HumanEval from the
nl2postcond artifact (Endres, Fakhoury, Chakraborty, Lahiri; FSE 2024).

Each of the four prompts (BasePromptNoRef, BasePromptWithRef,
SimplePromptNoRef, SimplePromptWithRef) has a `summary_eval_results.jsonl`
whose `post_condition` contains comment lines and one assert statement.  
We keep the assert and strip the comment.

Usage:  python3 extract_nl2postcond_python.py <folder holding the four unpacked EvalPlus/GPT4 ablation folders>
        (https://github.com/microsoft/intent-formalization/tree/main/nl2postcondition-fse2024/GeneratedPostconditions)
Writes: nl2postcond_python_gpt4.json  (task_id, response_num, ablation, test_set_correct, num_bopi_run, num_bopi_killed, postcondition)
"""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def assert_condition(snippet):
    """The condition of the snippet's assert, or None if there is no assert."""
    code = '\n'.join(l for l in snippet.splitlines() if l.strip() and not l.lstrip().startswith('#'))
    m = re.search(r'^\s*assert\b', code, flags=re.M)   # a statement, not the word in a prose answer
    if not m: return None
    cond = code[m.end():].strip()
    depth, quote = 0, None                          # cut the message: a top-level comma followed by a string
    for i, c in enumerate(cond):
        if quote:
            if c == '\\': continue
            if c == quote: quote = None
        elif c in '"\'': quote = c
        elif c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0 and re.match(r'\s*[rbfu]{0,2}["\']', cond[i + 1:]): return cond[:i].strip()
    return cond

root = sys.argv[1]
rows = []
for ablation in ['SimplePromptNoRef', 'SimplePromptWithRef', 'BasePromptWithRef', 'BasePromptNoRef']:
    [path] = glob.glob(os.path.join(root, ablation, '*', 'summary_eval_results.jsonl'))
    for line in open(path):
        r = json.loads(line)
        cond = assert_condition(r['post_condition'])
        if cond is None: continue
        count = lambda k: int(r[k]) if r.get(k, 'None') != 'None' else None    # absent when the postcondition failed to run
        rows.append({'task_id': r['task_id'], 'response_num': int(r['response_num']), 'ablation': ablation,
                     'test_set_correct': str(r['test_set_correct']) == 'True',
                     'num_bopi_run': count('num_bopi_run'), 'num_bopi_killed': count('num_bopi_killed'),
                     'postcondition': cond})
json.dump(rows, open(os.path.join(HERE, 'nl2postcond_python_gpt4.json'), 'w'), indent=0)
print(len(rows), 'postconditions')
