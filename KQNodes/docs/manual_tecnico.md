## 1 Introducción y Contexto

### 1.1 Propósito de KQNodes y relación con QNodes y GeoMIP
KQNodes es una extensión de QNodes diseñada para abordar el problema de la k‑partición de mínima información (k‑MIP). Aprovecha la infraestructura y métricas de `QNodes` para generalizar la búsqueda de particiones óptimas a k partes (k ≥ 2). GeoMIP aporta referencias y ejemplos de tablas de costos T que KQNodes puede consumir para evaluaciones específicas.

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
| `GeoMIP/src/.../controllers/` | generador de T | Fuente de tablas de costos T para pruebas y casos reales |

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
Entrada: T (matriz de costos, n×n)
Salida: list[frozenset] (k partes que suman V_res)

V_res ← frozenset(range(n))
partes_fijas ← []

para i = 1 hasta k-1:
    f_i(S) ← _evaluar_perdida_restringida(S, V_res, partes_fijas, T)
    S_opt ← Queyranne(V_res, f_i)
    partes_fijas.append(S_opt)
    V_res ← V_res \ S_opt
    
    si verbose:
        imprimir [iter=i, S_opt, pérdida=f_i(S_opt)]
    
    si V_res = ∅: romper

si V_res ≠ ∅: partes_fijas.append(V_res)

retornar partes_fijas
```

### 2.2 Parámetros de _queyranne_iterativo
| Parámetro | Tipo | Descripción | Default |
|---|---:|---|---|
| `T` | `np.ndarray` | Matriz de costos (n×n), pre-calculada | requerido |
| `self.k` | `int` | Número de particiones buscadas | 2 |
| `self.verbose` | `bool` | Imprimir progreso de iteraciones | False |

### 2.3 Análisis de complejidad
| Componente | Complejidad | Observación |
|---|---|---|
| Queyranne (una fase) | O(n³) | n fases de construcción de secuencia, cada una evalúa O(n²) pares |
| k iteraciones | O(k · n³) | Ejecuta Queyranne k veces |
| `_evaluar_perdida_restringida` | O(n) | Consulta T en O(1), suma restringida O(n) |
| **Total KQNodes** | **O(k · n³)** | Lineal en k, cúbica en n |
| QNodes (k=2) | O(n³) | Caso especial con una sola iteración |
| Búsqueda exhaustiva | O(n^k) | Impracticable para n, k moderados |

### 2.4 Casos límite
- **k=2**: Equivalente a QNodes puro; una iteración extrae la bipartición óptima y lo restante forma la segunda parte.
- **k=n**: Cada iteración extrae un singleton; resulta en partición trivial {0}, {1}, ..., {n-1}.
- **V_res vacío**: Si todas las variables se asignan antes de k-1 iteraciones, el bucle se interrumpe; partes_fijas tendrá < k elementos.
- **V_res singleton**: En última iteración, si V_res = {v}, se añade como parte final sin ejecutar Queyranne.

## 3 API Pública y Referencia de Métodos

### 3.1 Tabla de métodos de KQNodes
| Método | Firma completa | Retorno | Descripción | Complejidad |
|---|---|---|---|---|
| `__init__` | `__init__(gestor, k=2, refinar=True, verbose=False)` | - | Inicializa el algoritmo con parámetros | O(1) |
| `aplicar_estrategia` | `aplicar_estrategia() -> Solution` | `Solution` | Ejecuta la estrategia k-MIP | O(k·n³) |
| `_obtener_tabla_costos` | `_obtener_tabla_costos() -> np.ndarray` | `np.ndarray` | Construye matriz T | O(n²) |
| `_queyranne_iterativo` | `_queyranne_iterativo(T) -> List[frozenset]` | `List[frozenset]` | Ejecuta Queyranne k veces | O(k·n³) |
| `_evaluar_perdida_restringida` | `_evaluar_perdida_restringida(S, V_res, partes_fijas, T)` | `float` | Evalúa pérdida de parte S | O(n) |
| `_intercambio_local` | `_intercambio_local(partes) -> List[frozenset]` | `List[frozenset]` | Refina partición con intercambios | O(k²·n²) |
| `_validar_particion` | `_validar_particion(partes) -> bool` | `bool` | Valida que suma sea todas las vars | O(n) |

### 3.2 Detalle de _evaluar_perdida_restringida()
```python
def _evaluar_perdida_restringida(
    self,
    S: frozenset,
    V_res: frozenset,
    partes_fijas: List[frozenset],
    T: np.ndarray,
) -> float:
    """
    Parámetros:
    - S: frozenset de índices de variables candidatas (ej: {0, 2})
    - V_res: frozenset de variables aún sin particionar (ej: {0, 1, 2})
    - partes_fijas: lista de frozensets ya asignadas en iteraciones previas
    - T: matriz de costos n×n
    
    Restricciones:
    - S no puede ser vacío ni igual a V_res → retorna float('inf')
    - Requiere que sia_subsistema esté inicializado (llamar sia_preparar_subsistema)
    
    Retorna: float (pérdida EMD entre distribución global y producto tensorial)
    
    Ejemplo de llamada:
    S = frozenset({0})
    V_res = frozenset({0, 1, 2})
    partes_fijas = []
    T = np.array([[1, 2, 3], [2, 4, 5], [3, 5, 6]], dtype=np.float32)
    
    perdida = kqnodes._evaluar_perdida_restringida(S, V_res, partes_fijas, T)
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
from src.strategies.kqnodes import KQNodes

def iniciar():
    gestor = Manager(estado_inicial)
    analizador = KQNodes(gestor, k=3, refinar=True, verbose=True)
    resultado = analizador.aplicar_estrategia()
    print(resultado)
```
Imitar el patrón de QNodes: importar clase → instanciar → llamar `aplicar_estrategia()`.

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
    
    def _evaluar_perdida_restringida(self, S, V_res, partes_fijas, T):
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
┌─────────────────────────────────┐
│  aplicar_estrategia()           │
└────────────┬────────────────────┘
             │ t0 = perf_counter()
             ▼
    ┌─────────────────────────┐
    │  _obtener_tabla_costos()│──→ T (n×n)
    └────────┬────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ _queyranne_iterativo(T)  │──→ partes (k frozensets)
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ _validar_particion()     │ (lanza ValueError si falla)
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ if refinar               │
    │   _intercambio_local()   │──→ partes refinadas
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ tiempo_ms = elapsed()    │
    │ return Solution(...)     │
    └──────────────────────────┘
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
| EMD negativa o `NaN` | Pérdida calculada con `emd_efecto()` recibe distribuciones no normalizadas o con ceros | Verificar `sia_dists_marginales`, normalizar marginals y agregar epsilon antes de `log`/división |
| `ImportError` por paths incorrectos entre KQNodes y QNodes | `src` no apunta a las carpetas correctas o los módulos se importan desde la raíz equivocada | Asegurar `sys.path` incluye `KQNodes/src` y `QNodes/src`, o usar imports relativos en tests y `main.py` |
| Queyranne sin convergencia | Dominio de `V_res` mal reducido o función `f_i` no submodular | Revisar construcción de `V_res`, `partes_fijas` y la definición de `_evaluar_perdida_restringida()` |

### 5.3 Referencias
- Queyranne, D. P. (1998). “A fast algorithm for minimization of submodular functions.”
- Nemhauser, G. L., Wolsey, L. A., & Fisher, M. L. (1978). “An analysis of approximations for maximizing submodular set functions.”
- Documento de formalización: `../KQNodes_Formalizacion.docx`
- Diagramas de diseño: `../KQNodes_Diagramas.md`

| Versión | Autor | Fecha | Estado |
|---|---|---|---|
| 0.1 | Equipo KQNodes | 30/05/2026 | Draft funcional |
