<!-- Context: main@6a474a9 -->
# Repository Context

Last updated: 2026-09-27

## Tech Stack

- **Language**: Python 3.14 (developed/tested on `Python\pythoncore-3.14-64`)
- **Build Tool**: none yet (pure package)
- **Package Manager**: pip
- **Key Dependencies**:
  - `pytest`: test runner (installed globally, declared in `pyproject.toml` `[tool.pytest.ini_options]`)
  - `pygame`: planned for phase F10 (UI), not yet a dependency

## What This Project Is

An implementation of the **Instinct** language (spec: `instinct.md`, PDF `instinct.pdf`) —
a small creature-programming language plus a 2D tick-based world simulator and a GUI.
Theme: **Instinct Bizarre Adventure** (JoJo's Bizarre Adventure). Written for an
OOP course; the graded criteria are OO design quality (spec §5), not just "it runs".

Mandatory base = spec sections 2–4. All plan decisions are recorded in **`PLAN.md`**
(requirements R1–R19, invariants I1–I15, phases F0–F11, decisions D1–D8).

## Directory Structure

```
instinct/               Python package (phases F1+)
  frontend/             compiler front end (Crafting Interpreters style)
    errors.py           CompileError(line, msg) + LexError/ParseError/SemanticError
    tokens.py           TokenType enum + Token(type, lexeme, literal, line)
    scanner.py          line-oriented scanner, scan(source) -> ScanResult
    (parser.py, ast_nodes.py, resolver.py — planned F2/F3)
  lang/                 language runtime: actions/, functions, perceptions, interpreter (F6-F7)
  world/                entities, world rules, perceptions, rng.py (seeded Rng)
  loaders/              .te / .ob / .map / .ins loaders (F4, F8, F9)
  sim/                  engine.py tick loop + cli.py terminal runner (F5, F9)
  ui/                   Pygame app (F10)
tests/                  pytest suite (20 tests)
terrains/ objects/ maps/ creatures/   runtime content dirs the app loads (spec §4.1), .gitkeep placeholders
PLAN.md                 the project plan (source of truth for decisions)
instinct.md             the specification (do not edit)
```

## Core Architecture

Two-stage front end → tree-walking interpreter (spec §5 forbids a bytecode VM in the base):

1. `scanner.py` turns `.ins` text into tokens. **Line-oriented**: every line with
   tokens ends with a `NEWLINE` token; blank and `#`-comment-only lines emit nothing.
   Lexical errors are *collected* (several per file), each with its line, and the whole
   corrupt line is dropped so tokens never leak into the next line (panic mode).
2. `parser.py` (F2) will build an AST of expression/statement node classes, each
   evaluating itself — a hierarchy, **never** `if tipo == "move"` chains (spec §5).
3. `resolver.py` (F3) performs the compile-time checks of spec §2.8 (header, labels,
   arity, assignment targets) against the catalog of actions/functions/perceptions.
4. `sim/engine.py` owns the RNG, shuffles turn order per tick, refreshes perceptions
   and interprets each creature from its saved program counter (spec §2.7).
   Only the engine talks to the interpreter; UI and CLI are clients of `step()/state()`.

## Conventions & Patterns

- **Errors**: everything compile-time derives from `CompileError(line, message)`; the
  `line` is carried on every `Token` and will be carried on every AST node (spec §1
  requires line numbers on all errors).
- **Naming**: modules snake_case, packages no `__init__` content; English code, Spanish docs.
- **Docs/plan language**: `PLAN.md` and commit bodies in English; spec citations use `§N`.
- **Comments**: none in code (project rule); spec citations live in `PLAN.md`.
- **Commits**: atomic, conventional prefixes (`docs:`, `feat:`, `chore:`), why not what.
- **Content files**: `.ins` creatures, `.te` terrains, `.ob` objects, `.map` maps.

## Testing

- **Framework**: pytest, `testpaths = ["tests"]`, run with `python -m pytest -q`.
- **Layers**: `test_scaffold.py` (content dirs + seeded RNG determinism),
  `test_scanner.py` (tokens, line numbers, lexical error recovery, operator set).
- Tests use inline `.ins` sources — the repo intentionally ships **no** example content
  (spec examples live in `instinct.md`; the professors bring their own at defense).

## Build & Scripts

- `python -m pytest -q` — run the whole suite (must be green before every commit).

## Current Status

- **F0 done**: package scaffold, runtime content dirs, seeded `Rng`, pytest wired.
- **F1 done**: scanner with error recovery.
- **Next**: F2 — AST hierarchy + Pratt parser for spec §2.5 precedence, statements §2.3.
- Nothing committed after `main@6a474a9`.

## Additional Context Files

- None yet (project is small; everything fits here).
