# Instinct Bizarre Adventure

Simulador de criaturas programables inspirado en *JoJo's Bizarre Adventure*. Implementa un lenguaje de scripting propio (`.ins`), un motor de simulación tick-based, cargadores de contenido dinámico y una interfaz gráfica con editor de código integrado.

---

## 🎮 Características Principales

### Lenguaje Instinct (`.ins`)
- **Cabecera obligatoria**: `creature`, `faction`, `health`, `vision`, `lifespan`, etiqueta `start:`
- **7 acciones nativas**: `wait`, `move`, `attack`, `consume`, `reproduce`, `roar`, `say`
- **31 percepciones**: `health`, `enemy_dist`, `ally_dx`, `random`, `see(x,y)`, `name(x,y)`, etc.
- **Expresiones tipadas**: enteros, texto, lógica booleana (`and`/`or`/`not`), precedencia §2.5
- **Control de flujo**: `goto`, `if expr goto label`, etiquetas, asignaciones
- **Manejo de errores**: errores léxicos, sintácticos y semánticos con número de línea

### Motor de Simulación
- **Ticks discretos** con orden aleatorio por tick (semilla determinista)
- **Leyes de ejecución** (8 leyes): orden de turnos, refresco percepciones, 100 líneas/turno, wrap a `start:`, etc.
- **Entidades**: Terrenos (regeneración), Objetos (reserva finita), Criaturas (HP, edad, facción, variables)
- **Sistema de rugidos**: propagación por distancia Chebyshev, escucha en tick siguiente
- **Ciclo de vida**: -1 HP/tick, envejecimiento, muerte por edad/HP 0, reproducción con coste

### Cargadores de Contenido (Pipeline `.te → .ob → .map → .ins`)
- **Terrenos (`.te`)**: `resource_max`, `regen`, `char` único
- **Objetos (`.ob`)**: `resource_max`, `char` único
- **Mapas (`.map`)**: nombre + filas iguales, validación chars contra registro
- **Criaturas (`.ins`)**: compilación completa (léxico → sintaxis → semántica)
- **Tolerancia a fallos parciales**: un archivo roto no impide cargar el resto

### Interfaces
| Interfaz | Descripción |
|----------|-------------|
| **GUI** (`python -m instinct.ui`) | Pygame: grid renderizado, panel lateral, logs coloreados, 5 velocidades, semilla visible + repetir |
| **Editor** (`F4` en GUI) | Editor `.ins` con pestañas, resaltado, autocompletado, linting tiempo real, hot-reload (Ctrl+R) |

---

## 🏗 Arquitectura

```
instinct/
├── compiler/          # Front-end: lexer → parser (Pratt) → semantic (resolver)
│   ├── lexer.py       # Scanner orientado a líneas, panic-mode recovery
│   ├── parser.py      # Pratt parser (precedencia §2.5) + 5 formas de línea
│   ├── semantic.py    # Resolvedor: cabecera, etiquetas, aridad, asignaciones
│   └── catalogs.py    # Fuente única: ACTION_ARITY, PERCEPTIONS, CONSTANTS...
├── lang/              # Runtime del lenguaje
│   ├── interpreter.py # PC persistente, 100 líneas/turno, frame percepciones
│   ├── actions/       # 7 acciones (polimorfismo sobre Action base)
│   ├── values.py      # Tipos dinámicos, verdad, operaciones binarias
│   └── perceptions.py # 31 resolvers, foto de turno (TurnFrame)
├── world/             # Modelo de mundo
│   ├── world.py       # Grid, colocación, clonado prototipos
│   ├── entities.py    # Entity → Terrain/WorldObject/Creature
│   └── rng.py         # RNG único (perception_random + shuffle turnos)
├── loaders/           # Pipeline de carga tolerante a fallos
│   ├── pipeline.py    # load_all(): .te → .ob → .map → .ins
│   ├── creature_loader.py, map_loader.py, terrain_loader.py, object_loader.py
│   └── registry.py    # Registro único de chars (invarianza I14)
├── sim/
│   └── engine.py      # Engine: tick loop, orden aleatorio, leyes E1-E4, rugidos
├── ui/                # Interfaces
│   ├── app.py         # Pygame loop 60fps, ventana + editor Qt (F4)
│   ├── view.py        # Render grid, panels, logs, HUD
│   ├── controls.py    # Input mapping → UIAction
│   └── editor/        # Editor Qt: tabs, highlighter, linter, completer, hot-reload
└── world/             # Modelos de mundo compartidos
```

### Patrones Clave
- **Polimorfismo**: `Action` (7 subclases), `Expr` (7 nodos), `Entity` (3 subclases), `PerceptionResolver` (dict de lambdas)
- **Inmutabilidad**: `ScanResult`, `ParseResult`, `ResolveResult`, `WorldSnapshot`, `TickReport` — `frozen=True`
- **Errores como valores**: `ScanResult.errors`, `ParseResult.errors`, `ResolveResult.errors` — sin excepciones en pipeline
- **Inyección de dependencias**: `Engine.set_turn_runner(interpreter.run_turn)`

---

## 🚀 Instalación

```bash
# Clonar
git clone https://github.com/LuisDa04/Instinct-Bizarre-Adventure.git
cd Instinct-Bizarre-Adventure

# Entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Dependencias
pip install -r requirements.txt
# o manualmente:
pip install pygame-ce>=2.5
# Para editor:
pip install PyQt6
```

> **Nota**: El proyecto usa Python ≥3.10. `pygame-ce` es un fork mantenido de `pygame` con wheels para Python 3.14+.

---

## ▶️ Ejecución

### GUI + Editor (Pygame + PyQt6)
```bash
# Ventana principal + editor (F4)
python -m instinct.ui
```
Controles GUI:
| Tecla | Acción |
|-------|--------|
| `Space` | Pausa / Play |
| `S` | Paso a paso (1 tick) |
| `1`-`5` | Velocidad 0.5 / 1 / 5 / 10 / 30 tps |
| `R` | Reiniciar mapa (limpia criaturas) |
| `F4` | Abrir / cerrar editor de código |
| `Q` / `Esc` | Salir |

**Editor (ventana separada):**
| Tecla | Acción |
|-------|--------|
| `Ctrl+S` | Guardar archivo actual |
| `Ctrl+R` | Hot-reload: recompila `.ins` y recarga criatura en vivo |
| `Ctrl+N` | Nueva pestaña |
| `Ctrl+O` | Abrir archivo `.ins` |
| Clic en error | Salta a la línea |

---

## 🧪 Testing

```bash
# Suite completa
python -m pytest -q

# Solo tests rápidos (excluye slow)
python -m pytest -q -k "not slow"

# Módulo específico
python -m pytest tests/test_interpreter.py -v
python -m pytest tests/test_ui_*.py -v
```

**Cobertura**: tests por capas: scanner, parser, resolver, world, loaders,
map_loader, creature_loader, pipeline, engine, interpreter, actions, content,
acceptance, scaffold, layering y ui (state, session, assets, view, controls, app, editor,
file_manager, hot_reload, linter, completer, highlighter, compiler_bridge, imports).

---

## 📁 Estructura de Contenidos (directorios de carga)

```
terrains/      # *.te  (terrain Nombre + char + resource_max + regen)
objects/       # *.ob  (object Nombre + char + resource_max)
maps/          # *.map (nombre + filas iguales de chars)
creatures/     # *.ins (programas Instinct)
```

El repo incluye ejemplos JoJo en `tests/acceptance/fixtures/` para tests de aceptación.

---

## 📜 Licencia

MIT License — ver [LICENSE](LICENSE) si existe.