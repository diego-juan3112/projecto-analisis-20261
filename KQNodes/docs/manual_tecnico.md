## 1 Introducción y Contexto

### 1.1 Propósito de KQNodes y relación con QNodes y GeoMIP
KQNodes es una extensión de QNodes diseñada para abordar el problema de la k‑partición de mínima información (k‑MIP). Aprovecha la infraestructura y métricas de `QNodes` para generalizar la búsqueda de particiones óptimas a k partes (k ≥ 2).

> **Nota de diseño (v0.2):** versiones tempranas contemplaban consumir una *tabla de costos* `T` (n×n) inspirada en GeoMIP para guiar Queyranne. En la implementación final esa tabla resultó ser **código muerto** —ninguna función de evaluación la leía— y fue eliminada. La función objetivo de KQNodes es directamente la EMD entre la distribución global y el producto tensorial de las marginales de cada parte, sin matriz de costos intermedia. Ver Anexo C, optimización K6.

### 1.2 Qué reutiliza de QNodes y qué extiende
- Reutiliza: la base SIA (clase `SIA`), utilidades en `funcs` (EMD, reindexado, hamming), modelos (`System`, `NCube`, `Solution`) y el gestor (`Manager`) para carga de TPM.
- Extiende: la implementación de particionado (Queyranne para k=2) hacia un flujo iterativo/jerárquico que soporte k≥2, además de añadir refinamientos locales y validaciones para particiones múltiples.

### 1.3 Tabla de dependencias
| Módulo (referencia) | Función / objeto | Propósito en KQNodes |
|---|---:|---|
| `QNodes/src/strategies/q_nodes.py` | Queyranne / submodular logic | Base algorítmica a extender para k‑particiones |
| `QNodes/src/funcs/iit.py` | `emd_efecto`, `seleccionar_emd` | Cálculo de la métrica de pérdida (EMD) |
| `QNodes/src/models/core/system.py` | `System`, `NCube` | Construcción y manipulación de subsistemas / marginales |
| `QNodes/src/controllers/manager.py` | `Manager` | Carga de TPM desde `.samples/` y manejo de entradas |

### 1.4 Árbol de carpetas (KQNodes)
```
KQNodes/
├─ docs/
│  └─ manual_tecnico.md   # (este documento)
├─ src/
│  ├─ strategies/
│  │  └─ kqnodes.py       # extensión de la estrategia QNodes
│  ├─ controllers/        # copiar/adaptar desde QNodes
│  ├─ models/             # copiar/adaptar desde QNodes
│  ├─ funcs/              # copiar/adaptar desde QNodes
│  └─ middlewares/        # copiar/adaptar desde QNodes
└─ tests/
	└─ test_kqnodes.py
```

## 2 Algoritmo Central

### 2.1 _queyranne_iterativo(): pseudocódigo
```
Entrada: (usa self.k y self.sia_subsistema; sin argumentos)
Salida: list[frozenset] (k partes que suman V_res)

n_ss ← sia_dists_marginales.size          # tamaño real del subsistema
V_res ← frozenset(range(n_ss))            # índices LOCALES 0..n_ss-1
partes_fijas ← []

para i = 1 hasta k-1:
    f_i(S) ← _evaluar_perdida_restringida(S, V_res, partes_fijas)
    S_opt ← Queyranne(V_res, f_i)
    partes_fijas.append(S_opt)
    V_res ← V_res \ S_opt
    
    si verbose:
        imprimir [iter=i, S_opt, pérdida=f_i(S_opt)]
    
    si V_res = ∅: romper

si V_res ≠ ∅: partes_fijas.append(V_res)

retornar partes_fijas
```

> **Nota de índices:** los índices en las partes son **locales** (0 … n_ss-1). Cada función de pérdida los traduce a índices globales del TPM completo mediante `indices_ncubos[local_idx]` antes de llamar a `substraer`. Esto permite manejar correctamente subsistemas cuyos nodos no empiezan en 0 (p.ej. alcance=BCDEFGHIJ → `indices_ncubos=[1..9]`).

### 2.2 _refinamiento_divisivo(): pseudocódigo
```
Entrada: (usa self.k y self.sia_subsistema)
Salida: list[frozenset] (k partes, construidas top-down)

partes ← [ frozenset(range(n_ss)) ]   # parte inicial: conjunto completo

para _ en range(k-1):
    mejor_loss ← ∞
    mejor_partes ← None

    para cada (idx, parte) en partes:
        si |parte| ≤ 1: continuar
        otras ← partes sin parte[idx]
        para cada nodo x en parte:
            candidato ← otras + [{x}, parte \ {x}]
            loss ← _calcular_perdida_final(candidato)
            si loss < mejor_loss:
                mejor_loss ← loss
                mejor_partes ← candidato

    si mejor_partes es None: romper
    partes ← mejor_partes

retornar partes
```

**Motivación:** Queyranne en la iteración 1 optimiza `f(S) = EMD(global, marginal(S) ⊗ marginal(V\S))`, que es la función para una bipartición. Esta elección greedy de S₁ no tiene en cuenta las k-1 iteraciones restantes, por lo que puede producir una k-partición con pérdida mayor que la k=2 óptima. El refinamiento divisivo evalúa directamente `_calcular_perdida_final` (pérdida real de la k-partición completa) en cada paso, evitando ese sesgo. En `aplicar_estrategia` se comparan ambas estrategias y se conserva la de menor pérdida antes del hill climbing.

### 2.3 Parámetros de _queyranne_iterativo
| Parámetro | Tipo | Descripción | Default |
|---|---:|---|---|
| `self.k` | `int` | Número de particiones buscadas | 2 |
| `self.verbose` | `bool` | Imprimir progreso de iteraciones | False |
| `self.max_tiempo_seg` | `float` | Timeout por fase de Queyranne (segundos) | 300.0 |

> El método ya no recibe la matriz de costos `T`; infiere `n_ss` directamente de `self.sia_dists_marginales.size`. Ver Anexo C, optimización K6.

### 2.4 Análisis de complejidad
| Componente | Complejidad | Observación |
|---|---|---|
| Queyranne (una fase) | O(n_ss³) | n_ss fases de construcción de secuencia, cada una evalúa O(n_ss²) pares |
| k iteraciones Queyranne | O(k · n_ss³) | Ejecuta Queyranne k veces |
| `_evaluar_perdida_restringida` | O(n_ss) | Traducción local→global + marginalización por parte |
| `_calcular_perdida_final` | O(k · n_ss) | Un marginal por cada parte de la k-partición |
| `_refinamiento_divisivo` | O(k · n_ss · eval) | k-1 pasos × n_ss extracciones × coste de eval |
| `_intercambio_local` | O(k² · n_ss²) | n_ss nodos × k partes destino × hasta n_ss·k iteraciones |
| **Total KQNodes** | **O(k · n_ss³)** | Dominado por Queyranne; divisivo y hill climbing son O(k·n_ss²) |
| QNodes (k=2) | O(n³) | Caso especial con una sola iteración |
| Búsqueda exhaustiva | O(n^k) | Impracticable para n, k moderados |

### 2.5 Casos límite
- **k=2**: Una iteración de Queyranne extrae una bipartición y lo restante forma la segunda parte. Produce una bipartición válida, pero **no necesariamente idéntica** a la de QNodes (ver §2.6: KQNodes parte variables enteras, QNodes parte vértices por-tiempo).
- **k=n**: Cada iteración extrae un singleton; resulta en partición trivial {0}, {1}, ..., {n-1}.
- **V_res vacío**: Si todas las variables se asignan antes de k-1 iteraciones, el bucle se interrumpe; partes_fijas tendrá < k elementos.
- **V_res singleton**: En última iteración, si V_res = {v}, se añade como parte final sin ejecutar Queyranne.
- **Subsistema con índices no contiguos desde 0**: Si el alcance excluye nodos intermedios (p.ej. BCDEFGHIJ → `indices_ncubos=[1..9]`), los índices locales (0..n_ss-1) se traducen a globales antes de cada llamada a `substraer`, garantizando marginalizaciones correctas.

### 2.6 Modelo de partición y relación con QNodes (por qué k=2 puede diferir)

Es **esperado y correcto** que, para k=2, KQNodes y QNodes encuentren a veces **particiones distintas** y, por tanto, valores de φ distintos para la misma red. La causa no es un error de cálculo, sino que **ambas estrategias particionan espacios diferentes**:

| | QNodes | KQNodes |
| --- | --- | --- |
| Unidad que se particiona | **Vértices por-tiempo** (2·n): cada variable existe por separado como presente `tₐ` y efecto `t₊₁` | **Variables enteras** (n): cada nodo se asigna completo a una sola parte (presente y efecto juntos) |
| Cortes representables | Puede separar `A_efecto` de `A_presente` (cortes asimétricos en el tiempo) | Solo cortes simétricos por variable (`{A} \| {B,C}`, `{B} \| {A,C}`, …) |
| Espacio de búsqueda k=2 | Biparticiones del conjunto de 2·n vértices | Biparticiones del conjunto de n variables |

**La métrica de pérdida es la misma.** Se verificó empíricamente que `_calcular_perdida_final` de KQNodes (vía `substraer`) produce **exactamente el mismo valor** que la reconstrucción `bipartir()` tipo IIT que usa QNodes, para una misma partición de variables enteras:

| Partición (red N3C, estado `100`) | KQNodes (`substraer`) | QNodes (`bipartir`) |
| --- | --- | --- |
| `{A} \| {B,C}` | 1.0000 | 1.0000 |
| `{B} \| {A,C}` | 0.0000 | 0.0000 |
| `{C} \| {A,B}` | 1.0000 | 1.0000 |

Lo que cambia es **cuál partición elige cada algoritmo dentro de su propio espacio**. En N3C:

- **QNodes** (espacio de 2·n vértices) reporta `⎛A⎞⎛B,C⎞` con φ = **0.5**.
- **KQNodes** (espacio de n variables) reporta `{B} \| {A,C}` con φ = **0.0**.

Como `bipartir([B],[B]) = [0,0,1]` = distribución global, la bipartición `{B}|{A,C}` es **tan válida como la de QNodes y tiene menor pérdida**. Es decir, en este caso KQNodes es **igual de eficaz y más eficiente** (encuentra una bipartición correcta con φ menor), no menos correcto.

**Conclusión:** la afirmación "k=2 ≡ QNodes" no es exacta y se reemplaza por esta caracterización: KQNodes resuelve la k-partición sobre **variables enteras** con una métrica de pérdida **consistente con la de QNodes/GeoMIP**; para k=2 entrega la mejor bipartición *de variables enteras*, que puede diferir de —y ser mejor que— la MIP por-tiempo de QNodes. Esto lo valida el test `test_k2_biparticion_valida_y_no_peor_que_qnodes`.

## 3 API Pública y Referencia de Métodos

### 3.1 Tabla de métodos de KQNodes
| Método | Firma completa | Retorno | Descripción | Complejidad |
|---|---|---|---|---|
| `__init__` | `__init__(gestor, k=2, refinar=True, verbose=False, max_tiempo_seg=300.0)` | - | Inicializa el algoritmo. Default del constructor: `k=2` (el CLI `--k` usa default 3 vía `main.py`). | O(1) |
| `aplicar_estrategia` | `aplicar_estrategia() -> Solution` | `Solution` | Ejecuta k-MIP: Queyranne + divisivo + hill climbing | O(k·n_ss³) |
| `_queyranne_iterativo` | `_queyranne_iterativo() -> List[frozenset]` | `List[frozenset]` | Extrae k-1 partes con Queyranne greedy. Infiere `n_ss` de `sia_dists_marginales` | O(k·n_ss³) |
| `_refinamiento_divisivo` | `_refinamiento_divisivo() -> List[frozenset]` | `List[frozenset]` | Construye k-partición top-down por extracciones singleton | O(k·n_ss·eval) |
| `_calcular_perdida_final` | `_calcular_perdida_final(partes) -> float` | `float` | EMD(global, ⊗ marginal(Pi)) para la k-partición completa | O(k·n_ss) |
| `_evaluar_perdida_restringida` | `_evaluar_perdida_restringida(S, V_res, partes_fijas) -> float` | `float` | Pérdida incremental de extraer S de V_res (usada internamente por Queyranne) | O(k·n_ss) |
| `_intercambio_local` | `_intercambio_local(partes) -> List[frozenset]` | `List[frozenset]` | Hill climbing: mueve nodos individuales entre partes | O(k²·n_ss²) |
| `_validar_particion` | `_validar_particion(partes) -> bool` | `bool` | Verifica disjunción, completitud y no-vacío | O(n_ss) |
| `_format_partition_letters` | `_format_partition_letters(partes) -> str` | `str` | Formatea la partición como `{A,B} \| {C}` | O(n_ss) |

### 3.2 Detalle de _evaluar_perdida_restringida()
```python
def _evaluar_perdida_restringida(
    self,
    S: frozenset,
    V_res: frozenset,
    partes_fijas: List[frozenset],
) -> float:
    """
    Parámetros:
    - S: frozenset de índices de variables candidatas (ej: {0, 2})
    - V_res: frozenset de variables aún sin particionar (ej: {0, 1, 2})
    - partes_fijas: lista de frozensets ya asignadas en iteraciones previas
    
    Restricciones:
    - S no puede ser vacío ni igual a V_res → retorna float('inf')
    - Requiere que sia_subsistema esté inicializado (llamar sia_preparar_subsistema)
    
    Retorna: float (pérdida EMD entre distribución global y producto tensorial)
    
    Ejemplo de llamada:
    S = frozenset({0})
    V_res = frozenset({0, 1, 2})
    partes_fijas = []
    
    perdida = kqnodes._evaluar_perdida_restringida(S, V_res, partes_fijas)
    # Salida esperada: perdida ≈ 0.15 (valor numérico depende de TPM)
    """
```

### 3.3 Tabla de casos edge
| Situación | Comportamiento | Cómo evitarlo |
|---|---|---|
| S vacío `frozenset()` | Retorna `float('inf')` | Asegurar S ≠ ∅ antes de llamar |
| S == V_res | Retorna `float('inf')` | Queyranne no selecciona singletons finales |
| Subsistema no preparado | Excepción o distribución uniforme | Llamar `sia_preparar_subsistema()` primero |
| k > n | Partición incompleta < k partes | Limitar k ≤ n en validación inicial |
| V_res singleton al final | Se añade sin ejecutar Queyranne | Comportamiento correcto (caso límite) |

## 4 Integración, Registro y Extensibilidad

### 4.1 Registrar KQNodes en main.py
En `KQNodes/src/main.py`, agregar:
```python
from shared_src.controllers.manager import Manager
from KQNodes.src.strategies.kqnodes import KQNodes

def iniciar():
    estado_inicial = "1000000000"
    condiciones    = "1111111111"
    alcance        = "1101101101"
    mecanismo      = "1111111111"

    gestor = Manager(estado_inicial, ruta_base=sample_path)
    analizador = KQNodes(gestor, k=3, refinar=True, verbose=True, max_tiempo_seg=300.0)

    # Guardar alcance/mecanismo para la salida formateada
    analizador.alcance = alcance
    analizador.mecanismo = mecanismo

    # IMPRESCINDIBLE: preparar el subsistema antes de aplicar la estrategia.
    # Sin esto, self.sia_dists_marginales no existe y aplicar_estrategia() falla.
    analizador.sia_preparar_subsistema(estado_inicial, condiciones, alcance, mecanismo)

    resultado = analizador.aplicar_estrategia()
    print(resultado)
```
Patrón obligatorio: instanciar con un `gestor` (no con la TPM) → `sia_preparar_subsistema(...)` → `aplicar_estrategia()`. El constructor recibe el **gestor** y obtiene la TPM internamente vía `gestor.cargar_red()`.

### 4.2 Invariantes de _validar_particion()
Tres propiedades son obligatorias:
1. **Disjunción**: `∀ i,j: i≠j ⟹ partes[i] ∩ partes[j] = ∅`
2. **Completitud**: `⋃ partes = V = {0..n-1}`
3. **No-vacío**: `∀ parte: |parte| ≥ 1`

Violación lanza `ValueError` con mensaje descriptivo indicando cuál propiedad falló.

### 4.3 Extensibilidad: subclasificación
Para usar métrica distinta a EMD, sobrescribir `_evaluar_perdida_restringida()`:
```python
class KQNodesKullback(KQNodes):
    """KQNodes con divergencia KL en lugar de EMD."""
    
    def _evaluar_perdida_restringida(self, S, V_res, partes_fijas):
        # Reemplazar emd_efecto() con divergencia KL
        marginal_global = self.sia_dists_marginales[...]
        marginal_restringida = System.substraer(...)
        
        # Cálculo de KL(P || Q)
        kl_div = np.sum(marginal_global * np.log(marginal_global / marginal_restringida + 1e-10))
        return kl_div
```
Heredar hereda automáticamente `aplicar_estrategia()` y la orquestación completa.

### 4.4 Flujo de aplicar_estrategia()
```
┌──────────────────────────────────────────────────┐
│  aplicar_estrategia()                            │
└────────────────────┬─────────────────────────────┘
                     │ t0 = perf_counter()
                     │ _memo_marginal = {}      ← invalida cachés
                     │ _memo_perdida_final = {}    por-caso
                     ▼
        ┌─────────────────────┐
        │                     │
        ▼                     ▼
┌──────────────────┐  ┌──────────────────────┐
│ _queyranne_      │  │ _refinamiento_       │
│  iterativo()     │  │  divisivo()          │
│ (greedy Queyranne│  │ (top-down singleton  │
│  bipartition     │  │  extractions, eval   │
│  objective)      │  │  _calcular_perdida_  │
│                  │  │  final at each step) │
└────────┬─────────┘  └──────────┬───────────┘
         │ partes_q               │ partes_div
         └──────────┬─────────────┘
                    ▼
        ┌───────────────────────────────────┐
        │ Comparar:                         │
        │   loss_q = _calcular_perdida_final│
        │              (partes_q)           │
        │   loss_d = _calcular_perdida_final│
        │              (partes_div)         │
        │   partes ← argmin(loss_q, loss_d) │
        └───────────────┬───────────────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ _validar_particion() │ (lanza ValueError si falla)
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ if refinar:          │
             │  _intercambio_local()│──→ partes refinadas
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ perdida_final =      │
             │ _calcular_perdida_   │
             │ final(partes)        │
             │ return Solution(...) │
             └──────────────────────┘
```

## 5 Testing, Troubleshooting y Referencias

### 5.1 Cómo correr los tests
Desde la raíz de `KQNodes/` ejecutar:
```bash
cd projecto-analisis-20261/KQNodes && uv run pytest tests/ -v
```

### 5.2 Tabla de troubleshooting
| Error | Causa | Solución |
|---|---|---|
| `ValueError` partición inválida | `_validar_particion()` detecta disjunción/completitud/no-vacío rotos | Revisar la partición retornada por `_queyranne_iterativo()` o `_intercambio_local()` y corregir la función de generación de partes |
| EMD negativa o `NaN` | `emd_efecto()` recibe vectores de distinto tamaño o distribuciones mal normalizadas | Verificar que `sia_dists_marginales.size == n_ss` y que cada marginal de parte tenga exactamente `len(parte)` entradas |
| Pérdida infinita en subsistemas parciales (fila 13+ en Excel) | `n = tpm.shape[1]` (tamaño del TPM completo) usado en lugar de `n_ss = sia_dists_marginales.size` (tamaño del subsistema): `emd_efecto(size9, size10)` falla | Asegurarse de que toda referencia a `n` dentro del algoritmo use `sia_dists_marginales.size`, NO `tpm.shape[1]` |
| Pérdida infinita con alcance no-contiguo (p.ej. BCDEFGHIJ) | Índices locales `{0..n_ss-1}` usados directamente en `substraer` cuando `indices_ncubos=[1..9]`: `setdiff1d([1..9], [0])` no elimina nada | Traducir `indices_local → indices_global = sia_subsistema.indices_ncubos[indices_local]` antes de cada llamada a `substraer` |
| `ImportError: No module named 'shared_src'` al correr `main.py` directo | Python no encuentra `shared_src` porque el CWD no es la raíz del proyecto | Añadir `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` al inicio de `KQNodes/src/main.py` |
| `ImportError` por paths incorrectos entre KQNodes y QNodes | `src` no apunta a las carpetas correctas | Asegurar `sys.path` incluye la raíz del proyecto, o lanzar desde `KQNodes/` con `uv run python src/main.py` |
| Queyranne sin convergencia | Dominio de `V_res` mal reducido o función `f_i` no submodular | Revisar construcción de `V_res`, `partes_fijas` y la definición de `_evaluar_perdida_restringida()` |
| Pérdida k=3 > k=2 con sólo Queyranne | Queyranne itera 1 optimiza objetivo bipartición, no el objetivo k-partición | Asegurarse de que `aplicar_estrategia` ejecuta también `_refinamiento_divisivo` y conserva el mínimo |

### 5.3 Referencias
- Queyranne, D. P. (1998). “A fast algorithm for minimization of submodular functions.”
- Nemhauser, G. L., Wolsey, L. A., & Fisher, M. L. (1978). “An analysis of approximations for maximizing submodular set functions.”
- Documento de formalización: `../KQNodes_Formalizacion.docx`
- Diagramas de diseño: `../KQNodes_Diagramas.md`

| Versión | Autor | Fecha | Estado |
|---|---|---|---|
| 0.1 | Equipo KQNodes | 30/05/2026 | Draft funcional |

---

## Anexo A — Optimizaciones de rendimiento en QNodes

### A.1 Motivación

Durante las pruebas de volcado masivo con las hojas `20A-Elementos`, `22A-Elementos` y `25A-Elementos` se identificó que el tiempo de ejecución de QNodes escala de forma prohibitiva con N. El análisis de cuellos de botella reveló tres causas principales:

1. Todos los n-cubos se almacenaban en `float64` (8 bytes/valor), usando el doble de memoria y ancho de banda de caché necesarios.
2. La distribución marginal de la **unión** (`delta ∪ omega`) se recalculaba en cada una de las ~8 000–16 000 llamadas a `funcion_submodular`, aunque la bipartición subyacente ya estaba memoizada.
3. El script de volcado `fill_excel_qnodes.py` procesaba los 50 casos de forma estrictamente secuencial, dejando un núcleo físico ocioso.

### A.2 Optimización 1 — float64 → float32 (`QNodes/src/models/core/system.py`)

**Archivo:** `QNodes/src/models/core/system.py`, método `__init__`

**Cambio:** al crear cada `NCube`, se añade `.astype(np.float32, copy=False)`:

```python
# Antes
data=tpm[:, idx].reshape((BASE_TWO,) * num_nodos)

# Después
data=(
    tpm[:, idx].reshape((BASE_TWO,) * num_nodos)
    ...
).astype(np.float32, copy=False)
```

**Efecto en la cadena de cómputo:**

- `NCube.marginalizar()` llama `np.mean(self.data, axis=...)` → opera en float32 → instrucciones SIMD de 256 bits procesan 8 valores simultáneos (vs 4 en float64).
- `System.distribucion_marginal()` llena un array `dtype=np.float32` — ya declarado así; ahora la asignación no promueve a float64.
- `emd_efecto(u, v)` recibe ambos vectores en float32 → `np.abs(u - v)` es float32.

**Complejidad afectada:** `O(2^n_ss)` por llamada a `marginalizar()`, repetida ~40 000–80 000 veces en un caso N=20.

**Precisión:** float32 provee ~7 dígitos decimales significativos. Las distribuciones de probabilidad son valores en [0, 1]; la diferencia respecto a float64 es inferior a 1e-6 en todos los casos observados.

### A.3 Optimización 2 — Caché de distribución marginal de uniones (`QNodes/src/strategies/q_nodes.py`)

**Archivo:** `QNodes/src/strategies/q_nodes.py`, método `funcion_submodular` e `__init__`

**Problema:** dentro del triple bucle `i × j × k` de `algorithm()`, para cada `k` se evalúa la unión `{delta_k} ∪ omegas_ciclo`. `bipartir()` ya devuelve los n-cubos desde caché, pero `distribucion_marginal()` sobre el objeto `System` resultante recorre los n-cubos en un loop Python cada vez.

**Cambio:**

```python
# __init__
self._memo_dist_biparticion = {}   # clave → dist_marginal union

# funcion_submodular — bloque unión
clave_union = tuple(idxs_alcance_union), tuple(dims_mecanismo_union)
if clave_union not in self._memo_dist_biparticion:
    particion_union = self.sia_subsistema.bipartir(...)
    self._memo_dist_biparticion[clave_union] = particion_union.distribucion_marginal()
vector_union_marginal = self._memo_dist_biparticion[clave_union]
```

**Nota:** `_memo_dist_biparticion` se reinicia al crear una nueva instancia `QNodes(tpm)` por caso. El caché del delta (`memoria_delta`) ya existía previamente.

**Complejidad afectada:** `distribucion_marginal()` es `O(n_ss)` por llamada; con ~16 000 llamadas de unión en N=20 la mejora es `O(n_ss × 16 000)` → reducida a `O(n_ss × claves_únicas)`.

### A.4 Optimización 3 — Ejecución paralela (`scripts/fill_excel_qnodes.py`)

**Archivo:** `scripts/fill_excel_qnodes.py`

**Cambio:** sustitución del bucle secuencial por `concurrent.futures.ProcessPoolExecutor`:

```python
MAX_WORKERS = 2   # núcleos físicos del AMD 3020e

with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_trabajo = {
        executor.submit(_ejecutar_caso_qnodes, ...): trabajo
        for trabajo in trabajos
    }
    for future in concurrent.futures.as_completed(future_to_trabajo):
        particion, perdida, tiempo = future.result()
        escribir_resultado(...)   # escritura serial en proceso principal
```

**Función worker:** `_ejecutar_caso_qnodes` está definida a nivel de módulo (requerimiento de `multiprocessing` en Windows). Cada proceso hijo reconstruye su propio `QNodes(tpm)`, evitando estado compartido y condiciones de carrera.

**Escritura serial:** `escribir_resultado` abre, modifica y cierra el `.xlsx` en el proceso principal, garantizando que no haya escrituras concurrentes sobre el archivo Excel.

**Escalabilidad:** ajustar `MAX_WORKERS` al número de núcleos del equipo. En máquinas con 4+ núcleos el speedup es proporcional.

### A.5 Impacto combinado (referencia empírica — AMD 3020e, 2 núcleos, 1.2 GHz, 8 GB RAM)

| Condición                              | Caso 1 (N=20, subsistema completo) | 50 casos totales |
| -------------------------------------- | ---------------------------------- | ---------------- |
| Sin optimizaciones, secuencial         | ~13 min                            | ~4–6 h           |
| float32 + caché unión, secuencial      | ~6–8 min                           | ~2–3 h           |
| float32 + caché unión + 2 workers      | ~6–8 min                           | ~1–1.5 h         |

> Los casos con subsistemas parciales (alcance < 15 nodos de 20) son sustancialmente más rápidos; la tabla refleja el peor caso.

---

## Anexo B — Optimizaciones de rendimiento en GeoMIP

### B.1 Motivación

La implementación base de GeoMIP construye una tabla de transiciones `tabla_transiciones` de tamaño O(2^N) y la rellena invocando `calcular_costo()` en cada nivel de Hamming. Para N=15 esto implica ~32 768 entradas; para N=20, ~1 000 000. El análisis de cuellos de botella reveló cinco causas:

1. Dos sentencias `print()` de depuración activas en `NCube.condicionar()` generaban I/O síncrono en **cada** llamada a `condicionar`, que se ejecuta decenas de miles de veces por caso.
2. Los n-cubos se almacenaban en `float64`, igual que en QNodes antes de optimizar.
3. En `calcular_costo()`, la conversión de estado a entero usaba `int("".join(map(str, estado[::-1])), 2)` — una operación de cadena por cada uno de los ~2^N estados.
4. Los diffs entre distribuciones y la acumulación por sumatoria usaban list comprehensions de Python puro en lugar de operaciones vectorizadas de NumPy.
5. El script `fill_excel_geomip.py` procesaba los casos de forma estrictamente secuencial y, a diferencia del script QNodes, no podía matar procesos colgados en timeout.

### B.2 Optimización G1 — Eliminación de prints de depuración (`ncube.py`)

**Archivo:** `GeoMIP/.../models/core/ncube.py`, método `condicionar`

**Problema:** Dos sentencias `print` quedaron activas desde la fase de desarrollo:

```python
# Antes
numero_dims = self.dims.size
seleccion = [slice(None)] * numero_dims
print(indices_condicionados)          # ← I/O síncrono
for condicion in indices_condicionados:
    level_arr = numero_dims - (condicion + 1)
    seleccion[level_arr] = estado_inicial[condicion]
print(tuple(seleccion))               # ← I/O síncrono
```

**Cambio:** eliminación de ambas líneas `print`.

```python
# Después
numero_dims = self.dims.size
seleccion = [slice(None)] * numero_dims
for condicion in indices_condicionados:
    level_arr = numero_dims - (condicion + 1)
    seleccion[level_arr] = estado_inicial[condicion]
```

**Efecto:** `condicionar()` es invocado en `System.condicionar()` y `System.substraer()`, que a su vez son llamados decenas de miles de veces durante la construcción del subsistema y la evaluación de candidatos. El I/O de consola es bloqueante en Windows; su eliminación reduce la latencia de cada invocación de microsegundos a nanosegundos.

### B.3 Optimización G2 — float64 → float32 (`system.py`)

**Archivo:** `GeoMIP/.../models/core/system.py`, método `__init__`

**Cambio:** misma estrategia que QNodes — `.astype(np.float32, copy=False)` al construir cada `NCube`:

```python
# Antes
data=(
    tpm[:, i].reshape((2,) * n_nodes)
    if notacion == Notation.LIL_ENDIAN.value
    else tpm[:, i][reindexar(tpm[COLS_IDX])].reshape((2,) * n_nodes)
),

# Después
data=(
    tpm[:, i].reshape((2,) * n_nodes)
    if notacion == Notation.LIL_ENDIAN.value
    else tpm[:, i][reindexar(tpm[COLS_IDX])].reshape((2,) * n_nodes)
).astype(np.float32, copy=False),
```

**Efecto en la cadena:** igual que en QNodes — `NCube.marginalizar()` opera en float32, habilitando instrucciones SIMD de 256 bits (8 valores simultáneos vs 4 en float64). `distribucion_marginal()` en `system.py` ya declara el buffer `dtype=np.float32`; la asignación ya no promueve a float64.

### B.4 Optimización G3 — Array 2D + conversión estado→índice vectorizada (`geometric.py`)

**Archivo:** `GeoMIP/.../controllers/strategies/geometric.py`, método `aplicar_estrategia`

**Problema original:** `_flat_data` era una lista Python de arrays 1D. En `calcular_costo()` se accedía elemento a elemento con list comprehensions:

```python
# Antes — dos list comprehensions dentro de calcular_costo (llamada 2^N veces)
diffs = np.abs(
    np.array([flat[estado_ini_int] for flat in self._flat_data])
  - np.array([flat[estado_fin_int] for flat in self._flat_data])
)
```

**Cambio en `aplicar_estrategia`:**

```python
# Después — una sola matriz 2D y el vector de potencias de 2 precalculado
_n_dims = self.sia_subsistema.dims_ncubos.size
self._flat_data_2d = np.stack([ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos])
self._estado_powers = (2 ** np.arange(_n_dims)).astype(np.int64)
```

`_flat_data_2d` tiene forma `(n_ncubos, 2^n_dims)`. En `calcular_costo()`:

```python
# Antes — conversión por cadena de caracteres
estado_ini_int = int("".join(map(str, estado_inicial[::-1])), 2)
estado_fin_int  = int("".join(map(str, estado_final[::-1])),  2)

# Después — producto escalar sobre vector de potencias (sin strings)
ini_int = int(np.dot(estado_inicial, self._estado_powers))
fin_int = int(np.dot(estado_final,   self._estado_powers))
```

**Efecto:** la indexación de columna única `_flat_data_2d[:, ini_int]` es una operación de array contigua en memoria, sin loop Python. La conversión estado→entero pasa de O(N) operaciones de string a O(N) multiplicaciones enteras ya vectorizadas por NumPy.

### B.5 Optimización G4 — Tabla con arrays numpy y `calcular_costo` vectorizado (`geometric.py`)

**Archivo:** `GeoMIP/.../controllers/strategies/geometric.py`, métodos `find_mip` y `calcular_costo`

**Problema original:** la tabla se inicializaba con listas Python y la acumulación y la multiplicación por factor usaban loops `for n in ncubos`:

```python
# Antes — inicialización
self.tabla_transiciones[key] = [0.0 for _ in range(len(self.sia_subsistema.indices_ncubos))]

# Antes — acumulación en caso distancia > 1
for n in ncubos:
    self.tabla_transiciones[key][n] = self.tabla_transiciones[key][n] + self.tabla_transiciones[temp_key][n]

# Antes — multiplicación por factor
tmp = []
for i, n in enumerate(self.tabla_transiciones[key]):
    if n is not None:
        tmp.append(factor * n)
    else:
        tmp.append(n)
self.tabla_transiciones[key] = tmp
```

**Cambio — inicialización con `np.zeros`:**

```python
self.tabla_transiciones[tuple(self.caminos[0][0]), tuple(self.caminos[0][0])] = \
    np.zeros(len(self.sia_subsistema.indices_ncubos))
```

**Cambio — cuerpo completo de `calcular_costo`:**

```python
def calcular_costo(self, estado_inicial: tuple, estado_final: tuple):
    key = tuple(estado_inicial), tuple(estado_final)
    if key in self.tabla_transiciones:
        return
    distancia_hamming = self.hamming(estado_inicial, estado_final)
    factor = 1.0 / (2 ** distancia_hamming)

    ini_int = int(np.dot(estado_inicial, self._estado_powers))
    fin_int = int(np.dot(estado_final,   self._estado_powers))
    diffs = np.abs(self._flat_data_2d[:, ini_int] - self._flat_data_2d[:, fin_int])

    if distancia_hamming > 1:
        for i in range(len(estado_inicial)):
            if estado_inicial[i] != estado_final[i]:
                nuevo_estado = list(estado_final)
                nuevo_estado[i] = estado_inicial[i]
                temp_key = tuple(estado_inicial), tuple(nuevo_estado)
                diffs = diffs + self.tabla_transiciones[temp_key]   # suma de arrays

    self.tabla_transiciones[key] = diffs * factor   # multiplicación escalar-array
```

**Efecto:** las operaciones `diffs + tabla[temp_key]` y `diffs * factor` son operaciones vectorizadas de NumPy sobre arrays de longitud `n_ncubos`. El parámetro `ncubos: list[int]` fue eliminado de la firma al quedar sin uso — los índices ya están implícitos en las dimensiones de `_flat_data_2d`.

**Compatibilidad con `identificar_particiones_optimas()`:** los accesos `actual[idx]`, `actual[idx] <= complementario[idx]` y `costo_candidato += actual[idx]` funcionan sin cambios sobre arrays NumPy (indexación y comparación escalar son idénticos a listas para enteros).

### B.6 Optimización G6 — Paralelismo con `ThreadPoolExecutor` y kill-on-timeout (`fill_excel_geomip.py`)

**Archivo:** `scripts/fill_excel_geomip.py`

**Problema con `ProcessPoolExecutor`:** `future.result(timeout=MAX_TIME_SEG)` lanza `TimeoutError` pero **no mata** el proceso worker subyacente. En GeoMIP los casos grandes pueden colgar indefinidamente (e.g. N=20, alcance completo), bloqueando un núcleo sin retornar nunca.

**Solución — patrón ThreadPoolExecutor + Process manual:**

```python
MAX_WORKERS = 2

def _run_geomip_con_timeout(
    geomip_method, geomip_sp,
    estado_inicial, pagina, condiciones,
    alcance_bin, mecanismo_bin,
) -> tuple:
    queue = multiprocessing.Queue()
    proc  = multiprocessing.Process(
        target=_worker_geomip,
        args=(queue, geomip_method, geomip_sp, estado_inicial,
              pagina, condiciones, alcance_bin, mecanismo_bin),
        daemon=True,
    )
    proc.start()
    proc.join(timeout=MAX_TIME_SEG)
    if proc.is_alive():
        proc.terminate()   # ← kill garantizado
        proc.join()
        return ("timeout",)
    if queue.empty():
        return ("crash",)
    return queue.get()
```

En `main()`, el `ThreadPoolExecutor` lanza todos los trabajos pendientes y consume resultados con `as_completed()`:

```python
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_trabajo = {
        executor.submit(_run_geomip_con_timeout, ...): t
        for t in trabajos
    }
    for future in concurrent.futures.as_completed(future_to_trabajo):
        msg = future.result()
        if msg[0] == "ok":
            escribir_resultado(...)   # escritura serial en proceso principal
```

**Por qué ThreadPoolExecutor y no ProcessPoolExecutor:**

| Característica | `ProcessPoolExecutor` | `ThreadPoolExecutor` + `Process` manual |
| --- | --- | --- |
| Timeout sin bloqueo | No — `future.result(timeout)` lanza excepción pero el worker sigue vivo | Sí — `proc.join(timeout)` + `proc.terminate()` mata el proceso |
| Uso de GIL | Irrelevante (procesos independientes) | Hilo I/O-bound (espera `proc.join`) → GIL liberado durante la espera |
| Complejidad | Menor | Mayor, pero necesaria para garantizar kill |
| Estado compartido | No (serialización automática de argumentos) | No (cada hilo crea su propio `Process`) |

**Cuatro estados de retorno manejados:**

| Tupla | Significado | Acción en Excel |
| --- | --- | --- |
| `("ok", particion, perdida, tiempo)` | Éxito | Escribe resultado normal |
| `("timeout",)` | Proceso superó `MAX_TIME_SEG` | Escribe `"TIMEOUT"` y `>MAX_TIME_SEGs` |
| `("crash",)` | Proceso terminó sin poner nada en la cola | Log + continúa (sin escribir) |
| `("err", exc_str, tb_str)` | Excepción en el worker | Log completo del traceback + continúa |

### B.7 Impacto combinado (referencia empírica — AMD 3020e, 2 núcleos, 1.2 GHz, 8 GB RAM)

| Condición | Caso N=15 (subsistema completo) | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~4–6 min | ~2–3 h |
| G1+G2+G3+G4, secuencial | ~1–2 min | ~40–70 min |
| G1+G2+G3+G4 + G6 (2 workers) | ~1–2 min | ~20–40 min |

> Para N=20 los casos del subsistema completo pueden superar el timeout de 300 s incluso con las optimizaciones. El timeout garantiza que el script no se cuelgue indefinidamente y continúa con los casos restantes.

---

## Anexo C — Optimizaciones de rendimiento en KQNodes

### C.1 Motivación

KQNodes evalúa la función `_evaluar_perdida_restringida` en el corazón del algoritmo de Queyranne. Para cada subconjunto candidato `S` dentro de una fase, la función construye un vector de distribuciones marginales combinando `substraer() + distribucion_marginal()` para cada parte de la partición parcial. Con complejidad O(k · n³) total (k fases × n² evaluaciones por fase), el número de llamadas a `substraer` escalaba como:

- N=10, k=4 → ~3 fases × ~45 evaluaciones × 3 partes = ~405 marginalizaciones por caso
- N=15, k=4 → ~3 fases × ~105 evaluaciones × 3 partes = ~945 marginalizaciones por caso

Además, `_calcular_perdida_final` (usada en `_refinamiento_divisivo` e `_intercambio_local`) se llamaba repetidamente con las mismas particiones sin reutilizar resultados previos. El análisis reveló cuatro causas principales:

1. Las distribuciones marginales de `partes_fijas` (que no cambian durante una fase) se recomputaban en cada una de las O(n²) llamadas a `f_i(S)`.
2. `f(S_union)` se evaluaba O(n) veces por paso de la secuencia de Queyranne, siendo constante en ese loop.
3. `_calcular_perdida_final` no tenía cache: particiones ya evaluadas (muy frecuente en hill climbing convergiendo) se recomputaban desde cero.
4. El script `fill_excel_kqnodes.py` era secuencial, detenía todo el volcado en el primer error y no podía matar procesos colgados externamente.

### C.2 Optimización K1 — Cache de distribuciones marginales (`kqnodes.py`)

**Archivo:** `KQNodes/src/strategies/kqnodes.py`, métodos `_evaluar_perdida_restringida` y `_calcular_perdida_final`

**Problema:** en cada llamada a `_evaluar_perdida_restringida`, el loop sobre `partes_a_combinar` construía y calculaba la distribución marginal de cada parte desde cero:

```python
# Antes — substraer + distribucion_marginal por cada parte, en cada llamada
subsistema_parte = self.sia_subsistema.substraer(
    alcance_idx=np.setdiff1d(self.sia_subsistema.indices_ncubos, indices_global),
    mecanismo_dims=np.setdiff1d(self.sia_subsistema.dims_ncubos, indices_global),
)
dist_parte = subsistema_parte.distribucion_marginal()
```

**Cambio:** diccionario `_memo_marginal` compartido entre ambas funciones, con clave `tuple(int(x) for x in indices_global)`:

```python
# En __init__
self._memo_marginal: dict[tuple, np.ndarray] = {}

# En aplicar_estrategia — invalida al iniciar cada caso
self._memo_marginal = {}

# En _evaluar_perdida_restringida y _calcular_perdida_final
memo_key = tuple(int(x) for x in indices_global)
if memo_key not in self._memo_marginal:
    subsistema_parte = self.sia_subsistema.substraer(...)
    self._memo_marginal[memo_key] = subsistema_parte.distribucion_marginal()
dist_parte = self._memo_marginal[memo_key]
```

**Por qué la clave es `indices_global` y no el frozenset local:** `substraer` recibe índices globales del TPM y las dimensiones del subsistema; la marginal resultante depende exclusivamente de qué nodos globales componen la parte. Los índices locales (0..n_ss-1) son solo una vista relativa y no identifican unívocamente el cálculo.

**Qué se cachea y por qué no hay stale data:** la clave identifica un conjunto de nodos globales en el contexto de `sia_subsistema`. El cache se invalida en `aplicar_estrategia()` (que es llamado una vez por caso, con un `sia_subsistema` distinto cada vez). No hay riesgo de usar marginals de un caso anterior.

**Impacto:** las partes de `partes_fijas` (las ya extraídas en iteraciones anteriores de Queyranne) se recomputan solo una vez por caso en lugar de O(n²) veces por fase. Los singletons y complementos que aparecen en múltiples evaluaciones también se cachean.

### C.3 Optimización K2 — `f(S_union)` invariante en el loop interno (`kqnodes.py`)

**Archivo:** `KQNodes/src/strategies/kqnodes.py`, función anidada `_queyranne_on_set`

**Problema:** en la construcción de la secuencia de Queyranne, el valor `f(S_union)` se evaluaba dentro del loop `for a in remaining` aunque `S_union` no cambia durante esa iteración:

```python
# Antes — f(S_union) recalculado |remaining| veces por paso
for a in remaining:
    union = frozenset(set(S_union) | set(a))
    gain = f(union) - f(S_union)   # ← f(S_union) constante aquí
```

**Cambio:** precalcular una vez fuera del loop interno:

```python
# Después
val_S_union = f(S_union)  # evaluado una sola vez por paso de secuencia
for a in remaining:
    union = frozenset(set(S_union) | set(a))
    gain = f(union) - val_S_union
```

**Ahorro cuantificado:** en una fase con `n` bloques, la secuencia tiene `n` pasos. En cada paso el loop interno tiene `|remaining|` iteraciones (n, n-1, n-2, …, 1). Sin K2 se evalúa `f(S_union)` en total n + (n-1) + … + 1 = n(n+1)/2 veces por fase. Con K2 se evalúa `n` veces (una por paso). Para n=10: 55 → 10 evaluaciones; para n=15: 120 → 15.

Con K1 activo, muchas de esas evaluaciones de `f(S_union)` ya habrían golpeado la cache, pero K2 elimina incluso el overhead del lookup del diccionario para las `|remaining|-1` llamadas redundantes por paso.

### C.4 Optimización K3 — Cache de `_calcular_perdida_final` (`kqnodes.py`)

**Archivo:** `KQNodes/src/strategies/kqnodes.py`, método `_calcular_perdida_final`

**Problema:** `_calcular_perdida_final` es llamada en tres contextos:

| Contexto | Frecuencia | Repeticiones típicas |
| --- | --- | --- |
| `aplicar_estrategia` (comparar Queyranne vs Divisivo) | 2 veces | 0 (particiones distintas) |
| `_refinamiento_divisivo` | O(n_ss × k) veces | ~30–50 % duplicadas |
| `_intercambio_local` (hill climbing) | O(n_ss² × k) por iteración | ~70–90 % duplicadas en convergencia |

En hill climbing, cuando el algoritmo converge (ningún movimiento mejora), evalúa todas las combinaciones de (nodo, parte destino) sin encontrar mejora — muchas de esas particiones candidatas ya fueron evaluadas en iteraciones anteriores.

**Cambio:**

```python
# En __init__
self._memo_perdida_final: dict[tuple, float] = {}

# En aplicar_estrategia
self._memo_perdida_final = {}

# En _calcular_perdida_final
_cache_key = tuple(tuple(sorted(p)) for p in sorted(partes, key=min))
if _cache_key in self._memo_perdida_final:
    return self._memo_perdida_final[_cache_key]
# ... cálculo ...
self._memo_perdida_final[_cache_key] = resultado
return resultado
```

**Construcción de la clave:** `sorted(partes, key=min)` ordena las partes por su elemento mínimo (orden canónico independiente del orden de construcción), y `tuple(sorted(p))` ordena los elementos dentro de cada parte. Esto garantiza que `{A,B} | {C}` y `{C} | {A,B}` produzcan la misma clave.

**Interacción con K1:** K3 cachea el resultado final (un float), K1 cachea los marginales intermedios (arrays). Son complementarios: K1 acelera el cálculo cuando hay miss en K3; K3 evita el cálculo y el lookup de K1 cuando la partición ya fue evaluada.

### C.5 Optimización K5 — `copy=False` en conversiones float32 (`kqnodes.py`)

**Archivo:** `KQNodes/src/strategies/kqnodes.py`, métodos `_evaluar_perdida_restringida` y `_calcular_perdida_final`

**Cambio:** añadir `copy=False` a todas las llamadas `.astype(np.float32)` sobre distribuciones ya en float32:

```python
# Antes
emd_efecto(
    u=distribucion_global.astype(np.float32),
    v=producto_por_variable.astype(np.float32),
)

# Después
emd_efecto(
    u=distribucion_global.astype(np.float32, copy=False),
    v=producto_por_variable,   # ya es float32, no necesita cast
)
```

`sia_dists_marginales` se declara `dtype=np.float32` en `System.distribucion_marginal()`. Sin `copy=False`, `.astype()` creaba una copia en heap en cada evaluación de EMD — O(n_ss) bytes por llamada, O(k·n³) llamadas totales.

### C.6 Optimización K4 — Paralelismo con kill-on-timeout (`fill_excel_kqnodes.py`)

**Archivo:** `scripts/fill_excel_kqnodes.py`

**Problema con el script original:**

1. **Secuencial**: un caso a la vez; el segundo núcleo físico permanecía ocioso.
2. **`sys.exit(1)` en primer error**: un caso fallido detenía todo el volcado, perdiendo el progreso.
3. **Sin kill externo garantizado**: `max_tiempo_seg` controla el timeout *interno* de Queyranne (devuelve la mejor parcial encontrada), pero si el proceso se cuelga por otra razón (OOM, deadlock en imports, etc.) no había mecanismo para terminarlo.

**Solución:** mismo patrón que `fill_excel_geomip.py` — `ThreadPoolExecutor(max_workers=2)` con worker por subproceso:

```python
def _run_kqnodes_con_timeout(...) -> tuple:
    queue = multiprocessing.Queue()
    proc  = multiprocessing.Process(target=_worker_kqnodes, args=(...), daemon=True)
    proc.start()
    proc.join(timeout=MAX_TIME_SEG)
    if proc.is_alive():
        proc.terminate()   # kill garantizado
        proc.join()
        return ("timeout",)
    if queue.empty():
        return ("crash",)
    return queue.get()
```

**Diferencia respecto al script original:** el script original instanciaba `KQNodes` una sola vez y llamaba `sia_preparar_subsistema` entre casos para reutilizar la TPM cargada. El nuevo script crea una instancia fresca en cada subproceso — el overhead de cargar la TPM (~50 ms) es despreciable frente a los minutos que tarda cada caso, y elimina cualquier riesgo de estado compartido entre workers paralelos.

**Manejo de errores:** cuatro estados de retorno idénticos al patrón GeoMIP:

| Tupla | Significado | Acción |
| --- | --- | --- |
| `("ok", particion, perdida, tiempo)` | Éxito | Escribe en Excel y continúa |
| `("timeout",)` | Proceso excedió `MAX_TIME_SEG` | Escribe `"TIMEOUT"` y continúa |
| `("crash",)` | Proceso terminó sin poner nada en la cola | Log + continúa |
| `("err", exc_str, tb_str)` | Excepción en el worker | Log del traceback completo + continúa |

### C.7 Optimización K6 — Eliminación de la tabla de costos T (código muerto)

**Archivo:** `KQNodes/src/strategies/kqnodes.py`, métodos `aplicar_estrategia`, `_obtener_tabla_costos` (eliminado), `_queyranne_iterativo` y `_evaluar_perdida_restringida`

**Problema:** el diseño inicial preveía una *tabla de costos* `T` de tamaño `n_ss × n_ss` —inspirada en las tablas de transición de GeoMIP— que guiaría las decisiones de Queyranne. La implementación quedó a medias:

1. `_obtener_tabla_costos()` construía `T` con un **doble bucle Python** `for i in range(n): for j in range(n)` que asignaba `0.0` en la diagonal y `1.0` fuera de ella (una matriz uniforme), con coste O(n_ss²) y una asignación de memoria O(n_ss²) por caso.
2. `T` se pasaba como parámetro a `_queyranne_iterativo(T)` y de ahí a cada llamada de `_evaluar_perdida_restringida(S, V_res, partes_fijas, T)`.
3. **`_evaluar_perdida_restringida` nunca leía `T`.** Su función objetivo es directamente `EMD(global, ⊗ marginal(Pᵢ))`; la matriz entraba por la firma y se descartaba. El único uso real de `T` era `n = int(T.shape[0])` para recuperar el tamaño del subsistema, dato ya disponible en `self.sia_dists_marginales.size`.

En resumen: `T` era **código muerto** que consumía CPU (doble bucle + relleno), memoria (matriz n×n por caso) y ancho de banda de firma, sin influir en ningún resultado.

**Cambio:**

```python
# Antes — aplicar_estrategia
self._tabla_costos = None
T = self._obtener_tabla_costos()          # O(n²) bucle + matriz n×n
partes_queyranne = self._queyranne_iterativo(T)

# Después — aplicar_estrategia
partes_queyranne = self._queyranne_iterativo()

# Antes — _queyranne_iterativo
def _queyranne_iterativo(self, T: np.ndarray) -> List[frozenset]:
    n = int(T.shape[0])

# Después — _queyranne_iterativo
def _queyranne_iterativo(self) -> List[frozenset]:
    n = self.sia_dists_marginales.size
```

Se eliminó por completo el método `_obtener_tabla_costos`, el atributo `self._tabla_costos` (y su invalidación en `aplicar_estrategia`) y el parámetro `T` de `_queyranne_iterativo`, `_evaluar_perdida_restringida` y de los closures internos `f_i` / `f_local`.

**Por qué es seguro:** ninguna ruta de cómputo leía `T`. La única lectura (`T.shape[0]`) se sustituyó por la fuente canónica del tamaño del subsistema (`sia_dists_marginales.size`), que ya se usaba en el resto del algoritmo (p.ej. en `_calcular_perdida_final` y `_validar_particion`). Los tests y los scripts de volcado solo invocan `aplicar_estrategia()`, por lo que la firma interna no afecta su API.

**Impacto:**

- Elimina un bucle anidado O(n_ss²) en Python puro por cada caso ejecutado.
- Elimina una asignación de matriz `float32` de n_ss² entradas por caso.
- Reduce la superficie de la firma y la carga cognitiva: el algoritmo queda descrito por su verdadera función objetivo (EMD del producto tensorial), sin una matriz fantasma que sugería —erróneamente— una dependencia de costos por pares.
- No cambia ningún resultado numérico. Verificado end-to-end con la red 10A (`alcance=1101101101`, k=3): φ = 3.1895, idéntico al valor previo documentado en la observación 3.4 del manual de usuario.

> La complejidad asintótica total O(k·n_ss³) no cambia (estaba dominada por Queyranne, no por la construcción de `T`); el ahorro es de constante y de memoria, pero la principal ganancia es de **limpieza y mantenibilidad** de cara a la entrega.

### C.8 Impacto combinado estimado (AMD 3020e, 2 núcleos, 1.2 GHz, 8 GB RAM)

Los números dependen fuertemente de cuántas particiones candidatas se reutilizan (hit rate de K1 y K3). Para k=3 y N=10, el hit rate de K1 en una fase de Queyranne típica supera el 60 %; para k=4 y N=15 supera el 75 %.

| Condición | Caso N=10, k=3 (subsistema completo) | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~15–30 s | ~15–25 min |
| K1+K2+K3+K5, secuencial | ~4–10 s | ~4–8 min |
| K1+K2+K3+K5 + K4 (2 workers) | ~4–10 s | ~2–4 min |

| Condición | Caso N=15, k=4 (subsistema completo) | 50 casos totales |
| --- | --- | --- |
| Sin optimizaciones, secuencial | ~5–15 min | ~3–8 h |
| K1+K2+K3+K5, secuencial | ~1–4 min | ~50–200 min |
| K1+K2+K3+K5 + K4 (2 workers) | ~1–4 min | ~25–100 min |

> Las estimaciones son conservadoras para subsistemas completos (alcance = todos los nodos). Los casos con alcance parcial son significativamente más rápidos porque `n_ss` es menor y el número de evaluaciones de Queyranne escala como n_ss³.
