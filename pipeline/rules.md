Shevrin and Maoz's score estimates how hard a propositional Boolean formula is to read: abstract predicates `p1`, `p2`, ... joined by `&`, `|`, `!`, `->` and `<->`. Code is not written that way. A postcondition mixes its Boolean structure with arithmetic, calls, comparisons, conditionals and quantifiers, so before it can be scored, every such construct has to be mapped to the formula model. The rules below apply this mapping consistently across languages. Predicates are numbered in order of appearance. Each example shows a postcondition, its translation and its score, with every predicate and the source text it stands for in the same color.

- **Connectives.** `and`, `or`, `not` (and `&&`, `||`, `!`) become `&`, `|`, `!`. Grouping and nesting are preserved: `a and (b or c)` is `p1 & (p2 | p3)`.
- **Conditional expressions.** An expression that picks one of two values by a condition: `A if C else B` in Python, `C ? A : B` in Java and JML, `if C then A else B` in Dafny. When `A` and `B` are Boolean it reads "if C then A, and if not C then B".
    `A if C else B` becomes `(C -> A) & (!C -> B)`, i.e. `(p1 -> p2) & (!p1 -> p3)`.
- **Equality between Booleans.** `A == B` where either side is Boolean (a comparison, a connective, a quantifier, a literal, an `isinstance`/`instanceof`, or a call whose name sounds Boolean such as `isEmpty`, `startswith`, `has...`) is "A if and only if B": `A <-> B`, i.e. `p1 <-> p2`; `A != B` is `!(A <-> B)`, i.e. `!(p1 <-> p2)`. 
- **Implication written as `<=`** (Python only). `A <= B` with two Boolean sides is `A -> B`, i.e. `p1 -> p2`.
- **Quantifiers.** Quantifiers are made transparent since readers need to comprehend what's inside them.
    `all(B for x in xs)`, `forall x :: B`, `\forall T x; B` and `allMatch(x -> B)` all become `B`, i.e. `p1` when `B` is a single comparison; so do `any`, `exists` and `anyMatch`.
    `noneMatch(x -> B)` becomes `!B`, i.e. `!p1`.
- **Restricted quantifiers.** A condition `R` that restricts which elements are quantified (`if R` in a Python generator, a JML range, Dafny's `| R`, a Java stream `filter(x -> R)`) is kept.
    Under all / forall / allMatch it becomes `R -> B`, i.e. `p1 -> p2`.
    Under any / exists / anyMatch it becomes `R & B`,  i.e. `p1 & p2`.
    Under noneMatch it becomes `R -> !B`, i.e. `p1 -> !p2`.
- **A conditional between two quantifiers.** `all(G1 if C else G2)` becomes `(C -> all(G1)) & (!C -> all(G2))`, i.e. `(p1 -> p2) & (!p1 -> p3)`.
- **Chained comparisons.** `a < b <= c` is two comparisons: `(a < b) & (b <= c)`, i.e. `p1 & p2`. If the chain already sits inside an `and`, the two comparisons join that `and`.
- **Conditionals inside a predicate.** A conditional expression anywhere inside a predicate splits the predicate into one case per branch.
    `x == len(A if C else B) + 1` becomes `(C -> x == len(A) + 1) & (!C -> x == len(B) + 1)`, i.e. `(p1 -> p2) & (!p1 -> p3)`.
    `(a if C else b) + (c if C else d) == n` has one condition, `C`, in two places, so there are only 2 branches: `(C -> a + c == n) & (!C -> b + d == n)`, i.e. `(p1 -> p2) & (!p1 -> p3)`.
    Exception: inside a quantifier body, a lambda or a comprehension the conditional may depend on the bound variable, so it stays inside the predicate: `sum(1 if x > 0 else 0 for x in xs) == n` is `p1`.
- **Boolean literals.** Shevrin and Maoz's formulas have no constants (every atom is a propositional variable), so a literal `True` or `False` cannot be a predicate. It is removed by the usual identities:
    `X == True` is `X`, i.e. `p1`; `X == False` is `!X`, i.e. `!p1`. In Python, `X is True` and `X is False` are read the same way.
    `A if C else True` is `C -> A`, i.e. `p1 -> p2`; `A if C else False` is `C & A`, i.e. `p1 & p2`; `True if C else B` is `C | B`, i.e. `p1 | p2`.
    `X and True` is `X`, i.e. `p1`.
    A postcondition that is nothing but a literal has no formula at all; it is counted as one predicate, the lowest possible score. `X or True` is always true, so it collapses to a bare literal.
- **Old values and local names.** `old(E)` / `\old(E)` with Boolean structure inside is translated as `E`, with `old` kept on each predicate: `old(a and b)` becomes `old(a) & old(b)`, i.e. `p1 & p2`; a Dafny `var x := e; B` is translated as `B`.
- **Everything else is a predicate:** arithmetic, calls, field accesses, single comparisons, and a filter inside a value-building expression such as `sorted(... if R)`, `sum(... if R)` or a set or list comprehension.
