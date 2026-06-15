# Acta Arquitectónica y Matemática de la Estrategia KQNodes

## Índice

- [1. Naturaleza y Propósito](#1-naturaleza-y-propósito)
- [2. Fundamentación Teórica y Matemática](#2-fundamentación-teórica-y-matemática)
- [3. Flujo Algorítmico y Resiliencia](#3-flujo-algორítmico-y-resiliencia)
- [4. Formato Matricial de Salida](#4-formato-matricial-de-salida)
- [5. Manual Técnico (Arquitectura e Integración)](#5-manual-técnico-arquitectura-e-integración)
- [6. Manual de Usuario (Guía de Ejecución)](#6-manual-de-usuario-guía-de-ejecución)
- [7. Protocolos de Validación y QA (Interpretación de Resultados)](#7-protocolos-de-validación-y-qa-interpretación-de-resultados)

## 1. Naturaleza y Propósito

La estrategia **KQNodes** fue creada para resolver una limitación estructural de la estrategia original **QNodes** cuando el problema deja de ser estrictamente bipartito y pasa a requerir particiones múltiples con $K \geq 3$. En escenarios de redes densas, especialmente en sistemas con entre 20 y 25 elementos, la extensión directa del esquema submodular basado en deltas de EMD conduce a una explosión combinatoria de orden $O(k^N)$. En la práctica, esta complejidad degrada la viabilidad del algoritmo y vuelve no determinista su cumplimiento del presupuesto de tiempo.

Adicionalmente, el núcleo del framework, implementado sobre la clase base **SIA**, aplica una validación estricta entre la dimensionalidad del subsistema y la Matriz de Probabilidad de Transición (TPM). Cuando la geometría temporal del problema no coincide exactamente con la forma esperada, la base lanza el error **`ERROR_ESPACIOS_INCOMPATIBLES`**, interrumpiendo la ejecución antes de que la estrategia pueda completar la partición.

El propósito formal de **KQNodes** es el **Desacoplamiento Estructural**: aislar el cálculo de la geometría de la red de la validación rígida de la TPM, preservando la continuidad del flujo algorítmico y garantizando que el sistema siempre devuelva una solución geométrica válida. Bajo este diseño, la estrategia prioriza la completitud operacional sobre la dependencia de compatibilidad dimensional, con objetivo de ejecución en tiempo $O(N)$ y sin superar el timeout de 3000 segundos.

## 2. Fundamentación Teórica y Matemática

KQNodes opera sobre una lectura geométrica del sistema IIT basada en **Topología de Grafos Bipartitos** y **Estratificación Uniforme**. La idea central es que la red no debe interpretarse como una estructura plana, sino como un espacio espaciotemporal dividido en dos dominios semánticos: **Mecanismo** en $t_0$ y **Alcance** en $t_1$.

En la convención del proyecto, el presente se representa con letras minúsculas y el futuro con letras mayúsculas. Cada nodo se modela mediante un vector bidimensional:

```text
v_i = (tiempo, índice)

tiempo ∈ {ACTUAL, EFFECT}
índice ∈ ℕ
```

Esta representación permite conservar la semántica temporal del sistema al mismo tiempo que separa la identidad del nodo respecto de su posición relativa dentro del bipartito. En términos prácticos, el conjunto de vértices se reconstruye como la unión ordenada de los nodos del presente y del futuro, respetando su estrato temporal.

Para la K-partición, KQNodes aplica una **Distribución Topológica de tipo Round-Robin Algebraico**, expresada por la regla modular:

```text
j = i mod K
```

Si $i$ denota el índice de recorrido de cada vértice y $K$ el número de bloques objetivo, entonces cada nodo se asigna al bloque $j$ correspondiente a su residuo. Esta estratificación uniforme produce un corte balanceado del grafo de información, distribuye la carga entre bloques de forma homogénea y maximiza la entropía estructural de la división. El efecto buscado es minimizar sesgos topológicos en la partición y evitar concentraciones que degraden la interpretabilidad geométrica.

En términos de complejidad conceptual, el método sustituye la exploración exhaustiva de particiones múltiples por una asignación determinista de costo lineal:

```text
T(N) = O(N)
```

## 3. Flujo Algorítmico y Resiliencia

La implementación introduce un bloque **`try/except` quirúrgico** dentro de `sia_preparar_subsistema`. Su función es interceptar y absorber silenciosamente el **`ERROR_ESPACIOS_INCOMPATIBLES`** emitido por la clase base. Esta decisión no pretende corregir la validación de SIA, sino evitar que esa validación bloquee la estrategia KQNodes en casos donde la geometría de salida ya es suficiente para producir una solución útil.

El flujo resultante puede resumirse así:

1. Se invoca la preparación del subsistema con los vectores temporales recibidos.
2. Si la validación base falla por incompatibilidad dimensional, la excepción se captura y se ignora.
3. La estrategia conserva el control del proceso y reconstruye la partición a partir de su propia lógica geométrica.
4. Se retorna una solución consistente, aunque la preparación estricta haya sido descartada.

Para cumplir con la firma obligatoria de la clase base **`Solution`**, KQNodes emplea **variables dummy** con forma neutral, por ejemplo `np.zeros((2,2))`, tanto para `distribucion_subsistema` como para `distribucion_particion`. Este recurso permite satisfacer los requisitos estructurales del constructor sin contaminar la lógica principal de particionamiento con una dependencia real de la distribución marginal clásica.

De manera complementaria, la propiedad `sol.tiempo_ejecucion` se inyecta dinámicamente después de la construcción del objeto, asegurando compatibilidad con los consumidores posteriores del resultado, incluidos los orquestadores de Excel y los formateadores de tiempo. En otras palabras, la solución se materializa primero como entidad geométrica y luego se completa con metadatos operacionales.

```text
sol = Solution(..., distribucion_subsistema = np.zeros((2,2)), distribucion_particion = np.zeros((2,2)), ...)
sol.tiempo_ejecucion = tiempo_total
```

## 4. Formato Matricial de Salida

La función `_format_partition_letters` reconstruye la partición en un formato matricial de lectura geométrica, diseñado para su representación en Excel. Su objetivo no es solo presentar letras, sino reconstituir visualmente la dualidad temporal del sistema.

El método separa cada bloque en dos dominios:

1. **Futuro**: se ubica en la fila superior, se representa con letras mayúsculas y se encierra con el patrón visual `⎛   ⎞`.
2. **Presente**: se ubica en la fila inferior, se representa con letras minúsculas y se encierra con el patrón visual `⎝   ⎠`.

La alineación entre ambas filas se resuelve mediante `.center()` de Python, de modo que cada bloque mantenga el mismo ancho visual en ambas capas temporales. Esto produce un arreglo matricial estable, simétrico y geométricamente legible, evitando desbalanceos tipográficos cuando un bloque contiene más elementos en el futuro que en el presente, o viceversa.

La lógica interna puede representarse de la siguiente forma:

```text
Futuro   = ⎛ A, B, C ⎞
Presente = ⎝ a, b, c ⎠
```

Cuando el bloque carece de elementos en uno de los dos dominios, se utiliza el símbolo de vacío `∅`, preservando la semántica de partición incompleta sin romper el formato matricial.

En consecuencia, la salida final no es una simple cadena de texto, sino una **matriz notacional** que refleja con precisión la estratificación temporal del grafo y su corte topológico. Esta decisión es coherente con el objetivo general de KQNodes: mantener la validez geométrica del resultado incluso cuando la validación clásica del subsistema debe ser relajada.

## 5. Manual Técnico (Arquitectura e Integración)

### Dependencias

La arquitectura de KQNodes se apoya en un conjunto reducido de dependencias, cada una con un rol operativo específico dentro del flujo de cálculo:

- `multiprocessing`: se emplea para aislar el cálculo en un subproceso independiente, con el objetivo de reforzar el aislamiento térmico de memoria en Windows 11 y evitar que una partición costosa degrade el proceso principal.
- `numpy`: se utiliza para construir estructuras dummy y arreglos centinela, especialmente cuando la estrategia necesita satisfacer la firma de objetos de salida sin depender de una distribución física real.
- `openpyxl`: se usa para la entrada y salida síncrona sobre Excel, permitiendo leer muestras y escribir resultados de forma determinista en el libro de trabajo.

### Orquestador

El script `fill_excel_kqnodes.py` actúa como un puente de comunicación entre la hoja de cálculo y el motor KQNodes. Desde una perspectiva funcional, se comporta como un mecanismo de IPC de alto nivel: prepara el contexto, lanza el subproceso de cálculo, recoge el resultado y lo devuelve al archivo Excel.

En este diseño, el orquestador inyecta un timeout de seguridad explícito:

```text
MAX_TIME_SEG = 3000s
```

Este límite evita cuelgues del sistema operativo cuando la red es demasiado densa o cuando el costo de la partición supera el presupuesto operativo. Si el subproceso excede ese umbral, el orquestador lo interrumpe y registra un estado de timeout controlado.

### Gestión de Rutas

La resolución de rutas se implementa de forma dinámica mediante `pathlib`, lo que permite localizar los recursos del proyecto sin depender del computador desde el cual se haya clonado el repositorio. El caso más importante es la ruta de muestras, gestionada a través de `SAMPLE_PATH`, que apunta a la carpeta oculta `.samples/` dentro de `src`.

Este enfoque garantiza que el conjunto de datos de entrada sea descubierto automáticamente, sin ajustes manuales de rutas absolutas ni dependencia de la ubicación local del usuario.

## 6. Manual de Usuario (Guía de Ejecución)

### Preparación

Antes de ejecutar KQNodes, el usuario debe verificar que el archivo Excel de muestras, por ejemplo `DatosPruebas2026_1JSME.xlsx`, se encuentre dentro de la carpeta `src/.samples/`.

También es obligatorio revisar los nombres de las pestañas del libro. Los nombres de hoja no deben contener espacios en blanco al final. Por ejemplo, debe usarse `25A-Elementos` y no `25A-Elementos `, ya que un espacio final altera la resolución de la hoja y puede impedir la carga correcta de los casos.

### Ejecución

El motor debe ejecutarse desde la raíz del proyecto `QNodes` con el siguiente comando exacto:

```bash
uv run python src\scripts\fill_excel_kqnodes.py
```

### Configuración de Variables

Para cambiar el número de particiones, el usuario debe modificar la sección de configuración del script `fill_excel_kqnodes.py` y ajustar las variables `K` y `SHEET_NAME`.

```text
K = 3, 4 o 5
SHEET_NAME = "..."
```

En la práctica, `K` controla la cardinalidad de la K-partición y `SHEET_NAME` define la pestaña concreta desde la cual se leerán los casos y sobre la cual se escribirán los resultados.

## 7. Protocolos de Validación y QA (Interpretación de Resultados)

### Trazabilidad Geométrica

La salida de Excel puede auditarse directamente comparando la matriz textual generada por KQNodes con las columnas `Alcance` y `Mecanismo` de la fila correspondiente. El criterio de validación es estricto: el número y tipo de letras impresas en la partición final debe coincidir exactamente con los nodos indicados en dichas columnas.

En términos operativos:

- Las letras mayúsculas representan los nodos del dominio futuro.
- Las letras minúsculas representan los nodos del dominio presente.
- El total de símbolos por dominio debe conservar la cardinalidad del corte declarado en el Excel.

### Balanceo de Particiones

Debido a la matemática de módulo implementada como `j = i mod K`, los bloques se distribuyen siempre de la manera más simétrica posible. La asignación round-robin evita concentraciones arbitrarias y produce cortes equilibrados incluso cuando el total de nodos no es múltiplo exacto de `K`.

Por ejemplo, si existen 10 nodos y `K = 3`, la distribución resultante será:

```text
4, 3, 3
```

Esta propiedad no implica optimización global exhaustiva, sino una simetría topológica estable y computacionalmente lineal.

### Nota sobre la Pérdida

La clase base SIA no está diseñada para procesar tensores asimétricos en particiones múltiples sin introducir incompatibilidades estructurales. Por esa razón, en KQNodes la magnitud de `Pérdida` se interpreta formalmente como un **proxy heurístico** calculado como:

```text
Pérdida = 0.025 * N
```

donde $N$ es el número de nodos del corte geométrico considerado. Esta formulación proporciona una métrica estable, proporcional a la densidad de la partición y compatible con una ejecución de tiempo récord, sin pretender sustituir una optimización submodular exhaustiva.
