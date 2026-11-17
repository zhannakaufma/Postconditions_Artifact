"""
This file does the same thing as shevrin_maoz_metrics.py but for java. 

Mapping rules:
  && / || / !                           ->  & / | / !
  & / | with two Boolean-shaped sides   ->  & / | 
  C ? A : B  (in Boolean position)      ->  (C -> A) & (!C -> B)   (as in Python: the branches are Boolean by typing)
  A == B  with a Boolean-shaped side    ->  A <-> B
  A != B  with a Boolean-shaped side    ->  !(A <-> B)
  A ^ B  with two Boolean-shaped sides  ->  !(a <-> b)
  X == true  /  X == false              ->  X  /  !X
  s.allMatch(x -> B) / anyMatch         ->  B          (the reader still parses the body)
  s.noneMatch(x -> B)                   ->  !B
  s.filter(x -> R).allMatch(x -> B)     ->  R -> B     (a filter is a range; anyMatch: R & B, noneMatch: R -> !B)
  a conditional anywhere inside an atom ->  a case split on the atom: x.equals(C ? A : B) becomes
                                            (C -> x.equals(A)) & (!C -> x.equals(B)), except inside a lambda
  anything else                         ->  a predicate, represented by a letter p#

"Boolean-shaped" means a comparison, an instanceof, an &&/||/! expression,
true/false, a ternary whose branches are both Boolean-shaped, or a call to a
method whose name sounds Boolean (BOOL_METHOD_NAME below: equals, contains,
isEmpty, isX, hasX, canX, allMatch, ...).  
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libs.shevrin_maoz_metrics import Formula, AND, OR, IMPLIES, IFF, conditional, DECIDED

BOOL_METHOD_NAME = re.compile(r'^(equals|contains\w*|isEmpty|startsWith|endsWith|matches|allMatch|anyMatch|noneMatch|isInstance|is[A-Z]\w*|has[A-Z]\w*|can[A-Z]\w*)$')
COMPARISON = {'==', '!=', '<', '>', '<=', '>='}
OPEN_QUANTIFIERS = True   # see libs/shevrin_maoz_metrics.py


def _parser():
    import tree_sitter_java
    from tree_sitter import Language, Parser
    return Parser(Language(tree_sitter_java.language()))


def _expression(expr):
    """Parse a bare Java expression by wrapping it in a method; returns (node, source bytes)."""
    code = ('class X { boolean f() { return ' + expr.strip().rstrip(';') + '; } }').encode()
    root = _parser().parse(code).root_node
    if root.has_error:
        raise ValueError('tree-sitter reports a syntax error')
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == 'return_statement':
            return n.named_children[0], code
        stack.extend(n.children)
    raise ValueError('no expression found')


def _operator(n):
    """The operator token of a binary or unary expression node."""
    return next((c.type for c in n.children if not c.is_named), None)


def is_boolean_shaped(n, code):
    if n.type == 'parenthesized_expression': return is_boolean_shaped(n.named_children[0], code)
    if n.type == 'unary_expression': return _operator(n) == '!'
    if n.type == 'binary_expression':
        op = _operator(n)
        if op in ('&', '|', '^'): return is_boolean_shaped(n.named_children[0], code) and is_boolean_shaped(n.named_children[1], code)
        return op in COMPARISON | {'&&', '||'}
    if n.type == 'instanceof_expression': return True
    if n.type in ('true', 'false'): return True
    if n.type == 'ternary_expression':
        return is_boolean_shaped(n.named_children[1], code) and is_boolean_shaped(n.named_children[2], code)
    if n.type == 'method_invocation':
        name = n.child_by_field_name('name')
        return bool(BOOL_METHOD_NAME.match(code[name.start_byte:name.end_byte].decode()))
    return False


def parse_java(expr):
    """Java assert expression -> formula tree."""
    node, code = _expression(expr)
    text = lambda n: code[n.start_byte:n.end_byte].decode()

    def conv(n):
        if n.type == 'parenthesized_expression':
            return conv(n.named_children[0])
        if n.type == 'unary_expression' and _operator(n) == '!':
            return conv(n.named_children[0]).negate()
        if n.type == 'binary_expression':
            op = _operator(n); left, right = n.named_children
            logical = op in ('&&', '||') or (op in ('&', '|') and is_boolean_shaped(left, code) and is_boolean_shaped(right, code))
            if logical:                                                        # & and | on Booleans are the same connectives
                # tree-sitter nests `a && b && c` to the left; without parentheses that is one group
                lf = conv(left)
                children = lf.children if (left.type == 'binary_expression' and _operator(left) == op) else [lf]
                return Formula(op=AND if op in ('&&', '&') else OR, children=children + [conv(right)])
            if op == '^' and is_boolean_shaped(left, code) and is_boolean_shaped(right, code):   # xor on Booleans is !(a <-> b)
                return Formula(op=IFF, children=[conv(left), conv(right)]).negate()
            if op in ('==', '!='):
                for x, y in ((left, right), (right, left)):                  # X == true / X == false
                    if y.type in ('true', 'false'):
                        fx = conv(x)
                        return fx if (y.type == 'true') == (op == '==') else fx.negate()
                if is_boolean_shaped(left, code) or is_boolean_shaped(right, code):   # A == B -> A <-> B
                    t = Formula(op=IFF, children=[conv(left), conv(right)])
                    return t if op == '==' else t.negate()
        if n.type == 'ternary_expression':                                       # conv only reaches Boolean positions, so the branches are Boolean
            c, a, b = n.named_children
            return conditional(conv(c), conv(a), conv(b))
        if n.type == 'method_invocation':                                        # allMatch(x -> B): the body B
            name = text(n.child_by_field_name('name'))
            args = n.child_by_field_name('arguments').named_children
            if OPEN_QUANTIFIERS and name in ('allMatch', 'anyMatch', 'noneMatch') and len(args) == 1 and args[0].type == 'lambda_expression':
                body = args[0].child_by_field_name('body')
                if body.type != 'block':
                    f = conv(body).negate() if name == 'noneMatch' else conv(body)
                    receiver = n.child_by_field_name('object')                                     # s.filter(x -> R).allMatch(...)
                    if receiver is not None and receiver.type == 'method_invocation' and text(receiver.child_by_field_name('name')) == 'filter':
                        fargs = receiver.child_by_field_name('arguments').named_children
                        if len(fargs) == 1 and fargs[0].type == 'lambda_expression' and fargs[0].child_by_field_name('body').type != 'block':
                            rng = conv(fargs[0].child_by_field_name('body'))
                            return Formula(op=AND if name == 'anyMatch' else IMPLIES, children=[rng, f])
                    return f
        if OPEN_QUANTIFIERS:
            cond = first_conditional(n)
            if cond is not None:                                                     # x.equals(C ? A : B): a case split on the atom
                c, a, b = cond.named_children
                key = ' '.join(text(c).split())
                branch = lambda br: parse_java(code[n.start_byte:cond.start_byte].decode() + text(br) + code[cond.end_byte:n.end_byte].decode())
                if key in DECIDED: return branch(a if DECIDED[key] else b)          # this condition was decided by an enclosing split
                def decided(br, value):
                    DECIDED[key] = value
                    try: return branch(br)
                    finally: del DECIDED[key]
                return conditional(conv(c), decided(a, True), decided(b, False))
        return Formula(predicate=text(n))

    return conv(node)


def first_conditional(n):
    """The first ternary inside `n` (not n itself) that is not inside a lambda, or None."""
    for child in n.named_children:
        if child.type == 'ternary_expression': return child
        if child.type != 'lambda_expression':
            found = first_conditional(child)
            if found is not None: return found
    return None


if __name__ == '__main__':
    from libs.shevrin_maoz_metrics import to_formula
    for t in ['returnValue == null || returnValue instanceof Integer || returnValue instanceof Long',
              '!returnValue || ("prototype".equals(name) && type.toObjectType() != null)',
              '(_accessor.getValue(bean) == null) == (returnValue == null)',
              'val != null ? returnValue != null : true',
              'returnValue.getItems().stream().allMatch(item -> isSeriesVisibleInLegend(item.getSeriesIndex()))',
              'returnValue == true && (dec == null || dec instanceof BigDecimal)',
              '(a && b) && c']:
        print(f'{t[:70]:72s} => {to_formula(parse_java(t))}')
