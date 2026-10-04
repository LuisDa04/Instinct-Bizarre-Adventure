<!-- Context: main@793547e -->
# Catálogo de mensajes de error

> **Regla del proyecto: todo mensaje de error va en español.** Quien los lee es el
> usuario final leyendo los logs de la aplicación (spec §4.1) o el profesor en la
> defensa (§6). Los identificadores del código (clases, funciones, variables, tipos de
> token) van en inglés. Este fichero es el catálogo de referencia: **al añadir un
> mensaje nuevo, añádelo aquí en el mismo commit.**

Los números de línea son orientativos (se desplazan al editar); lo estable es el
fichero + la función.

---

## 1. Forma común — `instinct/compiler/errors.py`

Toda excepción de compilación hereda de `CompileError(line, message)`, que formatea:

```
línea {line}: {message}
```

| Clase | Cuándo |
|---|---|
| `LexError` | El scanner no puede convertir un trozo a token (`lexer.py`) |
| `ParseError` | Las fichas no encajan en ninguna forma de línea / no forman una expresión (`parser.py`) |
| `SemanticError` | La forma es válida pero el significado no (F3: cabecera, etiquetas, catálogos) |

Los errores **no interrumpen el proceso**: el scanner y el parser los **recogen** en
listas (`ScanResult.errors`, `ParseResult.errors`) para reportar varios de una vez, y
`ParseResult` devuelve `program=None` en cuanto hay un solo error (spec §2.8: el archivo
se rechaza entero). Los errores de ejecución (F7) no se recogen: dan un ictus y la
criatura muere.

---

## 2. Scanner — `instinct/compiler/lexer.py` (3 mensajes)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `carácter inesperado '!'` | `_scan_token` L88 | Un `!` que no es `!=` (la spec no tiene `not` en forma de símbolo) |
| `carácter inesperado {char!r}` | `_scan_token` L100 | Cualquier otro carácter fuera del conjunto del lenguaje |
| `literal de texto sin cerrar` | `_scan_text` L122 | `"` sin su cierre antes del fin de línea o del archivo |

Los tres descartan el resto de la línea para que los tokens no se filtren a la
siguiente (modo pánico). El del texto sin cerrar reporta la línea **de apertura**, no
la de cierre.

---

## 3. Parser — `instinct/compiler/parser.py` (18 mensajes)

### Cabecera (spec §2.2)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba una clave de cabecera` | `_parse_header` L69 | La línea no empieza por un identificador |
| `token inesperado tras una entrada de cabecera` | `_parse_header` L71 | Sobra algo: `health 80 90` |
| `valor de cabecera inválido` | `_parse_header_value` L91, L94 | El valor no es nombre, entero ni entero negativo |

### Despacho de instrucción (spec §2.3)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `línea inválida` | `_parse_statement` L114 | La línea no encaja en ninguna de las 5 formas |

### Etiqueta

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba el nombre de una etiqueta` | `_parse_label` L117 | Falta el identificador antes del `:` |
| `se esperaba ':' tras el nombre de la etiqueta` | `_parse_label` L118 | `wander` sin los dos puntos |

### Salto

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba 'goto'` | `_parse_goto` L123 | Rama muerta: `goto` se detecta en `_parse_statement` antes de mirar la línea |
| `se esperaba el nombre de una etiqueta tras 'goto'` | `_parse_goto` L124, `_parse_if_goto` L132 | `goto` sin etiqueta |

### Salto condicional

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba 'if'` | `_parse_if_goto` L129 | Rama muerta por el mismo motivo que arriba |
| `se esperaba 'goto' tras la condición` | `_parse_if_goto` L131 | `if x flee` — la condición acaba en `goto`, no en un valor |

### Asignación

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba el nombre de una variable` | `_parse_assign` L137 | Rama muerta: `=` se detecta en `_parse_statement` |
| `se esperaba '=' tras el nombre de la variable` | `_parse_assign` L138 | Rama muerta por el mismo motivo |

### Acción

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba el nombre de una acción` | `_parse_action_call` L144 | Rama muerta: `(` se detecta en `_parse_statement` |
| `se esperaba '(' tras el nombre de la acción` | `_parse_action_call` L145 | Rama muerta por el mismo motivo |

### Expresiones (spec §2.5)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `se esperaba una expresión` | `_parse_precedence` L157 | Donde se esperaba un valor: `1 +`, `f(1,`, `f(1,)` |
| `se esperaba ')' tras la expresión` | `_prefix_grouping` L227 | `(a` sin cerrar |
| `se esperaba ')' tras los argumentos` | `_parse_argument_list` L252 | `f(1` sin cerrar |

### Fin de línea

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `token inesperado tras la instrucción` | `_consume_end_of_line` L174 | Sobra algo en la línea: `x = 1 2`, `wait(1) extra` |

Las filas marcadas como *rama muerta* existen por robustez: `_parse_statement` ya ha
descartado esos casos mirando `IDENT`/`=`/`(`, así que nunca se disparan hoy. Se
conservan para que el parser siga siendo correcto si alguien llama a los
`_parse_*` directamente o cambia el reparto.

---

## 4. Resolver — `instinct/compiler/semantic.py` (15 mensajes)

Solo se invoca si el parser devolvió un `Program` sin errores. Recoge varios
`SemanticError` de una vez (cabecera → etiquetas → cuerpo, en ese orden) y
devuelve `resolved=None` en cuanto hay uno solo: el archivo se rechaza entero.

Los nombres y aridades válidos viven en `instinct/compiler/catalogs.py`
(`ACTION_ARITY`, `FUNCTION_ARITY`, `PERCEPTIONS`, `CONSTANTS`, `HEADER_KEYS`).

### Cabecera (spec §2.2)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `la primera línea debe ser 'creature Nombre'` | `_check_header` L84 | La primera entrada no es `creature` |
| `falta la clave 'vision' en la cabecera` | `_check_header` L87 | Falta alguna de las 5 (una por cada ausente; la clave va entre comillas) |
| `clave de cabecera desconocida 'speed'` | `_check_header` L78 | Una clave que no es de las 5 |
| `clave de cabecera duplicada 'health'` | `_check_header` L80 | La clave aparece dos veces (se reporta la segunda) |
| `valor de cabecera inválido` | `_header_text` L111, `_header_range` L119 | `creature`/`faction` con número, o `health`/`vision`/`lifespan` con nombre |
| `health debe ser mayor que 0` | `_header_range` L122 | `health < 1` (el parser guarda los negativos a propósito para esto) |
| `vision debe ser mayor o igual que 1` | `_header_range` L122 | `vision < 1` |
| `lifespan debe ser mayor que 0` | `_header_range` L122 | `lifespan < 1` |

Sin entradas de cabecera (archivo vacío) salen los 5 `falta la clave…` con la
línea 1. Una clave ausente no impide revisar el resto: todo se recoge junto.

### Etiquetas (spec §2.3, §2.8)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `falta la etiqueta 'start:'` | `_collect_labels` L136 | No hay ninguna etiqueta `start` (línea 1 del archivo) |
| `etiqueta duplicada 'flee'` | `_collect_labels` L130 | Segunda definición del mismo nombre |
| `salto a etiqueta inexistente 'nowhere'` | `_check_target` L153 | `goto` o `if…goto` a una etiqueta no definida (valen los saltos hacia adelante) |

### Asignación (spec §2.3, decisión D3)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `no se puede asignar a la percepción 'health'` | `_check_assign_target` L157 | El destino es una de las 31 percepciones de §2.6 |
| `no se puede asignar a la constante 'NONE'` | `_check_assign_target` L159 | El destino es `NONE/GROUND/OBJECT/ALLY/ENEMY` |
| `no se puede asignar a la función 'see'` | `_check_assign_target` L161 | El destino es `see` o `name` |

### Acciones y funciones (spec §2.4, §2.5, §2.8)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `acción desconocida 'shoot'` | `_check_action` L166 | La acción no está en el catálogo (p. ej. usar `see` como instrucción) |
| `la acción 'wait' espera 1 argumento, no 2` | `_check_action` L168 | Aridad distinta (`_arity_message`: singular con 1, plural si no) |
| `función desconocida 'volar'` | `_check_expr` L179 | La llamada en una expresión no es `see`/`name` (p. ej. usar `wait` en una cuenta) |
| `la función 'see' espera 2 argumentos, no 1` | `_check_expr` L181 | Aridad distinta |

`_check_expr` baja por toda la expresión (`Binary`/`Logical`/`Unary`/`Group`/
argumentos de llamada), así que también caza `wait(see(1))` o
`if see(x) > 0 goto start`. Lo que F3 **no** comprueba a propósito: tipos,
`dx`/`dy` fuera de rango, variable no asignada — §2.8 los lista como errores
de **ejecución** (ictus, F7), aunque el argumento sea un literal.

---

## 5. Loaders — `instinct/loaders/` (10 mensajes)

`LoadError(line, message, path="")` hereda de `CompileError` (decisión **D9**):
el formato es el mismo (`línea N: mensaje`); `.path` lo rellena el escaneo de
directorios para el log por archivo (spec §4.1.1). Los dos formatos comparten
el parser de `definition.py`: cada línea con contenido es `clave valor`; `#`
solo vale como comentario a línea completa (decisión **D11**: así `char #` del
`rock.ob` del Anexo sigue funcionando).

### Primera línea y forma (spec §3.2)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `la primera línea debe ser 'terrain Nombre'` | `_parse_first` | La primera línea con contenido no es `terrain Nombre` (`'object Nombre'` en `object_loader`) |
| `línea inválida` | `_parse_entry` | La línea no es `clave valor` (1 token o 3+) |

### Claves y valores

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `falta la clave 'regen'` | `parse_definition` | Clave obligatoria ausente (línea de la primera entrada; 1 si el archivo está vacío) |
| `clave desconocida 'speed'` | `_parse_entry` | Clave fuera de las de su clase (`regen` en un `.ob` también cae aquí) |
| `clave duplicada 'char'` | `_parse_entry` | Segunda aparición de la misma clave |
| `el valor de 'resource_max' debe ser un entero` | `entry_int` | Valor no numérico |
| `char debe ser un solo carácter` | `entry_char` | `char ab` |
| `resource_max debe ser mayor o igual que 0` | `entry_range` | Valor negativo (decisión **D10**: 0 es legal) |
| `regen debe ser mayor o igual que 0` | `entry_range` | Igual |

### Registro (invariante I14, `registry.py`)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `el char '.' ya está declarado por 'Grass'` | `_claim` | Otro archivo declara el mismo char (vale entre `.te` y `.ob`); se reporta en la línea del `char` del segundo archivo |

---

## 6. Pendientes (spec §2.8, PLAN §2) — aún NO implementados

Estos mensajes **todavía no existen en el código**. Se anotan aquí para que F7 y
F8 los formulen en español desde el principio, no para dar por hecho que existen.

**F7 — ejecución** (dan ictus, la criatura muere, van a los logs con su línea):
división por cero, resto por cero (decisión **D2**: también ictus), lectura de variable
no asignada, `dx`/`dy` fuera de `{-1, 0, 1}`, mezclar entero y texto en un operador no
lógico, texto donde se exige un número.

**F8 — mapa** (`char` no declarado, spec §3.3): rechazo con char y línea, la app sigue.

---

## 6. Tests

Los tests afirman pares `(line, message)` **exactos** (`tests/test_scanner.py`,
`tests/test_parser.py`, `tests/test_resolver.py`, `tests/test_loaders.py`). Cambiar un mensaje es romper la suite a propósito: obliga a
revisar el texto en lugar de colarlo en silencio. Al traducir, se actualizan código y
tests en el mismo commit.