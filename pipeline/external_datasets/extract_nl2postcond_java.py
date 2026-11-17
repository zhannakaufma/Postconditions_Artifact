"""
Extract every GPT-4 Java postcondition for Defects4J from the nl2postcond
artifact (Endres, Fakhoury, Chakraborty, Lahiri; FSE 2024).

Each ablation (no_ref -> NoBuggyRef, yes_ref -> WithBuggyRef) has a folder
`human_readable_programs/<method>/<file>.java` with one generated `assert`
statement per file. 
We keep the assert and strip the comment.

Usage:  python3 extract_nl2postcond_java.py <folder holding the unpacked no_ref and yes_ref Defects4J/GPT4 folders>
        (https://github.com/microsoft/intent-formalization/tree/main/nl2postcondition-fse2024/GeneratedPostconditions)
Writes: nl2postcond_java_gpt4.json  (method, file, ablation, postcondition)
"""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ABLATIONS = {'yes_ref': 'WithBuggyRef', 'no_ref': 'NoBuggyRef'}

def assert_condition(source):
    """The condition of the file's assert statement, or None if there is none."""
    code = re.sub(r'```\w*', '', source)                               # markdown fences left by the model
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    code = '\n'.join(l for l in code.splitlines() if not l.strip().startswith('//'))
    m = re.search(r'\bassert\b\s*(.*?);\s*$', code, flags=re.S | re.M)
    if not m: return None
    cond = ' '.join(m.group(1).split())
    depth, quoted, colon = 0, False, None                              # a top-level ':' before a string is the message
    for i, c in enumerate(cond):
        if c == '"' and (i == 0 or cond[i - 1] != '\\'): quoted = not quoted
        if quoted: continue
        if c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ':' and depth == 0 and '?' not in cond[:i].split(':')[-1]: colon = i
    if colon is not None and cond[colon + 1:].strip().startswith('"'): cond = cond[:colon].strip()
    return cond

root = sys.argv[1]
rows = []
for folder, ablation in ABLATIONS.items():
    for path in sorted(glob.glob(os.path.join(root, folder, '*', 'human_readable_programs', '*', '*.java'))):
        cond = assert_condition(open(path, encoding='utf-8', errors='replace').read())
        if cond is None: continue
        rows.append({'method': os.path.basename(os.path.dirname(path)), 'file': os.path.basename(path),
                     'ablation': ablation, 'postcondition': cond})
json.dump(rows, open(os.path.join(HERE, 'nl2postcond_java_gpt4.json'), 'w'), indent=0)
print(len(rows), 'postconditions')
