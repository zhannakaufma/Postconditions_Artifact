"""
This file does the same thing as shevrin_maoz_metrics.py but for Dafny
postconditions (`ensures` clauses).

Mapping rules:
  && / || / !                           ->  & / | / !
  A ==> B  /  A <== B                   ->  A -> B
  A <==> B                              ->  A <-> B
  if C then A else B (Boolean position) ->  (C -> A) & (!C -> B)   (the branches are Boolean by typing)
  old(E), E with Boolean structure      ->  E's formula, with old(...) kept on each atom
  var x := e; B                         ->  B
  a conditional anywhere inside an atom ->  a case split on the atom: x == f(if C then A else B) becomes
                                            (C -> x == f(A)) & (!C -> x == f(B)), except inside a lambda or a comprehension
  A == B  with a Boolean-shaped side    ->  A <-> B
  A != B  with a Boolean-shaped side    ->  !(A <-> B)
  X == true  /  X == false              ->  X  /  !X
  forall x :: B  /  forall x | R :: B   ->  B  /  R -> B   (the reader still parses the body)
  exists x :: B  /  exists x | R :: B   ->  B  /  R & B
  0 <= i < n  (a chained comparison)    ->  (0 <= i) & (i < n): two conditions to check
  anything else                         ->  a predicate, represented by a letter p#

"Boolean-shaped" means a comparison (including `in` / `!in`, disjointness `!!`
and a chain such as 0 <= i < n), an &&/||/==>/<==>/! expression, true/false, a
quantifier, a conditional whose branches are both Boolean-shaped, or a call to
a function whose name sounds Boolean (BOOL_METHOD_NAME, shared with sm_java.py
and sm_jml.py).

Setup: install the .NET 8 SDK, then build:
  dotnet build -c Release sm_dafny

parse_dafny_many(expressions) parses a whole corpus in one run and returns one
Formula (or an Exception) per expression.
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libs.shevrin_maoz_metrics import Formula, AND, OR, IMPLIES, IFF, conditional
from sm_java import BOOL_METHOD_NAME

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, 'sm_dafny', 'bin', 'Release', 'net8.0', 'SMDafny.dll')

COMPARISON = {'Eq', 'Neq', 'Lt', 'Le', 'Ge', 'Gt', 'In', 'NotIn', 'Disjoint'}
SYMBOL = {'Eq': '==', 'Neq': '!=', 'Lt': '<', 'Le': '<=', 'Ge': '>=', 'Gt': '>', 'In': 'in', 'NotIn': '!in', 'Disjoint': '!!'}
CONNECTIVE = {'And', 'Or', 'Imp', 'Exp', 'Iff'}
OPEN_QUANTIFIERS = True   # see libs/shevrin_maoz_metrics.py


def find_dotnet():
    for c in [shutil.which('dotnet'), '/opt/homebrew/opt/dotnet@8/bin/dotnet', '/opt/homebrew/bin/dotnet',
              '/usr/local/share/dotnet/dotnet']:
        if c and os.path.exists(c): return c
    return None


def syntax_trees(expressions):
    """Run the harness once over all expressions; one JSON tree (or {"error"}) each."""
    dotnet = find_dotnet()
    if dotnet is None or not os.path.exists(HARNESS):
        raise RuntimeError('Dafny parser not available: see the setup note at the top of sm_dafny.py')
    env = dict(os.environ, DOTNET_ROOT=os.path.dirname(os.path.realpath(dotnet)), DOTNET_CLI_TELEMETRY_OPTOUT='1')
    text = '\n'.join(' '.join(e.split()) for e in expressions) + '\n'
    result = subprocess.run([dotnet, HARNESS], input=text, capture_output=True, text=True, check=True, env=env)
    trees = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(trees) == len(expressions), (len(trees), len(expressions))
    return trees


def is_boolean_shaped(n):
    t = n['t']
    if t == 'ParensExpression': return is_boolean_shaped(n['inner'])
    if t == 'UnaryOpExpr': return n['op'] == 'Not'
    if t == 'BinaryExpr': return n['op'] in COMPARISON | CONNECTIVE
    if t == 'LiteralExpr': return n['value'] is not None
    if t in ('ChainingExpression', 'ForallExpr', 'ExistsExpr'): return True   # (all map to formulas now, still Boolean-shaped)
    if t == 'ITEExpr': return is_boolean_shaped(n['then']) and is_boolean_shaped(n['else'])
    if t == 'ApplySuffix':                                     # f(...) or a.b.f(...): the called name
        m = re.match(r'[\w.]*?(\w+)\s*\(', n['s'])
        return bool(m and BOOL_METHOD_NAME.match(m.group(1)))
    return False


def to_tree(n):
    """Apply the mapping rules to one JSON syntax-tree node."""
    t = n['t']
    if t == 'ParensExpression':                                                  # (0 <= i < n) keeps its own group
        f = to_tree(n['inner'])
        return Formula(op=f.op, children=f.children, negated=f.negated) if f.chain else f
    if t == 'UnaryOpExpr' and n['op'] == 'Not':
        return to_tree(n['expr']).negate()
    if t == 'BinaryExpr':
        op, left, right = n['op'], n['left'], n['right']
        if op in ('And', 'Or'):
            lf, rf = to_tree(left), to_tree(right)                                # a && b && c is one group;
            children = lf.children if (left['t'] == 'BinaryExpr' and left['op'] == op) else [lf]   # (a && b) && c stays nested
            if op == 'And':                                                       # a && 0 <= i < n: the chain's conjuncts join as siblings
                children = [c for f in children for c in (f.children if (f.chain and not f.negated) else [f])]
                if rf.chain and not rf.negated: return Formula(op=AND, children=children + rf.children)
            return Formula(op=AND if op == 'And' else OR, children=children + [rf])
        if op in ('Imp', 'Exp'): return Formula(op=IMPLIES, children=[to_tree(left), to_tree(right)])
        if op == 'Iff':          return Formula(op=IFF, children=[to_tree(left), to_tree(right)])
        if op in ('Eq', 'Neq'):
            for x, y in ((left, right), (right, left)):                          # X == true / X == false
                if y['t'] == 'LiteralExpr' and y['value'] is not None:
                    fx = to_tree(x)
                    return fx if y['value'] == (op == 'Eq') else fx.negate()
            if is_boolean_shaped(left) or is_boolean_shaped(right):              # A == B -> A <-> B
                f = Formula(op=IFF, children=[to_tree(left), to_tree(right)])
                return f if op == 'Eq' else f.negate()
    if t == 'ITEExpr':                                                           # to_tree only reaches Boolean positions
        return conditional(to_tree(n['cond']), to_tree(n['then']), to_tree(n['else']))
    if t == 'OldExpr' and is_boolean_shaped(n['expr']):                          # old(a && b)
        return to_tree(n['expr']).rename(lambda p: f'old({p})')
    if t == 'LetExpr':                                                           # var x := e; body
        return to_tree(n['body'])
    if OPEN_QUANTIFIERS and t == 'ChainingExpression':                           # 0 <= i < n  ->  (0 <= i) & (i < n)
        ops, operands = n['ops'], n['operands']
        return Formula(op=AND, children=[Formula(predicate=f"{operands[i]['s']} {SYMBOL.get(ops[i], ops[i])} {operands[i + 1]['s']}") for i in range(len(ops))], chain=True)
    if OPEN_QUANTIFIERS and t in ('ForallExpr', 'ExistsExpr'):                   # forall x | R :: B
        body = to_tree(n['term'])
        if n.get('range') is None: return body
        return Formula(op=IMPLIES if t == 'ForallExpr' else AND, children=[to_tree(n['range']), body])
    if OPEN_QUANTIFIERS and 'cond1' in n:                                        # x == f(if C then A else B): a case split on the atom
        from sm_jml import hoist
        return hoist(n, lambda text: syntax_trees([text])[0])
    return Formula(predicate=n['s'])


def parse_dafny_many(expressions):
    """One Formula per expression, or a ValueError where Dafny's parser rejected it."""
    out = []
    for tree in syntax_trees(list(expressions)):
        out.append(ValueError(tree['error']) if 'error' in tree else to_tree(tree))
    return out


if __name__ == '__main__':
    from libs.shevrin_maoz_metrics import to_formula
    tests = ['forall i :: 0 <= i < |xs| ==> a[i] == xs[i]',
             '0 <= index < a.Length ==> a[index] == x',
             '|s| == |t|',
             'multiset(a[..]) == multiset(old(a[..]))',
             'if x > 0 then r == x else r == -x',
             'Valid() && fresh(Repr - old(Repr))',
             'index == -1 ==> forall i : int :: 0 <= i < a.Length ==> a[i] != x',
             'contains == false ==> item !in circularQueue[..]',
             '(a && b) && c']
    for t, f in zip(tests, parse_dafny_many(tests)):
        print(f'{t[:70]:72s} => {f if isinstance(f, Exception) else to_formula(f)}')
