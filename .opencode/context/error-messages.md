<!-- Context: main@309265f -->
# Catálogo de mensajes de error

> **Regla del proyecto: todo mensaje de error va en español.** Quien los lee es el
> usuario final leyendo los logs de la aplicación (spec §4.1) o el profesor en la
> defensa (§6). Los identificadores del código (clases, funciones, variables, tipos de
> token) van en inglés. Este fichero es el catálogo de referencia: **al añadir un
> mensaje nuevo, añádelo aquí en el mismo commit.**

Los números de línea son orientativos (se desplazan al editar); lo estable es el
fichero + la función.

---

## 1. Forma común — `instinct/frontend/errors.py`

Toda excepción de compilación hereda de `CompileError(line, message)`, que formatea:

```
línea {line}: {message}
```

| Clase | Cuándo |
|---|---|
| `LexError` | El scanner no puede convertir un trozo a token (`scanner.py`) |
| `ParseError` | Las fichas no encajan en ninguna forma de línea / no forman una expresión (`parser.py`) |
| `SemanticError` | La forma es válida pero el significado no (F3: cabecera, etiquetas, catálogos) |

Los errores **no interrumpen el proceso**: el scanner y el parser los **recogen** en
listas (`ScanResult.errors`, `ParseResult.errors`) para reportar varios de una vez, y
`ParseResult` devuelve `program=None` en cuanto hay un solo error (spec §2.8: el archivo
se rechaza entero). Los errores de ejecución (F7) no se recogen: dan un ictus y la
criatura muere.

---

## 2. Scanner — `instinct/frontend/scanner.py` (3 mensajes)

| Mensaje | Nace en | Cuándo |
|---|---|---|
| `carácter inesperado '!'` | `_scan_token` L88 | Un `!` que no es `!=` (la spec no tiene `not` en forma de símbolo) |
| `carácter inesperado {char!r}` | `_scan_token` L100 | Cualquier otro carácter fuera del conjunto del lenguaje |
| `literal de texto sin cerrar` | `_scan_text` L122 | `"` sin su cierre antes del fin de línea o del archivo |

Los tres descartan el resto de la línea para que los tokens no se filtren a la
siguiente (modo pánico). El del texto sin cerrar reporta la línea **de apertura**, no
la de cierre.

---

## 3. Parser — `instinct/frontend/parser.py` (18 mensajes)

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

## 4. Pendientes (spec §2.8, PLAN §2) — aún NO implementados

Estos mensajes **todavía no existen en el código**. Se anotan aquí para que F3, F7 y
F8 las formulen en español desde el principio, no para dar por hecho que existen.

**F3 — compilación** (`SemanticError` en `resolver.py`): cabecera incompleta o con las
claves en mal orden, valor fuera de rango (`health ≤ 0`, `vision < 1`, `lifespan ≤ 0`),
falta `start:`, etiqueta duplicada, salto a etiqueta inexistente, asignación a una
percepción o a una constante, nombre de acción o de función desconocido, número de
argumentos distinto del esperado, mapa con un `char` no declarado.

**F7 — ejecución** (dan ictus, la criatura muere, van a los logs con su línea):
división por cero, resto por cero (decisión **D2**: también ictus), lectura de variable
no asignada, `dx`/`dy` fuera de `{-1, 0, 1}`, mezclar entero y texto en un operador no
lógico, texto donde se exige un número.

---

## 5. Tests

Los tests afirman pares `(line, message)` **exactos** (`tests/test_scanner.py`,
`tests/test_parser.py`). Cambiar un mensaje es romper la suite a propósito: obliga a
revisar el texto en lugar de colarlo en silencio. Al traducir, se actualizan código y
tests en el mismo commit.