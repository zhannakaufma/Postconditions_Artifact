"""
Shevrin & Maoz reading-complexity metrics for Python postconditions.

Shevrin & Maoz (TOSEM 2025, doi 10.1145/3744557) measure how hard a Boolean
formula is to read. The formulas are propositional. This is the grammar from
the Shevrin & Maoz artifact (BooleanFormula.g4):

formula:
	(negated='!')? 
	(
		literal=CONST | 
		( '(' elements+=formula (op=( '|' | '&' | '->' | '<->' ) elements+=formula)+ ')' )
	);

CONST:
  	'^'?('a'..'z'|'A'..'Z'|'_') ('a'..'z'|'A'..'Z'|'_'|'0'..'9')*;
  
 WS: [ \t]+ -> skip ;

This module transforms python assert statements into this grammar by:

  1. mapping the postcondition to a formula tree
  2. printing that tree in the grammar syntax         
  3. handing the result to boolean-comprehension-materials/jars/formula_score_calculator.jar
     to compute the metrics and score

Mapping rules:

  and / or / not                        ->  & / | / !
  (A and B) and C                       ->  ((A & B) & C)  
  A if B else C                         ->  (B -> A) & (!B -> C)
  Boolean literals simplify away        ->  A if C else True -> C -> A;  A if C else False -> C & A;
                                            True if C else B -> C | B;  X and True -> X;  X or True -> True;
                                            X == True handled above.  A bare literal on its own stays an atom.
  A == B  with a Boolean-shaped side    ->  A <-> B
  A != B  with a Boolean-shaped side    ->  !(A <-> B)
  A <= B  with two Boolean-shaped sides ->  A -> B
  X == True  /  X == False              ->  X  /  !X
  all(B for x in xs)                    ->  B          (the reader still parses the body)
  all(B for x in xs if R)               ->  R -> B     (a generator filter is a range, as in JML and Dafny)
  any(B for x in xs) / any(... if R)    ->  B  /  R & B
  all(G1 if C else G2), G1/G2 generators ->  (C -> all(G1)) & (!C -> all(G2))
  a conditional anywhere inside an atom ->  a case split on the atom: x == len(A if C else B) + 1 becomes
                                            (C -> x == len(A) + 1) & (!C -> x == len(B) + 1), except under a 
                                            binder (lambda, comprehension)
  a < b <= c  (a chained comparison)    ->  (a < b) & (b <= c)
  anything else                         ->  a predicate, represented by a letter p#

"Boolean-shaped" means an and/or/not expression, a comparison, True/False, a
quantifier, a call whose name sounds Boolean (all, any, isinstance, hasattr,
is*, has*, can*, startswith, endswith, issubset, ...; the same name test the
Java, JML and Dafny front ends use), or a ternary whose branches are
Boolean-shaped.

For == and !=, we require only one Boolean-shaped side, because in practice 
one of the sides is often return_value, and we can't tell the type of return_value
from the syntax of the assertion. We don't want to turn something like 
`return_value == (a and b)` into a single predicate. 

For <=, we require two Boolean-shaped sides, because this represents an implication
only when both sides are boolean. Almost always, this represents a numeric comparison, 
and we don't want to conflate the numeric comparison with the logical implication.  

The grammar has no quantifiers. A quantifier itself is not scored, but the
Boolean structure inside it is: readers must still process the body, so
all(...) and any(...) over a generator map to the formula of the body (with the
filter as a range), the same way `forall x :: R ==> B` does in Dafny and
`\forall T x; R; B` does in JML. all/any over anything other than a generator
or list comprehension stay predicates.

"""
import ast, copy, io, os, re, shutil, subprocess
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.join(HERE, 'boolean-comprehension-materials', 'jars', 'formula_score_calculator.jar')
HARNESS = os.path.join(HERE, 'sm_java')

AND, OR, IMPLIES, IFF = '&', '|', '->', '<->'
OPEN_QUANTIFIERS = True   # False reproduces the original mapping (quantifiers and chained comparisons as single
                          # predicates); only make_samples_pdf.py --legacy sets it, to show the two side by side.

PROPERTIES = ['NegationCount', 'NegationLevel', 'OperatorNesting', 'OperatorCount', 'ImplicationCount',
              'ImplicationNesting', 'IffCount', 'DistinctOperatorCount', 'NegationNesting', 'AndCount',
              'OrCount', 'SM_Score']


class Formula:
    # A node of a formula tree
    def __init__(self, predicate=None, op=None, children=(), negated=False, chain=False):
        self.predicate = predicate 
        self.op = op
        self.children = list(children)
        self.negated = negated
        self.chain = chain          # a conjunction that came from a chained comparison a < b <= c (no parentheses in the source)

    def negate(self):
        return Formula(self.predicate, self.op, self.children, not self.negated)

    def rename(self, f):
        """The same tree with every predicate text passed through f (used to keep `old(...)` on atoms)."""
        if self.predicate is not None: return Formula(f(self.predicate), None, (), self.negated)
        return Formula(None, self.op, [c.rename(f) for c in self.children], self.negated)


BOOL_LITERALS = {'True', 'False', 'true', 'false'}

def literal(value):
    return Formula(predicate='True' if value else 'False')

def is_literal(f, value):
    """f is a bare Boolean literal that means `value` (a negated literal means the opposite)."""
    if f.predicate not in BOOL_LITERALS: return False
    return ((f.predicate.lower() == 'true') != f.negated) == value

SIMPLIFY_LITERALS = os.environ.get('SM_SIMPLIFY_LITERALS', '1') != '0'
GUARD_ONCE = os.environ.get('SM_GUARD_ONCE', '0') == '1'   # set SM_GUARD_ONCE=1 to count a compound if-then-else guard once (sensitivity check)   # set SM_SIMPLIFY_LITERALS=0 to keep Boolean literals as predicates (sensitivity check)

def conditional(c, a, b):
    """C ? A : B  ->  (C -> A) & (!C -> B), simplified when a branch is a Boolean literal."""
    if not SIMPLIFY_LITERALS: return Formula(op=AND, children=[Formula(op=IMPLIES, children=[c, a]), Formula(op=IMPLIES, children=[c.negate(), b])])
    if is_literal(a, True) and is_literal(b, False): return c
    if is_literal(a, False) and is_literal(b, True): return c.negate()
    if is_literal(b, True):  return Formula(op=IMPLIES, children=[c, a])
    if is_literal(b, False): return Formula(op=AND, children=[c, a])
    if is_literal(a, True):  return Formula(op=OR, children=[c, b])
    if is_literal(a, False): return Formula(op=AND, children=[c.negate(), b])
    if GUARD_ONCE and c.predicate is None:                                   # sensitivity check: a compound guard is comprehended once;
        c2 = Formula(predicate='guard:' + to_formula(c))                       # the else-branch sees it as a single predicate
        return Formula(op=AND, children=[Formula(op=IMPLIES, children=[c, a]), Formula(op=IMPLIES, children=[c2.negate(), b])])
    return Formula(op=AND, children=[Formula(op=IMPLIES, children=[c, a]), Formula(op=IMPLIES, children=[c.negate(), b])])

def simplify(f):
    """Remove Boolean literals from a formula tree: X & True -> X, X | True -> True, True -> X -> X,
    X -> True -> True, X -> False -> !X, X <-> True -> X, X <-> False -> !X (and the symmetric cases)."""
    if f.predicate is not None or not SIMPLIFY_LITERALS: return f
    kids = [simplify(k) for k in f.children]
    if f.op in (AND, OR):
        absorbing, neutral = (False, True) if f.op == AND else (True, False)
        if any(is_literal(k, absorbing) for k in kids): res = literal(absorbing)
        else:
            kids = [k for k in kids if not is_literal(k, neutral)]
            res = literal(neutral) if not kids else kids[0] if len(kids) == 1 else Formula(op=f.op, children=kids, chain=f.chain)
    elif f.op == IMPLIES:
        a, b = kids
        if is_literal(a, True): res = b
        elif is_literal(a, False) or is_literal(b, True): res = literal(True)
        elif is_literal(b, False): res = a.negate()
        else: res = Formula(op=IMPLIES, children=[a, b])
    else:                                                                  # IFF
        a, b = kids
        if is_literal(b, True): res = a
        elif is_literal(b, False): res = a.negate()
        elif is_literal(a, True): res = b
        elif is_literal(a, False): res = b.negate()
        else: res = Formula(op=IFF, children=[a, b])
    return res.negate() if f.negated else res


# Python expression -> formula tree

# A call whose name sounds Boolean, the Python counterpart of BOOL_METHOD_NAME in sm_java.py (shared by the JML and Dafny front ends):
# builtins all/any/isinstance/issubclass/callable/hasattr/bool and methods is*/has*/can*/startswith/endswith/issubset/issuperset/isdisjoint.
BOOL_CALL_NAME = re.compile(r'^(all|any|isinstance|issubclass|callable|hasattr|bool|is[a-z_]*|has[a-z_]*|can[a-z_]*|startswith|endswith|issubset|issuperset|isdisjoint)$')

def is_boolean_call(node):
    if not isinstance(node, ast.Call): return False
    name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
    return bool(BOOL_CALL_NAME.match(name))

def is_boolean_shaped(node):
    return isinstance(node, (ast.BoolOp, ast.Compare)) \
        or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)) \
        or is_boolean_call(node) \
        or (isinstance(node, ast.Constant) and isinstance(node.value, bool)) \
        or (isinstance(node, ast.IfExp) and is_boolean_shaped(node.body) and is_boolean_shaped(node.orelse))


def predicate(node):
    return Formula(predicate=ast.unparse(node))


def to_tree(node):
    # Apply mapping rules
    if isinstance(node, ast.BoolOp):                                   # a and b and c  /  a or b
        op = AND if isinstance(node.op, ast.And) else OR
        children = []
        for v in node.values:
            f = to_tree(v)
            children += f.children if (op == AND and f.chain and not f.negated) else [f]   # a and b < c <= d: three conjuncts
        return Formula(op=op, children=children)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):  # not a
        return to_tree(node.operand).negate()

    if isinstance(node, ast.IfExp):                                    # A if C else B
        return conditional(to_tree(node.test), to_tree(node.body), to_tree(node.orelse))

    if OPEN_QUANTIFIERS and isinstance(node, ast.Compare) and len(node.ops) > 1:   # a < b <= c  ->  (a < b) & (b <= c)
        operands = [node.left] + node.comparators
        pairs = [ast.Compare(left=operands[i], ops=[node.ops[i]], comparators=[operands[i + 1]]) for i in range(len(node.ops))]
        return Formula(op=AND, children=[to_tree(p) for p in pairs], chain=True)

    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right, op = node.left, node.comparators[0], node.ops[0]
        if isinstance(op, (ast.Eq, ast.NotEq)):
            for x, y in ((left, right), (right, left)):                # X == True  /  X == False
                if isinstance(y, ast.Constant) and isinstance(y.value, bool):
                    x = to_tree(x)
                    return x if (y.value is True) == isinstance(op, ast.Eq) else x.negate()
            if is_boolean_shaped(left) or is_boolean_shaped(right):    # A == B  ->  A <-> B
                tree = Formula(op=IFF, children=[to_tree(left), to_tree(right)])
                return tree if isinstance(op, ast.Eq) else tree.negate()
        if isinstance(op, ast.LtE) and is_boolean_shaped(left) and is_boolean_shaped(right):   # A <= B  ->  A -> B
            return Formula(op=IMPLIES, children=[to_tree(left), to_tree(right)])

    if OPEN_QUANTIFIERS and isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('all', 'any') \
            and len(node.args) == 1 and isinstance(node.args[0], ast.IfExp) \
            and all(isinstance(g, (ast.GeneratorExp, ast.ListComp)) for g in (node.args[0].body, node.args[0].orelse)):   # all(G1 if C else G2)
        test = node.args[0]
        quantified = lambda g: ast.Call(func=node.func, args=[g], keywords=[])
        return conditional(to_tree(test.test), to_tree(quantified(test.body)), to_tree(quantified(test.orelse)))

    if OPEN_QUANTIFIERS and isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('all', 'any') \
            and len(node.args) == 1 and isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp)):   # all(B for x in xs if R)
        body = to_tree(node.args[0].elt)
        ifs = [to_tree(c) for g in node.args[0].generators for c in g.ifs]
        if not ifs:
            return body
        rng = ifs[0] if len(ifs) == 1 else Formula(op=AND, children=ifs)
        return Formula(op=IMPLIES if node.func.id == 'all' else AND, children=[rng, body])

    if OPEN_QUANTIFIERS:
        cond = first_conditional(node)
        if cond is not None:                                               # x == len(A if C else B): a case split on the atom
            test = ast.unparse(cond.test)
            return conditional(to_tree(cond.test), to_tree(resolve(node, test, True)), to_tree(resolve(node, test, False)))
    return predicate(node)


BINDERS = (ast.Lambda, ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)

def first_conditional(node):
    """The first conditional expression inside `node` (not node itself) that is not under a binder, or None."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.IfExp): return child
        if not isinstance(child, BINDERS):
            found = first_conditional(child)
            if found is not None: return found
    return None

def resolve(node, test, value):
    """A copy of `node` in which every conditional whose condition is `test` is replaced by its
    then-branch (value True) or else-branch (value False): one decision resolves every occurrence."""
    class Resolve(ast.NodeTransformer):
        def visit_IfExp(self, n):
            self.generic_visit(n)
            return (n.body if value else n.orelse) if ast.unparse(n.test) == test else n
    return Resolve().visit(copy.deepcopy(node))

DECIDED = {}   # conditions already decided while hoisting (text -> True/False), shared with the Java/JML/Dafny front ends


def parse(expression):
    node = ast.parse(expression.strip(), mode='eval').body
    if isinstance(node, ast.Tuple) and node.elts:                      # `cond, "message"`, or a stray trailing comma `cond,`
        node = node.elts[0]
    return to_tree(node)


# Step 2: formula tree -> propositional syntax

def to_formula(tree, names=None):
    if names is None: tree, names = simplify(tree), {}                   # literals are simplified away once, at the top
    if tree.predicate is not None:
        names.setdefault(tree.predicate, f'p{len(names) + 1}')
        body = names[tree.predicate]
    else:
        body = '(' + f' {tree.op} '.join(to_formula(child, names) for child in tree.children) + ')'
    return ('!' if tree.negated else '') + body


# Score with shevrin + maoz artifact

def find_java():
    java_home = os.environ.get('JAVA_HOME')
    candidates = [os.path.join(java_home, 'bin', 'java') if java_home else None,
                  '/opt/homebrew/opt/openjdk/bin/java', '/usr/local/opt/openjdk/bin/java', shutil.which('java')]
    for java in candidates:
        if java and os.path.exists(java):
            try:
                if subprocess.run([java, '-version'], capture_output=True).returncode == 0:
                    return java
            except OSError:
                pass
    return None


def artifact_metrics(formulas):
    java = find_java()
    if java is None or not os.path.exists(os.path.join(HARNESS, 'SMMetrics.class')):
        raise RuntimeError('Java or sm_java/SMMetrics.class not found: see the Shevrin & Maoz setup in README.md')
    text = '\n'.join('' if pd.isna(f) else f for f in formulas) + '\n'
    result = subprocess.run([java, '-cp', f'{JAR}{os.pathsep}{HARNESS}', 'SMMetrics'],
                            input=text, capture_output=True, text=True, check=True)
    return pd.read_csv(io.StringIO(result.stdout), sep='\t', skip_blank_lines=False)



def explain(expression):
    """Print the expression, its Python syntax tree, and the formula it maps to."""
    node = ast.parse(expression.strip(), mode='eval').body
    print(f'\n{expression.strip()}\n{ast.dump(node, indent=2)}\n=> {to_formula(to_tree(node))}')


def sm_table(expressions, show=False):
    # SM_Formula, the 11 properties, SM_Score. Invalid Python -> NaN.
    # show=True prints each expression, its syntax tree and its formula.
    formulas = []
    for expression in expressions:
        try:
            if show: explain(expression)
            formulas.append(to_formula(parse(expression)))
        except Exception: formulas.append(np.nan)
    table = pd.DataFrame({'SM_Formula': formulas})
    table[PROPERTIES] = artifact_metrics(table.SM_Formula)[PROPERTIES].values
    return table


if __name__ == '__main__':
    scores = artifact_metrics(pd.Series(['((!a & !b & !c)->d)', '(a|b|c|d)'])).SM_Score.round(2).tolist()
    assert scores == [21.26, 11.42], scores
    print('artifact reproduces the README examples (21.26, 11.42)')
    print(sm_table(['return_value == (a and not b) if c else len(xs) > 0']).to_string())
