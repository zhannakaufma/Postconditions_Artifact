"""
Extract the ground-truth postconditions of PostCondBench (Zhang et al.) and the
source of each of its methods (compare_functions.py measures those sources with
the same tools as the HumanEval functions).

Every `data/step/8.benchmark/<method>.json` has a `ref_postcond` field: for Java
methods a JML comment with `//@ ensures <expr>;` lines, for Python methods a
stack of `@icontract.ensure(lambda ...: <expr>)` decorators.  One row per
clause / decorator body.

Usage:  python3 extract_postcondbench.py <clone of https://github.com/zhang-ge-hao/postcond-bench>
Writes: postcondbench_python.json, postcondbench_java.json  (id, method, ref_source, postcondition)
        postcondbench_methods.json                          (id, language, ref_source, source)
"""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def icontract_bodies(source):
    """The lambda body of each @icontract.ensure(lambda <args>: <body>) in source."""
    bodies = []
    for m in re.finditer(r'@icontract\.ensure\s*\(', source):
        i, depth, quote = m.end(), 1, None
        j = i
        while j < len(source) and depth:                     # find the decorator's closing parenthesis
            c = source[j]
            if quote:
                if c == '\\': j += 1
                elif c == quote: quote = None
            elif c in '"\'': quote = c
            elif c in '([{': depth += 1
            elif c in ')]}': depth -= 1
            j += 1
        inner = source[i:j - 1].strip()
        lam = re.match(r'lambda\b[^:]*:', inner)
        if lam:
            body = inner[lam.end():].strip()
            body = re.sub(r',\s*(description|error|enabled)\s*=.*$', '', body, flags=re.S)   # keyword arguments after the lambda
            bodies.append(body)
    return bodies

def jml_ensures(spec):
    """Every `ensures` clause of a JML spec: one per `//@ ensures` line, ended by `;` or by the next clause.
    (42 PostCondBench clauses have no terminating semicolon, so splitting on `;` alone glues or drops clauses.)"""
    clauses = []
    for seg in re.split(r'(?:^|\n)\s*(?://)?\s*@?\s*ensures\s+', spec)[1:]:
        seg = re.split(r'\n\s*(?://)?\s*@\s*\w', seg)[0].strip()        # stop at the next JML clause on a later line
        clauses.append(seg[:-1] if seg.endswith(';') else seg)
    return clauses

root = sys.argv[1]
postconditions, methods = {'python': [], 'java': []}, []
for path in sorted(glob.glob(os.path.join(root, 'data', 'step', '8.benchmark', '*.json'))):
    d = json.load(open(path))
    language, method = d['repo']['language'], os.path.basename(path)[:-5]
    methods.append({'id': method, 'language': language, 'ref_source': d.get('ref_source'), 'source': d['content']})
    spec = d.get('ref_postcond') or ''
    clauses = jml_ensures(spec) if language == 'java' else icontract_bodies(spec)
    for k, clause in enumerate(clauses):
        postconditions[language].append({'id': f'{method}#{k}', 'method': method, 'ref_source': d.get('ref_source'),
                                         'postcondition': ' '.join(clause.split())})
for language, name in [('python', 'postcondbench_python.json'), ('java', 'postcondbench_java.json')]:
    json.dump(postconditions[language], open(os.path.join(HERE, name), 'w'), indent=0)
json.dump(methods, open(os.path.join(HERE, 'postcondbench_methods.json'), 'w'), indent=0)
print(len(methods), 'methods;', {l: len(v) for l, v in postconditions.items()}, 'postconditions')
