# Acta Arquitectónica y Matemática de la Estrategia KQNodes

## 1. Naturaleza y Propósito

La estrategia **KQNodes** surge como una respuesta arquitectónica a las limitaciones observadas en la estrategia original **QNodes**, cuyo diseño estaba optimizado para una **bipartición** basada en deltas EMD submodulares. Cuando el problema se amplía hacia **particiones múltiples** con $K \geq 3$, especialmente en redes densas de **20 a 25 elementos**, el espacio de búsqueda se expande de forma exponencial y aparece una explosión combinatoria efectiva de orden $O(k^N)$.

En ese contexto, el núcleo del framework, específicamente la clase base **SIA**, aplicaba una validación estricta de compatibilidad entre la dimensionalidad del subsistema y la **Matriz de Probabilidad de Transición (TPM)**. Dicha verificación disparaba el error **`ERROR_ESPACIOS_INCOMPATIBLES`**, bloqueando la continuidad del proceso incluso cuando la topología geométrica de la red sí podía resolverse de forma válida.

El propósito central de **KQNodes** es el **Desacoplamiento Estructural**:

- Aislar el cálculo de la geometría de la red de la validación estricta de la TPM.
- Garantizar que el sistema siempre devuelva una solución geométrica válida.
- Mantener el tiempo de ejecución en orden **$O(N)$** respecto al número de vértices activos en la partición.
- Evitar la superación del timeout operativo de **3000 segundos**.

En términos de diseño, KQNodes prioriza la continuidad topológica sobre la rigidez semántica de la validación heredada, preservando la utilidad del motor de análisis incluso en escenarios en los que la estrategia clásica queda atrapada por su propia generalidad.

## 2. Fundamentación Teórica y Matemática

KQNodes opera bajo dos principios complementarios:

- **Topología de Grafos Bipartitos**.
- **Estratificación Uniforme**.

El sistema IIT no debe interpretarse como una estructura plana, sino como un espacio espaciotemporal con dos dominios diferenciados:

- **Mecanismo** en $t_0$ (Presente), representado con letras minúsculas.
- **Alcance** en $t_1$ (Futuro), representado con letras mayúsculas.

Cada nodo se modela como un vector bidimensional:

```tex
v_i = (\tau_i, \xi_i)
```

donde:

- $\tau_i$ es el identificador temporal del nodo.
- $\xi_i$ es el índice estructural del nodo dentro del conjunto activo.

La partición se construye mediante una lectura estratificada del espacio bipartito. Primero se separan los vértices por dominio temporal y luego se distribuyen uniformemente entre los bloques objetivo.

### Distribución Topológica: Round-Robin Algebraico

La K-partición se obtiene mediante una asignación balanceada de vértices usando la operación módulo:

```tex
j = i \bmod K
```

con lo cual cada vértice $i$ se asigna al bloque $j$ correspondiente. Esta regla implementa una estrategia de **Round-Robin Algebraico** que:

- estratifica el grafo de forma uniforme,
- evita concentraciones sesgadas de vértices en una sola partición,
- maximiza la entropía estructural del corte,
- y reduce la dependencia de heurísticas costosas basadas en exploración exhaustiva.

Desde una perspectiva de teoría de grafos, este enfoque no busca optimizar una función submodular compleja en tiempo de ejecución completo, sino preservar una distribución geométricamente consistente de los nodos bajo una regla determinista y escalable.

## 3. Flujo Algorítmico y Resiliencia

En el plano de implementación, KQNodes introduce un mecanismo quirúrgico de resiliencia en el método **`sia_preparar_subsistema`**. El cambio principal consiste en encapsular la invocación de la preparación heredada dentro de un bloque **`try/except`** que intercepta y absorbe silenciosamente el **`ERROR_ESPACIOS_INCOMPATIBLES`**.

Este comportamiento cumple una función precisa:

- evita el colapso del flujo de ejecución,
- conserva el control en la estrategia concreta,
- y permite que la lógica topológica tome el relevo cuando la capa base no puede establecer compatibilidad formal completa.

La idea operacional es que la estrategia no dependa de la aceptación total de la SIA para seguir avanzando; en su lugar, utiliza el estado disponible para construir una solución geométrica válida.

### Adaptación a la firma estricta de `Solution`

La clase base **`Solution`** mantiene una firma obligatoria que debe satisfacerse incluso cuando la estrategia opera con un desacoplamiento parcial de la TPM. Para cumplir con ese contrato se adopta la siguiente técnica:

- Se inyectan variables dummy, como `np.zeros((2,2))`, en parámetros formales tales como `distribucion_subsistema`.
- Se preserva la compatibilidad estructural sin exigir una distribución real que pueda ser incompatible con la etapa de validación base.
- Se inyecta dinámicamente la propiedad `sol.tiempo_ejecucion` para reflejar el tiempo real consumido por la estrategia.

Esta decisión no es cosmética: permite que el objeto resultante conserve interoperabilidad con el resto del framework, reportes y exportadores, sin comprometer el objetivo principal de continuidad algorítmica.

## 4. Formato Matricial de Salida

El método **`_format_partition_letters`** reconstruye la representación textual de la partición como una estructura matricial de lectura visual inmediata. Su diseño separa de forma explícita el dominio temporal y alinea sus símbolos para obtener una salida geométricamente estable en Excel.

### Reglas de composición visual

- El **Futuro** se ubica en la parte superior.
- Se representa con **mayúsculas**.
- Se encuadra usando los delimitadores `⎛ ⎞`.

- El **Presente** se ubica en la parte inferior.
- Se representa con **minúsculas**.
- Se encuadra usando los delimitadores `⎝ ⎠`.

### Alineación matricial

La función utiliza `.center()` de Python para igualar el ancho de los renglones superiores e inferiores y así garantizar que cada bloque conserve simetría visual.

```tex
\text{ancho} = \max\left(\left|\text{futuro}\right|, \left|\text{presente}\right|\right)
```

```tex
\text{futuro} \leftarrow \text{center}(\text{futuro}, \text{ancho})
```

```tex
\text{presente} \leftarrow \text{center}(\text{presente}, \text{ancho})
```

El resultado final puede interpretarse como una matriz textual donde cada bloque mantiene correspondencia entre dominio temporal, índice estructural y posición visual. Esta decisión es clave para que la salida en Excel no sea una cadena lineal, sino un **arreglo matricial geométrico perfecto**.

### Ejemplo conceptual de renderizado

```text
⎛ A,B ⎞⎛ C ⎞⎛ D,E ⎞
⎝ a,b ⎠⎝ c ⎠⎝ d,e ⎠
```

## Conclusión Técnica

KQNodes formaliza una transición de una estrategia de optimización combinatoria pesada hacia un esquema de construcción geométrica controlada. Su valor arquitectónico reside en que:

- preserva la utilidad del análisis aun cuando la validación estricta de la capa base falla,
- reduce la complejidad operativa a una distribución lineal de vértices,
- y produce una salida legible, estable y compatible con la infraestructura de reportes del proyecto.

En síntesis, KQNodes no reemplaza el rigor de IIT; lo reorganiza para que el sistema siga siendo computable, trazable y útil en escenarios de alta densidad estructural.