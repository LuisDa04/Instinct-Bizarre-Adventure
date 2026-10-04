from __future__ import annotations

from dataclasses import dataclass

from .errors import LoadError


@dataclass(frozen=True)
class Entry:
    key: str
    value: str
    line: int


def parse_definition(
    source: str, keyword: str, keys: tuple[str, ...]
) -> tuple[str | None, dict[str, Entry], list[LoadError]]:
    errors: list[LoadError] = []
    significant = [
        (number, text)
        for number, text in enumerate(source.splitlines(), start=1)
        if text.strip() and not text.strip().startswith("#")
    ]
    anchor = significant[0][0] if significant else 1
    if not significant:
        errors.append(LoadError(anchor, f"la primera línea debe ser '{keyword} Nombre'"))
    name = _parse_first(significant[0], keyword, errors) if significant else None
    entries: dict[str, Entry] = {}
    for number, text in significant[1:]:
        _parse_entry(number, text, keys, entries, errors)
    for key in keys:
        if key not in entries:
            errors.append(LoadError(anchor, f"falta la clave {key!r}"))
    return name, entries, errors


def entry_int(entry: Entry | None, errors: list[LoadError]) -> int | None:
    if entry is None:
        return None
    try:
        return int(entry.value)
    except ValueError:
        errors.append(
            LoadError(entry.line, f"el valor de {entry.key!r} debe ser un entero")
        )
        return None


def entry_range(entry: Entry | None, errors: list[LoadError]) -> int | None:
    if entry is None:
        return None
    value = entry_int(entry, errors)
    if value is None:
        return None
    if value < 0:
        errors.append(
            LoadError(entry.line, f"{entry.key} debe ser mayor o igual que 0")
        )
        return None
    return value


def entry_char(entry: Entry | None, errors: list[LoadError]) -> str | None:
    if entry is None:
        return None
    if len(entry.value) != 1:
        errors.append(LoadError(entry.line, "char debe ser un solo carácter"))
        return None
    return entry.value


def _parse_first(
    line: tuple[int, str], keyword: str, errors: list[LoadError]
) -> str | None:
    number, text = line
    tokens = text.split()
    if len(tokens) != 2 or tokens[0] != keyword:
        errors.append(
            LoadError(number, f"la primera línea debe ser '{keyword} Nombre'")
        )
        return None
    return tokens[1]


def _parse_entry(
    number: int,
    text: str,
    keys: tuple[str, ...],
    entries: dict[str, Entry],
    errors: list[LoadError],
) -> None:
    tokens = text.split()
    if len(tokens) != 2:
        errors.append(LoadError(number, "línea inválida"))
        return
    key = tokens[0]
    if key not in keys:
        errors.append(LoadError(number, f"clave desconocida {key!r}"))
    elif key in entries:
        errors.append(LoadError(number, f"clave duplicada {key!r}"))
    else:
        entries[key] = Entry(key=key, value=tokens[1], line=number)
