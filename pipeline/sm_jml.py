"""
This file does the same thing as shevrin_maoz_metrics.py but for JML

Mapping rules:
  && / || / !                           ->  & / | / !
  & / | with two Boolean-shaped sides   ->  & / |
  A ^ B  with two Boolean-shaped sides  ->  !(A <-> B)
  A ==> B  /  A <== B                   ->  A -> B
  A <==> B                              ->  A <-> B
  A <=!=> B                             ->  !(A <-> B)
  C ? A : B  (in Boolean position)      ->  (C -> A) & (!C -> B)   (the branches are Boolean by typing)
  \\old(E), E with Boolean structure     ->  E's formula, with \\old(...) kept on each atom
  A == B  with a Boolean-shaped side    ->  A <-> B
  A != B  with a Boolean-shaped side    ->  !(A <-> B)
  X == true  /  X == false              ->  X  /  !X
  \\forall T x; R; B                     ->  R -> B     (the reader still parses the body; no range: B)
  \\exists T x; R; B                     ->  R & B
  a <= b < c  (a chained comparison)    ->  (a <= b) & (b < c): two conditions to check
  s.allMatch(x -> B) / anyMatch         ->  B          (stream quantifiers, as in sm_java.py)
  s.noneMatch(x -> B)                   ->  !B
  s.filter(x -> R).allMatch(x -> B)     ->  R -> B     (a filter is a range; anyMatch: R & B, noneMatch: R -> !B)
  a conditional anywhere inside an atom ->  a case split on the atom: x.equals(C ? A : B) becomes
                                            (C -> x.equals(A)) & (!C -> x.equals(B)), however deep the conditional
                                            sits, except inside a lambda or a quantifier
  anything else                         ->  a predicate, represented by a letter p#

"Boolean-shaped" means a comparison (including JML's chained a <= b <= c and
subtype <:), an instanceof, an &&/||/! expression, true/false, a quantified
expression, a conditional whose branches are both Boolean-shaped, or a call to a
method whose name sounds Boolean (BOOL_METHOD_NAME, shared with sm_java.py).

"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libs.shevrin_maoz_metrics import Formula, AND, OR, IMPLIES, IFF, find_java, conditional, DECIDED, binder, hoisting
from sm_java import BOOL_METHOD_NAME

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.join(HERE, 'tools', 'jmltk-cli-1.0.0-all.jar')
HARNESS = os.path.join(HERE, 'sm_jml')

COMPARISON = {'EQUALS', 'NOT_EQUALS', 'LESS', 'GREATER', 'LESS_EQUALS', 'GREATER_EQUALS', 'SUBTYPE'}
OP_SYMBOL = {'EQUALS': '==', 'NOT_EQUALS': '!=', 'LESS': '<', 'GREATER': '>', 'LESS_EQUALS': '<=', 'GREATER_EQUALS': '>=', 'SUBTYPE': '<:'}
QUANTIFIER = re.compile(r'^\s*\\(forall|exists|num_of|sum|product|min|max)\b')
OPEN_QUANTIFIERS = True   # see libs/shevrin_maoz_metrics.py


def normalize(expr):
    """jmlparser requires a quantified expression to be parenthesized; the OpenJML
    specs sometimes write `\\forall ...` bare at the top level."""
    expr = ' '.join(expr.split())
    return f'({expr})' if QUANTIFIER.match(expr) else expr


def syntax_trees(expressions):
    """Run the harness once over all expressions; one JSON tree (or {"error"}) each."""
    java = find_java()
    if java is None or not os.path.exists(JAR) or not os.path.exists(os.path.join(HARNESS, 'SMJml.class')):
        raise RuntimeError('jmlparser not available: see the setup note at the top of sm_jml.py')
    text = '\n'.join(normalize(e) for e in expressions) + '\n'
    result = subprocess.run([java, '-cp', f'{JAR}{os.pathsep}{HARNESS}', 'SMJml'],
                            input=text, capture_output=True, text=True, check=True)
    trees = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(trees) == len(expressions), (len(trees), len(expressions))
    return trees


def is_boolean_shaped(n):
    t = n['t']
    if t == 'EnclosedExpr': return is_boolean_shaped(n['inner'])
    if t == 'UnaryExpr': return n['op'] == 'LOGICAL_COMPLEMENT'
    if t == 'BinaryExpr':
        if n['op'] in ('BINARY_AND', 'BINARY_OR', 'XOR'): return is_boolean_shaped(n['left']) and is_boolean_shaped(n['right'])
        return n['op'] in COMPARISON | {'AND', 'OR', 'IMPLICATION', 'RIMPLICATION', 'EQUIVALENCE', 'ANTIVALENCE'}
    if t in ('InstanceOfExpr', 'BooleanLiteralExpr', 'JmlQuantifiedExpr', 'JmlMultiCompareExpr'): return True
    if t == 'ConditionalExpr': return is_boolean_shaped(n['then']) and is_boolean_shaped(n['else'])
    if t == 'MethodCallExpr': return bool(BOOL_METHOD_NAME.match(n['name']))
    return False


def to_tree(n):
    """Apply the mapping rules to one JSON syntax-tree node."""
    t = n['t']
    if t == 'EnclosedExpr':                                                      # (0 <= i < n) keeps its own group
        f = to_tree(n['inner'])
        return Formula(op=f.op, children=f.children, negated=f.negated) if f.chain else f
    if t == 'UnaryExpr' and n['op'] == 'LOGICAL_COMPLEMENT':
        return to_tree(n['expr']).negate()
    if t == 'BinaryExpr':
        op, left, right = n['op'], n['left'], n['right']
        logical = op in ('AND', 'OR') or (op in ('BINARY_AND', 'BINARY_OR') and is_boolean_shaped(left) and is_boolean_shaped(right))
        if logical:
            lf, rf = to_tree(left), to_tree(right)                                # a && b && c is one group;
            children = lf.children if (left['t'] == 'BinaryExpr' and left['op'] == op) else [lf]   # (a && b) && c stays nested
            if op in ('AND', 'BINARY_AND'):                                       # a && 0 <= i < n: the chain's conjuncts join as siblings
                children = [c for f in children for c in (f.children if (f.chain and not f.negated) else [f])]
                if rf.chain and not rf.negated: return Formula(op=AND, children=children + rf.children)
            return Formula(op=AND if op in ('AND', 'BINARY_AND') else OR, children=children + [rf])
        if op == 'XOR' and is_boolean_shaped(left) and is_boolean_shaped(right):
            return Formula(op=IFF, children=[to_tree(left), to_tree(right)]).negate()
        if op == 'IMPLICATION':  return Formula(op=IMPLIES, children=[to_tree(left), to_tree(right)])
        if op == 'RIMPLICATION': return Formula(op=IMPLIES, children=[to_tree(right), to_tree(left)])
        if op == 'EQUIVALENCE':  return Formula(op=IFF, children=[to_tree(left), to_tree(right)])
        if op == 'ANTIVALENCE':  return Formula(op=IFF, children=[to_tree(left), to_tree(right)]).negate()
        if op in ('EQUALS', 'NOT_EQUALS'):
            for x, y in ((left, right), (right, left)):                          # X == true / X == false
                if y['t'] == 'BooleanLiteralExpr':
                    fx = to_tree(x)
                    return fx if y['value'] == (op == 'EQUALS') else fx.negate()
            if is_boolean_shaped(left) or is_boolean_shaped(right):              # A == B -> A <-> B
                f = Formula(op=IFF, children=[to_tree(left), to_tree(right)])
                return f if op == 'EQUALS' else f.negate()
    if t == 'ConditionalExpr':                                                   # to_tree only reaches Boolean positions
        return conditional(to_tree(n['cond']), to_tree(n['then']), to_tree(n['else']))
    if t == 'MethodCallExpr' and n['name'] == '\\old' and 'old_arg' in n and is_boolean_shaped(n['old_arg']):   # \old(a && b)
        return to_tree(n['old_arg']).rename(lambda p: f'\\old({p})')
    if OPEN_QUANTIFIERS and t == 'MethodCallExpr' and n['name'] in ('allMatch', 'anyMatch', 'noneMatch') and 'lambda_body' in n:   # filter(x -> R).allMatch(x -> B)
        with binder():
            body = to_tree(n['lambda_body'])
            if n['name'] == 'noneMatch': body = body.negate()
            if 'filter_body' not in n: return body
            return Formula(op=AND if n['name'] == 'anyMatch' else IMPLIES, children=[to_tree(n['filter_body']), body])
    if OPEN_QUANTIFIERS and t == 'JmlMultiCompareExpr':                          # a <= b < c  ->  (a <= b) & (b < c)
        ops, operands = n['ops'], n['operands']
        return Formula(op=AND, children=[Formula(predicate=f"{operands[i]['s']} {ops[i]} {operands[i + 1]['s']}") for i in range(len(ops))], chain=True)
    if OPEN_QUANTIFIERS and t == 'JmlQuantifiedExpr' and n.get('binder', '').upper() in ('FORALL', 'EXISTS'):   # \forall T x; R; B
        exprs = [x for x in n['exprs'] if x is not None]
        with binder():
            if len(exprs) == 1: return to_tree(exprs[0])
            if len(exprs) == 2:
                rng, body = to_tree(exprs[0]), to_tree(exprs[1])
                return Formula(op=IMPLIES if n['binder'].upper() == 'FORALL' else AND, children=[rng, body])
    if hoisting() and 'cond1' in n:                                             # x.equals(C ? A : B): a case split on the atom
        return hoist(n, lambda text: syntax_trees([text])[0])
    return Formula(predicate=n['s'])


def hoist(n, parse_one):
    """(C -> atom[A]) & (!C -> atom[B]) for the first conditional C ? A : B inside the atom n: each branch is
    substituted into the atom's text and re-parsed, so nested conditionals unroll too."""
    c1 = n['cond1']
    key = ' '.join(c1['cond']['s'].split())
    def branch(br):
        tree = parse_one(n['s'].replace(c1['s'], br['s'], 1))
        return Formula(predicate=n['s'].replace(c1['s'], br['s'], 1)) if 'error' in tree else to_tree(tree)
    if key in DECIDED: return branch(c1['then'] if DECIDED[key] else c1['else'])   # decided by an enclosing split
    def decided(br, value):
        DECIDED[key] = value
        try: return branch(br)
        finally: del DECIDED[key]
    return conditional(to_tree(c1['cond']), decided(c1['then'], True), decided(c1['else'], False))


def parse_jml_many(expressions):
    """One Formula per expression, or a ValueError where jmlparser rejected it."""
    out = []
    for tree in syntax_trees(list(expressions)):
        out.append(ValueError(tree['error']) if 'error' in tree else to_tree(tree))
    return out


if __name__ == '__main__':
    from libs.shevrin_maoz_metrics import to_formula
    tests = ['\\old(childNodeSize()) != 0 ==> \\result != null',
             '(\\result == 0.0) <==> (this.type == MassType.INFINITE || this.type == MassType.FIXED_LINEAR_VELOCITY)',
             '\\result == (\\real)v & v == (double)\\result',
             '\\forall int i; 0 <= i && i < a.length; a[i] >= 0',
             '(\\forall int i; 0 <= i && i < a.length; a[i] >= 0) && \\result.isEmpty()',
             'Long.MIN_VALUE <= \\result <= Long.MAX_VALUE & \\result == (\\real)v',
             '\\result != null && \\result.equals("-34")',
             '(a && b) && c']
    for t, f in zip(tests, parse_jml_many(tests)):
        print(f'{t[:70]:72s} => {f if isinstance(f, Exception) else to_formula(f)}')
