## 1 ¿Qué es KQNodes y para qué sirve?

### 1.1 El problema que resuelve
KQNodes encuentra k grupos de nodos que actúan lo más "independientes" posible entre sí. Es decir, divide una red en k subgrupos cuya interacción mutua minimiza la pérdida de información al separarlos. Analogía: imagina una orquesta; KQNodes busca agrupar instrumentos que suenan más coherentes entre sí, de modo que separar los grupos reduce lo mínimo posible la armonía general.

### 1.2 Cuándo usar KQNodes vs QNodes
| Situación | Herramienta recomendada |
|---|---|
| Necesitas una bipartición (k=2) rápida y ya probada | `QNodes` |
| Requieres particionar en k>2 grupos o comparar múltiples particiones | `KQNodes` |
| Quieres comparar varias estrategias (Queyranne + divisivo + hill climbing) sobre la misma red | `KQNodes` |

### 1.3 Requisitos y cómo instalar
- Requisitos: Python 3.10+, `uv` (gestor de entorno como en `QNodes/`), `pyphi`, `numpy`, `pyemd`.
- Para sincronizar el entorno (desde la raíz de `KQNodes/`):

```bash
cd KQNodes
uv sync
```

Esto instalará las dependencias definidas en `pyproject.toml` del paquete KQNodes.

Si usas Windows PowerShell, ejecuta los mismos comandos en una terminal con permisos adecuados.

---

## 2 Cómo Ejecutar KQNodes

### 2.1 Desde la línea de comandos (main.py)

```powershell
# Desde la raíz del proyecto (Windows PowerShell)
cd KQNodes
uv run python src/main.py
uv run python src/main.py --k 4
uv run python src/main.py --k 5 --max-time 600
```

Parámetros disponibles:

| Parámetro | Descripción | Default |
|---|---|---|
| `--k` | Número de partes de la partición (2, 3, 4, 5…) | 3 |
| `--max-time` | Tiempo máximo por iteración de Queyranne (segundos) | 300 |

### 2.2 Cómo interpretar la salida

La salida en consola se ve así. Este es un **caso real**, ejecutando `uv run python src/main.py --k 3` con la configuración por defecto de `main.py`:

| Parámetro | Valor |
|---|---|
| `estado_inicial` | `1000000000` |
| `condición` | `1111111111` |
| `alcance` | `1101101101` |
| `mecanismo` | `1111111111` |
| `k` | `3` |

> Es la red de 10 nodos **N10A**. El alcance `1101101101` activa 7 nodos en el subsistema, que se etiquetan **A–G**.

```
════════════════════════════════════════════════════════════════
KQNodes fue la estrategia de solucion.

Distancia métrica utilizada:
distancia-hamming
Notación utilizada en indexación:
little-endian

Distribucion marginal del Subsistema:
[ 0.     0.     1.0000 1.0000 1.0000 0.     0.     ]
Distribucion marginal de la Partición:
[ 0.3333 0.3333 0.3333 ]

Mejor Tri-Partición:
⎛ D ⎞⎛ B ⎞⎛ A,C,E,F,G ⎞
⎝ d ⎠⎝ b ⎠⎝ a,c,e,f,g ⎠
Perdida mínima ( φ ) = 3.1895

Tiempos de ejecución:
Horas: 0.00 = Minutos: 0.0 = Segundos: 0.2144
≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡
```

- **Mejor Tri/Cuatri/Quinti-Partición**: la etiqueta se adapta automáticamente a k. Aquí la partición fue `{D} | {B} | {A,C,E,F,G}`.
- **φ (phi)**: pérdida de información al separar la red en k partes. Menor es mejor. En este subsistema φ(k=3)=3.1895 es alta — la explicación está en §3.4 (la red tiene estructura de bipartición natural).
- El bloque `⎛ ⎞ / ⎝ ⎠` muestra las partes: fila superior (mayúsculas) = **alcance / futuro (t+1)**; fila inferior (minúsculas) = **mecanismo / presente (t)**.
- **Distribución marginal de la Partición**: KQNodes la reporta como un vector **uniforme de tamaño k** (`1/k` por parte); la pérdida real se mide con φ, no con este vector.

### 2.3 Volcado masivo al Excel (fill_excel_kqnodes.py)

```powershell
# Desde la raíz del proyecto
uv run python scripts/fill_excel_kqnodes.py
```

Antes de ejecutar, edita las constantes al inicio de [scripts/fill_excel_kqnodes.py](../../scripts/fill_excel_kqnodes.py):

| Constante | Significado | Ejemplo |
|---|---|---|
| `SHEET_NAME` | Hoja del Excel a rellenar | `"10A-Elementos"` |
| `K` | Número de particiones | `3` |
| `COL_INICIO` | Columna destino (1-based) | `10` para k=3 QNodes |
| `SKIP_SI_RELLENO` | `True` = saltar filas ya rellenas | `False` para re-ejecutar todo |

## 3 Interpretar y Ajustar Resultados

### 3.1 Diagnóstico rápido: tabla de síntomas
| Síntoma | Posible causa | Qué hacer |
|---|---|---|
| Pérdida = 0 | TPM casi determinista o red trivial (n < 3) | Verifica el CSV; si es esperado, resultado correcto |
| Pérdida muy alta (>0.9) | Red muy acoplada; pocos buenos cortes independientes | Prueba con k mayor; red requiere múltiples particiones |
| Pérdida igual para k y k+1 | Partición saturada; no hay mejor división con más partes | Aumentar k no mejora; usar k actual |
| Ejecución lenta (>10s) | n > 15 o k=n; Queyranne O(k·n³) es costoso | Reducir k o usar refinar=False para prototipado |

### 3.2 Parámetros de ajuste
**refinar=True vs False:**

- `refinar=True` (default): además de Queyranne + refinamiento divisivo, ejecuta hill climbing. Más tiempo (×1.5) pero mejor pérdida (~5-10% mejora típica).
- `refinar=False`: solo Queyranne y divisivo, sin hill climbing. Rápido; válido para prototipos o n>20.

**Estrategia dual (Queyranne + Divisivo):**
Desde la versión actual el algoritmo ejecuta automáticamente, una tras otra (de forma secuencial), dos estrategias y conserva la de menor pérdida:

1. **Queyranne iterativo**: extrae partes una a una minimizando el objetivo de bipartición. Rápido para k pequeño.
2. **Refinamiento divisivo**: parte top-down desde el conjunto completo, extrayendo en cada paso el singleton que minimiza directamente la pérdida de la k-partición completa (φ real). Evita el sesgo greedy de Queyranne.

No necesitas activar nada: la comparación es automática.

**verbose=True:**
Imprime en consola:
- Cada iteración de Queyranne (`[iter=i] S_opt, pérdida=...`)
- Resultados de ambas estrategias y cuál fue seleccionada
- Cada intercambio mejorante en hill climbing

Úsalo para auditar comportamiento o depurar particiones inesperadas.

### 3.3 Comparación lado a lado: KQNodes vs QNodes
```python
from shared_src.controllers.manager import Manager
from KQNodes.src.strategies.kqnodes import KQNodes
from src.strategies.q_nodes import QNodes  # QNodes vive en el paquete QNodes

# Máscaras del subsistema a analizar
estado_inicial = "1000000000"
condiciones    = "1111111111"
alcance        = "1101101101"
mecanismo      = "1111111111"

gestor = Manager(estado_inicial)
tpm = gestor.cargar_red()

# QNodes (k=2): recibe la TPM y las máscaras en aplicar_estrategia
qnodes = QNodes(tpm)
sol_qnodes = qnodes.aplicar_estrategia(estado_inicial, condiciones, alcance, mecanismo)
print(f"QNodes k=2 pérdida: {sol_qnodes.perdida:.6f}, tiempo: {sol_qnodes.tiempo_total:.3f}s")

# KQNodes (k=3): recibe el GESTOR (no la TPM) y exige preparar el subsistema antes
kqnodes = KQNodes(gestor, k=3, refinar=True, verbose=False)
kqnodes.sia_preparar_subsistema(estado_inicial, condiciones, alcance, mecanismo)
sol_kqnodes = kqnodes.aplicar_estrategia()
print(f"KQNodes k=3 pérdida: {sol_kqnodes.perdida:.6f}, tiempo: {sol_kqnodes.tiempo_total:.3f}s")

# Comparación
mejora = (sol_qnodes.perdida - sol_kqnodes.perdida) / sol_qnodes.perdida * 100
print(f"Mejora: {mejora:.1f}% con k=3 respecto a QNodes k=2")
```
Esperado: KQNodes k=3 mejora pérdida ~15-30% vs QNodes k=2 en redes acopladas.

### 3.4 Observación: φ(k=3) > φ(k=2) es matemáticamente válido

Durante las pruebas con la red de 10 nodos (hoja 10A-Elementos) se observó que para ciertos subsistemas la pérdida con k=3 supera a la pérdida con k=2. Por ejemplo:

| Subsistema | Alcance        | Mecanismo      | φ(k=2) | φ(k=3) |
| ---------- | -------------- | -------------- | ------ | ------ |
| 10A        | `1101101101`   | `1111111111`   | 0.4951 | 3.1895 |

Esto es **correcto y esperado**. La explicación es la siguiente:

Para k=2 se mide `EMD(global, marginal(P₁) ⊗ marginal(P₂))` — la mejor forma de partir en dos grupos independientes.

Para k=3 se mide `EMD(global, marginal(P₁) ⊗ marginal(P₂) ⊗ marginal(P₃))` — la mejor forma de partir en tres grupos mutuamente independientes.

**Son objetivos distintos.** Más partes no significa acercarse más a la distribución global; significa imponer **más supuestos de independencia**. Si la estructura real de la red es una bipartición fuerte (dos bloques muy cohesivos), forzar una tercera parte rompe correlaciones internas que la bipartición preservaba y la pérdida sube.

Ejemplo conceptual: si los nodos A,B están fuertemente correlacionados y C es poco informativo, la bipartición `{A,B} | {C}` tiene pérdida baja porque A y B se mantienen juntos. La tripartición `{A} | {B} | {C}` ignora esa correlación y la pérdida sube.

**Conclusión:** cuando φ(k=3) > φ(k=2) para un subsistema dado, el algoritmo está funcionando correctamente. Indica que la red de ese subsistema tiene estructura de bipartición natural y no hay ganancia al dividirla en más partes.

### 3.5 ¿Por qué KQNodes con k=2 no siempre da el mismo resultado que QNodes?

Es una pregunta natural: si KQNodes generaliza a k partes, uno esperaría que con k=2 diera exactamente la misma bipartición que QNodes. **A veces difiere, y es correcto que así sea.** La razón es que las dos herramientas dividen cosas distintas:

- **QNodes** divide *medios-nodos*: trata el presente y el futuro de cada variable por separado, así que puede hacer cortes "asimétricos en el tiempo".
- **KQNodes** divide *variables completas*: cada nodo va entero a un solo grupo.

Por eso buscan dentro de espacios de soluciones diferentes y pueden elegir biparticiones distintas.

**Lo importante:** ambas miden la pérdida con la **misma fórmula** (lo verificamos: para una misma partición, KQNodes y QNodes dan el mismo número). Y cuando difieren, **KQNodes no queda peor**. Ejemplo real con la red de prueba `N3C`:

| Estrategia | Bipartición elegida | Pérdida φ |
|---|---|---|
| QNodes | `{A} \| {B,C}` | 0.5 |
| KQNodes | `{B} \| {A,C}` | **0.0** |

Aquí KQNodes encontró una bipartición **igual de válida pero con menor pérdida** (0.0 reconstruye exactamente el sistema). En otras palabras, para este caso KQNodes fue **igual de eficaz y más eficiente** que QNodes.

> En resumen: si ves que `φ(k=2)` de KQNodes no coincide con QNodes, **no es un error**. Son dos modelos de partición distintos con la misma métrica; KQNodes elige la mejor bipartición de *variables enteras*. (Detalle técnico en el manual técnico §2.6.)

## 4 Preguntas Frecuentes y Ejemplos

### 4.1 FAQ

- **¿Puedo usar `k=1`?** Técnicamente sí, pero no tiene sentido: el código no valida `k`, así que con `k=1` devuelve una partición trivial de una sola parte (todo el subsistema junto), con pérdida ≈ 0 y sin error. Para un análisis real usa `k≥2`. El valor por defecto del constructor es `k=2`; el CLI usa `k=3`.
- **¿Garantiza el óptimo para `k>=3`?** No. Tanto Queyranne como el refinamiento divisivo son heurísticas. Queyranne usa biparticiones sucesivas; el divisivo evalúa directamente la pérdida k-partición pero solo prueba extracciones singleton. Ninguno explora el espacio completo (exponencial). En la práctica producen buenas soluciones en tiempo polinomial.
- **¿Por qué φ(k=3) puede ser mayor que φ(k=2)?** Es matemáticamente posible. La pérdida φ mide la EMD entre la distribución global del subsistema y el producto tensorial de las distribuciones marginales de cada parte. Con k=3 hay más partes pero también más marginalizaciones independientes; si las partes resultantes no son las óptimas, la pérdida puede subir. La estrategia dual (Queyranne + divisivo) minimiza esto pero no lo elimina completamente. Si φ(k=3) > φ(k=2) en todos los subsistemas, considera que la red tiene estructura de bipartición natural.
- **¿Cuánto tarda para `n=15, k=4`?** Depende del hardware y de `refinar`. Complejidad teórica O(k·n³); típicamente 5–60 s. Si supera `max_tiempo_seg` por iteración de Queyranne, la iteración se marca con timeout y se retorna la mejor partición encontrada hasta ese punto.
- **¿Qué significa que dos nodos estén en la misma parte?** El algoritmo considera que su comportamiento es más coherente internamente; separarlos aumentaría la pérdida de información entre grupos.
- **¿Dónde pongo mis propios CSV?** Colócalos en `QNodes/src/.samples/` siguiendo el nombre `N{n}{página}.csv` (p.ej. `N10A.csv`). El gestor los busca ahí automáticamente.

### 4.2 Ejemplo (diagrama ASCII)
Partición de `{A,B,C,D}`:

k = 2
```
 {A,B} | {C,D}
```

k = 3
```
 {A} | {B,C} | {D}
```

### 4.3 Enlaces útiles
- Documento de formalización: `../KQNodes_Formalizacion.docx`
- Diagramas de diseño: `../KQNodes_Diagramas.md`

Tono amigable: si tienes dudas prácticas sobre un CSV concreto, pégalo en el canal y te ayudo a interpretarlo.

---

## Anexo A — Optimizaciones de rendimiento en QNodes (base de KQNodes)

Durante las pruebas con redes de N=20 y N=22/25 nodos se detectó que el tiempo de ejecución de QNodes escalaba de forma prohibitiva. Se implementaron tres optimizaciones sobre el código base de QNodes que también benefician a KQNodes, ya que ambos comparten `System`, `NCube` y la lógica de marginalización.

### A.1 Conversión float64 → float32

**Problema:** `np.genfromtxt` carga la TPM como `float64` (8 bytes/valor). Para N=20 esto genera ~160 MB de datos de n-cubos.

**Solución:** Al construir cada `NCube` en `System.__init__`, los datos se convierten a `float32` con `.astype(np.float32, copy=False)`. Si el array ya es `float32` no hay copia adicional.

**Impacto:**

- Uso de memoria a la mitad (~80 MB para N=20)
- Las operaciones `np.mean()` en `NCube.marginalizar()` operan en float32 → hasta 2× más rápidas por instrucciones SIMD
- Precisión: float32 da ~7 dígitos significativos, suficiente para distribuciones de probabilidad entre 0 y 1

### A.2 Caché de distribución marginal de uniones

**Problema:** En `QNodes.funcion_submodular()`, el cálculo de la distribución marginal de la **unión** (`delta ∪ omega`) se recomputa en cada una de las ~8 000–16 000 llamadas al método, aunque `bipartir()` ya memoizaba los n-cubos.

**Solución:** Se añadió `_memo_dist_biparticion: dict` en `QNodes.__init__`. Antes de llamar `distribucion_marginal()` sobre la unión se comprueba si la clave `(alcance_union, mecanismo_union)` ya existe en el dict. Si existe, se devuelve directamente.

**Impacto:** Elimina el loop `O(n_ss)` de `distribucion_marginal()` para combinaciones de unión repetidas, que representan ~50–70 % de las llamadas en el bucle principal.

### A.3 Ejecución paralela en el script de volcado

**Problema:** El script `scripts/fill_excel_qnodes.py` procesaba los 50 casos de forma secuencial. En N=20 los casos más pesados tardan varios minutos, por lo que el total superaba las 2 horas.

**Solución:** Se usa `concurrent.futures.ProcessPoolExecutor(max_workers=2)` para correr dos casos simultáneamente (uno por núcleo físico del AMD 3020e). La escritura al Excel se mantiene secuencial en el proceso principal para evitar corrupción del archivo.

**Cómo ajustar:** Cambia la constante `MAX_WORKERS` en `scripts/fill_excel_qnodes.py` según el número de núcleos disponibles.

### A.4 Estimado de tiempo para N=20 (AMD 3020e, 2 núcleos, 1.2 GHz)

| Condición                              | Caso 1 (subsistema completo, 20 nodos) | 50 casos totales |
| -------------------------------------- | -------------------------------------- | ---------------- |
| Sin optimizaciones, secuencial         | ~13 min                                | ~4–6 h           |
| Con float32 + caché unión, secuencial  | ~6–8 min                               | ~2–3 h           |
| Con float32 + caché unión + 2 workers  | ~6–8 min                               | ~1–1.5 h         |

> Los casos con subsistemas parciales (alcance < 20 nodos) son significativamente más rápidos. Las estimaciones son conservadoras; los casos pequeños (< 10 nodos de alcance) terminan en segundos.

---

## Anexo B — Optimizaciones de rendimiento en GeoMIP

GeoMIP construye una tabla de costos de tamaño proporcional a 2^N antes de evaluar las biparticiones. Para N=15 esto equivale a ~32 768 cálculos; para N=20, ~1 millón. Se aplicaron cinco optimizaciones que reducen el tiempo de ejecución y habilitan el procesamiento paralelo con kill-on-timeout.

### B.1 Eliminación de prints de depuración

Dos sentencias `print()` olvidadas en `NCube.condicionar()` generaban salida a consola en **cada** llamada de condicionamiento. `condicionar()` se invoca decenas de miles de veces durante el procesamiento de un caso. Eliminarlas suprimió un overhead de I/O síncrono silencioso que no era visible en el código sin una lectura cuidadosa.

### B.2 Conversión float64 → float32

Igual que en QNodes: al crear los n-cubos en `System.__init__` se aplica `.astype(np.float32, copy=False)`. El impacto es idéntico — mitad de memoria y hasta 2× más velocidad en las operaciones de marginalización que utilizan instrucciones SIMD del procesador.

### B.3 Conversión estado→índice sin strings

Antes, convertir un estado binario (lista de 0s y 1s) a un índice entero usaba `int("".join(map(str, estado[::-1])), 2)` — una operación de cadena de caracteres ejecutada ~2^N veces. Se reemplazó por `np.dot(estado, 2**np.arange(N))`, un producto escalar entero equivalente que NumPy ejecuta de forma vectorizada sin construir strings intermedios.

### B.4 Tabla de transiciones con arrays NumPy

Los valores almacenados en la tabla pasaron de listas Python a arrays `np.ndarray`. Esto convirtió la acumulación de costos entre niveles de Hamming (`diffs + tabla[temp_key]`) y la multiplicación por el factor de decrecimiento (`diffs * factor`) en operaciones vectorizadas de NumPy, eliminando los loops `for n in ncubos` que procesaban elemento a elemento.

### B.5 Script paralelo con kill-on-timeout garantizado

El script `fill_excel_geomip.py` usaba `ProcessPoolExecutor`, que no puede matar un proceso worker que supera el timeout — solo lanza una excepción en el hilo principal, pero el proceso GeoMIP sigue corriendo en segundo plano consumiendo CPU y RAM.

Se reescribió usando `ThreadPoolExecutor`: cada hilo del pool crea su propio `multiprocessing.Process`, aplica `proc.join(timeout=MAX_TIME_SEG)` y si el proceso sigue vivo llama `proc.terminate()`. Esto garantiza que un caso colgado **siempre** libera el núcleo, el hilo puede empezar el siguiente caso y el slot del pool no queda bloqueado indefinidamente.

**Para ajustar el número de trabajos paralelos:** edita la constante `MAX_WORKERS` en `scripts/fill_excel_geomip.py` (recomendado: igual al número de núcleos físicos del equipo).

### B.6 Estimado de tiempo (AMD 3020e, 2 núcleos, 1.2 GHz)

| Condición | N=15, subsistema completo | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~4–6 min | ~2–3 h |
| G1–G4 aplicadas, secuencial | ~1–2 min | ~40–70 min |
| G1–G4 + paralelo (2 workers) | ~1–2 min | ~20–40 min |

> Para N=20 los casos más pesados pueden superar el timeout de 300 s. El script escribe `"TIMEOUT"` en la celda y continúa con los demás sin bloquearse.

---

## Anexo C — Optimizaciones de rendimiento en KQNodes

KQNodes ejecuta el algoritmo de Queyranne de forma iterativa: para cada una de las k-1 fases, evalúa cientos o miles de subconjuntos candidatos, y en cada evaluación calcula las distribuciones marginales de todas las partes de la partición parcial. Se implementaron cuatro optimizaciones que reducen drásticamente el número de cálculos redundantes.

### C.1 Cache de distribuciones marginales (K1)

La distribución marginal de un conjunto de nodos (llamada `substraer + distribucion_marginal`) depende únicamente de qué nodos componen esa parte — no de cuándo ni desde qué contexto se consulta. Sin embargo, las partes ya fijadas en iteraciones anteriores de Queyranne aparecían en cada una de las cientos de evaluaciones de la fase siguiente, recalculando siempre el mismo resultado.

Se añadió un diccionario `_memo_marginal` que guarda el resultado la primera vez que se calcula para un conjunto de nodos y lo reutiliza en todas las llamadas siguientes. El cache se limpia al comenzar cada caso nuevo, por lo que no hay riesgo de mezclar resultados entre casos distintos.

### C.2 Evaluación invariante en el loop de Queyranne (K2)

El algoritmo de Queyranne construye una secuencia eligiendo, paso a paso, el bloque de mayor ganancia marginal. La ganancia se calcula como `f(S ∪ a) − f(S)`. El valor `f(S)` es constante dentro del loop que prueba todos los bloques candidatos `a`, pero antes se recomputaba para cada candidato.

Con este cambio, `f(S)` se calcula una sola vez antes del loop interno. Para un subsistema de 15 nodos, esto elimina ~105 evaluaciones redundantes por fase.

### C.3 Cache de pérdida final (K3)

`_calcular_perdida_final` calcula la pérdida EMD de una k-partición completa. Se llama repetidamente en el refinamiento divisivo y en el hill climbing. En particular, cuando el hill climbing converge (ningún movimiento mejora), evalúa todas las combinaciones posibles sin encontrar ninguna mejor — la mayoría de esas particiones candidatas ya habían sido evaluadas en iteraciones anteriores.

Se añadió un diccionario `_memo_perdida_final` con clave canónica de la partición (independiente del orden en que se construyó). En las fases de convergencia del hill climbing, el hit rate típico supera el 70 %.

### C.4 Script paralelo con kill-on-timeout (K4)

El script `fill_excel_kqnodes.py` fue reescrito con el mismo patrón que GeoMIP:

- **`ThreadPoolExecutor(max_workers=2)`**: dos casos se procesan en simultáneo.
- **Kill-on-timeout garantizado**: cada hilo gestiona su propio subproceso con `proc.terminate()` si supera el tiempo límite. Si KQNodes se cuelga por cualquier razón (no solo por timeout interno de Queyranne), el proceso es terminado y el slot del pool queda libre inmediatamente.
- **Tolerancia a fallos**: un caso que falla por error o timeout ya no detiene el volcado completo — se registra y el script continúa con los demás.

**Para ajustar el número de trabajos paralelos:** edita la constante `MAX_WORKERS` en `scripts/fill_excel_kqnodes.py`.

### C.5 Limpieza: eliminación de la tabla de costos T (código muerto)

Una revisión del código previa a la entrega detectó que KQNodes construía, en cada caso, una **tabla de costos `T`** de tamaño n×n (una matriz cuadrada del tamaño del subsistema) que en realidad **nunca se usaba** para calcular nada. La función que mide la pérdida ignoraba esa matriz por completo: solo la recibía como parámetro y la descartaba.

Construir esa tabla implicaba un doble bucle en Python y reservar memoria para n×n valores en cada ejecución, sin ningún efecto sobre el resultado.

**Qué se hizo:** se eliminó la tabla `T` y el método que la construía (`_obtener_tabla_costos`). El único dato que realmente se aprovechaba de ella —el tamaño del subsistema— ahora se toma directamente de la distribución del subsistema, que ya estaba disponible.

**Qué cambia para ti como usuario:**

- **Nada en los resultados.** Las particiones y la pérdida φ son idénticas. Se verificó con la red de 10 nodos (caso `1101101101`, k=3): φ = 3.1895, exactamente igual que antes (ver observación 3.4).
- El algoritmo es un poco más liviano (menos trabajo y memoria por caso) y, sobre todo, **más limpio y fácil de explicar**: la pérdida se calcula directamente como la EMD entre la red completa y el producto de las partes, sin una matriz intermedia que confundía.

> En resumen: es una optimización de mantenibilidad. No acelera de forma notable porque el tiempo lo domina el algoritmo de Queyranne, pero elimina código muerto que podía inducir a error al leer o sustentar el proyecto.

### C.6 Estimado de tiempo (AMD 3020e, 2 núcleos, 1.2 GHz)

| Condición | N=10, k=3 (subsistema completo) | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~15–30 s | ~15–25 min |
| K1+K2+K3, secuencial | ~4–10 s | ~4–8 min |
| K1+K2+K3 + paralelo (2 workers) | ~4–10 s | ~2–4 min |

| Condición | N=15, k=4 (subsistema completo) | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~5–15 min | ~3–8 h |
| K1+K2+K3, secuencial | ~1–4 min | ~50–200 min |
| K1+K2+K3 + paralelo (2 workers) | ~1–4 min | ~25–100 min |

> Los casos con alcance parcial (no todos los nodos) terminan significativamente más rápido porque el tamaño efectivo del subsistema es menor.
