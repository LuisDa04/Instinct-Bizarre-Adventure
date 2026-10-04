from instinct.compiler.ast_nodes import (
    ActionCall,
    Assign,
    Binary,
    Call,
    Goto,
    Group,
    IfGoto,
    Label,
    Literal,
    Logical,
    Program,
    Unary,
    Variable,
)
from instinct.compiler.errors import ParseError
from instinct.compiler.parser import parse
from instinct.compiler.lexer import scan
from instinct.compiler.tokens import TokenType


def parse_ok(source: str) -> Program:
    result = parse(scan(source).tokens)
    assert result.errors == []
    assert result.program is not None
    return result.program


def parse_errors(source: str) -> list[ParseError]:
    result = parse(scan(source).tokens)
    assert result.program is None
    return result.errors


def test_empty_source_gives_empty_program() -> None:
    program = parse_ok("")
    assert program.header.entries == []
    assert program.body == []


def test_header_collects_five_keys_in_any_order() -> None:
    program = parse_ok(
        "lifespan 400\ncreature Uruk\nvision 6\nhealth 80\nfaction isengard\nstart:\n"
    )
    assert {entry.key: entry.value for entry in program.header.entries} == {
        "lifespan": 400,
        "creature": "Uruk",
        "vision": 6,
        "health": 80,
        "faction": "isengard",
    }
    assert program.header.entries[0].line == 1
    assert [type(statement).__name__ for statement in program.body] == ["Label"]


def test_header_entries_keep_their_lines() -> None:
    program = parse_ok("creature Uruk\n\nhealth 80\nstart:\n")
    assert [(entry.key, entry.line) for entry in program.header.entries] == [
        ("creature", 1),
        ("health", 3),
    ]


def test_negative_header_value_is_kept() -> None:
    program = parse_ok("lifespan -5\nstart:\n")
    assert program.header.entries[0].value == -5


def test_header_without_body_is_allowed() -> None:
    program = parse_ok("creature X\nhealth 80\n")
    assert len(program.header.entries) == 2
    assert program.body == []


def test_label_parses_with_name_and_line() -> None:
    program = parse_ok("start:\nwander:\n")
    assert program.body == [
        Label(name="start", line=1),
        Label(name="wander", line=2),
    ]


def test_goto_parses_with_target() -> None:
    program = parse_ok("start:\n    goto wander\n")
    assert program.body[1] == Goto(label="wander", line=2)


def test_if_goto_parses_condition_and_target() -> None:
    program = parse_ok("start:\n    if health < 20 goto flee\n")
    statement = program.body[1]
    assert isinstance(statement, IfGoto)
    assert statement.label == "flee"
    assert statement.line == 2
    assert statement.condition == Binary(
        left=Variable(name="health", line=2),
        op=TokenType.LESS,
        right=Literal(value=20, line=2),
        line=2,
    )


def test_assign_parses_name_and_value() -> None:
    program = parse_ok("start:\n    home_x = x\n")
    assert program.body[1] == Assign(
        name="home_x", value=Variable(name="x", line=2), line=2
    )


def test_action_call_without_arguments() -> None:
    program = parse_ok("start:\n    wait()\n")
    assert program.body[1] == ActionCall(name="wait", args=[], line=2)


def test_action_call_with_arguments() -> None:
    program = parse_ok("start:\n    move(1, 0, 2)\n")
    assert program.body[1] == ActionCall(
        name="move",
        args=[
            Literal(value=1, line=2),
            Literal(value=0, line=2),
            Literal(value=2, line=2),
        ],
        line=2,
    )


def test_indentation_is_free() -> None:
    program = parse_ok("start:\n\t\tgoto wander\n        wander:\n")
    assert program.body[1] == Goto(label="wander", line=2)


def test_and_binds_tighter_than_or() -> None:
    program = parse_ok("start:\n    x = a or b and c\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Logical(
        left=Variable(name="a", line=2),
        op=TokenType.OR,
        right=Logical(
            left=Variable(name="b", line=2),
            op=TokenType.AND,
            right=Variable(name="c", line=2),
            line=2,
        ),
        line=2,
    )


def test_comparison_binds_tighter_than_and() -> None:
    program = parse_ok("start:\n    x = health < 20 and enemy_dist < 3\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Logical(
        left=Binary(
            left=Variable(name="health", line=2),
            op=TokenType.LESS,
            right=Literal(value=20, line=2),
            line=2,
        ),
        op=TokenType.AND,
        right=Binary(
            left=Variable(name="enemy_dist", line=2),
            op=TokenType.LESS,
            right=Literal(value=3, line=2),
            line=2,
        ),
        line=2,
    )


def test_modulo_binds_tighter_than_minus() -> None:
    program = parse_ok("start:\n    d = random % 3 - 1\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Binary(
        left=Binary(
            left=Variable(name="random", line=2),
            op=TokenType.PERCENT,
            right=Literal(value=3, line=2),
            line=2,
        ),
        op=TokenType.MINUS,
        right=Literal(value=1, line=2),
        line=2,
    )


def test_grouped_comparisons_subtract() -> None:
    program = parse_ok("start:\n    s = (home_x > x) - (home_x < x)\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Binary(
        left=Group(
            inner=Binary(
                left=Variable(name="home_x", line=2),
                op=TokenType.GREATER,
                right=Variable(name="x", line=2),
                line=2,
            ),
            line=2,
        ),
        op=TokenType.MINUS,
        right=Group(
            inner=Binary(
                left=Variable(name="home_x", line=2),
                op=TokenType.LESS,
                right=Variable(name="x", line=2),
                line=2,
            ),
            line=2,
        ),
        line=2,
    )


def test_not_binds_tighter_than_comparison() -> None:
    program = parse_ok("start:\n    n = not a == b\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Binary(
        left=Unary(
            op=TokenType.NOT, operand=Variable(name="a", line=2), line=2
        ),
        op=TokenType.EQUAL_EQUAL,
        right=Variable(name="b", line=2),
        line=2,
    )


def test_unary_minus_binds_tighter_than_star() -> None:
    program = parse_ok("start:\n    m = -x * y\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Binary(
        left=Unary(
            op=TokenType.MINUS, operand=Variable(name="x", line=2), line=2
        ),
        op=TokenType.STAR,
        right=Variable(name="y", line=2),
        line=2,
    )


def test_call_with_nested_expression_arguments() -> None:
    program = parse_ok("start:\n    c = see(x, y + 1) != GROUND\n")
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Binary(
        left=Call(
            callee="see",
            args=[
                Variable(name="x", line=2),
                Binary(
                    left=Variable(name="y", line=2),
                    op=TokenType.PLUS,
                    right=Literal(value=1, line=2),
                    line=2,
                ),
            ],
            line=2,
        ),
        op=TokenType.BANG_EQUAL,
        right=Variable(name="GROUND", line=2),
        line=2,
    )


def test_text_literal_assigns() -> None:
    program = parse_ok('start:\n    s = "meat"\n')
    statement = program.body[1]
    assert isinstance(statement, Assign)
    assert statement.value == Literal(value="meat", line=2)


def test_last_line_without_trailing_newline_parses() -> None:
    program = parse_ok("start:\n    move(0, 0, 1)")
    assert program.body[1] == ActionCall(
        name="move",
        args=[
            Literal(value=0, line=2),
            Literal(value=0, line=2),
            Literal(value=1, line=2),
        ],
        line=2,
    )


def test_bare_identifier_is_an_invalid_line() -> None:
    assert [(error.line, error.message) for error in parse_errors("start:\nfoo")] == [
        (2, "línea inválida")
    ]


def test_goto_without_label_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\ngoto")
    ] == [(2, "se esperaba el nombre de una etiqueta tras 'goto'")]


def test_if_goto_without_label_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nif x goto")
    ] == [(2, "se esperaba el nombre de una etiqueta tras 'goto'")]


def test_if_without_goto_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nif x flee")
    ] == [(2, "se esperaba 'goto' tras la condición")]


def test_incomplete_expression_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nu = 1 +")
    ] == [(2, "se esperaba una expresión")]


def test_unclosed_grouping_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nv = (a")
    ] == [(2, "se esperaba ')' tras la expresión")]


def test_unclosed_call_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nw = f(1,")
    ] == [(2, "se esperaba una expresión")]


def test_trailing_comma_in_call_errors() -> None:
    assert [
        (error.line, error.message)
        for error in parse_errors("start:\nmove(1, 2,)")
    ] == [(2, "se esperaba una expresión")]


def test_trailing_tokens_after_statement_error() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("start:\nx = 1 2")
    ] == [(2, "token inesperado tras la instrucción")]
    assert [
        (error.line, error.message)
        for error in parse_errors("start:\nwait(1) extra")
    ] == [(2, "token inesperado tras la instrucción")]
    assert [
        (error.line, error.message)
        for error in parse_errors("start: extra")
    ] == [(1, "token inesperado tras la instrucción")]


def test_header_without_value_errors() -> None:
    assert [(error.line, error.message) for error in parse_errors("health")] == [
        (1, "valor de cabecera inválido")
    ]


def test_header_with_wrong_value_errors() -> None:
    assert [(error.line, error.message) for error in parse_errors("health = 3")] == [
        (1, "valor de cabecera inválido")
    ]
    assert [(error.line, error.message) for error in parse_errors("health -x")] == [
        (1, "valor de cabecera inválido")
    ]


def test_header_with_extra_tokens_errors() -> None:
    assert [
        (error.line, error.message) for error in parse_errors("health 80 90")
    ] == [(1, "token inesperado tras una entrada de cabecera")]


def test_header_with_non_identifier_key_errors() -> None:
    assert [(error.line, error.message) for error in parse_errors("= 3")] == [
        (1, "se esperaba una clave de cabecera")
    ]


def test_several_errors_are_all_reported() -> None:
    errors = parse_errors(
        "creature Uruk\n"
        "faction\n"
        "health 80\n"
        "start:\n"
        "    if health < goto flee\n"
        "    move(1, 2)\n"
        "    bogus line here\n"
        "    goto start\n"
        "    x =\n"
    )
    assert [(error.line, error.message) for error in errors] == [
        (2, "valor de cabecera inválido"),
        (5, "se esperaba una expresión"),
        (7, "línea inválida"),
        (9, "se esperaba una expresión"),
    ]


def test_complete_creature_parses() -> None:
    program = parse_ok(
        "# uruk.ins\n"
        "creature Uruk\n"
        "faction isengard\n"
        "health 80\n"
        "vision 6\n"
        "lifespan 400\n"
        "\n"
        "start:\n"
        "    if health < 20 goto flee\n"
        "    if enemy_dist == 1 goto bite\n"
        "wander:\n"
        "    move(random % 3 - 1, random % 3 - 1, 1)\n"
        "    goto start\n"
        "bite:\n"
        "    consume(enemy_dx, enemy_dy, 15, 15)\n"
        "    goto start\n"
        "flee:\n"
        "    move(-enemy_dx, -enemy_dy, 3)\n"
        "    goto start\n"
    )
    assert len(program.header.entries) == 5
    assert len(program.body) == 12
    assert program.body[0] == Label(name="start", line=8)
    assert isinstance(program.body[1], IfGoto)
    assert isinstance(program.body[4], ActionCall)
