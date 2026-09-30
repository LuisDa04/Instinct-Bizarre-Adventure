from instinct.frontend.errors import SemanticError
from instinct.frontend.parser import parse
from instinct.frontend.resolver import ResolvedProgram, resolve
from instinct.frontend.scanner import scan

HEADER = (
    "creature Uruk\nfaction isengard\nhealth 80\nvision 6\nlifespan 400\nstart:\n"
)


def resolve_ok(source: str) -> ResolvedProgram:
    parsed = parse(scan(source).tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.errors == []
    assert result.resolved is not None
    return result.resolved


def resolve_errors(source: str) -> list[SemanticError]:
    parsed = parse(scan(source).tokens)
    assert parsed.errors == []
    assert parsed.program is not None
    result = resolve(parsed.program)
    assert result.resolved is None
    return result.errors


def test_valid_program_resolves_header_values() -> None:
    resolved = resolve_ok(HEADER + "wait(1)\n")
    assert resolved.name == "Uruk"
    assert resolved.faction == "isengard"
    assert resolved.health == 80
    assert resolved.vision == 6
    assert resolved.lifespan == 400


def test_labels_resolve_to_instruction_indices() -> None:
    resolved = resolve_ok(HEADER + "goto end\nend:\nwait(1)\n")
    assert resolved.labels == {"start": 0, "end": 2}


def test_header_keys_may_come_in_any_order_after_creature() -> None:
    resolved = resolve_ok(
        "creature Uruk\nlifespan 400\nvision 6\nhealth 80\nfaction x\nstart:\nwait(1)\n"
    )
    assert (resolved.health, resolved.vision, resolved.lifespan) == (80, 6, 400)


def test_first_line_must_be_creature() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "faction x\ncreature Uruk\nhealth 80\nvision 6\nlifespan 400\nstart:\nwait(1)\n"
        )
    ] == [(1, "la primera línea debe ser 'creature Nombre'")]


def test_missing_header_key_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 80\nlifespan 400\nstart:\nwait(1)\n"
        )
    ] == [(1, "falta la clave 'vision' en la cabecera")]


def test_empty_file_reports_every_missing_key_and_start() -> None:
    assert [
        (error.line, error.message) for error in resolve_errors("")
    ] == [
        (1, "falta la clave 'creature' en la cabecera"),
        (1, "falta la clave 'faction' en la cabecera"),
        (1, "falta la clave 'health' en la cabecera"),
        (1, "falta la clave 'vision' en la cabecera"),
        (1, "falta la clave 'lifespan' en la cabecera"),
        (1, "falta la etiqueta 'start:'"),
    ]


def test_unknown_header_key_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 80\nvision 6\nlifespan 400\nspeed 5\nstart:\nwait(1)\n"
        )
    ] == [(6, "clave de cabecera desconocida 'speed'")]


def test_duplicate_header_key_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 80\nhealth 90\nvision 6\nlifespan 400\nstart:\nwait(1)\n"
        )
    ] == [(4, "clave de cabecera duplicada 'health'")]


def test_zero_or_negative_header_values_error() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 0\nvision 0\nlifespan -1\nstart:\nwait(1)\n"
        )
    ] == [
        (3, "health debe ser mayor que 0"),
        (4, "vision debe ser mayor o igual que 1"),
        (5, "lifespan debe ser mayor que 0"),
    ]


def test_header_values_with_wrong_type_error() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature 5\nfaction x\nhealth fast\nvision 6\nlifespan 400\nstart:\nwait(1)\n"
        )
    ] == [
        (1, "valor de cabecera inválido"),
        (3, "valor de cabecera inválido"),
    ]


def test_missing_start_label_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 80\nvision 6\nlifespan 400\nwander:\nwait(1)\n"
        )
    ] == [(1, "falta la etiqueta 'start:'")]


def test_duplicate_label_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "flee:\nwait(1)\nflee:\nwait(1)\n")
    ] == [(9, "etiqueta duplicada 'flee'")]


def test_jump_to_unknown_label_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "goto nowhere\n")
    ] == [(7, "salto a etiqueta inexistente 'nowhere'")]


def test_conditional_jump_to_unknown_label_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "if health < 20 goto flee\n")
    ] == [(7, "salto a etiqueta inexistente 'flee'")]


def test_assign_to_perception_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "health = 5\n")
    ] == [(7, "no se puede asignar a la percepción 'health'")]


def test_assign_to_constant_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "NONE = 1\n")
    ] == [(7, "no se puede asignar a la constante 'NONE'")]


def test_assign_to_function_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "see = 1\n")
    ] == [(7, "no se puede asignar a la función 'see'")]


def test_unknown_action_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "shoot(1, 2)\n")
    ] == [(7, "acción desconocida 'shoot'")]


def test_action_with_wrong_arity_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "wait(1, 2)\n")
    ] == [(7, "la acción 'wait' espera 1 argumento, no 2")]
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "move(1, 0)\n")
    ] == [(7, "la acción 'move' espera 3 argumentos, no 2")]


def test_all_seven_actions_with_exact_arity_resolve() -> None:
    resolve_ok(
        HEADER
        + "wait(1)\nmove(1, 0, 2)\nattack(1, 0, 5)\nconsume(1, 0, 5, 3)\n"
        + "reproduce(1, 0, 20)\nroar(7)\nsay(9)\n"
    )


def test_unknown_function_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "hambre = volar(1)\nwait(1)\n")
    ] == [(7, "función desconocida 'volar'")]


def test_function_with_wrong_arity_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "hambre = see(1)\nwait(1)\n")
    ] == [(7, "la función 'see' espera 2 argumentos, no 1")]


def test_calls_inside_conditions_and_action_args_are_checked() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "if see(x) > 0 goto start\n")
    ] == [(7, "la función 'see' espera 2 argumentos, no 1")]
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "wait(see(1))\n")
    ] == [(7, "la función 'see' espera 2 argumentos, no 1")]


def test_expression_using_see_and_name_resolves() -> None:
    resolve_ok(HEADER + "hambre = see(x + 1, y) + name(0, 0)\nwait(1)\n")


def test_several_errors_are_all_reported_in_order() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(
            "creature Uruk\nfaction x\nhealth 80\nlifespan 400\nstart:\n"
            + "goto nowhere\nshoot(1)\n"
        )
    ] == [
        (1, "falta la clave 'vision' en la cabecera"),
        (6, "salto a etiqueta inexistente 'nowhere'"),
        (7, "acción desconocida 'shoot'"),
    ]


def test_body_with_only_start_resolves() -> None:
    resolved = resolve_ok(HEADER)
    assert resolved.labels == {"start": 0}


def test_backward_jump_to_start_resolves() -> None:
    resolved = resolve_ok(HEADER + "wait(1)\ngoto start\n")
    assert resolved.labels == {"start": 0}


def test_boundary_header_values_resolve() -> None:
    resolved = resolve_ok(
        "creature Uruk\nfaction x\nhealth 1\nvision 1\nlifespan 1\nstart:\nwait(1)\n"
    )
    assert (resolved.health, resolved.vision, resolved.lifespan) == (1, 1, 1)


def test_labels_are_case_sensitive() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "goto Start\n")
    ] == [(7, "salto a etiqueta inexistente 'Start'")]


def test_duplicate_start_label_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "wait(1)\nstart:\nwait(1)\n")
    ] == [(8, "etiqueta duplicada 'start'")]


def test_see_used_as_action_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "see(1, 2)\n")
    ] == [(7, "acción desconocida 'see'")]


def test_wait_used_as_function_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "hambre = wait(1)\nwait(1)\n")
    ] == [(7, "función desconocida 'wait'")]


def test_action_with_no_arguments_errors() -> None:
    assert [
        (error.line, error.message) for error in resolve_errors(HEADER + "wait()\n")
    ] == [(7, "la acción 'wait' espera 1 argumento, no 0")]


def test_function_with_extra_arguments_errors() -> None:
    assert [
        (error.line, error.message)
        for error in resolve_errors(HEADER + "hambre = see(1, 2, 3)\nwait(1)\n")
    ] == [(7, "la función 'see' espera 2 argumentos, no 3")]


def test_spec_example_resolves_end_to_end() -> None:
    resolved = resolve_ok(
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
        "    if enemy_dist > 0 goto hunt\n"
        "    if health > 70 and allies_near < 2 goto breed\n"
        "    if allies_near > 3 goto celebrate\n"
        "wander:\n"
        "    move(random % 3 - 1, random % 3 - 1, 1)\n"
        "    goto start\n"
        "\n"
        "bite:\n"
        "    consume(enemy_dx, enemy_dy, 15, 15)\n"
        "    goto start\n"
        "\n"
        "hunt:\n"
        "    move(enemy_dx, enemy_dy, 2)\n"
        "    goto start\n"
        "\n"
        "flee:\n"
        "    move(-enemy_dx, -enemy_dy, 3)\n"
        "    goto start\n"
        "\n"
        "breed:\n"
        "    # bred in the pits of Isengard\n"
        "    if see(x, y + 1) != GROUND goto wander\n"
        "    reproduce(0, 1, 30)\n"
        "    goto start\n"
        "\n"
        "celebrate:\n"
        '    say("meat is back on the menu")\n'
        '    roar("we are the fighting Uruk-hai")\n'
        "    goto start\n"
    )
    assert resolved.name == "Uruk"
    assert set(resolved.labels) == {
        "start",
        "wander",
        "bite",
        "hunt",
        "flee",
        "breed",
        "celebrate",
    }
