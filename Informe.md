## Severidad alta

### 1. El intérprete despacha expresiones y sentencias mediante `isinstance`

* **Dónde:** `instinct/lang/interpreter.py:103-119` (`_run_stmt`) y `157-188` (`_eval`).
* **Cuál es el error:** Tanto la evaluación de expresiones (`Literal`, `Variable`, `Group`, `Unary`, `Binary`, `Logical`, `Call`) como la ejecución de sentencias (`Label`, `Goto`, `IfGoto`, `Assign`, `ActionCall`) se resuelven con cadenas centralizadas de `isinstance(...)` dentro del intérprete.
* **Por qué es un error:** Contradice directamente el diseño orientado a objetos pedido en la sección 5 del enunciado (*"Cada nodo sabe evaluarse solo"* y evitar cadenas de `if` por tipo en el intérprete). Aunque las acciones, las entidades del mundo y las percepciones sí están desacopladas, el núcleo del intérprete queda acoplado a cada clase concreta del AST, obligando a modificar el intérprete cada vez que se extienda el lenguaje y afectando el criterio principal de evaluación arquitectónica (§5 y §6).
* **Idea para corregirlo:** Mueve la responsabilidad de evaluarse/ejecutarse a las propias clases del AST usando polimorfismo. Como `compiler/ast_nodes.py` no debe importar módulos de `lang/` ni `world/` (para no crear dependencias circulares), aplica inversión de dependencias: define un contrato o interfaz abstracta para el contexto de ejecución en la capa del compilador y haz que el intérprete lo implemente y lo pase a los nodos. Ten en cuenta preservar el avance de `pc`, el límite de 100 líneas por turno y el cortocircuito lógico de `and`/`or`.

---

## Severidad media

### 2. Hot-reload incompleto, con reinicio de estado y desajuste entre nombre de archivo y especie

* **Dónde:** `instinct/ui/editor/hot_reload.py:44, 52-73`, `instinct/ui/editor/editor_widget.py:261-262`, `instinct/loaders/creature_loader.py:88`, `instinct/world/entities.py:128-131` y `tests/test_ui_hot_reload.py:19-21`.
* **Cuál es el error:**
  1. `_recolocar_si_existe` recorre la grilla y hace `return` tras encontrar la **primera** criatura coincidente; el resto de individuos de esa especie siguen ejecutando el código viejo.
  2. Al sustituir la criatura, la retira del mundo y crea una instancia nueva de `Creature`, perdiendo su vida actual, edad, variables guardadas y turnos de `wait` pendientes.
  3. El editor pasa el nombre del archivo sin extensión (`tab.path.stem`, p. ej. `"dio"`), mientras que el cargador indexa las especies por el nombre declarado en la cabecera (`creature Name`, p. ej. `"Dio"`). Cuando difieren en texto o mayúsculas, no encuentra las criaturas en el mapa y además crea una entrada duplicada en el registro de especies.
  4. `Creature.__init__` copia atributos de cabecera (`name`, `faction`, `vision`, `lifespan`) en la instancia, por lo que cambiar esos valores y actualizar solo el programa dejaría los atributos viejos en las criaturas vivas.
  5. El test `test_ui_hot_reload.py` intenta seleccionar `"Morioh Town"` sobre un `tmp_path` vacío, falla silenciosamente dejando `world = None` y nunca llega a probar el reemplazo de criaturas en un mapa real.
* **Por qué es un error:** En una simulación con varias criaturas de la misma especie, el hot-reload solo afecta a una y además la "resucita" con salud llena y edad 0 (rompiendo la continuidad de la simulación y el principio de §4.1 de no alterar entidades durante la ejecución). Por el desajuste de nombres, además, falla con los propios `.ins` del proyecto.
* **Idea para corregirlo:** Identifica la especie a partir del programa compilado en lugar del nombre de archivo. En vez de quitar y volver a colocar criaturas en la grilla, recorre todas las instancias vivas de esa especie en el mundo y actualiza su programa en el sitio (junto con los atributos de cabecera que corresponda sincronizar), manteniendo su posición, salud, edad, variables y `wait_remaining`. Ten especial cuidado con `pc`: al ser un índice entero sobre las líneas anteriores, conservar el valor previo puede apuntar a otra instrucción o salirse de rango si cambiaste líneas, así que conviene reiniciarlo a la etiqueta de inicio. Añade además un test que coloque varias criaturas en un mapa válido y verifique que todas cambian de programa sin perder su estado.

### 3. Hot-reload rompe el encapsulamiento de `Session`

* **Dónde:** `instinct/ui/editor/hot_reload.py:44, 70`.
* **Cuál es el error:** `HotReloadManager` modifica directamente el registro de criaturas accediendo a atributos internos privados de la sesión (`self._session._cli.loaded.creatures`).
* **Por qué es un error:** Acopla el editor a la estructura interna de `Session` y del `CLI`, rompe la frontera entre UI de edición y capa de simulación, y asume sin comprobar que `loaded` ya existe. Cualquier cambio futuro en cómo `Session` guarda el estado o las criaturas romperá el editor.
* **Idea para corregirlo:** Define una operación pública en `Session` encargada de actualizar una especie compilada tanto en el catálogo cargado como en el mundo activo, y haz que el gestor de hot-reload trabaje únicamente a través de esa interfaz pública (integrándolo con la corrección del punto 2).

### 4. `processEvents()` de Qt se ejecuta dentro del bucle de eventos de Pygame

* **Dónde:** `instinct/ui/app.py:90-92`.
* **Cuál es el error:** La llamada `self._qt_app.processEvents()` está dentro del `for event in pygame.event.get():`.
* **Por qué es un error:** En cualquier frame donde no entren eventos en la ventana de Pygame, Qt no procesa ningún evento, congelando la ventana del editor y sus temporizadores (como el linter). A la inversa, cuando llegan múltiples eventos de Pygame en un mismo frame (p. ej. movimiento del ratón), Qt procesa su cola varias veces en mitad de la iteración, pudiendo disparar callbacks (como el hot-reload) de forma reentrante mientras Pygame aún está procesando eventos.
* **Idea para corregirlo:** Saca el procesamiento de eventos de Qt del `for` de Pygame para que se ejecute una única vez por iteración del bucle principal.

### 5. Uso de `assert` con efectos secundarios en rutas normales de ejecución

* **Dónde:** `instinct/world/world.py:176` y `instinct/lang/actions/reproduce.py:51` (además de invariantes sin efectos secundarios en `instinct/lang/perceptions.py:70`, `instinct/lang/functions.py:91`, `instinct/lang/actions/strike.py:27` y `instinct/lang/actions/wait.py:33`).
* **Cuál es el error:** `World.move_creature` (`assert self.remove_creature(...) is creature`) y `Reproduce.apply` (`assert ctx.world.place_creature(...)`) ejecutan llamadas que modifican el estado del mapa dentro de sentencias `assert`.
* **Por qué es un error:** `assert` es una herramienta de depuración que Python elimina por completo cuando se ejecuta con optimización (`python -O`). En ese modo, las llamadas dentro del `assert` dejan de ejecutarse: al moverse, la criatura nunca se retira de la celda origen y queda duplicada en el mapa; al reproducirse, la madre pierde vida y la cría se encola en el motor, pero nunca se coloca en la grilla.
* **Idea para corregirlo:** Ejecuta primero la operación que modifica el estado guardando su resultado en una variable y, después, comprueba ese resultado de forma explícita lanzando una excepción de tiempo de ejecución (`RuntimeError` o similar) si falla la invariante. Conviene aplicar el mismo criterio para reemplazar los `assert` usados como validación de invariantes en ejecución normal.

---

## Severidad baja

### 6. Inconsistencia entre docstring y código generado en `Diagnostic.code`

* **Dónde:** `instinct/ui/editor/compiler_bridge.py:33, 40, 61`.
* **Cuál es el error:** El docstring de `Diagnostic` documenta los valores `"LEXICAL"`, `"SYNTAX"` y `"SEMANTIC"`, mientras que `compile_source` genera `"LEX"`, `"PARSE"` y `"SEMANTIC"` manipulando el nombre de la clase de error (`error.__class__.__name__.upper().replace("ERROR", "")`).
* **Por qué es un error:** Aunque actualmente ningún módulo ni test consume `.code`, la discrepancia entre lo documentado y lo devuelto inducirá errores en cuanto alguien filtre o muestre diagnósticos guiándose por el docstring.
* **Idea para corregirlo:** Alinea la generación del código con lo documentado usando un mapeo explícito por tipo de error del compilador en lugar de transformar cadenas sobre el nombre de la clase.

### 7. Anotaciones con `Optional` sin importar en `app.py`

* **Dónde:** `instinct/ui/app.py:67-68`.
* **Cuál es el error:** Se utilizan `Optional[QMainWindow]` y `Optional[EditorWidget]` sin importar `Optional` de `typing`.
* **Por qué es un error:** En tiempo de ejecución no falla únicamente gracias a `from __future__ import annotations`, pero rompe comprobadores estáticos de tipos y cualquier introspección de anotaciones en runtime.
* **Idea para corregirlo:** Sustitúyelo por la sintaxis `| None` utilizada en el resto del código base o añade el import correspondiente.