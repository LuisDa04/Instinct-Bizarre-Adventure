# Guía de la Interfaz Pygame (F10) — explicada en cristiano

> (Haz clic en los enlaces 📄 para abrir el código. Junto a cada uno van las
> líneas exactas donde mirar. En GitHub el enlace salta directo a la línea;
> en VS Code abre el archivo y buscas el número.)

Esta guía es **local y personal**: está en el `.gitignore`, no se commitea.

---

## 0. La idea en una frase

El **pipeline (F9)** ya sabe cargar todo y el **CLI (F9)** ya sabe correr la simulación por terminal. La **F10** pone una **ventana Pygame** encima: dibuja la rejilla a 60 fps, traduce clics/teclas en acciones, muestra logs y deja al usuario elegir mapa, colocar criaturas, play/pausa/paso/velocidades, reinicio y repetir con semilla.

```
[App.run] ─→ eventos → [Controls.handle] → UIAction → [Session] → [CLI] → [Engine/Interpreter]
                    ↑                                         │
                    └──── hotspots (View.render) ←───────────┘
```

**Analogía**: `App` es el director de orquesta; `Controls` lee la partitura (teclado/ratón) y la traduce a órdenes (`UIAction`); `Session` las ejecuta sobre el CLI (que ya sabe montar motor + intérprete); `View` pinta lo que ve en `UIState` y devuelve la tabla de *hotspots* (qué rectángulo es cada botón/celda) para que el siguiente frame los controles sepan dónde clicó el usuario.

---

## 1. Arquitectura: tres capas y un estado compartido

```
┌─────────────────────────────────────────────────────────────────┐
│ App (bucle 60 fps)                                              │
│   ├─ Session (lógica de fases: carga → mapa → colocación → sim) │
│   ├─ View (render + hotspots)                                   │
│   ├─ Controls (eventos → UIAction)                              │
│   └─ UIState (única fuente de verdad: fase, mundo, cámara, log) │
└─────────────────────────────────────────────────────────────────┘
```

**Regla de oro**: la vista **solo lee** `UIState`; los controles **solo mutan** la parte visual (`camera_x`, `hover_cell`, `seed_input`, `seed_focused`); la sesión muta la parte lógica (`phase`, `world`, `engine`, `messages`, `placements`). Así render e input nunca se desincronizan.

---

## 2. `UIState`: la única fuente de verdad

📄 [instinct/ui/state.py](instinct/ui/state.py)

### 2.1. Campos lógicos (mutados por `Session`)

| Campo | Qué es |
|-------|--------|
| `phase` | `loading` \| `no_maps` \| `map_select` \| `placement` \| `simulation` |
| `loaded` | `LoadedWorld` del pipeline (registry, maps, creatures, errors) |
| `load_report` | Texto del reporte de carga (para el panel) |
| `map_name` | Nombre del mapa elegido |
| `world` / `engine` | Instancias vivas montadas al `select_map` |
| `messages` | Log de la sesión (colocación + motor) |
| `placements` (en `Session._placements`) | Lista `(species, x, y)` para poder repetir |

### 2.2. Campos visuales (mutados por `Controls`)

| Campo | Qué es |
|-------|--------|
| `camera_x`, `camera_y` | Desplazamiento de la rejilla (píxeles) |
| `tile_size` | Zoom actual (16–64 px, paso 4) |
| `hover_cell` | Celda bajo el ratón (`None` si fuera) |
| `selected_cell` | Celda clicada en simulación (resaltada) |
| `speed_index` | Índice en `SPEEDS = (1, 5, 10, 30)` |
| `seed`, `seed_input`, `seed_focused` | Semilla visible + edición |

### 2.3. Properties derivadas

📄 [state.py — líneas 61-79](instinct/ui/state.py#L61-L79)

- `speed_tps` → `SPEEDS[speed_index]`
- `map_names` / `species_names` → claves de `loaded.maps` / `loaded.creatures`
- `in_simulation()` → `phase == "simulation"`

---

## 3. `App`: el bucle a 60 fps

📄 [instinct/ui/app.py](instinct/ui/app.py)

### 3.1. `__init__` (L31-47)

Crea ventana (`1280×800`, redimensionable), `Session`, `Assets`, `View`, `Controls`, reloj.

### 3.2. `run()` — el bucle principal (L49-62)

```python
while self._running:
    for event in pygame.event.get():
        for action in self.controls.handle(event, self.view.hotspots):
            self._execute(action)
    self._advance_simulation()          # ticks según velocidad
    self.view.render(self.screen, self.session.state)
    pygame.display.flip()
    self.clock.tick(TARGET_FPS)         # 60 fps
```

### 3.3. `_advance_simulation` (L68-76)

Avanza **un tick** cuando toca según `speed_tps` y sin pausa:

```python
if not state.in_simulation() or state.paused: return
if now - self._last_step >= 1.0 / state.speed_tps:
    self.session.step_once()
    self._last_step = now
```

### 3.4. `_execute(action)` (L82-110)

Despacha la `UIAction` a la sesión:

| `action.type` | Efecto |
|---------------|--------|
| `map` | `session.select_map` + centra cámara |
| `species` | `session.pick_species` (toggle) |
| `start` | `session.start()` (valida ≥1 criatura) |
| `cell` | `session.cell(x, y)` (colocar/quitar en colocación) |
| `select_cell` | `session.select_cell(x, y)` (resalta en sim) |
| `pause` | `session.toggle_pause()` |
| `step` | `session.step_once()` |
| `speed` | `session.set_speed(index)` |
| `reset` | `session.reset()` (vuelve a colocación, mismo mapa/seed) |
| `repeat` | `session.repeat_seed()` (nueva CLI misma seed, recoloca) |
| `quit` | `_running = False` |

### 3.5. `_center_camera` (L111-122)

Centra la rejilla en el área visible al cambiar de mapa.

### 3.6. `main()` (L123-126)

Punto de entrada: `python -m instinct.ui`

---

## 4. `Session`: fachada sobre el CLI

📄 [instinct/ui/session.py](instinct/ui/session.py)

**Responsabilidad**: traducir acciones de usuario en llamadas al CLI (que ya sabe montar motor + intérprete) y mantener `UIState` + historial de colocaciones para `repeat_seed`.

### 4.1. `load()` (L45-56)

Llama `cli.load_content()` → reporte + `loaded` → fase `map_select` o `no_maps`.

### 4.2. `select_map(name)` (L62-85)

Valida nombre → `cli.select_map` → obtiene `world`/`engine` del CLI → fase `placement`, limpia `messages`, `placements`, `tick=0`.

### 4.3. Colocación (L86-136)

| Método | Qué hace |
|--------|----------|
| `pick_species(name)` | Toggle especie activa para colocar |
| `cell(x, y)` | Si hay especie activa → `cli.place_creature` + guarda en `_placements`; si hay criatura → `cli.remove_creature` + quita de `_placements` |
| `select_cell(x, y)` | Solo resalta celda en simulación |

### 4.4. Simulación (L138-167)

| Método | Qué hace |
|--------|----------|
| `start()` | Valida ≥1 criatura → fase `simulation`, `paused=False` |
| `toggle_pause()` | Alterna `paused` |
| `step_once()` | `engine.step()` + actualiza `tick` + `_pull_logs()` |
| `set_speed(index)` | Valida 0-3 → `speed_index` |

### 4.5. `reset()` (L180-193)

Llama `cli.reset()` → nuevo `world`/`engine` mismo mapa/seed → fase `placement`, limpia `messages`, `placements`, `tick=0`.

### 4.5. `repeat_seed()` (L194-226)

**La joya de F10**: crea **nuevo `CLI` con la semilla del campo**, **reutiliza `LoadedWorld`** (sin releer disco), **recoloca** las mismas criaturas en las mismas celdas (`_placements`), arranca en marcha. La traza es **idéntica** en cada repetición (D31).

### 4.6. `_pull_logs()` (L228-236)

Toma logs nuevos del CLI desde `_log_cursor`, los añade a `state.messages` (capado a `MAX_LOG_LINES=200`).

---

## 5. `Controls`: eventos → `UIAction`

📄 [instinct/ui/controls.py](instinct/ui/controls.py)

### 5.1. `handle(event, hotspots)` (L49-68)

Despacha según tipo de evento:

| Evento | Método |
|--------|--------|
| `QUIT` | `quit` |
| `KEYDOWN` | `_key_down` |
| `MOUSEMOTION` | `_motion` (hover + pan) |
| `MOUSEBUTTONDOWN` | `_button_down` |
| `MOUSEBUTTONUP` (btn 3) | fin de pan |
| `MOUSEWHEEL` | `_zoom` |

### 5.2. Teclado (L70-106)

| Tecla | Contexto | Acción |
|-------|----------|--------|
| `ESC` / `Q` | Siempre | `quit` |
| `SPACE` | Simulación | `pause` |
| `S` | Simulación | `step` |
| `R` | Simulación | `reset` |
| `1-4` | Simulación | `speed 0-3` |
| Dígitos / Backspace / Enter / Esc | Campo semilla | edición / `repeat` / blur |

### 5.2. Ratón (L108-171)

| Evento | Qué hace |
|--------|----------|
| Click izq en hotspot | `_hotspot_action(key)` → `UIAction` |
| Click izq en grid | `cell` (colocación) / `select_cell` (sim) |
| Click der + arrastrar | Pan cámara (`_panning`) |
| Wheel | `_zoom` (±4 px, límites 16–64) |

### 5.3. `_hotspot_action(key)` (L134-158)

| Prefijo/clave | Acción |
|---------------|--------|
| `map:Nombre` | `map` |
| `species:Nombre` | `species` |
| `seed_input` | foco en campo semilla |
| `start`/`pause`/`step`/`reset`/`repeat`/`quit` | acción simple |

### 5.4. `_cell_at(pos, grid)` (L161-170)

Convierte píxel → celda mundo `(x, y)` usando `camera_x/y` y `tile_size`. Devuelve `None` si fuera de límites.

---

## 5. `View`: render + hotspots

📄 [instinct/ui/view.py](instinct/ui/view.py)

### 5.1. `render(screen, state)` (L46-78)

Limpia `hotspots`, calcula rects (`panel`, `grid`, `logs`), despacha según `phase`:

| Fase | Qué dibuja |
|------|------------|
| `loading` | Texto "Cargando..." + reporte si existe |
| `no_maps` | Aviso + reporte + botón SALIR |
| `map_select` | Reporte + panel con lista de mapas (clicables) |
| `placement` | Grid + logs + panel (especies + botón INICIAR) |
| `simulation` | Grid + logs + panel (HUD + botones + campo semilla) |

Siempre dibuja barra de estado abajo.

### 5.2. `_render_grid` (L79-116)

Itera solo celdas **visibles** (culling por cámara + rect visible). Capas por celda:

1. Terreno (color + char)
2. Objeto (color + char)
3. Criatura (color facción + inicial mayúscula)
4. Línea de grid
5. Hover (translúcido) / Selección (borde cyan)

Registra `hotspots["grid"] = rect`.

### 5.3. `_render_panel` (L132-223)

Panel derecho (300px) según fase:

| Fase | Contenido |
|------|-----------|
| `no_maps` | Aviso + botón SALIR |
| `map_select` | Lista de mapas (item clicable + miniatura) |
| `placement` | Instrucciones + lista especies (toggle activo) + botón INICIAR (habilitado si hay criaturas) |
| `simulation` | HUD (tick, velocidad, seed, vivas) + botones PAUSA/PASO/VELOCIDAD/REINICIAR/REPETIR + campo semilla editable |

### 5.4. `_render_logs` (L242-257)

Últimos mensajes que caben (altura / 18). Colorea según prefijo:

| Prefijo | Color |
|---------|-------|
| `dice:` | cyan (`log_say`) |
| `ruge:` | naranja (`log_roar`) |
| `línea` | rojo (`log_ictus`) |
| resto | gris (`log_system`) |

### 5.5. Hotspots

Cada elemento clicable registra su `pygame.Rect` en `self.hotspots[key]` **durante el render**. Los controles leen esa tabla en el **siguiente frame** → botón dibujado y botón clicable **nunca se desincronizan** (D30).

---

## 6. `Assets`: fuentes + cachés

📄 [instinct/ui/assets.py](instinct/ui/assets.py)

- `font_mono` (Consolas monoespaciada, tamaño `tile_size - 8`, bold) → chars de grid
- `font_ui` (Arial 14) → paneles, logs, botones
- `tile(color)` → `Surface` `tile_size × tile_size` cacheada por color
- `terrain_color(name)`, `object_color(name)`, `faction_color(name)` → paletas JoJo con fallback gris
- `ensure_tile_size(size)` → recrea fuentes + vacía caché al hacer zoom

---

## 6. `constants.py`: todo configurable

📄 [instinct/ui/constants.py](instinct/ui/constants.py)

```python
SPEEDS = (1, 5, 10, 30)           # tps (desde CLI)
BASE_TILE_SIZE = 32               # zoom inicial
ZOOM_STEP = 4                     # paso de rueda
PANEL_WIDTH = 300                 # px
LOG_HEIGHT = 180                  # px
MAX_LOG_LINES = 200               # cap del registro
COLORS = {...}                    # paleta completa + logs + facciones
TERRAIN_COLORS / OBJECT_COLORS / FACTION_COLORS  # paletas JoJo
```

---

## 7. Tests

📄 [tests/test_ui_app.py](tests/test_ui_app.py) + `test_ui_*.py` (59 tests total)

| Archivo | Qué prueba |
|---------|------------|
| `test_ui_app.py` | Flujo completo: load → map → place → start → step/pause/speed/reset/repeat/quit |
| `test_ui_assets.py` | Fuentes, colores, caché de tiles |
| `test_ui_controls.py` | Teclado/ratón → UIAction, hotspots, pan/zoom, campo semilla |
| `test_ui_session.py` | Sesión: load, select_map, place/remove, start, step, speed, reset, repeat |
| `test_ui_state.py` | Properties, in_simulation, speed_tps |
| `test_ui_view.py` | Render por fase, hotspots, grid culling, colores de logs |

**Ejecutar**:
```bash
python -m pytest tests/test_ui_*.py -q    # 59 tests (driver dummy SDL)
python -m pytest -q                      # 332 tests (todo)
```

---

## 8. Mensajes de error (catálogo)

Todos vienen del pipeline/CLI/engine. La UI solo los muestra formateados en `_render_logs` con colores.

| Tipo | Prefijo | Color |
|------|---------|-------|
| `say` | `dice:` | cyan |
| `roar` | `ruge:` | naranja |
| `ictus` | `línea N:` | rojo |
| sistema | — | gris |

---

## 9. Las trampas que ya mordieron

| Si haces… | Lo que pasa | Dónde mirar |
|-----------|-------------|-------------|
| Mutar `UIState` lógico desde `View` | Render e input se desincronizan | Regla: **View solo lee**, Controls solo visual, Session lógica |
| No limpiar `hotspots` cada frame | Clics en botones "fantasmas" | `View.render` L49: `self.hotspots = {}` |
| No centrar cámara al cambiar de mapa | Mapa fuera de vista | `App._center_camera` L111-122 |
| No capar `messages` | Memoria crece sin límite | `Session._pull_logs` L233-235 (`MAX_LOG_LINES`) |
| No recrear fuentes al hacer zoom | Chars no escalan / crashean | `Assets.ensure_tile_size` L44-48 |
| Usar `pygame.font.SysFont` sin fallback | Falla en Linux sin fuentes MS | `Assets._build_fonts` L35-42: lista de fallbacks |
| No capar `speed_index` | IndexError en `SPEEDS` | `Session.set_speed` L167-170 |
| `repeat_seed` sin copiar `_placements` | Repite sin criaturas | `Session.repeat_seed` L207-208: recorre `_placements` y `cli.place_creature` |
| No etiquetar errores con ruta en pipeline | Log no dice qué archivo falló | `tag_errors` en `load_definitions` / `load_maps` / `load_creatures` |

---

## 10. Referencias rápidas (archivo → sección)

| Archivo | Qué contiene | Líneas clave |
|---------|--------------|--------------|
| `instinct/ui/app.py` | Bucle principal, ejecución de acciones, cámara | `run` L49, `_execute` L82, `_advance_simulation` L68 |
| `instinct/ui/session.py` | Fachada lógica: carga, mapa, colocación, simulación, reset, repeat | `load` L45, `select_map` L62, `cell` L97, `start` L138, `reset` L180, `repeat_seed` L194 |
| `instinct/ui/view.py` | Render por fase, grid culling, panel, logs, hotspots | `render` L46, `_render_grid` L79, `_render_panel` L132, `_render_logs` L242 |
| `instinct/ui/controls.py` | Eventos → UIAction, teclado/ratón, pan/zoom, campo semilla | `handle` L49, `_key_down` L70, `_button_down` L108, `_hotspot_action` L134 |
| `instinct/ui/state.py` | Estado observable único (fase, mundo, cámara, log, cámara) | `UIState` L19, properties L61-79 |
| `instinct/ui/assets.py` | Fuentes mono/UI, caché de tiles por color/tamaño | `Assets` L17, `ensure_tile_size` L44 |
| `instinct/ui/constants.py` | Layout, colores, paletas, SPEEDS | L1-75 |
| `tests/test_ui_*.py` | 59 tests (dummy SDL) | 6 archivos |

---

## 11. Límites actuales (lo que NO hace)

- Sin editor de código dentro de la UI (extensión opcional F11)
- Sin gráficas de población en tiempo real (extensión)
- Sin guardado/carga de partida (extensión)
- Sin sprites/animaciones (tiles de color + char; extensible en `Assets`)
- CLI/terminal (F9) y UI (F10) comparten `Session`/`CLI` → consistencia garantizada

---

## 12. Referencias a decisiones del plan

| Decisión | Qué fijó |
|----------|----------|
| **D29** | Sesión usa CLI como fachada (`select_map`, `place_creature`, `reset`); UI nunca habla con intérprete/motor |
| **D30** | View registra hotspots cada frame; Controls los consulta en frame siguiente → 0 desincronía View/Controls |
| **D31** | `repeat_seed` crea CLI nuevo con semilla del campo, transfiere `LoadedWorld`, recoloca `_placements` → traza idéntica |

---

**Siguiente: F11** — contenido JoJo en directorios, test 1000 ticks integración real, test UI ventana real, extensiones demo, preparación defensa.