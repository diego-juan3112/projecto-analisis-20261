# Arquitectura del proyecto KGeoMIP — Inventario para el commit de entrega

Documento de inventario arquitectónico generado leyendo el árbol real del disco a 2026-06-14. Su propósito es preparar el commit final: clasificar cada archivo, identificar candidatos a eliminar con justificación verificada, y dejar claro qué debe conservarse como evidencia.

**Ámbito.** El código vive en el subproyecto `GeoMIP/src/Method2_Dynamic_Programming_Reformulation/` (en adelante, *Method2*). La documentación de entrega vive en `docs/` (raíz del repositorio) y el respaldo del Excel en la raíz. Todas las rutas son relativas a *Method2* salvo que se indique lo contrario.

**Método.** El árbol se leyó con `find` sobre el disco (no se supuso). Todas las clasificaciones de "eliminable" se verificaron con `grep` sobre los imports reales, no por el nombre del archivo. Nada se elimina en este documento: solo se clasifica y se justifica.

> **Regla de oro (no negociable):** `geometric_oracle.py`, los JSON de validación de `review/`, los logs de llenado de `review/sprint4/`, las gráficas de `review/profiling/` y el `DatosPruebas2026_1.xlsx.bak` **nunca** son candidatos a eliminar: son la evidencia empírica que respalda el manual técnico.

---

## 1. Mapa de carpetas y archivos (árbol real)

Convención de etiquetas: **[N]** Núcleo, **[E]** Entrega, **[A]** Auditoría/Validación, **[O]** Obsoleto/Candidato. Se omiten `.venv/`, `__pycache__/` y `__pyphi_cache__/` (regenerables, no versionables).

```
Method2_Dynamic_Programming_Reformulation/
├── exec.py                         [E] Punto de entrada: activa el profiler e invoca iniciar() de src.main
├── llenar_excel.py                 [E] Orquestador de lotes que llena el Excel de entrega (lado Geometric)
├── test_kgeomip.py                 [E] Script de verificación/comparación (N5A: Geometric k=2 vs KGeometric k=3); citado en el Manual de Usuario
├── pyproject.toml                  [N] Declaración de dependencias y versión de Python (uv sync lo lee)
├── uv.lock                         [N] Versiones exactas resueltas de las dependencias
├── pyphi_config.yml                [O] Config de Pyphi (17 bytes); Pyphi no se usa en KGeoMIP
├── pyphi.log                       [O] Log de Pyphi (161 KB); Pyphi no se usa en KGeoMIP
│
├── src/
│   ├── main.py                     [E] Entrada Geometric (k=2): lee el Excel de pruebas y exporta resultados
│   ├── mainKGeometric.py           [E] Entrada KGeometric (k>=2): idem, con k_objetivo
│   │
│   ├── constants/
│   │   ├── base.py                 [N] Constantes base (bits, índices, etiquetas, rutas, símbolos)
│   │   ├── error.py                [N] Mensajes de error usados por SIA y System
│   │   └── models.py               [N] Etiquetas de estrategias y tags de profiling (incluye KGEOMETRIC_*)
│   │
│   ├── controllers/
│   │   ├── manager.py              [N] Resuelve la ruta del CSV/TPM y el directorio de salida
│   │   └── strategies/
│   │       ├── geometric.py        [N] Estrategia GeometricSIA reformulada (Sprint 2), streaming por niveles
│   │       ├── k_geometric.py      [N] Estrategia KGeometricSIA reescrita (Sprint 3), greedy + B&B
│   │       ├── geometric_oracle.py [A] Oráculo: GeometricSIA original verbatim (evidencia de correctitud)
│   │       ├── q_nodes.py          [E] Estrategia Q-Nodes (otra rama); importada EN VIVO por ambos mains
│   │       ├── phi.py              [O] Estrategia Pyphi; importada en try/except, Pyphi no instalado
│   │       └── force.py            [O] Estrategia BruteForce; solo referida en imports COMENTADOS
│   │
│   ├── funcs/
│   │   ├── base.py                 [N] EMD-efecto, ABECEDARY, reindexar, seleccionar_subestado, little-endian
│   │   ├── format.py               [N] Formato de particiones (fmt_biparte_q, fmt_k_particion)
│   │   ├── excel_io.py             [E] Lectura/escritura robusta del Excel (localización por contenido, N11)
│   │   └── system.py               [O] Helpers de generación de candidatos; ÚNICO importador es force.py
│   │
│   ├── middlewares/
│   │   ├── slogger.py              [N] SafeLogger (logging por estrategia)
│   │   └── profile.py              [N] Decorador @profile y profiler_manager (pyinstrument)
│   │
│   ├── models/
│   │   ├── base/
│   │   │   ├── sia.py              [N] Clase base SIA: sia_preparar_subsistema, condicionar/substraer
│   │   │   └── application.py      [N] Singleton de configuración (notación, semilla, métrica)
│   │   ├── core/
│   │   │   ├── system.py           [N] Clase System: condicionar, substraer, bipartir, distribucion_marginal
│   │   │   ├── ncube.py            [N] Clase NCube: marginalización perezosa por strides + memo
│   │   │   └── solution.py         [N] Clase Solution: empaqueta partición, phi, distribuciones, tiempo
│   │   └── enums/
│   │       ├── notation.py         [N] Enum de notación (little/big endian)
│   │       └── distance.py         [N] Enum de métrica de distancia (EMD-efecto/causa)
│   │
│   └── video/
│       ├── hyper-v0.py … hyper-v8.py  [O] 9 scripts de exploración del hipercubo; nadie los importa
│
├── review/                         (evidencia de la investigación; ver sección 4)
│   ├── sprint2/
│   │   ├── bench_baseline.py       [A] Benchmark del código original (antes de optimizar)
│   │   ├── bench_optimizado.py     [A] Benchmark de la versión reformulada
│   │   ├── diag_tpm.py             [A] Diagnóstico del ciclo de vida del TPM (formatos, carga)
│   │   ├── validar_oraculo.py      [A] Validación reformulada vs oráculo (15/15) + marginalización + endianness
│   │   ├── baseline.json           [A] EVIDENCIA: tiempos/memoria del código original
│   │   ├── optimizado.json         [A] EVIDENCIA: tiempos/memoria de la versión reformulada
│   │   ├── optimizado_n25.json     [A] EVIDENCIA: corrida N=25 completa (395.6 s)
│   │   ├── diag_tpm.json           [A] EVIDENCIA: mediciones del ciclo de vida del TPM
│   │   └── validacion_oraculo.json [A] EVIDENCIA: resultado 15/15 contra el oráculo
│   ├── sprint3/
│   │   ├── bench_kgeo_nuevo.py     [A] Benchmark de la KGeometricSIA reescrita
│   │   ├── bench_kgeo_viejo.py     [A] Benchmark de la KGeometricSIA anterior (baseline)
│   │   ├── validar_kgeo.py         [A] Aceptación k=2 (15/15) + fuerza bruta (7/9)
│   │   ├── kgeo_nuevo.json         [A] EVIDENCIA: mediciones de la versión reescrita (poda Fase 2)
│   │   ├── kgeo_viejo.json         [A] EVIDENCIA: mediciones de la versión anterior
│   │   └── validacion_kgeo.json    [A] EVIDENCIA: aceptación k=2 y fuerza bruta
│   ├── sprint4/
│   │   ├── validar_formales.py     [A] Validación de monotonía e invariancia dimensional
│   │   ├── validacion_formales.json[A] EVIDENCIA: monotonía 9/9, invariancia 10/10
│   │   ├── reanudar_llenado.ps1    [E] Script de la tarea programada de respaldo del llenado
│   │   ├── llenado_nocturno.log    [A] EVIDENCIA: log del llenado (tiempos por caso, 4 timeouts)
│   │   ├── llenado_22A.log         [A] EVIDENCIA: log del llenado de la hoja 22A
│   │   └── llenado_25A.log         [A] EVIDENCIA: log del llenado de la hoja 25A
│   ├── profiling/
│   │   └── NET{3A,5A,15A,20A}/…/aplicar_estrategia.html  [A] 11 perfiles pyinstrument (evidencia de rendimiento)
│   └── resolver/
│       └── N{3A,5A,…,25A}/<estado>/                      [O] 19 carpetas de salida VACÍAS (0 archivos)
│
├── .logs/                          [O] 80 logs auto-generados por SafeLogger (por fecha/hora); se regeneran
│   └── last_*.log                  [O] Enlaces al último log de cada tipo (auto-generados)
└── .dist/                          [O] Carpeta VACÍA
```

Documentación y respaldo (raíz del repositorio):

```
docs/
├── MANUAL_TECNICO_KGEOMIP.md       [A/Entregable] Manual técnico (formal, con demostraciones y evidencia)
├── GUIA_ESTUDIO_KGEOMIP.md         [Entregable]   Guía de estudio didáctica
├── MQ_MANUAL_USUARIO_KGEOMIP.docx  [Entregable]   Manual de usuario (Word, carta, Arial 11)
├── ARQUITECTURA_PROYECTO.md        [Entregable]   Este documento
├── DiagramaDeClases.svg            [Entregable]   Diagrama UML de clases
├── Pipeline.svg                    [Entregable]   Diagrama del pipeline
├── 1_Guía_Proyecto_ADAV1_2_0.pdf   [Ref]          Guía/rúbrica de la asignatura
├── 2_GeoMIP.pdf                    [Ref]          Documento base de GeoMIP
├── ManualGeoMIP.docx               [Ref]          Manual previo de GeoMIP (referencia histórica)
└── Proyecto_KGeoMIP.docx           [Ref]          Documento de proyecto KGeoMIP
DatosPruebas2026_1.xlsx             [E] Excel de entrega con los resultados (lado Geometric lleno)
DatosPruebas2026_1.xlsx.bak         [A] EVIDENCIA: respaldo del Excel previo al llenado (NO eliminar)
```

---

## 2. Clasificación por categoría (resumen)

| Categoría | Qué incluye | Conteo (.py salvo nota) |
|---|---|---|
| **NÚCLEO** | Imprescindible para que GeometricSIA y KGeometricSIA corran | 17 `.py` + `pyproject.toml` + `uv.lock` |
| **ENTREGA** | Produce/soporta los resultados del Excel | `main.py`, `mainKGeometric.py`, `exec.py`, `llenar_excel.py`, `excel_io.py`, `test_kgeomip.py`, `reanudar_llenado.ps1`, `q_nodes.py` (dependencia viva de los mains) |
| **AUDITORÍA/VALIDACIÓN** | Evidencia que respalda el manual | `geometric_oracle.py`, 8 scripts bench/validar, 9 JSON, 11 HTML, 3 logs de llenado, `.bak` |
| **OBSOLETO/CANDIDATO** | Sin función en el flujo actual | `force.py`, `funcs/system.py`, `phi.py`, 9 `video/hyper-v*.py`, `.logs/` (80), `pyphi.log`, `pyphi_config.yml`, `__pyphi_cache__/`, `resolver/` (vacío), `.dist/` (vacío) |

---

## 3. Candidatos a eliminar (con verificación de imports)

Cada candidato indica: ruta, por qué es eliminable, y el riesgo real verificado con `grep`.

### 3.1 Código fuente sin uso en vivo

**`src/controllers/strategies/force.py`** — Estrategia BruteForce.
- *Por qué:* solo aparece en imports **comentados** de `main.py` (línea 4) y `mainKGeometric.py` (línea 4). No hay ningún import en vivo (verificado: `grep` solo encuentra las dos líneas comentadas).
- *Riesgo:* ninguno para el código en ejecución. Es la única pieza que importa `funcs/system.py`, así que ambos se archivan juntos.

**`src/funcs/system.py`** — Helpers de generación de candidatos/subsistemas.
- *Por qué:* su **único** importador es `force.py` (verificado: `grep "funcs.system"` solo lo referencia desde `force.py`). No confundir con `models/core/system.py`, que es la clase `System` real del núcleo y se usa en todas partes.
- *Riesgo:* ninguno si `force.py` también se archiva. Si `force.py` se conserva, este debe conservarse.

**`src/video/hyper-v0.py` … `hyper-v8.py`** (9 archivos) — Scripts de exploración del hipercubo.
- *Por qué:* **nadie** los importa (verificado: `grep "video\|hyper-v"` sobre todo el repo, excluyendo la propia carpeta, devuelve vacío). Son tanteos de investigación desechados.
- *Riesgo:* ninguno. Conviene archivarlos por si documentan ideas, no borrarlos sin más.

**`src/controllers/strategies/phi.py`** — Estrategia basada en Pyphi.
- *Por qué:* se importa en un bloque `try/except` en ambos mains (línea 72/73); como **Pyphi no está instalado** (verificado), el `except` la neutraliza a `None`. Funcionalmente inactiva en este entorno.
- *Riesgo:* bajo. El `try/except` tolera su ausencia, así que borrarla no rompe la carga. **Recomendación: archivar, no borrar**, porque el manual técnico (sección 11) la menciona como vía futura de comparación contra PyPhi como *ground truth*. Si se archiva, conviene quitar también el bloque `try/except from src.controllers.strategies.phi import Phi` de ambos mains para no dejar una importación rota.

### 3.2 Dependencia viva que NO debe borrarse sin refactor

**`src/controllers/strategies/q_nodes.py`** — Estrategia Q-Nodes (otra rama).
- *Por qué parecería candidata:* el proyecto KGeoMIP no la usa, y aunque ambos mains la **importan**, **nunca la instancian** (verificado: `grep "QNodes("` no encuentra ninguna instanciación).
- *Riesgo: ALTO si se borra directamente.* La importación es **en vivo** (sin comentar): `main.py:69` y `mainKGeometric.py:70` ejecutan `from src.controllers.strategies.q_nodes import QNodes` al cargar el módulo. Borrar el archivo rompe la carga de ambos mains. Solo es eliminable como **refactor**: primero quitar esa línea de import de ambos mains (y solo entonces el archivo queda huérfano). No es una eliminación simple; queda fuera de la limpieza de bajo riesgo.

### 3.3 Artefactos y salidas regenerables

**`.logs/`** (80 archivos `.log` auto-generados por `SafeLogger`, organizados por fecha/hora, más los `last_*.log`).
- *Por qué:* son logs de cada corrida; se regeneran en cada ejecución. **No** son la evidencia del manual (esa está en `review/sprint4/`).
- *Riesgo:* ninguno. Recomendación: eliminar del commit y añadir `.logs/` a `.gitignore`.

**`pyphi.log`** (161 KB) y **`pyphi_config.yml`** (17 bytes) y **`__pyphi_cache__/`**.
- *Por qué:* artefactos de Pyphi, que no se usa en KGeoMIP (verificado: Pyphi no instalado; la única estrategia que lo invocaría es `phi.py`, inactiva).
- *Riesgo:* ninguno.

**`review/resolver/`** (19 subcarpetas) y **`.dist/`**.
- *Por qué:* `resolver/` contiene 0 archivos (verificado: `find review/resolver -type f` devuelve vacío); son solo carpetas de salida auto-generadas. `.dist/` está vacía.
- *Riesgo:* ninguno. Carpetas vacías; se recrean solas si el código las necesita.

---

## 4. Lo que debe quedarse sí o sí (por categoría)

### 4.1 Núcleo (sin esto el algoritmo no corre)

Los 17 `.py` del árbol marcados **[N]**, más `pyproject.toml` y `uv.lock`. Justificación: la cadena de imports de `geometric.py` y `k_geometric.py` (sección 5) toca exactamente estos archivos; quitar cualquiera produce un `ImportError`. `pyproject.toml`/`uv.lock` son necesarios para que `uv sync` reconstruya el entorno.

### 4.2 Entrega (produce los resultados del Excel)

- `llenar_excel.py` + `src/funcs/excel_io.py`: orquestador y E/S robusta del Excel de entrega.
- `src/main.py`, `src/mainKGeometric.py`, `exec.py`: puntos de entrada del flujo de resultados.
- `test_kgeomip.py`: verificación citada en el Manual de Usuario.
- `review/sprint4/reanudar_llenado.ps1`: tarea de respaldo del llenado.
- `q_nodes.py`: dependencia viva de los mains (ver 3.2); se conserva mientras los mains la importen.

### 4.3 Auditoría / Evidencia (respalda el manual; NO eliminar)

- **`src/controllers/strategies/geometric_oracle.py`** — el oráculo. Evidencia de correctitud; lo importa `validar_oraculo.py`. **Nunca** candidato.
- **JSON de validación (9):** `baseline.json`, `optimizado.json`, `optimizado_n25.json`, `diag_tpm.json`, `validacion_oraculo.json` (sprint2); `kgeo_nuevo.json`, `kgeo_viejo.json`, `validacion_kgeo.json` (sprint3); `validacion_formales.json` (sprint4). Son la evidencia empírica de los resultados del manual.
- **Scripts de benchmark/validación (8):** `bench_baseline.py`, `bench_optimizado.py`, `diag_tpm.py`, `validar_oraculo.py`, `bench_kgeo_nuevo.py`, `bench_kgeo_viejo.py`, `validar_kgeo.py`, `validar_formales.py`. Permiten reproducir la evidencia.
- **Perfiles pyinstrument (11 `.html`)** en `review/profiling/`: evidencia de rendimiento citada en el manual (sección 8).
- **Logs de llenado (3)** en `review/sprint4/`: `llenado_nocturno.log`, `llenado_22A.log`, `llenado_25A.log`. Registran los tiempos por caso y los 4 timeouts documentados.
- **`DatosPruebas2026_1.xlsx.bak`** (raíz): respaldo del Excel previo al llenado. **Nunca** candidato.

### 4.4 Documentación de entrega

`docs/MANUAL_TECNICO_KGEOMIP.md`, `docs/GUIA_ESTUDIO_KGEOMIP.md`, `docs/MQ_MANUAL_USUARIO_KGEOMIP.docx`, este documento, y los diagramas `DiagramaDeClases.svg` / `Pipeline.svg`.

---

## 5. Dependencias entre archivos clave (grafo)

Flecha `A → B` significa "A importa a B". Verificado con `grep` sobre los imports reales.

```
exec.py
  └─→ src/main.py
        ├─→ controllers/manager.py
        ├─→ controllers/strategies/geometric.py        (ver cadena NÚCLEO)
        ├─→ controllers/strategies/q_nodes.py          (import vivo, no instanciado)
        └─→ controllers/strategies/phi.py              (try/except; inactivo)

src/mainKGeometric.py
  ├─→ controllers/manager.py
  ├─→ controllers/strategies/geometric.py
  ├─→ controllers/strategies/k_geometric.py            (ver cadena NÚCLEO)
  ├─→ controllers/strategies/q_nodes.py                (import vivo, no instanciado)
  └─→ controllers/strategies/phi.py                    (try/except; inactivo)

llenar_excel.py
  ├─→ funcs/excel_io.py
  └─→ controllers/strategies/k_geometric.py            (en el subproceso)

CADENA NÚCLEO (común a geometric.py, k_geometric.py y geometric_oracle.py):
  geometric.py / k_geometric.py / geometric_oracle.py
    ├─→ models/base/sia.py
    │     ├─→ controllers/manager.py ─→ models/base/application.py
    │     │                            └─→ constants/base.py
    │     ├─→ models/core/system.py
    │     │     ├─→ models/core/ncube.py
    │     │     ├─→ models/enums/notation.py
    │     │     ├─→ funcs/base.py ─→ models/enums/{distance,notation}.py, models/base/application.py, constants/base.py
    │     │     └─→ constants/base.py
    │     ├─→ constants/{models,error,base}.py
    │     └─→ middlewares/slogger.py
    ├─→ models/core/solution.py        (usa colorama y pyttsx3)
    ├─→ funcs/base.py                  (usa pyemd para emd_causal; emd_efecto es numpy puro)
    ├─→ funcs/format.py ─→ funcs/base.py, constants/base.py
    ├─→ middlewares/profile.py         (pyinstrument)
    └─→ constants/{base,models}.py

DEPENDENCIAS DE LOS CANDIDATOS (por qué son huérfanos o no):
  force.py ─→ funcs/system.py          (force.py NO es importado en vivo por nadie → ambos huérfanos)
  funcs/system.py ←── solo force.py    (sin otro importador)
  video/hyper-v*.py                    (sin importadores; aislados)
  q_nodes.py ←── main.py, mainKGeometric.py (IMPORT VIVO → no huérfano)
  q_nodes.py ─→ funcs/base.py, funcs/format.py
```

Lectura del grafo: el núcleo es un grafo conexo que cuelga de `sia.py` y `manager.py`. `force.py`/`funcs/system.py` y `video/*` están **desconectados** del grafo vivo (nadie los alcanza). `q_nodes.py` **sí** está conectado (lo alcanzan los mains), por eso no es un candidato simple.

---

## 6. Recomendación de estructura final para el commit

### 6.1 Qué permanece tal cual

- Todo el árbol `src/` marcado **[N]** y **[E]** (núcleo + entrega), incluido `q_nodes.py` mientras los mains lo importen.
- `exec.py`, `llenar_excel.py`, `test_kgeomip.py`, `pyproject.toml`, `uv.lock`.
- Todo `review/sprint2`, `review/sprint3`, `review/sprint4` (scripts + JSON + logs) y `review/profiling/` (evidencia).
- `geometric_oracle.py` (en su sitio, junto a las estrategias).
- `docs/` y `DatosPruebas2026_1.xlsx` + `DatosPruebas2026_1.xlsx.bak`.

### 6.2 Qué archivar en vez de borrar

Crear `Method2_Dynamic_Programming_Reformulation/archive/` y mover allí, conservando la evidencia de investigación sin ensuciar la raíz:

- `src/controllers/strategies/force.py` → `archive/strategies/force.py`
- `src/funcs/system.py` → `archive/funcs/system.py` (va con force.py)
- `src/controllers/strategies/phi.py` → `archive/strategies/phi.py` (y quitar su `try/except` de los mains)
- `src/video/hyper-v0.py … hyper-v8.py` → `archive/video/`

> **NOTA:** archivar `force.py`/`phi.py` implica quitar sus líneas de import (comentadas e inactivas, respectivamente) de `main.py` y `mainKGeometric.py` para no dejar referencias colgando. El `q_nodes.py` queda donde está hasta que se decida si se desacopla de los mains.

### 6.3 Qué eliminar del commit (regenerable, sin valor de evidencia)

- `.logs/` (80 logs auto-generados) → eliminar y añadir a `.gitignore`.
- `review/resolver/` (carpetas vacías) y `.dist/` (vacía) → eliminar.
- `pyphi.log`, `pyphi_config.yml`, `__pyphi_cache__/` → eliminar (Pyphi inactivo).
- `__pycache__/`, `.venv/` → asegurarse de que estén en `.gitignore` (no versionar).

### 6.4 `.gitignore` sugerido (entradas mínimas)

```
.venv/
__pycache__/
__pyphi_cache__/
.logs/
.dist/
review/resolver/
*.pyc
pyphi.log
```

---

## 7. Resumen cuantitativo

- **Archivos totales en *Method2*** (excluyendo `.venv/`, `__pycache__/`, `__pyphi_cache__/`): **153**.
  - 45 `.py`, 84 `.log` (80 auto-generados en `.logs/` + 3 de llenado en `review/sprint4/` + `pyphi.log`), 11 `.html` (profiling), 9 `.json` (validación), más `pyproject.toml`, `uv.lock`, `pyphi_config.yml`, `reanudar_llenado.ps1`.
- **Núcleo:** 17 `.py` imprescindibles (+ `pyproject.toml`, `uv.lock`).
- **Entrega:** 7 `.py`/`.ps1` (+ `q_nodes.py` como dependencia viva).
- **Auditoría/Evidencia:** `geometric_oracle.py` + 8 scripts + 9 JSON + 11 HTML + 3 logs de llenado + `.bak`.
- **Obsoletos / candidatos:** **~95 elementos** repartidos así — 12 `.py` de código muerto (`force.py`, `funcs/system.py`, `phi.py`, 9 `video/*`), 80 logs auto-generados en `.logs/`, `pyphi.log`, `pyphi_config.yml`, más `__pyphi_cache__/`, `review/resolver/` (19 dirs vacíos) y `.dist/`. De los 45 `.py`, **12 son candidatos** (de los cuales `phi.py` se recomienda archivar, no borrar, y `q_nodes.py` NO es candidato pese a no usarse: import vivo).

Nada se elimina en este documento; la limpieza la ejecuta el equipo tras revisarlo.
