<!-- Context: main@1f95b71 -->
# Repository Context

Last updated: 2026-09-29

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
    ast_nodes.py        frozen AST: Node -> Expr (7) / Stmt (5) + Header/Program
    parser.py           Pratt parser, parse(tokens) -> ParseResult (F2, uncommitted)
    (resolver.py — planned F3)
  lang/                 language runtime: actions/, functions, perceptions, interpreter (F6-F7)
  world/                entities, world rules, perceptions, rng.py (seeded Rng)
  loaders/              .te / .ob / .map / .ins loaders (F4, F8, F9)
  sim/                  engine.py tick loop + cli.py terminal runner (F5, F9)
  ui/                   Pygame app (F10)
tests/                  pytest suite (64 tests: 4 scaffold + 24 scanner + 36 parser)
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
2. `parser.py` builds the AST of `ast_nodes.py`: **top-down recursive descent** for
   statements (5 line forms §2.3) + **Pratt/precedence-climbing** for expressions via
   `_PREFIX`/`_INFIX` tables mapping §2.5 1:1 (`or` < `and` < comparisons < `+ -` <
   `* / %` < unary). `and`/`or` build `Logical` (separate node → short-circuit in F6);
   `not`/`-` share the unary level *above* `*` (spec differs from Python here).
   `parse()` returns `ParseResult(program, errors)` — **panic-mode**: collects several
   `ParseError`s per file, header lines recover per-line to avoid error cascades.
   Syntax only: no semantic checks (F3), no evaluation (F6). Every node carries `line`.
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
- **Layers**: `test_scaffold.py` (content dirs + seeded RNG determinism, 4 tests),
  `test_scanner.py` (tokens, line numbers, lexical error recovery, operator set,
  24 tests incl. edge cases: multi-error lines, unterminated text, lone `!`,
  number/ident splitting, error on last line without trailing newline),
  `test_parser.py` (36 tests: §2.5 precedence trio + `not a == b`, the 5 line forms,
  header extraction, exact line+message for every syntax error, multi-error recovery).
- Tests use inline `.ins` sources — the repo intentionally ships **no** example content
  (spec examples live in `instinct.md`; the professors bring their own at defense).

## Build & Scripts

- `python -m pytest -q` — run the whole suite (must be green before every commit).

## Current Status

- **F0 done**: package scaffold, runtime content dirs, seeded `Rng`, pytest wired.
- **F1 done**: scanner with error recovery; lexer edge cases covered (`main@1f95b71`).
- **F2 done (uncommitted)**: `ast_nodes.py` + Pratt `parser.py` + `tests/test_parser.py`;
  64 tests green. Working tree: `?? ast_nodes.py ?? parser.py ?? test_parser.py`.
- **Next**: F3 — `resolver.py` with the §2.8 semantic checks (header keys/ranges,
  `start:`, duplicate/unknown labels, assignment targets, action/function catalogs
  + arity) + label resolution to instruction indices (I12). F2 stays syntax-only.

## Additional Context Files

- None yet (project is small; everything fits here).
