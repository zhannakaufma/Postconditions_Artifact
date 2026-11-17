"""
Random postconditions from the study and from each corpus, with their Shevrin & Maoz
translation.  Each predicate p# is colored and the part of the postcondition it stands
for is colored the same way.

Usage:  python3 make_samples_pdf.py  ->  ../analysis/postcondition_samples.pdf   (needs pdflatex)
"""
import ast, io, os, re, subprocess, sys, tokenize, warnings, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '.')
import libs.shevrin_maoz_metrics as sm, sm_java, sm_jml, sm_dafny
warnings.filterwarnings('ignore', category=SyntaxWarning)

SEED, N, MAX_LENGTH = 2027, 50, 320
GROUPS = [('Study', 'study'), ('nl2postcond Python', 'nl2postcond_py'), ('nl2postcond Java', 'nl2postcond_java'),
          ('OpenJML JDK', 'jdk_jml'), ('DafnyBench', 'dafnybench'),
          ('PostCondBench Python', 'postcondbench_py'), ('PostCondBench Java', 'postcondbench_java')]
QUANTIFIER = {'study': r'\b(all|any)\(', 'nl2postcond_py': r'\b(all|any)\(', 'postcondbench_py': r'\b(all|any)\(',
              'nl2postcond_java': r'\b(allMatch|anyMatch|noneMatch)\(', 'postcondbench_java': r'\\(forall|exists)\b|\b(allMatch|anyMatch|noneMatch)\(',
              'jdk_jml': r'\\(forall|exists)\b', 'dafnybench': r'\b(forall|exists)\b'}
COLORS = ['blue', 'red', 'ForestGreen', 'Purple', 'orange', 'brown', 'TealBlue', 'magenta', 'OliveGreen', 'RoyalBlue', 'Maroon', 'Sepia']

ESC = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '_': r'\_', '#': r'\#', '$': r'\$', '%': r'\%', '&': r'\&', '^': r'\^{}', '~': r'\textasciitilde{}', '<': r'\textless{}', '>': r'\textgreater{}'}
def tex(s):
    s = re.sub(r'[\\{}_#$%&^~<>]', lambda m: ESC[m.group()], s)
    return re.sub(r'[^\x00-\x7f]', lambda m: r'\textit{U+%04X}' % ord(m.group()), s)   # pdflatex cannot typeset e.g. a checkmark in a string literal

def predicates(tree):
    """predicate text -> p#, numbered in the order to_formula assigns them."""
    names = {}
    def walk(t):
        if t.predicate is not None: names.setdefault(t.predicate, f'p{len(names) + 1}')
        else:
            for c in t.children: walk(c)
    walk(tree)
    return names

def spans(src, text):
    """Every occurrence of `text` in `src`, ignoring whitespace in both; as (start, end) in src."""
    compact, index = ''.join(src.split()), [i for i, ch in enumerate(src) if not ch.isspace()]
    t = ''.join(text.split())
    out, k = [], 0
    while t:
        k = compact.find(t, k)
        if k < 0: break
        out.append((index[k], index[k + len(t) - 1] + 1)); k += len(t)
    return out

def color_source(src, names, sources):
    color_of = {text: COLORS[i % len(COLORS)] for i, text in enumerate(names)}
    marks, missing = [None] * len(src), []
    for text in sorted(names, key=len, reverse=True):                          # longest first
        found = spans(src, sources.get(text, text))
        if not found: missing.append(names[text])                             # predicate text not present verbatim (e.g. a hoisted conditional)
        for a, b in found:
            for i in range(a, b):                                              # color what is still unclaimed: the two atoms of a
                if marks[i] is None: marks[i] = color_of[text]               # chain a < b <= c share the operand b
    out, i = [], 0
    while i < len(src):
        j = i
        while j < len(src) and marks[j] == marks[i]: j += 1
        piece = tex(src[i:j])
        out.append(piece if marks[i] is None else r'\textcolor{%s}{%s}' % (marks[i], piece)); i = j
    return ''.join(out), color_of, missing

def color_formula(formula, names, color_of):
    """Color each p# by its predicate text."""
    by_name = {p: color_of.get(text, 'black') for text, p in names.items()}
    return re.sub(r'p\d+', lambda m: r'\textcolor{%s}{%s}' % (by_name.get(m.group(), 'gray'), m.group()), tex(formula))

def normalise(dataset, p):
    """One line: Python comments and backslash continuations removed, whitespace collapsed."""
    if dataset in ('study', 'nl2postcond_py', 'postcondbench_py'):
        try: p = tokenize.untokenize(t for t in tokenize.generate_tokens(io.StringIO(p).readline) if t.type != tokenize.COMMENT)
        except (tokenize.TokenError, SyntaxError): pass
    return ' '.join(re.sub(r'\\\s*\n', ' ', p).split())

def python_tree(src):
    node = ast.parse(src, mode='eval').body
    if isinstance(node, ast.Tuple) and node.elts: node = node.elts[0]             # `cond, "message"` or a trailing comma, as parse() does
    return sm.to_tree(node)

def python_sources(src):
    """ast.unparse text -> source text, for every sub-expression (predicates are unparse'd)."""
    node = ast.parse(src, mode='eval').body
    out = {}
    for n in ast.walk(node):
        if isinstance(n, ast.expr):
            seg = ast.get_source_segment(src, n)
            if seg: out.setdefault(ast.unparse(n), seg)
    return out

def trees_for(dataset, srcs):
    def safe(f, s):
        try: return f(s)
        except Exception as e: return e
    if dataset in ('study', 'nl2postcond_py', 'postcondbench_py'): return [safe(python_tree, s) for s in srcs]
    if dataset == 'nl2postcond_java': return [safe(sm_java.parse_java, s) for s in srcs]
    if dataset == 'dafnybench': return sm_dafny.parse_dafny_many(srcs)
    return sm_jml.parse_jml_many(srcs)                                          # jdk_jml, postcondbench_java

df = pd.read_csv('../data/postcondition_corpora.csv', low_memory=False)
entries, formulas = [], []
for label, dataset in GROUPS:
    pool = df[df.dataset == dataset]
    text = pool.postcondition.astype(str).map(lambda p: normalise(dataset, p))
    candidates = text[text.str.len() <= MAX_LENGTH].sample(frac=1, random_state=SEED).tolist()   # shuffle, then take the first N that parse
    chosen = []
    for start in range(0, len(candidates), 60):
        batch = candidates[start:start + 60]
        for src, t in zip(batch, trees_for(dataset, batch)):
            if isinstance(t, Exception) or t is None: continue
            chosen.append((src, t))
            if len(chosen) == N: break
        if len(chosen) == N: break
    for src, t in chosen:
        t = sm.simplify(t)
        sources = python_sources(src) if dataset.endswith('_py') or dataset == 'study' else {}
        entries.append((label, src, predicates(t), sm.to_formula(t), sources)); formulas.append(sm.to_formula(t))
scores = sm.artifact_metrics(pd.Series(formulas)).SM_Score.tolist()           # scored by the Shevrin & Maoz jar

body, last, uncolored = [], None, []
for (label, src, names, formula, sources), score in zip(entries, scores):
    if label != last:
        if last is not None: body.append(r'\end{enumerate}')
        body += [r'\subsection*{' + tex(label) + '}', r'\begin{enumerate}[leftmargin=*,itemsep=8pt]']; last = label
    colored_src, color_of, missing = color_source(src, names, sources)
    if missing: uncolored.append((label, missing, src))
    item = (r'\item \textbf{' + tex(label) + r' postcondition:} \texttt{' + colored_src + '}'
            + r'\\ \textbf{Translation:} \texttt{' + color_formula(formula, names, color_of) + r'}\quad (score ' + f'{score:.2f}' + ')')
    if missing:                                                                # predicates built by a rule (a hoisted conditional, old(...)): spell them out
        text_of = {pn: text for text, pn in names.items()}
        item += r'\\ \textbf{where} ' + '; '.join(r'\textcolor{%s}{%s} = \texttt{%s}' % (color_of[text_of[pn]], pn, tex(text_of[pn])) for pn in sorted(missing, key=lambda pn: int(pn[1:])))
    body.append(item)
body.append(r'\end{enumerate}')


def md_tex(line):
    """Light Markdown to LaTeX: `code` -> \\texttt, **bold** -> \\textbf, "quotes" -> ``quotes'', everything escaped."""
    out, i = [], 0
    for m in re.finditer(r'`([^`]*)`|\*\*(.+?)\*\*', line):
        out.append(prose(line[i:m.start()]))
        out.append(r'\texttt{%s}' % tex(m.group(1)) if m.group(1) is not None else r'\textbf{%s}' % md_tex(m.group(2)))
        i = m.end()
    out.append(prose(line[i:]))
    return ''.join(out)

def prose(text):
    """Escaped prose, with straight double quotes turned into LaTeX opening/closing quotes."""
    parts = tex(text).split('"')
    return ''.join(p + ('``' if k % 2 == 0 else "''") for k, p in enumerate(parts[:-1])) + parts[-1]

def rules_tex():
    """The rules page body from rules.md: paragraphs before the first bullet, then one \\item per '- ' line."""
    lines = [l.rstrip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rules.md'))]
    body, items = [], []
    for l in lines:
        if l.startswith('- '): items.append(r'\item ' + md_tex(l[2:]))
        elif l.startswith(' ') and l.strip() and items: items[-1] += r'\\ \hspace*{1.2em}' + md_tex(l.strip())   # example line under the rule
        elif l.strip(): body.append(md_tex(l))
    return '\n\n'.join(body) + '\n' + r'\begin{itemize}[itemsep=2pt]' + '\n' + '\n'.join(items) + '\n' + r'\end{itemize}'

head = r'''\documentclass[10pt]{article}
\usepackage[margin=0.9in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{upquote}
\usepackage[dvipsnames]{xcolor}
\usepackage{enumitem}
\setlength{\parindent}{0pt}
\sloppy\raggedright
\begin{document}
\section*{Rules}
''' + rules_tex() + r'''


'''
open('postcondition_samples.tex', 'w').write(head + '\n'.join(body) + '\n' + r'\end{document}')
r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'postcondition_samples.tex'], capture_output=True, text=True)
if r.returncode == 0:
    os.replace('postcondition_samples.pdf', '../analysis/postcondition_samples.pdf')
    for ext in ('tex', 'aux', 'log', 'out'):
        if os.path.exists(f'postcondition_samples.{ext}'): os.remove(f'postcondition_samples.{ext}')
print('postcondition_samples.pdf: pdflatex exit', r.returncode, '' if r.returncode == 0 else r.stdout[-1500:])
print('entries per source:', {label: sum(1 for e in entries if e[0] == label) for label, _ in GROUPS})
print(f'entries with a predicate that has no matching text in the source ({len(uncolored)}):')
for label, missing, src in uncolored: print(f'  [{label}] {", ".join(missing)}: {src[:150]}')
