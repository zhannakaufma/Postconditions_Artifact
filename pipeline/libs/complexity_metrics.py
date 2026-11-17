import ast, re
from radon.visitors import ComplexityVisitor
from radon.metrics import h_visit
from radon.raw import analyze
from complexipy import code_complexity


def wrap(postcondition):
    return f"\ndef assertion_func():\n    return {postcondition}\n"


def classic_metrics(postcondition):
    src = wrap(postcondition)
    return {'Cyclomatic': ComplexityVisitor.from_code(src).functions[0].complexity,
            'Cognitive': code_complexity(src).complexity,
            'Halstead_Difficulty': h_visit(src).total.difficulty}


def docstring(fn):
    for stmt in fn.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            return stmt.value.value
    return ''


# Capture all existing example formats
PREFIX = r'^\s*(?:>>>|\*|-|assert|for)?\s*'
def example_formats(name):
    return [
        PREFIX + re.escape(name) + r'\s*\(',                            # f(1) => 2,  >>> f(1),  f(1) returns 2
        PREFIX + r'\w+\(.*\)\s*(?:==|=>|==>|➞|->|=|returns|should)',    # same, when the docstring calls it by another name
        r'^\s*Input\b',                                                 # Input: ...  Output: ...
        r'^\s*For\s+\w+\s*=',                                           # For s = "abc", the output should be ...
        r'^\s*Example\s*\d',                                            # Example 1:  (blocks without Input lines)
    ]

def example_pattern(doc, name):
    """The first example format that matches a line of the docstring, or None."""
    return next((p for p in example_formats(name) if any(re.search(p, line) for line in doc.splitlines())), None)

def worked_examples(doc, name):
    pattern = example_pattern(doc, name)
    return sum(1 for line in doc.splitlines() if re.search(pattern, line)) if pattern else 0

def prose_words(doc, name):
    """Words in the docstring outside the examples"""
    lines = doc.splitlines()
    pattern = example_pattern(doc, name)
    if pattern:
        first = next(i for i, line in enumerate(lines) if re.search(pattern, line))
        tail = lines[first:]
        resume = next((i for i, line in enumerate(tail) if re.match(r'\s*(Note|Constraints)\b', line)), len(tail))
        lines = lines[:first] + tail[resume:]
    return len(' '.join(lines).split())


def function_metrics(src):
    fn = max((n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)), key=lambda n: len(docstring(n)))
    hal = h_visit(src).total
    doc = docstring(fn)
    functions = ComplexityVisitor.from_code(src).functions   # radon lists nested functions separately, as closures
    return dict(cyclomatic=sum(f.complexity for f in functions) + sum(c.complexity for f in functions for c in f.closures),
                cognitive=code_complexity(src).complexity,
                halstead_difficulty=hal.difficulty,
                sloc=analyze(src).sloc,
                docstring_words=prose_words(doc, fn.name),
                docstring_examples=worked_examples(doc, fn.name))
