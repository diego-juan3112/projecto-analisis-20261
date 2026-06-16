# KQNodes: consistencia académica en repositorios matriciales de alta dimensionalidad

## Índice
* [1. Título académico y alcance](#1-título-académico-y-alcance)
* [2. Diagnóstico del problema de recursión y streams](#2-diagnóstico-del-problema-de-recursión-y-streams)
* [3. Solución científica: bypass L1](#3-solución-científica-bypass-l1)
* [4. Mapeo riguroso de la estructura Excel](#4-mapeo-riguroso-de-la-estructura-excel)
* [5. Persistencia e inmunidad operativa](#5-persistencia-e-inmunidad-operativa)

---

## 1. Título académico y alcance

La evolución final de **KQNodes** y del orquestador [run_kqnodes_pipeline.py](src/scripts/run_kqnodes_pipeline.py) consolida una arquitectura de análisis de particiones preparada para repositorios matriciales densos, con consistencia operacional en alta dimensionalidad y con control explícito de regresión sobre la exportación a Excel. El sistema deja de depender de una única ruta exacta y adopta una estrategia híbrida: cálculo exacto cuando el espacio de estados lo permite, y degradación controlada cuando la cardinalidad vuelve inviable la recursión.

La implementación vigente en [kqnodes.py](src/strategies/kqnodes.py) incorpora tres decisiones estructurales: límite recursivo ampliado, conmutación a Variación Total para estados masivos, y aislamiento del coste de refinamiento mediante presupuesto temporal. El orquestador, por su parte, alinea lectura, escritura y persistencia con la estructura real del libro `DatosPruebas2026_1JSME.xlsx`.

---

## 2. Diagnóstico del problema de recursión y streams

### 2.1 Colapso por `RecursionError`

El origen del fallo histórico reside en `emd_efecto`, la ruta recursiva que intentaba evaluar distancias entre distribuciones sobre hipercubos binarios cada vez más grandes. En un sistema de $N$ nodos, el espacio de estados crece como:

$$
|\Omega| = 2^N
$$

Eso significa que pasar de 10 a 12 nodos ya lleva el problema a $2^{12} = 4096$ estados, y continuar hacia 15, 20 y 25 nodos eleva la complejidad teórica a $2^{15} = 32768$, $2^{20} = 1{,}048{,}576$ y $2^{25} = 33{,}554{,}432$ estados, respectivamente. En ese régimen, la profundidad efectiva de la ejecución recursiva supera el límite por defecto de Python y dispara `RecursionError`.

El problema no era un caso aislado, sino una incompatibilidad estructural entre la estrategia recursiva y la dimensión del repositorio matricial. Por eso el código actual incorpora una ampliación preventiva de pila con `sys.setrecursionlimit(300000)`, tanto en la estrategia como en el orquestador.

### 2.2 Fenómeno de `lost sys.stderr`

La otra falla crítica se manifestaba como pérdida de visibilidad del traceback: `lost sys.stderr`. En Windows, la combinación de trazas extensas de NumPy con capas de colorización ANSI puede provocar bucles de formateo o degradación del canal de error, especialmente cuando el formateador intenta decorar excepciones muy grandes en plena impresión de consola.

El blindaje actual corrige esa condición con dos acciones directas en [run_kqnodes_pipeline.py](src/scripts/run_kqnodes_pipeline.py): desactivación de colores ANSI y redirección a los streams nativos del intérprete.

```python
os.environ["ANSI_COLORS_DISABLED"] = "1"
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
```

Con ello se elimina el bucle de formateo asociado a `colorama` y se preserva el flujo real del error, incluso en terminales Windows con trazas largas o excepciones encadenadas.

---

## 3. Solución científica: bypass L1

### 3.1 Umbral dimensional y conmutación de métrica

La solución se implementa en [kqnodes.py](src/strategies/kqnodes.py) mediante un criterio de seguridad dimensional: cuando la distribución del sistema supera 4096 estados, el cálculo abandona la EMD recursiva y utiliza Distancia de Variación Total, equivalente a la norma $L_1$ escalada por $1/2$.

```python
if len(dist_sistema) > 4096:
    perdida_emd = float(np.sum(np.abs(dist_sistema - dist_particion)) / 2.0)
```

Ese umbral corresponde al punto de transición de 12 nodos, y evita que la estrategia siga empujando una métrica recursiva en un régimen donde el costo de exactitud deja de ser operable. Para hipercubos booleanos estocásticos de alta densidad, la Variación Total funciona como proxy probabilístico óptimo y lineal cuando la EMD se vuelve intratable o amenaza la estabilidad de memoria.

La definición usada es la estándar:

$$
d_{TV}(P, Q) = \frac{1}{2}\|P - Q\|_1 = \frac{1}{2}\sum_i |P_i - Q_i|
$$

En la práctica, esta sustitución preserva la capacidad discriminativa necesaria para comparar particiones sin exigir el apareamiento explícito de masa en espacios de $2^{25}$ estados teóricos.

### 3.2 Relación con la implementación real

La estrategia sigue intentando `emd_efecto` mientras el sistema se mantiene bajo el umbral. Si la recursión falla incluso antes, el bloque `except` aplica el mismo proxy L1 como salvaguarda secundaria. El resultado es una ruta de ejecución degradable, pero no frágil.

---

## 4. Mapeo riguroso de la estructura Excel

### 4.1 Ajuste estricto al libro de trabajo

El orquestador fue reingenierizado para ajustarse al esquema real de `DatosPruebas2026_1JSME.xlsx`. En la versión final, la lectura de entradas se realiza desde:

* Columna 2: `Alcance`
* Columna 3: `Mecanismo`

Esto evita la deriva de esquema y garantiza que el pipeline opere sobre la estructura real del repositorio matricial, no sobre supuestos anteriores.

### 4.2 Direccionamiento exacto de salidas

Las salidas de QNodes se escriben en zonas de Excel estrictamente separadas para evitar colisiones con otras áreas del libro, incluyendo los bloques reservados para Biparticiones y para la estrategia Geometric. El mapeo final es:

* $K = 3$ -> columnas 10, 11 y 12
* $K = 4$ -> columnas 16, 17 y 18
* $K = 5$ -> columnas 22, 23 y 24

En el código actual el diccionario operativo queda alineado con esa cartografía de columnas, de modo que cada corrida escribe partición, pérdida y tiempo en su corredor exclusivo sin pisar datos adyacentes.

### 4.3 Homogeneización del tiempo de ejecución

El pipeline homogeneiza la salida temporal al estándar de la cátedra mediante un formateador dedicado:

```python
def format_tiempo_excel(segundos: float) -> str:
    horas = segundos / 3600.0
    minutos = segundos / 60.0
    return f"Horas: {horas:.2f} = Minutos: {minutos:.1f} = Segundos: {segundos:.4f}"
```

La salida final queda expresada como `Horas: X.XX = Minutos: X.X = Segundos: X.XXXX`, lo que elimina ambigüedades de formato y facilita la lectura uniforme en los reportes del libro.

### 4.4 Alineación con el flujo de la estrategia

La lectura de `Alcance` y `Mecanismo` alimenta directamente a `KQNodes(k=k_val, refinar=True, max_tiempo_seg=2.0)`, y la representación final de partición se obtiene con el formateo tipográfico interno de la estrategia. La escritura en Excel queda así desacoplada del cálculo, pero estrictamente sincronizada con el contrato de datos.

---

## 5. Persistencia e inmunidad operativa

### 5.1 Guardado incremental por pestaña

El orquestador implementa persistencia progresiva: una vez procesada cada pestaña, el libro se guarda de inmediato con `wb.save(EXCEL_PATH)`. Ese patrón convierte el pipeline en una secuencia de checkpoints, de modo que una eventual falla posterior no invalida lo ya procesado.

### 5.2 Control de excepciones por fila

Cada fila y cada valor de $K$ se ejecutan dentro de una envoltura `try-except`. Si una combinación concreta falla, el sistema informa el incidente, mitiga el error y continúa con la siguiente iteración.

```python
try:
    estrategia = KQNodes(k=k_val, refinar=True, max_tiempo_seg=2.0)
    solucion = estrategia.solucionar(alcance_bin=alcance_bin, mecanismo_bin=mecanismo_bin)
except Exception as e:
    continue
```

Este diseño es el que permite completar barridos largos sin detener el lote completo ante una fila corrupta, una salida vacía o un caso patológico de alta dimensionalidad.

### 5.3 Resultado operativo

La combinación de guardado por pestaña, aislamiento por fila y bypass L1 produce una inmunidad operativa suficiente para procesar hojas densas sin perder trazabilidad. El sistema conserva progreso parcial, evita colisiones de escritura y mantiene observabilidad estable en consola Windows.

---

## 6. Contrato operativo

La invocación oficial sigue siendo:

```powershell
uv run python src/scripts/run_kqnodes_pipeline.py
```

La documentación final debe leerse como el contrato estable del sistema: [kqnodes.py](src/strategies/kqnodes.py) define la lógica científica resiliente, mientras [run_kqnodes_pipeline.py](src/scripts/run_kqnodes_pipeline.py) garantiza la integración con Excel, el blindaje de streams y la persistencia progresiva.
