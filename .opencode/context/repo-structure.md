<!-- Context: main@e22971f -->
# Repository Context

Last updated: 2026-10-24

## Tech Stack

- **Language**: Python 3.14.7 (developed/tested on `Python\pythoncore-3.14-64`; `requires-python = ">=3.10"`)
- **Build Tool**: none yet (pure package)
- **Package Manager**: pip
- **Key Dependencies**:
  - `pytest`: test runner (installed globally, declared in `pyproject.toml` `[tool.pytest.ini_options]`)
  - `pygame-ce>=2.5`: GUI (declared in `pyproject.toml`; the classic `pygame` has no
    wheel for Python 3.14, `pygame-ce` installs the same `pygame` module)

## What This Project Is

An implementation of the **Instinct** language (spec: `instinct.md`, PDF `instinct.pdf`) —
a small creature-programming language plus a 2D tick-based world simulator and a GUI.
Theme: **Instinct Bizarre Adventure** (JoJo's Bizarre Adventure). Written for an
OOP course; the graded criteria are OO design quality (spec §5), not just "it runs".

Mandatory base = spec sections 2–4. All plan decisions are recorded in **`PLAN.md`**
(requirements R1–R19, invariants I1–I15, phases F0–F11, decisions D1–D23).

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
    (lang/ runtime done in F6+F7: values, environment, actions/ base + 7 action
     subclasses + strike.py, functions, perceptions, interpreter; world/perceptions.py
     sensors; ui/ as planned; world/, loaders/ and sim/engine done in F4–F5)
  lang/                 language runtime: actions/ (base + 7 subclases + strike.py),
                        functions, perceptions, interpreter (F6–F7 done)
  world/                entities.py (Entity/Terrain/WorldObject/Creature),
                        world.py (Cell grid, placement, movement, walkable), rng.py (seeded Rng)
  loaders/              errors.py (LoadError + tag_errors), definition.py (shared parser),
                        terrain_loader.py, object_loader.py, registry.py,
                        map_loader.py, creature_loader.py, pipeline.py (F9 done)
  sim/                  engine.py tick loop + cli.py terminal runner (F9 done)
   ui/                   Pygame app (F10 done): constants.py (layout, colors, phases,
                         zoom char hide, health bar, procedural art sets),
                         state.py (mutable UIState, no pygame), session.py (actions over
                         the CLI, no pygame), assets.py (fonts + cached procedural tiles/icons/tokens, case-insensitive),
                         view.py (renderer + per-frame hotspots, health bar, char visibility by art),
                         controls.py (keyboard/mouse -> UIAction), app.py (60 fps loop) + __main__.py
tests/                  pytest suite (347 tests: 4 scaffold + 24 lexer + 36 parser + 35 semantic + 28 world + 24 loaders + 20 map loader + 11 creature loader + 6 pipeline + 16 engine + 25 interpreter + 27 actions + 17 cli + 4 ui state + 18 ui session + 11 ui assets + 11 ui view + 15 ui controls + 11 ui app + 4 content)
terrains/ objects/ maps/ creatures/   runtime content dirs the app loads (spec §4.1);
                        JoJo example content (D8): Morioh/Adoquin terrains,
                        Steamroller/Knives objects, the Morioh Town map and the
                        five Stand users (Jotaro, Kakyoin, Polnareff, Joseph, Dio)
PLAN.md                 the project plan (source of truth for decisions)
instinct.md             the specification (do not edit)
GUIA_*.md               local study guides, one per phase (AST/parser, resolver,
                        world+loaders, engine F5, interpreter F6, actions+ictus F7,
                        pipeline+CLI F9, UI Pygame F10;
                        plain-Spanish walkthroughs, gitignored, not pushed)
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
   frozen `TickReport`. Turn contents run through the `set_turn_runner()` hook,
   where F6 plugged the interpreter; F7 added `kill()` so mid-tick deaths
   (combat kills and strokes) are removed in place and counted in
   `TickReport.deaths` (D21). Only the engine talks to the interpreter; UI and
   CLI are clients of `step()/state()` (`state()` returns a frozen
   `WorldSnapshot` with no live references, no `_cells`, no RNG).
5. `lang/actions/` (F7 done): one subclass per action over the shared `Action`
   base (contract: `validate` args → `apply` effect, §5); `strike.py` resolves
   the target cell for attack/consume (creature > object > terrain; `(0, 0)`
   hits the creature's own terrain, out-of-map is a no-op). The interpreter
   catches every `ExecutionError` as a stroke: the creature dies in place via
   `Engine.kill()` and `Nombre: línea N: mensaje` goes to the log callback
   (D23). Amounts act literally, but `Entity.hit` clamps terrain/object
   reserves to `resource_max` (I3, D22) while creature health stays uncapped
   (I5); `reproduce` requires `health >= 1` or it is a natural abort (D22).
   `say` is the only action with `consumes_turn = False`.
6. `loaders/map_loader.py` (F8 done): `load_map` parses the `.map` — first
   content line is the name (spaces allowed), every following content line is a
   same-length row, blank lines skipped, row edges stripped, no comments
   (`#` is a rock cell, D11 does not apply) — and validates every char against
   the `Registry` (D24–D26); any error rejects the whole file with all errors
   collected at once, compiler-style. `GameMap` keeps the resolved prototypes
   and `build_world` materializes them through `World.place_terrain`/
   `place_object` clones (D27) — the loader calls the world, never the reverse
   (§5). `load_maps` scans `maps/` alphabetically with path-tagged errors and
   partial-failure tolerance (D28), mirroring `load_definitions` (§4.1.1).

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
  `test_world.py` (28 tests: I1/I2/I3 per placement call, walkable rules, hit
    clamping at 0 and capped at resource_max on negative damage, regen capped at
    max, prototype cloning, creature header/age, `move_creature`),
  `test_loaders.py` (24 tests: Anexo grass/rock end to end, one per loader error
    with exact line+message, `char #` not eaten as comment, I14 char clash,
    partial-failure directory scan via `tmp_path`),
  `test_map_loader.py` (20 tests: Anexo map end to end incl. `build_world` on the
    grid — dimensions, rock over base terrain, walkable rules, prototype clones —
    one per §3.3 map error with exact line+message — unknown char, uneven rows,
    empty/row-less sources, no-terrain registry —, blank-line skipping with
    physical line numbers, row-edge stripping, `#` as a cell not a comment, and
    the partial-failure `maps/` scan via `tmp_path`),
  `test_engine.py` (16 tests: E1–E4 order, L1 shuffle determinism incl. order,
    L8 newborn waits a tick incl. mid-tick queueing, sleeping still ages,
    `state()` read-only and frozen, `kill()` removal/counting incl. stale
    position by identity; adds no user-facing messages),
  `test_interpreter.py` (25 tests: turn laws 3–7 incl. the 100-line cap and EOF
    wrap, §2.5 precedence and type rules, the 31 perceptions, roar buffer,
    same-seed determinism, and the F7 stroke policy: every §2.8 runtime error
    kills the creature and logs `Nombre: línea N: mensaje`),
  `test_actions.py` (27 tests: the 7 actions end to end through the interpreter —
    move stopping rules, attack/consume targeting incl. `(0, 0)` own terrain and
    out-of-map no-ops, mid-tick kills counted, reproduce births/aborts, roar
    heard next tick, free say, validation strokes, and the four Anexo creatures
    running 50 ticks in one world),
  `test_ui_*.py` (59 tests over six files: state helpers, session actions over
    the CLI incl. same-seed replay determinism, asset colors/caches, per-phase
    render with hotspot assertions, synthetic keyboard/mouse events →
    `UIAction`s, and headless app integration via `SDL_VIDEODRIVER=dummy`;
    each file gates on `pytest.importorskip("pygame")` so the suite stays
    green without the GUI dependency),
  `test_content.py` (4 tests over the shipped JoJo content: zero load errors
    across the four dirs, every map cell declared — Steamroller/Knives objects,
    Morioh/Adoquin terrains —, a 100-tick battle via `Session` that keeps the
    log alive with says and roars, and same-seed determinism of creatures
    and messages).
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
- **F6 done**: `lang/` runtime (`errors.py` with `ExecutionError`, `values.py` with
  §2.5 type rules, `environment.py` name resolution, `actions/` with `Action` base +
  `Wait` + registry, `functions.py` with `see`/`name`, `perceptions.py` with frozen
  `TurnFrame` + 31 resolvers mirroring `catalogs.PERCEPTIONS`) + `world/perceptions.py`
  (Chebyshev sensors, D4 tie-break, self excluded per D15) + `lang/interpreter.py`
  (PC resume, 100-line cap counting labels per D17, EOF wraps next turn, `wait(n)`
  countdown, `ExecutionError` detection without ictus policy per D18) + engine
  wiring (`perception_random()` per D19, roar buffer published end-of-tick per
  D5/D20, `Creature.pc` starts at `labels["start"]`) + `tests/test_interpreter.py`;
  184 tests green. Decisions D15–D20 in `PLAN.md`.
- **F7 done**: `lang/actions/` completed — `Move`/`Attack`/`Consume`/`Reproduce`/
  `Roar`/`Say` over the shared base (validators `_require_number`/
  `_require_direction`), `strike.py` target resolution, registry asserting
  sync with `ACTION_ARITY` — + stroke policy in `Interpreter.run_turn` (catch →
  `Engine.kill()` → log `Nombre: línea N: mensaje`) + `Engine.kill()` counting
  every death of the tick in `TickReport.deaths` (D21) + `World.move_creature`
  + `Entity.hit` upper clamp at `resource_max` (D22) + `tests/test_actions.py`
  incl. the four Anexo creatures running 50 ticks together; 219 tests green.
  Decisions D21–D23 in `PLAN.md`.
- **F8 done**: `loaders/map_loader.py` — `load_map` validates every char against
  the registry (§3.3: first content line is the name, same-length rows, unknown
  char rejects the whole file with char and line, D24–D26), `GameMap`/`MapCell`
  hold the resolved prototypes, `build_world` materializes the grid through
  `place_terrain`/`place_object` clones without touching `world/` (D27),
  `load_maps` scans `maps/` with partial-failure tolerance like
  `load_definitions` (D28, §4.1.1), `tag_errors` now public in `errors.py` +
  `tests/test_map_loader.py`; 239 tests green. Decisions D24–D28 in `PLAN.md`.
- **F9 done**: `loaders/creature_loader.py` (`load_creature` compiles a `.ins`
  through scan→parse→resolve, converting every front-end error to `LoadError`
  with its line; `load_creatures` scans the folder alphabetically with
  path-tagged errors, partial-failure tolerance and duplicate-name rejection) +
  `loaders/pipeline.py` (`load_all` chains `.te → .ob → .map → .ins` into a
  frozen `LoadedWorld` with registry, maps by name, creatures by name, and all
  load errors accumulated) + `sim/cli.py` (`CLI` with testable methods for
  loading, map selection, creature placement/removal, tick stepping with
  speed control, reset, grid rendering, and log collection; the interactive
  `run()` loop drives those methods through input/print) +
  `tests/test_creature_loader.py` + `tests/test_pipeline.py` +
  `tests/test_cli.py`; 273 tests green.
- **F10 done**: `ui/` package — `constants.py` (window/layout/factions/phases,
                         reuses `SPEEDS` from the CLI), `state.py` (mutable `UIState`: the only thing
                         the renderer reads; pygame-free), `session.py` (`Session` executes user
                         actions over the CLI facade — load, select map, place/remove via `cell()`,
                         start, step, pause, speed, reset, `repeat_seed` builds a fresh `CLI` with the
                         typed seed, transfers the loaded content, re-places the same creatures and
                         relaunches; pygame-free and fully unit-tested), `assets.py` (fonts rebuilt
                         per zoom step, cached procedural terrain/object tiles and faction tokens with
                         case-insensitive keys, alpha icons/tokens), `view.py` (layered grid render with
                         culling, per-phase side panel, logs box, status bar, map thumbnails, health
                         bar, per-frame `hotspots` table — D30; hides chars only when procedural art
                         exists or zoom >= threshold), `controls.py` (keyboard/mouse → frozen
                         `UIAction`; mutates only camera/hover/zoom/seed field), `app.py` (`App` wires
                         session+view+controls in a 60 fps loop, ticks on a speed timer;
                         `main()` entry; `python -m instinct.ui`), `pyproject.toml` gains
                         `pygame-ce>=2.5`; UI tests run headless (`SDL_VIDEODRIVER=dummy` +
                         `pytest.importorskip`) — `tests/test_ui_state.py`, `test_ui_session.py`,
                         `test_ui_assets.py`, `test_ui_view.py`, `test_ui_controls.py`,
                         `test_ui_app.py`; 347 tests green. One new session message, catalogued in
                         `error-messages.md` §7. Decisions D29–D31 in `PLAN.md`.
- **JoJo content shipped**: the four content dirs now hold a playable example
  (D8) — `terrains/` Morioh (lawn, `.`) + Adoquin (cobblestone, `,`),
  `objects/` Steamroller (`#`, the road roller) + Knives (`k`, Dio's throwing
  knives), `maps/` Morioh Town (20x12: cobblestone streets framing grass
  blocks, the steamroller parked mid-street, knives in a lawn) and
  `creatures/` five Stand users in the joestar vs dio war: Jotaro (ORA rush,
  eats the lawn when wounded), Kakyoin (Emerald Splash roars, longest vision),
  Polnareff (fastest charge, double rapier), Joseph (Hamon overdrive via
  consume, flees under 30 hp, answers roars with predictions), Dio (drains
  blood with consume, roars ZA WARUDO at random, multiplies above 100 hp).
  All five wander via `random % 3 - 1` and heal from their own cell's reserve,
  so the world keeps itself alive; same-seed runs replay identically
  (`tests/test_content.py`, 4 tests; 337 total). UI palette covers every
  shipped name and faction.
- **Next**: F11 (optional language extensions, defense polish; manual window
  test of `python -m instinct.ui`).

## Additional Context Files

- `error-messages.md` — full catalog of every error message the project throws
  (lexer, parser, semantic, loaders incl. maps, interpreter and actions).
  **Append new messages there when they are added.**
