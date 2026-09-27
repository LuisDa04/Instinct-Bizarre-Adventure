from instinct.frontend.scanner import scan
from instinct.frontend.tokens import TokenType


def types(source: str) -> list[TokenType]:
    return [token.type for token in scan(source).tokens]


def test_empty_source_gives_only_eof() -> None:
    result = scan("")
    assert [token.type for token in result.tokens] == [TokenType.EOF]
    assert result.errors == []


def test_comment_only_line_emits_nothing() -> None:
    result = scan("# just a comment\n")
    assert [token.type for token in result.tokens] == [TokenType.EOF]
    assert result.errors == []


def test_tokens_are_line_terminated() -> None:
    assert types("health 80\nvision 6") == [
        TokenType.IDENT,
        TokenType.INT,
        TokenType.NEWLINE,
        TokenType.IDENT,
        TokenType.INT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]


def test_keywords_are_case_sensitive() -> None:
    assert types("if goto and or not") == [
        TokenType.IF,
        TokenType.GOTO,
        TokenType.AND,
        TokenType.OR,
        TokenType.NOT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]
    assert types("IF If ifx") == [
        TokenType.IDENT,
        TokenType.IDENT,
        TokenType.IDENT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]


def test_numbers_and_identifiers() -> None:
    result = scan("health80 42 0 _home home_2")
    assert result.errors == []
    kinds = [token.type for token in result.tokens]
    assert kinds == [
        TokenType.IDENT,
        TokenType.INT,
        TokenType.INT,
        TokenType.IDENT,
        TokenType.IDENT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]
    values = [token.literal for token in result.tokens if token.type == TokenType.INT]
    assert values == [42, 0]
    names = [token.lexeme for token in result.tokens if token.type == TokenType.IDENT]
    assert names == ["health80", "_home", "home_2"]


def test_text_literals() -> None:
    result = scan('name "" "grass" "AWOOO"')
    assert result.errors == []
    texts = [token for token in result.tokens if token.type == TokenType.TEXT]
    assert [token.literal for token in texts] == ["", "grass", "AWOOO"]


def test_operators() -> None:
    assert types("( ) , : + - * / % < <= > >= == != =") == [
        TokenType.LPAREN,
        TokenType.RPAREN,
        TokenType.COMMA,
        TokenType.COLON,
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.STAR,
        TokenType.SLASH,
        TokenType.PERCENT,
        TokenType.LESS,
        TokenType.LESS_EQUAL,
        TokenType.GREATER,
        TokenType.GREATER_EQUAL,
        TokenType.EQUAL_EQUAL,
        TokenType.BANG_EQUAL,
        TokenType.EQUAL,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]


def test_hash_inside_text_is_not_a_comment() -> None:
    result = scan('say("rock #1") # trailing comment')
    assert result.errors == []
    assert result.tokens[0].type == TokenType.IDENT
    assert [token.type for token in result.tokens if token.type == TokenType.TEXT] == [
        TokenType.TEXT
    ]


def test_trailing_comment_is_dropped() -> None:
    assert types("wait(1)  # nothing") == [
        TokenType.IDENT,
        TokenType.LPAREN,
        TokenType.INT,
        TokenType.RPAREN,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]


def test_line_numbers_are_reported() -> None:
    result = scan("creature Uruk\nfaction isengard\n\nhealth 80\n")
    lines = [token.line for token in result.tokens if token.type != TokenType.EOF]
    assert lines == [1, 1, 1, 2, 2, 2, 4, 4, 4]


def test_unterminated_text_reports_start_line() -> None:
    result = scan('creature X\nsay("oops\nwait(1)\n')
    assert len(result.errors) == 1
    assert result.errors[0].line == 2
    assert "unterminated" in result.errors[0].message
    assert not any(token.type == TokenType.TEXT for token in result.tokens)


def test_unexpected_character_drops_rest_of_line() -> None:
    result = scan("health 80 @ 90\nvision 6\n")
    assert len(result.errors) == 1
    assert result.errors[0].line == 1
    kinds = [token.type for token in result.tokens]
    assert kinds == [TokenType.IDENT, TokenType.INT, TokenType.NEWLINE, TokenType.EOF]


def test_bang_without_equals_is_an_error() -> None:
    result = scan("if a ! b")
    assert len(result.errors) == 1
    assert result.errors[0].line == 1


def test_crlf_line_endings() -> None:
    assert types("health 80\r\nvision 6\r\n") == [
        TokenType.IDENT,
        TokenType.INT,
        TokenType.NEWLINE,
        TokenType.IDENT,
        TokenType.INT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]


def test_whole_creature_source_scans_cleanly() -> None:
    source = (
        "creature Uruk\n"
        "faction isengard\n"
        "health 80\n"
        "vision 6\n"
        "lifespan 400\n"
        "\n"
        "start:\n"
        "    if health < 20 goto flee\n"
        "    move(random % 3 - 1, random % 3 - 1, 1)\n"
        "    goto start\n"
        "flee:\n"
        '    say("meat is back on the menu")\n'
        "    roar(\"we are the fighting Uruk-hai\")\n"
        "    goto start\n"
    )
    result = scan(source)
    assert result.errors == []


def test_label_and_goto_scan() -> None:
    assert types("start:\n    goto start\n") == [
        TokenType.IDENT,
        TokenType.COLON,
        TokenType.NEWLINE,
        TokenType.GOTO,
        TokenType.IDENT,
        TokenType.NEWLINE,
        TokenType.EOF,
    ]
