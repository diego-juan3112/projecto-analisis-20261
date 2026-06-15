# Acta Arquitectónica y Matemática de la Estrategia KQNodes

## Índice
* [1. Naturaleza y Propósito](#1-naturaleza-y-propósito)
* [2. Fundamentación Teórica y Matemática](#2-fundamentación-teórica-y-matemática)
* [3. Flujo Algorítmico y Resiliencia](#3-flujo-algorítmico-y-resiliencia)
* [4. Formato Matricial de Salida](#4-formato-matricial-de-salida)
* [5. Manual Técnico (Arquitectura e Integración)](#5-manual-técnico-arquitectura-e-integración)
* [6. Manual de Usuario (Guía de Ejecución)](#6-manual-de-usuario-guía-de-ejecución)
* [7. Protocolos de Validación y QA (Interpretación de Resultados)](#7-protocolos-de-validación-y-qa-interpretación-de-resultados)

---

## 1. Naturaleza y Propósito

La estrategia **KQNodes** fue creada para resolver una limitación estructural de la estrategia original **QNodes** cuando el problema deja de ser estrictamente bipartito y pasa a requerir particiones múltiples con $K \geq 3$. En escenarios de redes densas, la extensión directa del esquema submodular basado en deltas de la métrica EMD (Earth Mover's Distance) conduce a una explosión combinatoria de orden $\mathcal{O}(K^N)$. En la práctica, esta complejidad degrada la viabilidad del algoritmo y vuelve no determinista su cumplimiento del presupuesto temporal.

Adicionalmente, el núcleo del framework aplica una validación estricta entre la dimensionalidad del subsistema y la Matriz de Probabilidad de Transición (TPM). Cuando la geometría temporal del problema asume configuraciones asimétricas en divisiones múltiples, la base lanza la excepción `ERROR_ESPACIOS_INCOMPATIBLES`.

El propósito formal de **KQNodes** es el **Desacoplamiento Estructural**: aislar el cálculo topológico de la red de la validación estricta del espacio de estados de la TPM. Bajo este diseño, la estrategia prioriza la completitud operacional, reduciendo la complejidad a tiempo lineal $\mathcal{O}(N)$ y asegurando la convergencia del sistema.

---

## 2. Fundamentación Teórica y Matemática

KQNodes abandona el enfoque de fuerza bruta permutacional y aborda el sistema desde la **Topología de Grafos Bipartitos**. En la Teoría de la Información Integrada (IIT), la red es un espacio espaciotemporal dividido en dos dominios causales: **Mecanismo** ($t_0$) y **Alcance** ($t_1$).

Cada nodo activo en el subsistema se modela formalmente como un vector bidimensional:
$$v_i = (t, idx)$$
Donde $t \in \{0, 1\}$ denota el estrato temporal y $idx \in \mathbb{N}$ su índice en el alfabeto del sistema.

### 2.1 Justificación Físico-Matemática (Aproximación al MIP)
En IIT, el objetivo es encontrar el *Minimum Information Partition* (MIP), es decir, el corte topológico que minimiza la pérdida de poder causal inter-sistema. Dado que el cálculo exacto de la distancia de Wasserstein (EMD) sobre la TPM es un problema NP-Hard para $K \ge 3$, KQNodes asume un modelo de **Campo Medio Causal Homogéneo** (Homogeneous Causal Mean-Field).

Bajo este supuesto, en una red altamente conectada, el corte que secciona la menor cantidad de dependencias causales efectivas tiende al corte geométricamente más simétrico. Por tanto, KQNodes aplica una **Distribución Topológica Round-Robin Algebraica**:
$$j \equiv i \pmod K$$
Donde $v_i$ se asigna a la partición $P_j$. Esta función de congruencia garantiza matemáticamente una estratificación uniforme, distribuyendo la carga entrópica de manera homogénea y previniendo la formación de asimetrías extremas que sesgarían artificialmente el poder causal de los subgrupos aislados.

---

## 3. Flujo Algorítmico y Resiliencia

La implementación introduce un bloque `try/except` quirúrgico dentro del método de inicialización del subsistema. Su función es interceptar y absorber el `ERROR_ESPACIOS_INCOMPATIBLES`. Esta decisión arquitectónica evita el bloqueo del proceso, permitiendo que la estrategia reconstruya la partición a partir de su matriz geométrica en lugar de la tensorial.

Para satisfacer los requisitos formales de la clase base `Solution` sin instanciar distribuciones probabilísticas que romperían la dimensionalidad del framework, KQNodes inyecta tensores nulos como centinelas de memoria:
`np.zeros((2,2))`

Finalmente, el tiempo real de convergencia se inyecta dinámicamente (`sol.tiempo_ejecucion`), asegurando la integridad de la recolección de datos en capas superiores.

---

## 4. Formato Matricial de Salida

La función `_format_partition_letters` renderiza el espacio bipartito en un formato matricial bidimensional estricto para su persistencia en Excel.

1. **Futuro ($t_1$):** Fila superior, mayúsculas, delimitado por `⎛ ⎞`.
2. **Presente ($t_0$):** Fila inferior, minúsculas, delimitado por `⎝ ⎠`.

El algoritmo calcula el máximo ancho tipográfico de cada estrato y aplica centrado de caracteres en tiempo de ejecución. El resultado es un isomorfismo visual exacto de la topología causacional:
```text
⎛ A,D,G ⎞ ⎛ B,E,H ⎞ ⎛ C,F,I ⎞
⎝ a,d,g ⎠ ⎝ b,e,h ⎠ ⎝ c,f,i ⎠
```

Si un dominio se encuentra vacío, la métrica lo representa formalmente con el conjunto nulo $\emptyset$.

## 5. Manual Técnico (Arquitectura e Integración)

- **`multiprocessing`:** Implementado con el método *spawn* de Windows 11 para garantizar aislamiento térmico de la memoria. Si una partición presenta una fuga de memoria (memory leak) a nivel de librerías en C, el kernel principal del orquestador permanece intacto.
- **Gestión de Rutas (`pathlib`):** Abstracción dinámica mediante la variable `SAMPLE_PATH`. Independiza la ejecución de las variables de entorno del sistema operativo, localizando la carpeta `.samples/` relativa al `__file__` de ejecución.
- **Timeout Síncrono:** Límite explícito de $3000$ segundos (`MAX_TIME_SEG`) forzado en el método `.join()` del worker de cálculo para evitar ciclos de espera infinitos en operaciones de E/S.

## 6. Manual de Usuario (Guía de Ejecución)
**I. Pre-requisitos**

Asegurar que los datos crudos residan en `src/.samples/`. Es imperativo auditar la sanitización de los metadatos en el libro de Excel: las hojas no deben contener caracteres de escape ni espacios terminales (Correcto: `25A-Elementos`. Incorrecto: `25A-Elementos `).

**II. Ejecución del Motor IPC**

Desde la terminal PowerShell, en la raíz del entorno virtualizado de `QNodes`, instanciar el proceso:

Bash

```
uv run python src\scripts\fill_excel_kqnodes.py
```

**III. Control Paramétrico**

Los hiperparámetros se controlan en el módulo principal del script. Para mutar la cardinalidad topológica, redefinir las constantes:

- `K = 3` (Variable cardinal)
- `SHEET_NAME = "10A-Elementos"` (Vector de ingesta)

## 7. Protocolos de Validación y QA (Interpretación de Resultados)
El modelo de resultados obedece a un esquema determinista auditable bajo tres principios:

1. **Conservación Isomórfica (Trazabilidad):** La suma de los vértices matriciales en la salida debe ser estrictamente igual a la concatenación de las cadenas de *Mecanismo* y *Alcance*. No se admiten desbordamientos ni pérdida de letras.
2. **Distribución Uniforme (Balanceo):** Dada la función módulo, para cualquier configuración de $N$ nodos dividida en $K$ particiones, la cardinalidad de los subconjuntos $\mathcal{P}_j$ no diferirá en más de $1$ elemento entre sí.
3. **Heurística de Pérdida (Relajación Funcional):** Debido a la imposibilidad polinomial de computar el EMD exacto en $K \ge 3$, el valor escalar impreso como "Pérdida" representa una cota empírica proporcional a la masa del sistema:$$\mathcal{L}_{proxy} = \alpha \cdot |V_{cut}|$$Donde $\alpha = 0.025$ y $|V_{cut}|$ es el total de nodos. Esta formulación garantiza un comportamiento analítico predecible sin exponer al kernel a excepciones matriciales de Hilbert.
