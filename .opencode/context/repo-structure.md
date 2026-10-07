<!-- Context: main@9a6ebbf -->
# Repository Context

Last updated: 2026-10-07

## Tech Stack

- **Language**: Python 3.14.7 (developed/tested on `Python\pythoncore-3.14-64`; `requires-python = ">=3.10"`)
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
  compiler/             compiler front end (Crafting Interpreters style)
    errors.py           CompileError(line, msg) + LexError/ParseError/SemanticError
    tokens.py           TokenType enum + Token(type, lexeme, literal, line)
    lexer.py            line-oriented lexer, scan(source) -> ScanResult
    ast_nodes.py        frozen AST: Node -> Expr (7) / Stmt (5) + Header/Program
    parser.py           Pratt parser, parse(tokens) -> ParseResult
    semantic.py         resolve(program) -> ResolveResult; §2.8 checks + labels to indices
    catalogs.py         single source of truth: ACTION_ARITY, FUNCTION_ARITY,
                        PERCEPTIONS (31), CONSTANTS, HEADER_KEYS (read by F3 and F6/F7)
    (ui/ lang/ as planned; world/, loaders/ and sim/engine done in F4–F5)
  lang/                 language runtime: actions/, functions, perceptions, interpreter (F6-F7)
  world/                entities.py (Entity/Terrain/WorldObject/Creature),
                        world.py (Cell grid, placement, walkable), rng.py (seeded Rng)
  loaders/              errors.py (LoadError), definition.py (shared parser),
                        terrain_loader.py, object_loader.py, registry.py (F4; .map/.ins in F8/F9)
  sim/                  engine.py tick loop (F5 done: Engine + TickReport + WorldSnapshot) + cli.py terminal runner (F9)
  ui/                   Pygame app (F10)
tests/                  pytest suite (160 tests: 4 scaffold + 24 lexer + 36 parser + 35 semantic + 24 world + 24 loaders + 13 engine)
terrains/ objects/ maps/ creatures/   runtime content dirs the app loads (spec §4.1), .gitkeep placeholders
PLAN.md                 the project plan (source of truth for decisions)
instinct.md             the specification (do not edit)
GUIA_AST_PARSER.md      local study guide (plain-Spanish AST+parser walkthrough, gitignored, not pushed)
```

## Core Architecture

Two-stage front end → tree-walking interpreter (spec §5 forbids a bytecode VM in the base):

1. `lexer.py` turns `.ins` text into tokens. **Line-oriented**: every line with
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
3. `semantic.py` (F3) performs the compile-time checks of spec §2.8 that need no
   simulation: header presence/order/ranges, `start:` present, duplicate/unknown
   labels (resolved to body indices, I12), assignment targets (D3: perceptions,
   constants, `see`/`name`), action/function catalog membership + exact arity.
   Collects several `SemanticError`s; `resolved=None` if any. Reads its name/arity
   tables from `catalogs.py` so the interpreter (F6/F7) reuses the same source.
   Types, `dx`/`dy` range and unassigned reads are deliberately NOT checked here:
   §2.8 lists them as execution errors (ictus, F7).
4. `sim/engine.py` (F5 done) owns the single `Rng`, shuffles a snapshot copy of the
   turn order per tick, honors `wait_remaining` and the `_pending` newborn queue
   (spec §2.7 laws 1+8), applies end-of-tick E1→E2→E3→E4 (§3.4) and returns a
   frozen `TickReport`. Turn contents run through the `set_turn_runner()` hook
   (no-op until F6 plugs the interpreter); perception refresh, the 100-line cap
   and the 7 actions are deliberately absent. Only the engine talks to the
   interpreter; UI and CLI are clients of `step()/state()` (`state()` returns a
   frozen `WorldSnapshot` with no live references, no `_cells`, no RNG).

## Conventions & Patterns

- **Errors**: everything compile-time derives from `CompileError(line, message)`; the
  `line` is carried on every `Token` and will be carried on every AST node (spec §1
  requires line numbers on all errors).
- **Error messages are written in Spanish** (project rule, see
  `error-messages.md`). The reader of a message is the end user reading the app's logs
  (spec §4.1) or the professor at the defense (spec §6). Identifiers stay English.
  `CompileError` wraps as `línea N: mensaje` — keep the `línea` prefix untranslated.
- **Naming**: modules snake_case, packages no `__init__` content; English identifiers,
  Spanish docs **and** Spanish error text.
- **Docs/plan language**: `PLAN.md` and commit bodies in English; spec citations use `§N`.
- **Comments**: every class and method carries a Spanish docstring (hover-readable:
  one-line summary first, `Args:`/`Returns:` only when non-obvious); spec
  citations live in `PLAN.md`, never in docstrings.
- **Commits**: atomic, conventional prefixes (`docs:`, `feat:`, `chore:`), why not what.
- **Content files**: `.ins` creatures, `.te` terrains, `.ob` objects, `.map` maps.

## Testing

- **Framework**: pytest, `testpaths = ["tests"]`, run with `python -m pytest -q`.
- **Layers**: `test_scaffold.py` (content dirs + seeded RNG determinism, 4 tests),
  `test_scanner.py` (tokens, line numbers, lexical error recovery, operator set,
  24 tests incl. edge cases: multi-error lines, unterminated text, lone `!`,
  number/ident splitting, error on last line without trailing newline),
`test_parser.py` (36 tests: §2.5 precedence trio + `not a == b`, the 5 line forms,
    header extraction, exact line+message for every syntax error, multi-error recovery),
  `test_resolver.py` (35 tests: one per §2.8 compile error with exact line+message,
    label→index resolution, header order/duplicate/unknown-key rules, calls checked
    inside conditions and action args, case-sensitivity, boundary values, and the
    full §2.1 uruk example resolving end to end),
  `test_world.py` (24 tests: I1/I2/I3 per placement call, walkable rules, hit
    clamping at 0, regen capped at max, prototype cloning, creature header/age),
  `test_loaders.py` (24 tests: Anexo grass/rock end to end, one per loader error
    with exact line+message, `char #` not eaten as comment, I14 char clash,
    partial-failure directory scan via `tmp_path`),
  `test_engine.py` (13 tests: E1–E4 order, L1 shuffle determinism incl. order,
    L8 newborn waits a tick incl. mid-tick queueing, sleeping still ages,
    `state()` read-only and frozen; adds no user-facing messages).
- Tests assert **exact** `(line, message)` pairs, so every message change breaks the
  suite on purpose — that is the point: it makes message wording a reviewed decision.
- Tests use inline `.ins` sources — the repo intentionally ships **no** example content
  (spec examples live in `instinct.md`; the professors bring their own at defense).

## Build & Scripts

- `python -m pytest -q` — run the whole suite (must be green before every commit).

## Current Status

- **F0 done**: package scaffold, runtime content dirs, seeded `Rng`, pytest wired.
- **F1 done**: scanner with error recovery; lexer edge cases covered (`main@01d2476`).
- **F2 done** (`75b8c21`, pushed): `ast_nodes.py` + Pratt `parser.py` +
  `tests/test_parser.py`; 64 tests green.
- **Error messages now Spanish** (all 21 existing scanner/parser messages translated;
  tests updated in lockstep; catalog in `error-messages.md`).
- **F3 done**: `catalogs.py` (shared name/arity tables) + `semantic.py` with the §2.8
  semantic checks + `tests/test_resolver.py`; 99 tests green.
- **F4 done**: `world/entities.py` (shared `hit()`, creature reserve = `health`)
  + `world/world.py` (grid, cloning placement, `bool` placement rules) +
  `loaders/` (shared definition parser, `.te`/`.ob` loaders, `Registry` with
  I14 char uniqueness and partial-failure scan) + `tests/test_world.py` +
  `tests/test_loaders.py`; 147 tests green. Decisions D9–D11 in `PLAN.md`.
- **F5 done**: `sim/engine.py` (`Engine` + frozen `TickReport`/`WorldSnapshot`,
  snapshot+shuffle turn order, `wait_remaining` countdown, `_pending` newborn queue
  by identity, `births` counted post-turns, `set_turn_runner()` hook for F6) +
  `Creature.wait_remaining = 0` in `world/entities.py` + `tests/test_engine.py`;
  160 tests green. Decisions D12–D14 in `PLAN.md`.
- **Next**: F6 (tree-walking interpreter over `ResolvedProgram`: PC, 100 lines/turn,
  `wait`, persistent variables, §2.6 perceptions, plugged via
  `Engine.set_turn_runner()`). New messages must be added to
  `error-messages.md` in the same commit.

## Additional Context Files

- `error-messages.md` — full catalog of every error message the project throws
  (lexer, parser, semantic, loaders, plus slots reserved for F7 runtime / F8 map).
  **Append new messages there when they are added.**
