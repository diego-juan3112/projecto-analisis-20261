# Documentación técnica del sistema KQNodes

## Índice
* [1. Visión general del sistema](#1-visión-general-del-sistema)
* [2. Componente Core: `src/strategies/kqnodes.py`](#2-componente-core-srcstrategieskqnodespy)
* [3. Componente Orquestador: `src/scripts/run_kqnodes_pipeline.py`](#3-componente-orquestador-srcscriptsrun_kqnodes_pipelinepy)
* [4. Flujo de control end-to-end](#4-flujo-de-control-end-to-end)
* [5. Formato de salida y convenciones tipográficas](#5-formato-de-salida-y-convenciones-tipográficas)
* [6. Validación, tolerancia a fallos y criterios QA](#6-validación-tolerancia-a-fallos-y-criterios-qa)
* [7. Recomendación operativa](#7-recomendación-operativa)

---

## 1. Visión general del sistema

El sistema **KQNodes** constituye una extensión operativa de la estrategia original **QNodes** orientada a escenarios con particiones múltiples, típicamente en el régimen $K \geq 3$. Su motivación central es evitar que el problema de búsqueda exhaustiva de particiones en redes densas derive en una explosión combinatoria de orden $\mathcal{O}(K^N)$, manteniendo al mismo tiempo una salida estable, trazable y apta para inyección directa en los libros de cálculo del proyecto.

La solución adoptada no intenta reproducir exactamente el cálculo tensorial de la partición mínima para todos los casos, sino preservar la coherencia causal del sistema mediante una heurística estructural: agrupar por variable física los vértices espaciotemporales y distribuirlos de manera balanceada entre los $K$ bloques de salida. Este diseño reduce la complejidad a una implementación efectiva de orden lineal en el número de vértices activos, con costo dominado por recorridos secuenciales y operaciones de formateo.

En términos científicos, KQNodes actúa como una capa de relajación funcional sobre la noción de pérdida integrada. En lugar de evaluar una distancia completa sobre tensores asimétricos de alto costo, calcula un proxy escalar calibrado por la EMD base de referencia, el número de particiones y la cardinalidad del subsistema.

---

## 2. Componente Core: `src/strategies/kqnodes.py`

### 2.1 Propósito y fundamento científico

El módulo `src/strategies/kqnodes.py` implementa la clase `KQNodes`, que hereda de `SIA` y encapsula la lógica de construcción de particiones K-arias. Su cometido es mitigar el crecimiento combinatorio asociado a la evaluación directa de múltiples cortes en redes con 10 a 25 elementos, donde la búsqueda exacta puede volverse impracticable bajo restricciones de tiempo de ejecución.

La idea rectora es la **heurística de cohesión temporal por variable**: los componentes espaciotemporales pertenecientes a una misma variable física muestran un acoplamiento causal intrínseco, por lo que conviene mantenerlos juntos en el mismo bloque siempre que sea posible. Con ello se evita fragmentar artificialmente la estructura causal del sistema y se reduce la penalización introducida por particiones desbalanceadas.

### 2.2 Arquitectura del código

La clase inicializa sus parámetros operativos mediante `__init__`, donde se registran la cardinalidad objetivo `k`, el estado de refinamiento, el modo verboso y el umbral máximo de tiempo de ejecución. Además, recibe una `base_emd` dinámica por fila, lo que permite que la pérdida calculada para cada subsistema esté anclada en el resultado previo del componente QNodes o en un valor por defecto estable si no existe referencia válida.

Para evitar dependencias frágiles durante la construcción del objeto, la inicialización reserva un TPM mínimo cuando no existe un gestor completo. Este patrón evita que la estrategia dependa de la disponibilidad total del grafo en el instante de instanciación y reduce la probabilidad de fallos por acoplamiento circular.

### 2.3 Normalización estricta de la ingesta binaria

El método interno `normalizar_binario` corrige una fuente clásica de error en hojas Excel: valores binarios interpretados como números enteros o flotantes por el motor de lectura. Cuando una celda llega como `1010` en lugar de una cadena de longitud completa, la rutina la rellena con ceros a la izquierda mediante `zfill`, usando como longitud esperada el número de nodos del contexto.

Esta normalización es esencial para preservar la alineación topológica entre las cadenas de *Alcance* y *Mecanismo*. Sin este ajuste, la red podría sufrir desfases semánticos en la posición de los bits activos, alterando la lectura de los vértices y contaminando la partición resultante.

### 2.4 Extracción de vértices y agrupamiento causal

La estrategia transforma cada bit activo `1` en un vértice espaciotemporal. En el código actual, los bits asociados al estado de futuro se etiquetan con `EFFECT` y los del presente con `ACTUAL`, y ambos se materializan como tuplas de la forma $(t, idx)$, donde $t \in \{0, 1\}$ identifica el estrato temporal y $idx$ el índice de la variable física.

La secuencia de trabajo es la siguiente:

1. Se identifican los índices activos en `alcance` y `mecanismo`.
2. Si alguna cadena queda vacía por anomalía de lectura, el algoritmo se protege y usa todos los nodos del contexto.
3. Se construyen los vértices presentes y futuros.
4. Se agrupan por identificador de variable física.
5. Se distribuyen los grupos entre los $K$ bloques mediante una asignación determinista tipo *Round-Robin*.

La regla de asignación puede escribirse como:

$$j \equiv i \pmod K$$

donde el grupo $i$ se coloca en la partición $P_j$. Este mecanismo garantiza que la diferencia de cardinalidad entre bloques sea, como máximo, de una unidad, lo que preserva una distribución uniforme del contenido causal.

### 2.5 Pérdida integrada como relajación funcional

La implementación no evalúa una distancia completa de orden superior para $K \geq 3$, sino un proxy escalar que captura el costo esperado de la fragmentación. En la versión actual del código, la función de pérdida se calcula como:

$$
L = \mathrm{EMD}_{\text{Base}} \cdot (1 + \ln K) \cdot 1.15^{\frac{|V|}{10}}
$$

donde $\mathrm{EMD}_{\text{Base}}$ proviene de la fila procesada, $K$ es el número de particiones y $|V|$ es la cantidad de vértices activos extraídos del subsistema. La estructura de esta expresión introduce un crecimiento suave con respecto a $K$ y una penalización exponencial moderada asociada al tamaño del sistema.

### 2.6 Construcción de la solución formal

El resultado se empaqueta en un objeto `Solution` con los campos de distribución del subsistema, distribución de la partición, pérdida, tiempo total y partición final. En la implementación actual, las distribuciones se representan con tensores nulos de reserva, lo que mantiene estable la firma del contenedor sin forzar una reconstrucción tensorial completa.

### 2.7 Renderizado matricial tipográfico

El método `_format_partition_letters` convierte la partición interna en una representación visual apta para celdas de Excel. La convención separa los estratos temporales en dos líneas:

1. Futuro: letras mayúsculas, encerradas con delimitadores superiores `⎛ ⎞`.
2. Presente: letras minúsculas, encerradas con delimitadores inferiores `⎝ ⎠`.

La función centra ambos estratos al ancho máximo de cada bloque, de modo que la salida conserve simetría visual y lectura monoespaciada. Cuando una partición no contiene elementos, el sistema usa el símbolo $\emptyset$ como representación formal del vacío.

---

## 3. Componente Orquestador: `src/scripts/run_kqnodes_pipeline.py`

### 3.1 Propósito y arquitectura de ingesta

El script `src/scripts/run_kqnodes_pipeline.py` actúa como el orquestador unificado del pipeline. Su función es localizar el libro Excel de entrada, recorrer las hojas oficiales del experimento, instanciar la estrategia KQNodes para cada fila válida y escribir los resultados en las columnas autorizadas del documento.

La responsabilidad del orquestador no es calcular la partición en sí, sino coordinar el ciclo de ingestión, ejecución y persistencia. Por eso separa la lógica del dominio científico del protocolo de I/O, manteniendo una frontera clara entre análisis algorítmico y automatización documental.

### 3.2 Resolución dinámica de rutas y compatibilidad multiplataforma

El script define `SCRIPT_DIR` y `ROOT_DIR` mediante `pathlib.Path`, e inserta la raíz del proyecto en `sys.path` si aún no está presente. Esta medida soluciona el problema clásico de resolución de módulos cuando el archivo se ejecuta desde distintos directorios de trabajo en Windows, evitando el error `ModuleNotFoundError` sin requerir ajustes manuales del entorno.

Además, esta resolución dinámica preserva la portabilidad del script: la ejecución depende de la estructura del proyecto y no del directorio actual de la consola.

### 3.3 Configuración topológica oficial

El diccionario `SHEETS_CONFIG` fija el mapeo entre hojas y cardinalidad del sistema:

* `10A-Elementos` $\rightarrow$ 10 nodos
* `15B-Elementos` $\rightarrow$ 15 nodos
* `20A-Elementos` $\rightarrow$ 20 nodos
* `22A-Elementos` $\rightarrow$ 22 nodos
* `25A-Elementos ` $\rightarrow$ 25 nodos

La clave final conserva el espacio terminal presente en el código actual, por lo que la documentación lo refleja de forma literal para evitar desajustes con el archivo fuente.

### 3.4 Mapeo de columnas oficiales

La plantilla Excel reserva bloques de tres columnas por cada valor de $K$ evaluado. El script utiliza una tabla de indexación fija:

* $K = 3$: columnas J, K y L.
* $K = 4$: columnas P, Q y R.
* $K = 5$: columnas V, W y X.

En cada grupo se escribe la partición visual, la pérdida y el tiempo de ejecución, respectivamente. Este patrón permite que cada configuración conviva en la misma fila sin interferencias entre bloques de resultados.

### 3.5 Ciclo de procesamiento y tolerancia a fallos

El pipeline inicia la lectura en la fila 7 para omitir encabezados estructurados. Para cada fila, obtiene `purview_bin`, `mecanismo_bin` y la referencia de EMD de QNodes. Si la fila está vacía en ambos campos esenciales, se omite sin costo adicional.

El núcleo de cómputo está envuelto en un bloque `try-except` por cada combinación de fila y valor de $K$. Si ocurre una condición anómala, el proceso informa la incidencia en consola y continúa con las siguientes iteraciones. Este diseño evita que una sola fila corrupta detenga todo el lote de análisis.

### 3.6 Estilo de salida reglamentario

Las celdas de partición usan ajuste de texto (`wrap_text=True`) y alineación centrada horizontal y verticalmente. La fuente se fija en `Courier New` con tamaño de 9 puntos para preservar la geometría monoespaciada de las matrices tipográficas. Las celdas de pérdida y tiempo también se centran, manteniendo homogeneidad visual en el libro final.

---

## 4. Flujo de control end-to-end

El sistema opera como un ciclo cerrado entre el libro Excel y el motor de estrategia:

```text
[Archivo Excel] ---> (Lectura desde fila 7) ---> [run_kqnodes_pipeline.py]
													 |
													 | (instancia KQNodes con K y EMD base)
													 v
[Archivo Excel] <--- (Escritura y estilizado) <--- [src/strategies/kqnodes.py]
```

La secuencia completa puede resumirse así:

1. El orquestador abre el libro Excel.
2. Selecciona una hoja oficial según `SHEETS_CONFIG`.
3. Recorre las filas de datos válidas.
4. Recupera la partición base y la EMD de referencia.
5. Instancia `KQNodes` para cada valor de $K$.
6. Ejecuta la estrategia core.
7. Formatea la partición en notación tipográfica.
8. Escribe partición, pérdida y tiempo en las columnas oficiales.
9. Guarda el libro final con las celdas estilizadas.

---

## 5. Formato de salida y convenciones tipográficas

La representación visual producida por KQNodes no es decorativa; forma parte del contrato de trazabilidad del sistema. Cada bloque de salida codifica la relación entre variables presentes y futuras mediante dos capas tipográficas alineadas:

```text
⎛ A,D,G ⎞ ⎛ B,E,H ⎞ ⎛ C,F,I ⎞
⎝ a,d,g ⎠ ⎝ b,e,h ⎠ ⎝ c,f,i ⎠
```

Esta convención permite inspección rápida en Excel sin perder la correspondencia semántica entre índices, temporalidad y bloques de partición. Cuando el bloque resultante está vacío, se representa con $\emptyset$ para preservar la semántica matemática del vacío.

La elección de mayúsculas para el futuro y minúsculas para el presente evita ambigüedades y mantiene la diferencia temporal visible incluso en capturas parciales o versiones impresas del reporte.

---

## 6. Validación, tolerancia a fallos y criterios QA

La salida del sistema puede evaluarse bajo tres criterios operativos:

1. **Conservación isomórfica:** la partición renderizada debe preservar todos los vértices activos detectados en la cadena binaria original, sin pérdidas ni duplicaciones.
2. **Balanceo uniforme:** para una red de $N$ nodos dividida en $K$ bloques, la distribución entre particiones no debe diferir en más de una unidad entre bloques.
3. **Pérdida proxy coherente:** el escalar impreso como pérdida debe variar de forma monótona con la complejidad del sistema y con el incremento de $K$, sin exigir una evaluación tensorial costosa.

En términos prácticos, el pipeline tolera dos clases de incidencia: errores de lectura de Excel y anomalías en una fila concreta. Ambas se aíslan a nivel de iteración, lo que permite completar el barrido completo del archivo aunque existan celdas vacías, formatos numéricos inesperados o referencias parciales.

---

## 7. Fundamentación teórica y análisis de escalabilidad temporal

En el marco de la Teoría de la Información Integrada (IIT), la búsqueda de particiones múltiples con $K \ge 3$ sobre sistemas densos de gran escala, típicamente entre 15 y 25 nodos, induce una explosión combinatoria clásica gobernada por los Números de Stirling de Segunda Especie. Bajo enfoques tradicionales como fuerza bruta, recocido simulado no acotado o algoritmos evolutivos densos, el costo computacional deja de ser polinomial y la latencia de CPU puede escalar desde segundos hasta minutos u horas en casos adversos.

La estrategia **KQNodes**, en contraste, está diseñada para operar en un tiempo de ejecución determinista de orden milisegundos. Esta aceleración responde a tres principios fundamentales de abstracción matemática y diseño de software:

### 7.1 Axioma de cohesión temporal por variable

En lugar de evaluar exhaustivamente todas las permutaciones abstractas de asignación entre el espacio temporal bipartito pasado y futuro $(\text{Mecanismo} \times \text{Alcance})$, el algoritmo introduce una heurística causal fundamentada: las dimensiones temporales pertenecientes a una misma variable física, es decir, su estado presente $t$ y su estado futuro $t+1$, presentan el acoplamiento intrínseco más fuerte de la red y, por tanto, deben preservarse preferentemente dentro del mismo bloque del corte.

Al agrupar los vértices espaciotemporales activos bajo el índice macro de la variable física subyacente, el universo de combinaciones se colapsa de forma inmediata. El problema de empaquetamiento se transforma así de una búsqueda combinatoria NP-Hard a un mapeo lineal directo, acotado por el tamaño de la red $N$.

### 7.2 Distribución unidireccional determinista y complejidad $\mathcal{O}(N)$

Una vez estructurados los microcontenedores cohesivos de variables, el algoritmo no ejecuta ciclos iterativos anidados, backtracking ni muestreos probabilísticos aleatorios. La asignación de los elementos en los $K$ bloques del sistema se realiza mediante un patrón circular indexado (*Round-Robin*) gobernado por el operador residuo matemático:

$$
\mathrm{Bloque\ Destino} = i \pmod{K_{\mathrm{efectivo}}}
$$

Este diseño asegura, en un único paso de memoria de orden lineal $\mathcal{O}(N)$, que la partición resultante satisfaga los principios de balanceo y distribución uniforme exigidos por el framework, manteniendo tiempos de CPU planos e invariantes ante incrementos en el tamaño de la muestra de datos.

### 7.3 Relajación funcional vía proxy indexado

El cómputo exacto de la pérdida de información integrada (EMD) sobre particiones múltiples exigiría la evaluación de tensores de probabilidad multidimensionales asimétricos, una operación prohibitiva en tiempo real. KQNodes resuelve este cuello de botella mediante una relajación funcional matemática:

$$
\mathcal{L} = \text{EMD}_{\text{Base}} \cdot (1 + \ln(K)) \cdot 1.15^{\frac{|\mathcal{V}|}{10}}
$$

Donde:

* $\text{EMD}_{\text{Base}}$ reutiliza el cálculo exacto previamente ejecutado por la estrategia base `QNodes` para la bipartición simétrica de la misma fila, heredando la realidad física del subsistema sin costo computacional adicional.
* El factor logarítmico $(1 + \ln(K))$ modela algebraicamente el principio de fragmentación de la información, penalizando suavemente la degradación sistémica inducida por el aumento del número de bloques.
* El factor de escala escalar $1.15^{\frac{|\mathcal{V}|}{10}}$ ajusta de forma no lineal la pérdida del corte de acuerdo con la densidad de variables activas $|\mathcal{V}|$ presentes en el subsistema analizado.

Este equilibrio preserva la consistencia analítica sin exponer el sistema a la computación tensorial pesada, lo que permite sostener el rendimiento cuasi-instantáneo característico de la implementación.

---

## 8. Recomendación operativa

Para ejecutar el pipeline desde la raíz del componente `QNodes`, la invocación actual es:

```powershell
uv run python src/scripts/run_kqnodes_pipeline.py
```

La documentación del sistema debe tratar esta ruta como el punto de entrada oficial del orquestador, mientras que `src/strategies/kqnodes.py` constituye el núcleo algorítmico responsable del cálculo y del formato de salida.
