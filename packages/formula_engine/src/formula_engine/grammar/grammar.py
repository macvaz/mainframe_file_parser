from lark import Lark

formula_grammar = r"""
    ?start: assignment+

    assignment: identifier ":" expression

    ?expression: or_expr

    ?or_expr: and_expr
            | or_expr "OR" and_expr -> or_op

    ?and_expr: comparison
             | and_expr "AND" comparison -> and_op

    ?comparison: sum_expr
                | comparison "==" sum_expr -> eq
                | comparison "!=" sum_expr -> ne
                | comparison "<" sum_expr -> lt
                | comparison "<=" sum_expr -> le
                | comparison ">" sum_expr -> gt
                | comparison ">=" sum_expr -> ge

    ?sum_expr: product
             | sum_expr "+" product -> add
             | sum_expr "-" product -> sub

    ?product: atom
            | product "*" atom -> mul
            | product "/" atom -> div

    ?atom: function
         | reference
         | NUMBER
         | "(" expression ")"

    function: FUNC_NAME "(" [expression ("," expression)*] ")"

    // Column or indicator reference: {FULL_NAME}, {YEAR}, or {other_indicator}
    reference: "{" ref_body "}"

    ?ref_body: identifier
             | attribute+

    attribute: "T(" (CNAME | STRING_QUOTED) ")" -> table
            | "R(" INT ")"                     -> row
            | "C(" INT ")"                     -> column

    identifier: CNAME

    // Terminals

    FUNC_NAME.2: "SUM" | "PROD" | "DIV" | "LEN" | "BETWEEN"
    T_START.3: "T("
    R_START.3: "R("
    C_START.3: "C("
    STRING_QUOTED: /"[^"\\]*"/

    %import common.CNAME
    %import common.NUMBER
    %import common.INT
    %import common.WS
    %ignore WS
"""

parser = Lark(formula_grammar, parser="lalr")
