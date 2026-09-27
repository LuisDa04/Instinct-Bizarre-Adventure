# Plan de proyecto — Instinct Bizarre Adventure

Documento de plan derivado de la especificación `instinct.md` (referencias como `§N`).
Temática: **JoJo's Bizarre Adventure** (§1 deja la temática libre).

---

## 1. Requisitos

### Obligatorios (base, secciones 2–4; vale 3 pts, §6)

| # | Requisito | Cita |
|---|---|---|
| R1 | Compilador/intérprete Python de `.ins`: valida léxico, sintáctica y semánticamente; errores **siempre con número de línea** | §1 |
| R2 | Cabecera con las 5 claves obligatorias (`creature`, `faction`, `health>0`, `vision>=1`, `lifespan>0`); primera línea no vacía = `creature Name`; etiqueta obligatoria `start:` | §2.2 |
| R3 | 5 formas de línea: `#`, `name:`, `goto`, `if expr goto name`, `name = expr`, `action(...)` | §2.3 |
| R4 | Solo 5 palabras reservadas: `if`, `goto`, `and`, `or`, `not`. Identificadores `[A-Za-z_][A-Za-z0-9_]*`, case-sensitive, indentación libre | §2.3 |
| R5 | Las 7 acciones con nombres/argumentos/efectos exactos: `wait(n)`, `move(dx,dy,speed)`, `attack(dx,dy,damage)`, `consume(dx,dy,damage,heal)`, `reproduce(dx,dy,health)`, `roar(value)`, `say(value)`; `dx,dy ∈ {-1,0,1}`; todo salvo `say` consume turno | §2.4 |
| R6 | Expresiones con la precedencia exacta de §2.5 | §2.5 |
| R7 | Tipos dinámicos int/text con las reglas de error de §2.5 (texto solo `==`/`!=`; lógicos aceptan todo; falsos = `0` y `""`) | §2.5 |
| R8 | 5 constantes `see`: `NONE -1`, `GROUND 0`, `OBJECT 1`, `ALLY 2`, `ENEMY 3`; `NONE` se comprueba primero; fuera de mapa dentro de radio → `OBJECT`; `name` → `""` fuera de radio o mapa | §2.6 |
| R9 | Todas las percepciones de §2.6; distancia de Chebyshev | §2.6 |
| R10 | Las 8 leyes de ejecución: orden sorteado por tick, refresh de percepciones al inicio del turno, reanudación donde se quedó, acciones gratis/consumidoras, `wait(n)` salta `n-1` turnos, tope **100 líneas/turno**, wrap a `start:`, variables persistentes, cría actúa al tick siguiente | §2.7 |
| R11 | Errores de compilación (lista de §2.8) y de ejecución (§2.8) → ictus, criatura muere, mensaje con línea en logs | §2.8 |
| R12 | Mundo: rejilla 2D; casilla = terreno siempre + (objeto XOR criatura); reservas y regeneración según §3.1 | §3.1 |
| R13 | `.te` (`resource_max` + `regen`) y `.ob` (solo `resource_max`); `char` único; base: `grass.te` y `rock.ob` del Anexo | §3.2, Anexo |
| R14 | `.map`: primera línea = nombre, filas del mismo largo; char desconocido → rechazo **con char y línea**, la app sigue | §3.3 |
| R15 | Reglas de simulación de §3.4 | §3.4 |
| R16 | App: carga en orden `.te → .ob → .map → .ins` con fallo parcial tolerado; colocar/quitar criaturas; play con pausa, 1 tick, ≥3 velocidades; reinicio; logs | §4.1 |
| R17 | Diseño OO: jerarquía de acciones, de expresiones/AST, de entidades del mundo; percepciones sin cadenas de `if`; mundo separado de la interfaz (simulación completa por terminal) | §5 |
| R18 | Intérprete que recorre el AST (sin VM/bytecode en la base) | §5 |
| R19 | Las extensiones nunca rompen la base; los ejemplos de los profesores deben cargar y correr sin modificar | §6 |

### Opcionales (para 4–5)

- Lenguaje: acciones nuevas, funciones (`reserve`, `health_at`, `distance`), percepciones, `while`/`if-else-end` → saltos, `call`/`return`, concatenación, reales, listas (§2.8).
- Mundo: terrenos con efecto, objetos con comportamiento, atributos nuevos, cadáveres, herencia, día/noche (§3.4).
- App: inspector, gráficas, guardado/carga, **repetición con semilla (incluida en F10)**, editor con recarga, sprites (§4.1).

---

## 2. Reglas, invariantes y casos de error

### Invariantes

- **I1** Toda casilla tiene 1 terreno; objeto y criatura mutuamente excluyentes (§3.1).
- **I2** Criatura = exactamente 1 casilla (§2.2).
- **I3** `reserve ≤ resource_max`; terreno arranca lleno, objeto arranca en `resource_max` (§3.1).
- **I4** `health > 0`, `vision ≥ 1`, `lifespan > 0`; `age ≥ 0` siempre (§2.2, §3.4.1).
- **I5** `health` sin techo (§2.2).
- **I6** Distancia = `max(|Δx|,|Δy|)` (§2.6).
- **I7** `see` comprueba `NONE` antes que nada (§2.6).
- **I8** Toda aleatoriedad (`random` + sorteo de turnos) sale de **un solo `Random` con semilla** → simulación reproducible (§2.6).
- **I9** PC persistente entre turnos; al llegar al EOF, `start:` en el **próximo** turno (§2.7.3, §2.7.6).
- **I10** Máx. 100 líneas/turno; sin acción ⇒ turno ≡ `wait(1)` (§2.7.5).
- **I11** Percepciones recalculadas solo al inicio del turno (§2.6, §2.7.2).
- **I12** Destino de saltos resuelto en compilación (§2.8).
- **I13** Orden de carga fijo (§4.1).
- **I14** `char` único entre todos los `.te`/`.ob` (§3.2).
- **I15** Empates de "más cercano" estables (§2.6).

### Errores de compilación (app rechaza el archivo y sigue, §2.8)

Línea inválida · `goto`/`if...goto` a etiqueta inexistente · etiqueta duplicada · falta alguna de las 5 claves o `start:` · valor inválido de cabecera · expresión mal formada · asignación a percepción/constante · acción o función desconocida · aridad incorrecta · mapa con char no declarado (§3.3).

### Errores de ejecución (ictus: muere, log con línea, §2.8)

División por cero · **resto por cero (decisión D2)** · lectura de variable no asignada · `dx`/`dy ∉ {-1,0,1}` · mezclar entero y texto en operador no lógico · texto donde se exige número.

### No son error (no-op controladas)

`attack`/`consume`/`reproduce` fuera de mapa (§3.4) · `reproduce` fallida → "aborto natural" (§2.4) · `move` se detiene ante casilla no pisable (§2.4) · `wait(n<1)` = 1 (§2.4) · terreno con reserva 0 (§3.1).

---

## 3. Arquitectura

```
instinct/
  frontend/   scanner.py, tokens.py, parser.py (Pratt), ast_nodes.py, resolver.py, errors.py
  lang/       values.py, environment.py, actions/ (Action + 7 subclases), functions.py,
              perceptions.py, interpreter.py
  world/      entities.py (Terrain/Object/Creature), world.py, perceptions.py, rng.py
  loaders/    creature_loader, terrain_loader, object_loader, map_loader, registry
  sim/        engine.py (tick loop), cli.py (terminal, §5)
  ui/         app.py (Pygame)
tests/
terrains/ objects/ maps/ creatures/   # dirs de carga que exige §4.1; contenido propio (JoJo, F11)
```

- Scanner → parser en dos pasos (ch. 6-7 / 14-15 de *Crafting Interpreters*); `line` desde el token hasta el error; panic-mode recovery para reportar varios errores.
- Pratt parser mapeando 1:1 la tabla de precedencia de §2.5.
- `Environment` dinámico por criatura con estado "no asignada aún" explícito.
- Etiquetas resueltas en `resolver.py` → índices en la lista de instrucciones.
- Polimorfismo en acciones, AST, entidades y percepciones (§5): sin `if tipo == ...`.

---

## 4. Fases

| Fase | Contenido |
|---|---|
| **F0** | Andamiaje, dirs de carga con `.gitkeep`, pytest, `rng` semillado |
| **F1** | Scanner (tokens, líneas, comentarios, literales, reservadas) |
| **F2** | AST + parser (Pratt §2.5, statements §2.3, cabecera §2.2) |
| **F3** | `resolver.py`: chequeos de §2.8 + catálogos de acciones/funciones/percepciones |
| **F4** | Modelo de mundo + loaders `.te`/`.ob` |
| **F5** | Motor de simulación: ticks, sorteo, fin de tick (§3.4), 8 leyes (§2.7), RNG |
| **F6** | Intérprete (PC, 100 líneas, `wait`, variables) + percepciones §2.6 |
| **F7** | Las 7 acciones + errores de ejecución |
| **F8** | Loader `.map` + rechazo por char + colocación |
| **F9** | Pipeline de carga (§4.1.1) + CLI |
| **F10** | Interfaz Pygame: rejilla, colocación, play/pausa/paso/3 velocidades, reinicio, logs, **semilla visible + repetir** |
| **F11** | Pruebas, ejemplos JoJo, extensiones, defensa |

### Dependencias

```
F0 ─▶ F1 ─▶ F2 ─▶ F3 ─▶ F6 ─▶ F7 ─▶ F9 ─▶ F10
F0 ─▶ F4 ─────────────▶ F5 ──┘        │
                          F4 ─▶ F8 ───┘
todas ─▶ F11 (tests continuos)
```

---

## 5. Pruebas y aceptación

- **Front-end:** token/línea correctos; precedencia (`health < 20 and enemy_dist < 3`, `random % 3 - 1`, `(home_x > x) - (home_x < x)`); un test por cada error de compilación y de ejecución de §2.8 → mensaje y línea exactos.
- **Mundo:** tras cada tick `−1` vida y `+1` edad; `age ≥ 0`; `reserve ≤ resource_max`; objetos con reserva 0 desaparecen; nunca objeto+criatura en la misma casilla; reproducción con edad 0 y sin variables heredadas.
- **Determinismo:** misma semilla ⇒ traza idéntica de N ticks, incluido el orden de turnos.
- **Ejemplos (§6):** los `.ins`/`.te`/`.ob`/`.map` que traigan los profesores cargan y corren 1000 ticks sin excepción; un `.ins` roto no impide cargar el resto. El repo no los incluye: los del Anexo están en `instinct.md` y se copian a los dirs de carga cuando haga falta.
- **Comportamiento:** hobbit huye si `enemy_dist >= 0`; ent vuelve a `home_x/home_y`; enano mina solo `"Rock"`.
- **UI:** logs con archivo+línea; colocar/varias/ quitar; imposible sobre objeto/criatura; pausa/paso/3 velocidades/ reinicio; sin edición durante simulación; simulación completa por terminal.
- **Rendimiento:** 100 líneas/turno; 300+ criaturas a 30 tps sin bloquear.
- **Defensa (§6):** explicar y reescribir módulos (parser, `Move.apply`) delante del profe.

---

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Romper la base al extender (§6) | Suite de regresión con los ejemplos de los profesores; extensiones solo tras F11 verde |
| Percepciones O(n·vision²) por tick | Índice espacial + caché de "más cercano" |
| RNG tocado por la hebra de UI | Todo el RNG vive en el motor; UI solo envía `step()` |
| Error con línea incorrecta | `line` arrastrada por token y por nodo AST |
| UI hablando con el intérprete (§5) | Solo `sim/engine.py` expone `step()/state()` |
| No entender el código en la defensa | Parser e intérprete escritos a mano; notas de diseño |

---

## 7. Decisiones tomadas

| # | Decisión | Elegido | Base |
|---|---|---|---|
| **D1** | Coordenadas de `see`/`name` | **Absolutas** (mismo sistema que `x`,`y`); **`x+1` = derecha, `y+1` = abajo** | §2.6 «`x` crece hacia la derecha e `y` hacia abajo»; §2.4 `dx=1` derecha; Anexo `hobbit.ins` `see(x+1,y)` ↔ `reproduce(1,0,20)` |
| **D2** | `a % 0` | **Íctus** (igual que `/ 0`): error de ejecución, muere, log con línea | §2.8 «división por cero»; coherencia con Python |
| **D3** | Nombres protegidos frente a asignación | **Percepciones (§2.6) + constantes `NONE/GROUND/OBJECT/ALLY/ENEMY` + `see`/`name`**. Las 7 acciones **no** | §2.3 «no se puede asignar a una percepción ni a una constante»; acciones = catálogo libre |
| **D4** | Empates de "más cercano" | Orden fijo **(dist, y, x)** | §2.6 «uno cualquiera, pero siempre el mismo mientras la situación no cambie» |
| **D5** | Alcance de `roar` | **Radio al emitir**: al fin de tick se guarda `{posición, texto, oyentes (Chebyshev ≤ vision)}`; al tick siguiente se rellena `roars_near`/`last_roar` y se vacía | §2.4 «en el tick siguiente»; §2.6 «rugieron en el tick anterior» |
| **D6** | Semilla en la UI | **Campo visible + botón «repetir con esta semilla»** | §2.6 generador con semilla; §4.1 extensión de repetición |
| **D7** | Librería gráfica | **Pygame** (única dependencia) | §4.1 libre; §5 solo exige terminal |
| **D8** | Temática | **Stands y facciones**: criaturas = usuarios de Stand (Jotaro, Dio, Joseph, Polnareff, Kakyoin); facciones Joestar/Dio/Hamon. Terreno: hierba = césped de Morioh, roca = adoquín; objetos: steamroller, cuchillos. `consume` = drenar sangre/hamon, `roar` = «menacing», `say` = frase famosa | §1 temática libre; §6 sin tocar nombres/efectos de las 7 acciones |

**Pendientes menores (no bloqueantes):** textos/estética de la UI, cuántas extensiones JoJo se implementan (mínimo viable: ejemplos de `.ins`/`.te`/`.ob`/`.map` que usen solo la base).
