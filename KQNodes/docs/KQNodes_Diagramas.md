# KQNodes — Diagramas UML

> Diagramas de clases, secuencia, estados y paquetes para la implementación de KQNodes
> en el framework GeoMIP. Todos los diagramas están en sintaxis **Mermaid** y son
> renderizables directamente en GitHub, VS Code (extensión Mermaid Preview) y Notion.

---

## 1. Diagrama de Paquetes

```mermaid
graph TD
    subgraph framework["📦 GeoMIP Framework"]
        subgraph entrada["📥 Capa de Entrada"]
            CFG["configuracion.py\n(TPM, estado_inicial, k)"]
        end

        subgraph nucleo["⚙️ Núcleo Computacional IIT"]
            TPM_MOD["tpm.py\n(carga, validación)"]
            METRICS["metrics.py\n(emd_pyphi, hamming)"]
            TENSORS["tensors.py\n(producto tensorial,\nmarginalización)"]
            HYPERCUBE["hypercube.py\n(N-Cubo, BFS,\ntabla de costos T)"]
        end

        subgraph strategies["🧠 Capa de Estrategias"]
            SIA["sia.py\nClase Base SIA\n(interfaz común)"]
            QNODES["qnodes.py\nQNodes\n(Queyranne k=2)"]
            GEOMIP["geometric.py\nGeoMIP\n(hipercubo k=2)"]
            KQNODES["kqnodes.py ⭐\nKQNodes\n(Queyranne k≥2)"]
        end

        subgraph evaluacion["📊 Capa de Evaluación"]
            PARTITION["partition_eval.py\n(evaluar δₖ, generar\ncandidatos)"]
        end

        subgraph salida["📤 Capa de Salida"]
            RESULT["resultado_sia.py\n(ResultadoSIA:\npartición + pérdida)"]
        end

        subgraph tests["🧪 Tests"]
            T1["test_kqnodes.py ⭐\n(5 casos de prueba)"]
            T2["test_qnodes.py"]
            T3["test_geomip.py"]
        end
    end

    CFG --> TPM_MOD
    TPM_MOD --> nucleo
    SIA --> QNODES
    SIA --> GEOMIP
    SIA --> KQNODES
    KQNODES --> HYPERCUBE
    KQNODES --> METRICS
    KQNODES --> TENSORS
    KQNODES --> PARTITION
    PARTITION --> RESULT
    T1 --> KQNODES
```

---

## 2. Diagrama de Clases

```mermaid
classDiagram
    class SIA {
        <<abstract>>
        #gestor : Gestor
        #tpm : ndarray
        #estado_inicial : int
        +__init__(gestor)
        +aplicar_estrategia()* ResultadoSIA
        #_construir_resultado(partes) ResultadoSIA
        #_evaluar_emd(dist_a, dist_b) float
    }

    class QNodes {
        -_grafo : dict
        +__init__(gestor)
        +aplicar_estrategia() ResultadoSIA
        -_queyranne(V, f) tuple
        -_pendant_pairs(V, f) list
        -_construir_grafo_afinidad() dict
    }

    class GeoMIPSIA {
        -_tabla_T : ndarray
        -_ncubo : NCubo
        +__init__(gestor)
        +aplicar_estrategia() ResultadoSIA
        -_calcular_tabla_costos() ndarray
        -_identificar_biparticion(T) tuple
        -_evaluar_complementariedad(T) float
    }

    class KQNodes {
        -_tabla_T : ndarray
        -k : int
        -refinar : bool
        -verbose : bool
        +__init__(gestor, k, refinar, verbose)
        +aplicar_estrategia() ResultadoSIA
        -_obtener_tabla_costos() ndarray
        -_queyranne_iterativo(T) list~frozenset~
        -_evaluar_perdida_restringida(S, V_res, partes_fijas, T) float
        -_intercambio_local(partes) list~frozenset~
        -_validar_particion(partes) bool
    }

    class NCubo {
        -dimension : int
        -vertices : ndarray
        +__init__(n)
        +hamming(i, j) int
        +vecinos(v) list
        +bfs_ponderado(i, j, X) float
        +calcular_tabla_T(tensors) ndarray
    }

    class ResultadoSIA {
        +particion : list~frozenset~
        +perdida : float
        +metodo : str
        +tiempo_ms : float
        +k : int
        +__repr__() str
    }

    class Gestor {
        +tpm : ndarray
        +n : int
        +k : int
        +estado_inicial : int
        +mecanismo : list
        +purview : list
    }

    SIA <|-- QNodes : hereda
    SIA <|-- GeoMIPSIA : hereda
    SIA <|-- KQNodes : hereda ⭐
    KQNodes ..> NCubo : usa
    KQNodes ..> ResultadoSIA : produce
    GeoMIPSIA ..> NCubo : usa
    SIA --> Gestor : compone
    SIA ..> ResultadoSIA : produce
```

---

## 3. Diagrama de Secuencia — Flujo principal KQNodes

```mermaid
sequenceDiagram
    actor Usuario
    participant Main as main.py
    participant Gestor as Gestor
    participant KQ as KQNodes
    participant Geo as GeoMIPSIA
    participant NCubo as NCubo
    participant Metrics as metrics.py
    participant Result as ResultadoSIA

    Usuario->>Main: ejecutar(tpm, k=3, metodo="kqnodes")
    Main->>Gestor: __init__(tpm, estado_inicial, k)
    Main->>KQ: __init__(gestor, k=3, refinar=True)

    Main->>KQ: aplicar_estrategia()

    rect rgb(230, 240, 255)
        Note over KQ,NCubo: Fase 1 — Tabla de costos (reutiliza GeoMIP)
        KQ->>Geo: _calcular_tabla_costos()
        Geo->>NCubo: calcular_tabla_T(tensors)
        loop Por cada par (i,j) de estados
            NCubo->>NCubo: bfs_ponderado(i, j, X)
        end
        NCubo-->>Geo: tabla T [2ⁿ × 2ⁿ × n]
        Geo-->>KQ: tabla T
    end

    rect rgb(230, 255, 235)
        Note over KQ,Metrics: Fase 2 — Queyranne iterativo (k-1 veces)
        loop i = 1 hasta k-1
            KQ->>KQ: _queyranne(V_res, f_i)
            loop Pendant pairs
                KQ->>Metrics: emd_pyphi(dist_original, dist_parcial)
                Metrics-->>KQ: pérdida f_i(S)
            end
            KQ->>KQ: extraer S_opt, actualizar V_res
        end
        KQ->>KQ: agregar V_res como última parte
    end

    rect rgb(255, 245, 220)
        Note over KQ,Metrics: Fase 3 — Refinamiento local (hill climbing)
        loop Hasta convergencia
            loop Cada variable x, cada parte S_b
                KQ->>Metrics: emd_pyphi(dist_original, dist_con_movimiento)
                Metrics-->>KQ: pérdida si se mueve x
                alt Hay mejora
                    KQ->>KQ: mover x de S_a a S_b
                end
            end
        end
    end

    KQ->>Result: __init__(partes, pérdida, "KQNodes", tiempo, k)
    Result-->>KQ: resultado
    KQ-->>Main: ResultadoSIA
    Main-->>Usuario: partición óptima + δₖ
```

---

## 4. Diagrama de Estados — Ciclo de vida de KQNodes

```mermaid
stateDiagram-v2
    [*] --> Inicializado : KQNodes.__init__()

    Inicializado --> CargandoTPM : aplicar_estrategia()

    CargandoTPM --> CalculandoTablaT : TPM válida
    CargandoTPM --> Error : TPM inválida / dimensión incorrecta

    CalculandoTablaT --> CalculandoTablaT : BFS por par (i,j) — O(n·2ⁿ)
    CalculandoTablaT --> TablaLista : Todos los pares calculados

    TablaLista --> IteracionQueyranne : Iniciar loop i=1..k-1

    state IteracionQueyranne {
        [*] --> PendantPairs
        PendantPairs --> EvaluandoOraculo : por cada par candidato
        EvaluandoOraculo --> PendantPairs : siguiente candidato
        EvaluandoOraculo --> ExtraerCorte : mejor pendant pair encontrado
        ExtraerCorte --> [*]
    }

    IteracionQueyranne --> IteracionQueyranne : i < k-1, V_res no vacío
    IteracionQueyranne --> ParticionInicial : i = k-1 completado

    ParticionInicial --> Refinando : refinar = True
    ParticionInicial --> Finalizado : refinar = False

    state Refinando {
        [*] --> PasadaCompleta
        PasadaCompleta --> EvaluandoMovimiento : para cada (x, S_b)
        EvaluandoMovimiento --> AplicandoMovimiento : pérdida mejora
        EvaluandoMovimiento --> SiguienteMovimiento : sin mejora
        AplicandoMovimiento --> SiguienteMovimiento
        SiguienteMovimiento --> PasadaCompleta : quedan movimientos
        SiguienteMovimiento --> Convergido : sin mejoras en pasada
        Convergido --> [*]
    }

    Refinando --> Finalizado : Convergencia o max_iter alcanzado

    Finalizado --> ResultadoListo : construir ResultadoSIA
    ResultadoListo --> [*]

    Error --> [*]

    note right of CalculandoTablaT : Costo: O(n·2ⁿ)\nReutilizable entre iteraciones
    note right of IteracionQueyranne : k-1 ejecuciones\nCosto: O(k·n³·eval_δ)
    note right of Refinando : Convergencia garantizada\n(pérdida no aumenta)
```

---

## 5. Notas de Implementación

### Archivos a crear / modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `src/controllers/strategies/kqnodes.py` | **CREAR** | Clase KQNodes completa |
| `tests/test_kqnodes.py` | **CREAR** | 5 tests unitarios |
| `src/controllers/strategies/__init__.py` | **MODIFICAR** | Registrar KQNodes |
| `src/main.py` | **MODIFICAR** | Agregar opción `metodo="kqnodes"` |

### Dependencias internas a reutilizar

| Símbolo | Origen | Uso en KQNodes |
|---|---|---|
| `emd_pyphi` | `src/models/metrics.py` | Oráculo de Queyranne |
| `calcular_tabla_T` | `GeoMIPSIA` o `NCubo` | Fase 1 (reusar sin recalcular) |
| `_queyranne` | `QNodes` | Copiar/adaptar para V_res variable |
| `_construir_resultado` | `SIA` | Producir ResultadoSIA estándar |
| `producto_tensorial` | `src/models/tensors.py` | Calcular dist. reconstruida |

### Invariantes que KQNodes debe respetar

- La unión de todas las partes debe ser igual a V completo.
- La intersección de cualquier par de partes debe ser el conjunto vacío.
- Ninguna parte puede quedar vacía.
- Para k=2, el resultado debe coincidir con QNodes (tolerancia 1e-6 en pérdida).
- La pérdida después del refinamiento nunca puede ser mayor que antes.
