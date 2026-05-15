from lark import Lark

formula_grammar = r"""
    ?start: assignment+

    assignment: identifier ":" expression

    ?expression: function
            | reference
            | identifier
            | NUMBER

    function: FUNC_NAME "(" [expression ("," expression)*] ")"

    reference: "{" (attribute | identifier)+ "}"

    attribute: "T(" (CNAME | STRING_QUOTED) ")" -> table
            | "R(" INT ")"                     -> row
            | "C(" INT ")"                     -> column

    identifier: CNAME

    // Terminals

    FUNC_NAME.2: "SUM" | "PROD" | "DIV"
    T_START.3: "T("
    R_START.3: "R("
    C_START.3: "C("
    STRING_QUOTED: /"[^"\\]*"/  // Supports table names with spaces if needed

    %import common.CNAME
    %import common.NUMBER
    %import common.INT
    %import common.WS
    %ignore WS
"""

parser = Lark(formula_grammar, parser="lalr")
