# Guía de estudio KGeoMIP

Este documento es el complemento informal del manual técnico (`MANUAL_TECNICO_KGEOMIP.md`). El manual es el documento formal con las demostraciones; esta guía es para entender de qué se trata todo, preparar la presentación y tener a mano una respuesta clara cuando algo del manual no se entienda a la primera. Está escrita para alguien que programa pero que no es experto en Teoría de la Información Integrada (IIT) ni conocía este proyecto.

Regla de la guía: cada número que aparece acá viene de una medición real y dice de dónde sale (sección del manual o archivo `.json`/`.log` del directorio `review/`). Si algo no se midió, lo digo explícitamente.

---

## Parte A — Respuestas al checklist de presentación

### A.1 ¿Qué es phi y por qué menos phi es mejor?

**Phi (φ)** es un número que mide *cuánta información se rompe* cuando partís un sistema en pedazos que funcionan por separado. Es una "pérdida": cuánto se desvía el sistema partido del sistema entero.

Analogía: imaginá una orquesta tocando. Si dividís a los músicos en dos salas separadas y cada grupo sigue tocando su parte, ¿qué tan distinta suena la música respecto a la orquesta junta? Si suena casi igual, esos dos grupos casi no se necesitaban entre sí (φ chico). Si suena horrible y descoordinada, había una dependencia fuerte que cortaste (φ grande).

**Menos phi es mejor** porque buscamos el *corte que menos daño hace*: la línea de fractura natural del sistema, por donde las partes ya eran casi independientes. Ese corte de mínima pérdida es la **MIP** (Minimum Information Partition). El proyecto busca, entre todos los cortes posibles, el de φ más bajo. (Manual, sección 1.4.)

### A.2 ¿Qué es una k-partición? Partir vértices vs partir nodos

Una **bipartición** corta el sistema en 2 grupos. Una **k-partición** lo corta en `k` grupos (k=2, 3, 4, 5...). Más grupos = corte más fragmentado.

El punto sutil es **qué** se parte. Cada variable del sistema aparece en dos tiempos: su **presente** (lo que es ahora, en t) y su **futuro** (en qué se convierte, en t+1). Los llamamos por letra: presente en minúscula (`a`), futuro en mayúscula (`A`).

- **Partir nodos** (lo que hacía la versión vieja, y era un error): tratar a `a` y `A` como una sola cosa pegada. Si la variable A cae en el grupo 1, su presente y su futuro van juntos sí o sí.
- **Partir vértices** (lo correcto, decisión del Sprint 1): el presente `a` y el futuro `A` son **vértices independientes** y pueden caer en grupos distintos. El conjunto a partir es W = {todos los presentes} ∪ {todos los futuros}.

Analogía: pensá en cada variable como una persona con un "yo de hoy" y un "yo de mañana". Partir nodos obliga a que tu yo de hoy y tu yo de mañana estén siempre en el mismo equipo. Partir vértices permite que tu pasado quede en un equipo y tu futuro en otro, que es lo que de verdad necesitás para encontrar dónde se corta la cadena causal. (Manual, sección 1.3 y decisión de diseño 1.)

### A.3 ¿Por qué la EMD se reduce a una suma de restas?

La pérdida formalmente es una **EMD** (Earth Mover's Distance, "distancia del que mueve tierra"): el costo mínimo de transformar una distribución de probabilidad en otra, como si movieras montículos de arena. En general calcular eso es caro (es un problema de transporte óptimo).

Pero en este proyecto se reduce a algo trivial:

$$\varphi = \sum_j |v^{\text{orig}}_j - v^{\text{reconstruido}}_j|$$

es decir, **para cada nodo restás dos probabilidades y sumás los valores absolutos**. Una resta por nodo, y listo.

**El supuesto que lo permite** es la **independencia condicional entre nodos futuros**: dado el estado presente, cada nodo futuro se "decide" por su cuenta, sin mirar a los otros. Eso hace que tanto el sistema original como el reconstruido sean *productos* de distribuciones por nodo. Y cuando comparás dos productos con la distancia de Hamming como costo, la EMD conjunta se parte exactamente en la suma de las EMD de cada nodo; y para una variable binaria, la EMD entre dos marginales es la diferencia absoluta de sus probabilidades.

Analogía: si querés comparar dos recetas y sabés que cada ingrediente se mide por separado e independiente de los demás, no necesitás cocinar los dos platos y compararlos enteros; comparás ingrediente por ingrediente y sumás las diferencias. El supuesto de independencia es lo que te deja hacer eso. (Manual, sección 2.1, con la demostración formal por acoplamiento y variación total.)

Cuidado: este atajo vale **solo** mientras las reconstrucciones sean productos independientes. Si en el futuro alguien introdujera dependencias entre nodos, la suma de restas deja de ser válida.

### A.4 ¿Qué es la distancia de Hamming y el factor 2^−d?

La **distancia de Hamming** entre dos estados binarios es *cuántos bits hay que cambiar para pasar de uno al otro*. Entre `101` y `100` la distancia es 1 (cambia el último bit); entre `101` y `010` es 3 (cambian los tres).

Es la métrica natural del **hipercubo**: si pensás cada estado como un vértice de un cubo n-dimensional, la distancia de Hamming es la cantidad de aristas del camino más corto entre dos vértices.

El **factor 2^−d** aparece en la función de costo del método geométrico: cuando se mide el "costo de transición" entre dos estados a distancia `d`, ese costo se multiplica por `2^−d`. Es un **decaimiento**: cuanto más lejos están dos estados (más bits de diferencia), menos pesa esa relación. A distancia 1 pesa 1/2; a distancia 5 pesa 1/32; a distancia 10, 1/1024.

Analogía: es como el volumen de una conversación según la distancia. La persona a tu lado (1 paso) la escuchás fuerte; alguien a 10 pasos, casi nada. El factor 2^−d hace que las relaciones causales "cercanas" dominen y las "lejanas" se desvanezcan. (Manual, secciones 2.2 y 4.1.)

### A.5 ¿Por qué el algoritmo es exponencial y por qué no se pudo eliminar?

El método geométrico, para decidir el mejor corte, necesita recorrer los estados del **retículo del hipercubo**, y un sistema de `n` variables tiene **2^n estados**. Con n=25 eso son 33.554.432 estados. Esa es la raíz de la dificultad: el trabajo crece como 2^n, se duplica con cada variable que agregás. (Manual, sección 1, hallazgo raíz.)

Durante el Sprint 2 se intentó **eliminar** esa exponencialidad por dos caminos, y los dos fallaron *de manera demostrable*:

1. **Recortar el conjunto de estados** (mirar solo algunos niveles del retículo): no sirve, porque el barrido del algoritmo consume *todos* los niveles del 1 al n−1; lo único que sobraba era un nivel. (Manual, sección 4.5a.)
2. **Truncar la recursión de costos** (cortar los términos chicos): no sirve, porque se demostró que el error de truncar es *del mismo tamaño* que la señal que querés medir en los niveles bajos, así que cambiarías el resultado. (Manual, sección 4.5b.)

Y lo más importante: se **demostró una cota inferior** (Manual, sección 4.5c). Es un argumento adversarial: si tu algoritmo no lee el valor de algún estado de un nivel que el método barre, un "adversario" puede poner justo en ese estado un valor que cambie el ganador, y tu algoritmo daría una respuesta distinta del método correcto. Como los niveles barridos cubren del orden de 2^n estados, *cualquier* algoritmo que reproduzca fielmente este método debe leer al menos del orden de 2^n valores. La exponencialidad no es un defecto de implementación: está en la **definición** del método.

Entonces, ¿qué se logró en el Sprint 2 si no se pudo bajar de 2^n? Se eliminó todo lo *demás*: la versión vieja además guardaba un diccionario gigante de Python en memoria (decenas de GB en n=25) y hacía las cuentas con objetos lentos. La reformulación hace exactamente el mismo cálculo (bit a bit idéntico), pero con matrices `numpy` compactas que se procesan y se tiran nivel por nivel. Resultado: n=20 pasó de 129,4 s a 11,3 s, y n=25 que antes *no corría* (MemoryError) ahora corre en 395,6 s. (Manual, sección 8.2; `review/sprint2/optimizado.json` y `optimizado_n25.json`.)

### A.6 ¿Qué es el greedy top-down y por qué genera el "gap"?

**Greedy top-down** ("voraz, de arriba hacia abajo") es la estrategia para hacer k-particiones: empezás con todo junto (1 grupo) y vas **cortando de a uno** hasta tener k grupos. En cada paso elegís el corte que *en ese momento* deja la menor pérdida.

Analogía: cortar una torta para repartirla mejor, pero decidiendo cada corte sin poder deshacer los anteriores. El primer corte parece óptimo *visto solo*, pero quizás te deja mal parado para los cortes siguientes.

Eso es exactamente el **gap**: como cada decisión es local e irreversible, a veces el resultado final no es el mejor posible. Es la **miopía** del greedy. Se midió contra la respuesta perfecta (fuerza bruta) y en 2 de 9 casos el greedy quedó por encima del óptimo (ver A.11). El gap se aceptó como una limitación documentada e inherente a este tipo de heurística; mejorarlo (con intercambios de a pares) quedó como trabajo futuro. (Manual, secciones 5.2 y 11; decisión de diseño 5.)

### A.7 ¿Qué es la poda Branch & Bound?

Cuando, después del greedy, se intenta **mejorar** la k-partición moviendo vértices de un grupo a otro (Fase 2), hay muchísimos movimientos posibles. La **poda** (estilo Branch & Bound) es la técnica de *descartar movimientos sin calcularlos del todo*, cuando se puede demostrar que no van a mejorar.

Dos podas concretas en el proyecto (Manual, sección 5.3):

1. **Cota cero**: antes de evaluar un movimiento, se suma cuánta pérdida tienen *ahora* los nodos que ese movimiento podría tocar. Si esa suma es 0, el movimiento no puede mejorar nada (no hay pérdida que recuperar) → se descarta sin calcular. En la batería medida, esta poda descartó el 53-80% de los movimientos.
2. **Aborto temprano**: mientras se calcula el efecto de un movimiento nodo por nodo, si ya quedó claro que el balance no va a dar negativo (no va a mejorar), se corta el cálculo a la mitad.

Analogía: estás buscando una mejor jugada en el ajedrez y, antes de calcular una variante entera, ves que ya vas perdiendo material sin compensación → no seguís analizándola. Eso es podar.

Además se evita el "reinicio": un movimiento ya descartado no se vuelve a revisar mientras no cambien los grupos involucrados (contadores de versión). En toda la batería medida, la Fase 2 convergió en una sola pasada. (Manual, sección 5.3.)

### A.8 ¿Qué hace la marginalización perezosa y por qué evita el MemoryError?

**Marginalizar** una dimensión de un cubo de probabilidades es promediar sus dos caras (el caso "0" y el caso "1" de esa variable), colapsándola. (Manual, sección 3.1.)

El problema: la forma ingenua, `np.mean(cubo, axis=...)`, **materializa el cubo entero en memoria** y además lo convierte a float64. Para n=25 ese cubo tiene 2^25 = 33 millones de celdas *por cada nodo*; hacerlo así revienta la RAM (MemoryError).

La **marginalización perezosa** (`_mean_axis_flat`, Manual sección 3.2) hace lo mismo pero:
- trabaja sobre el arreglo **aplanado** (una tira de números), nunca arma el cubo n-dimensional;
- promedia con **vistas** (mira pares de mitades del arreglo sin copiarlas) y escribe en un único buffer de salida la mitad de grande;
- guarda el resultado memoizado, así no recalcula lo mismo dos veces.

Analogía: para sumar las páginas pares e impares de un libro de 10.000 páginas no fotocopiás el libro entero; pasás las hojas de a dos y vas anotando. Usás una libreta chica, no una segunda biblioteca.

Por eso n=25 entra en 16 GB: nunca existe el cubo completo en RAM, solo tiras que se procesan y se descartan.

### A.9 ¿Por qué float32 y no float64?

`float64` (doble precisión) usa 8 bytes por número; `float32` (precisión simple), 4 bytes. **float32 ocupa la mitad de RAM.**

Para N=25 eso es la diferencia entre 6.400 MB (float64) y 3.200 MB (float32) solo para la TPM. (Fuente: `review/sprint2/diag_tpm.json`, proyección N25A.) En un equipo de 15,7 GB, esa mitad es decisiva.

¿Y la precisión? No importa para este problema: los valores son promedios de datos binarios (números "redondos" en binario), que float32 representa exacto hasta 24 bits, y las decisiones del algoritmo (qué corte gana) no cambian por diferencias de ~1e-6. Se verificó: la versión float32 da **el mismo resultado** que la versión float64 original en los 15 casos de prueba (Manual, sección 4.8). Cuando hace falta sumar muchos términos, se acumula en float64 para no perder nada. (Manual, sección 4.7.)

Analogía: para anotar cuántos litros de nafta cargaste no necesitás 15 decimales; con dos alcanza y la libreta pesa la mitad.

### A.10 ¿Qué es el oráculo y por qué k=2 debe reproducir a GeometricSIA?

El **oráculo** es la versión *original* del algoritmo geométrico, guardada intacta en `geometric_oracle.py`. Es lenta y gastadora, pero se confía en que es **correcta**. Sirve como "juez": cualquier versión nueva y optimizada se compara contra el oráculo en casos chicos, y si no da exactamente lo mismo, la versión nueva tiene un error. (Manual, decisión de diseño 3.)

Analogía: una calculadora vieja confiable contra la cual probás tu calculadora nueva y veloz. Si difieren, la sospechosa es la nueva.

**Por qué k=2 debe reproducir a GeometricSIA**: la k-partición con k=2 *es* una bipartición. Si el código de k-particiones, puesto en k=2, no da exactamente lo mismo que el `GeometricSIA` ya validado (misma partición, mismo phi), entonces la generalización a k grupos rompió algo. Por eso fue la **prueba de aceptación no negociable** del Sprint 3. Resultado: **15/15 casos idénticos**, con máscaras triviales y no triviales. (Manual, sección 5.5; `review/sprint3/validacion_kgeo.json`.)

### A.11 ¿Qué demostró la fuerza bruta (7/9)?

La **fuerza bruta** enumera *todas* las particiones posibles y elige la mejor: da la respuesta perfecta, pero solo es viable en sistemas chicos (para N6A con k=3 ya evalúa 86.526 particiones). Se usó para medir **qué tan buena** es la heurística greedy comparándola con el óptimo real.

Resultado (Manual, sección 13.2; `review/sprint3/validacion_kgeo.json`): el greedy alcanzó el óptimo exacto en **7 de 9 casos**. En los otros 2 (N3A y N4A con k=3) quedó con un **gap de 0,25**: greedy dio 0,75 donde el óptimo era 0,50.

Qué demuestra esto: que la heurística es **buena pero no perfecta**, y honestamente *cuánto* le falta. No se barrió debajo de la alfombra: el gap está medido, cuantificado y explicado (la miopía del primer corte, A.6). Es información legítima sobre la calidad del método.

### A.12 ¿Qué son monotonía causal e invariancia dimensional?

Son dos **propiedades que el resultado debe cumplir** si el algoritmo es correcto. Se verificaron en el Sprint 4 (Manual, sección 13.1; `review/sprint4/validacion_formales.json`):

- **Monotonía causal** (φ₂ ≤ φ₃ ≤ φ₄ ≤ φ₅): cuantos más pedazos hacés, más información rompés. Cortar en 3 nunca puede perder *menos* que cortar en 2. Tiene que ser una escalera que sube. Se verificó en **9 de 9** casos de control. Ejemplo real (N10A completo): 0,4727 → 0,9531 → 1,4336 → 1,9180.
- **Invariancia dimensional**: si renombrás las variables (cambiás el orden en que están), el resultado tiene que ser *el mismo* salvo por ese renombre. Que A pase a llamarse C no debe cambiar qué tan integrado está el sistema. Se verificó en **5 casos × 2 permutaciones** (orden invertido y orden aleatorio), y tanto el φ como la composición de la partición quedaron invariantes.

Analogía de la invariancia: pesar una valija no debería depender de en qué orden metiste la ropa. Si tu balanza da distinto según el orden, la balanza está mal. Estas pruebas confirman que la "balanza" (el algoritmo) no tiene sesgos ocultos por el orden de los datos.

### A.13 ¿Por qué el cuello de botella fue la RAM y no la CPU?

Porque el algoritmo es **secuencial y liviano en cómputo, pero pesado en datos**. Cada operación (un promedio, una resta) es trivial para el procesador; lo que cuesta es que hay 2^n datos y todos tienen que *caber en memoria* y *recorrerse*.

El dato observado en la ejecución de 25A lo confirma: un caso consume ~5,9 GB de RAM con la **CPU al 8%**. Ese 8% no es que el procesador esté aburrido por falta de trabajo: es que el trabajo usa **un solo hilo** (8% ≈ 1 de los 12 hilos lógicos del i7), y ese hilo pasa la mayor parte del tiempo *esperando que la memoria le entregue datos*, no calculando. El límite es cuántos GB entran, no cuántas operaciones por segundo hace el chip. (Ver Parte C para el análisis completo.)

Analogía: mudarte no es difícil por levantar cajas (eso es fácil), sino porque tenés miles de cajas y un solo camión. El problema es el volumen y el transporte, no la fuerza.

### A.14 ¿Por qué ejecución por lotes con guardado atómico y reanudabilidad?

El llenado del Excel de entrega son **cientos de casos**, y los pesados (N=25 con mecanismo completo) tardan **minutos cada uno** (hasta ~929 s medidos bajo el límite, ver Parte C). El total es de horas de cómputo desatendido. Eso obliga a tres cosas:

- **Por lotes**: se procesan los casos uno tras otro sin que nadie esté mirando, cada uno en su propio subproceso con un límite de tiempo.
- **Guardado atómico**: el Excel se guarda escribiendo primero a un archivo temporal y recién al final se reemplaza el original de un saque (`os.replace`). Así, si el proceso muere a mitad de un guardado, el Excel nunca queda corrupto: o tenés la versión vieja entera o la nueva entera, nunca una mezcla rota.
- **Reanudabilidad**: cada caso ya resuelto se detecta (la celda está llena) y se saltea. Si se corta la corrida (timeout, o un apagón como el que pasó), relanzás y continúa *desde donde quedó*, sin rehacer lo hecho.

Analogía: bajar una película grande con un gestor de descargas. Si se corta internet, no empezás de cero; retoma desde el pedazo donde iba, y el archivo a medio bajar no te rompe los ya bajados. (Manual, sección 13.3 y 13.4; hubo un apagón real que se reanudó sin pérdida ni corrupción.)

### A.15 El bug N1: qué era, cómo se detectó, cómo se corrigió

**Qué era**: la versión vieja de la k-partición mezclaba dos sistemas de numeración. Construía los grupos usando **posiciones** (0, 1, 2... el lugar en una lista) pero después los comparaba contra las **etiquetas reales** de las variables (el índice original del nodo). Cuando se usaban máscaras "completas" (todas las variables presentes), posición y etiqueta coincidían por casualidad y todo *parecía* andar. Pero con máscaras no triviales (cuando algunas variables se sacan del subsistema), posición y etiqueta dejaban de coincidir, y el código asignaba nodos a grupos equivocados: producía particiones y pérdidas **silenciosamente erróneas**, sin tirar ningún error. (Manual, sección 9.5, hallazgo N1.)

Por qué es el peor tipo de bug: no se queja. El programa corre, devuelve un número, llena el Excel... y el número está mal. No hay un crash que te avise.

**Cómo se detectó**: en la auditoría del Sprint 1, leyendo el código y notando que `range(len(...))` (posiciones) se comparaba contra `cube.indice` y `cube.dims` (etiquetas). Se marcó como crítico y se confirmó que los casos de prueba existentes ya lo activaban.

**Cómo se corrigió** (Sprint 3): se reescribió la clase entera para que *todo* se maneje por **etiqueta global**, nunca por posición. Los grupos pasaron a ser conjuntos de pares `(tiempo, etiqueta)`. Así el bug es imposible por construcción: ya no existen dos sistemas de numeración que puedan desincronizarse. La corrección se validó con la prueba k=2 = GeometricSIA (15/15) y con la fuerza bruta. (Manual, secciones 5.1 y 9.5.)

---

## Parte B — El proyecto explicado de cero

### B.1 El problema

Tenemos un sistema de `n` variables binarias (prendido/apagado) que evolucionan en el tiempo: dado el estado de todas ahora (t), hay una probabilidad de que cada una esté prendida en el instante siguiente (t+1). Esa dinámica viene dada por una tabla, la **TPM** (Transition Probability Matrix).

La pregunta de la Teoría de la Información Integrada es: **¿qué tan "uno solo" es este sistema?** ¿Es una unidad indivisible donde todo depende de todo, o en realidad son subsistemas casi independientes pegados con cinta? La forma de responderlo es buscar **por dónde conviene cortarlo** para romper la menor cantidad de información: la partición de mínima pérdida (MIP), y su pérdida asociada φ.

Si el mejor corte posible casi no pierde información (φ ≈ 0), el sistema era separable: no estaba tan integrado. Si hasta el mejor corte duele mucho (φ grande), el sistema es genuinamente integrado.

### B.2 El modelo matemático, pieza por pieza, y por qué cada una

- **TPM** → **n-cubos**: la TPM es una tabla de 2^n filas (un renglón por cada estado posible del presente) y n columnas (uno por variable futura). Cada columna se reorganiza como un **n-cubo**: un tensor donde cada eje es una variable. *Por qué*: el cubo permite "marginalizar" (promediar) una variable simplemente colapsando un eje, que es la operación central del algoritmo. (Manual, sección 1.1.)

- **Condicionar y sustraer** → el **subsistema**: el usuario elige qué variables mirar (alcance, mecanismo). Condicionar fija variables a su valor inicial; sustraer las saca promediándolas. Lo que queda es el subsistema mínimo relevante. *Por qué*: no siempre interesa el sistema entero; muchas veces se estudia un subconjunto. (Manual, sección 1.2.)

- **Marginal de referencia** `v_orig`: para cada nodo futuro, su probabilidad de estar apagado en el estado inicial. Es la "huella" del sistema entero contra la que se compara cualquier corte. (Manual, sección 1.2.)

- **Partición** → **reconstrucción** → **φ**: un corte agrupa los vértices (presentes y futuros) en grupos. Se "reconstruye" el sistema como si cada grupo fuera independiente (cada futuro solo ve los presentes de su propio grupo, los demás se promedian). φ es la suma de diferencias absolutas entre la marginal original y la reconstruida. *Por qué la suma de restas*: por el supuesto de independencia condicional (A.3). (Manual, secciones 1.4 y 2.1.)

- **EMD-efecto** y **Hamming**: la métrica de pérdida y la métrica del retículo. (A.3 y A.4.)

- **Método geométrico**: la forma astuta de proponer cortes candidatos sin probarlos todos. En vez de las ~2^|W| particiones posibles, propone del orden de `n` candidatos buenos (basados en la geometría del hipercubo) y los evalúa exacto. (Manual, sección 4.3.)

### B.3 Ejemplo chico trazado a mano (N3A, n=3)

Vamos a calcular un φ real a mano y verificar que coincide con la implementación. Usamos la red **N3A** (3 variables: A, B, C), estado inicial `100` (A prendida, B y C apagadas), sistema completo.

**La TPM** (`data/samples/N3A.csv`), cada fila es un estado presente en little-endian (el bit de A es el menos significativo), cada columna la probabilidad de que ese nodo esté prendido en t+1:

```
estado     A  B  C
000        0  0  0
100        0  0  1     <- fila del estado inicial (A=1,B=0,C=0)
010        1  0  1
110        1  0  0
001        1  0  0
101        1  1  1
011        1  0  1
111        1  1  0
```

**Paso 1 — la huella del sistema entero (`v_orig`).** Para cada nodo, miramos su probabilidad de estar *apagado* en el estado inicial (fila `100`):
- A en la fila `100` vale 0 → apagado con probabilidad 1 → v_orig(A) = 1
- B en la fila `100` vale 0 → v_orig(B) = 1
- C en la fila `100` vale 1 → prendido, apagado con probabilidad 0 → v_orig(C) = 0

**v_orig = [1, 1, 0].** (Verificado con la implementación: `distribucion_marginal()` devuelve `[1, 1, 0]`.)

**Paso 2 — proponemos un corte.** El mejor corte que encuentra el método (y que confirma la fuerza bruta) aísla **el futuro de B** en un grupo solo, y deja todo lo demás (los presentes a, b, c y los futuros A, C) en el otro. Es decir: el futuro de B se queda *sin ningún presente* de su lado.

**Paso 3 — reconstruimos.** En la reconstrucción, cada nodo futuro solo conserva los presentes de su grupo:
- A y C están con todos los presentes → sus probabilidades no cambian: A sigue en 1, C sigue en 0.
- B quedó **sin presentes** → su cubo se promedia entero. El promedio de toda la columna B = (0+0+0+0+0+1+0+1)/8 = 2/8 = **0,25** de estar prendido → 0,75 de estar apagado.

**v_reconstruido = [1, 0,75, 0].** (Verificado con la implementación.)

**Paso 4 — calculamos φ:**
$$\varphi = |1-1| + |0{,}75-1| + |0-0| = 0 + 0{,}25 + 0 = \mathbf{0{,}25}$$

Y ese **0,25** es exactamente el φ que reporta la implementación para N3A (`review/sprint2/validacion_oraculo.json`, caso N3A: phi = 0,25). El corte cuesta 0,25: al aislar el futuro de B perdimos esa cantidad de información, y ningún otro corte pierde menos.

Lo que muestra el ejemplo: φ no es magia, es *comparar dos vectores de probabilidades y sumar las diferencias*. Lo difícil no es esta cuenta (es trivial), sino **encontrar cuál de todos los cortes da el φ más chico** sin probarlos todos. Eso es lo que hace el método geométrico, y por qué es exponencial.

### B.4 El pipeline de extremo a extremo (del CSV al resultado)

(Manual, sección 6.)

1. **CSV** → un archivo `N{n}{página}.csv` en `data/samples/` con la TPM. Para N grande hay además un caché binario `.npy` que carga muchísimo más rápido (ver Parte C).
2. **Manager** → resuelve qué archivo cargar según el tamaño del estado inicial.
3. **System** → convierte la TPM en n-cubos (en float32).
4. **Preparar subsistema** → aplica condicionar y sustraer; calcula `v_orig`; arranca el cronómetro.
5. **Estrategia** → `GeometricSIA` (k=2) o `KGeometricSIA` (k≥2) busca el corte de mínimo φ.
6. **Solution** → empaqueta el resultado: la partición (en notación de paréntesis grandes ⎛ ⎞), el φ, las distribuciones y el tiempo.
7. **Excel** → `llenar_excel.py` ubica la hoja (por tamaño de red) y el bloque (por k) en el libro de pruebas y escribe Partición, Pérdida y Tiempo del lado Geometric, de forma reanudable y con guardado atómico.

---

## Parte C — Análisis de ejecución en el equipo real

**Hardware** (dato del equipo): Windows 11, Intel Core i7-1255U (10 núcleos / 12 hilos lógicos), **15,7 GB de RAM**.

**Observado durante la 25A**: un caso consume **~5,9 GB de RAM** con la **CPU al ~8%**, y se ven **tres procesos Python** (el de cálculo más dos del andamiaje de `multiprocessing`), conviviendo con navegador, SQL Server y Oracle.

### C.1 Por qué N=25 está al límite de los 15,7 GB

La cuenta de memoria para N=25 (fuente: `review/sprint2/diag_tpm.json`, proyección N25A, y sección 12 del manual):

- La **TPM** en float32: **3.200 MB (~3,2 GB)**. (En float64 serían 6.400 MB, y por eso se usa float32, A.9.)
- Los **n-cubos** del sistema: otra copia del orden de la TPM, también en float32.
- Las **matrices de costos** del algoritmo en streaming: hasta ~1,7 GB en el pico (Manual, sección 4.6).
- El **intérprete de Python, numpy y el resto**.

Sumado, el caso observado da **~5,9 GB**. Sobre 15,7 GB de RAM total, y con el sistema operativo más navegador, SQL Server y Oracle ya ocupando varios GB, el **margen es ajustado pero alcanza**: el caso entra, pero no hay lugar para correr dos casos N=25 pesados a la vez, ni mucho colchón si los otros programas crecen.

**El punto clave**: N=25 está *al borde* no por casualidad. Cada variable extra **duplica** la memoria. N=24 usaría la mitad (~1,6 GB de TPM); N=26 usaría el doble (~6,4 GB de TPM sola) y ya no entraría junto con todo lo demás. 15,7 GB de RAM ponen el techo práctico de esta máquina justo alrededor de N=25.

### C.2 Qué margen queda

Con ~5,9 GB por caso sobre 15,7 GB totales, quedan ~9,8 GB nominales, pero de ahí hay que descontar Windows (~2-4 GB) y los programas que el dato menciona conviviendo (navegador, SQL Server, Oracle pueden sumar varios GB más). El margen **real** para el cálculo es de unos pocos GB: suficiente para **un** caso N=25 a la vez, no para dos. Por eso el llenado es secuencial (un caso tras otro), no paralelo.

### C.3 El rol del timeout de 1500 s

El **timeout** mata un caso que tarde más de 1500 s (25 minutos) y deja su celda vacía, para que la corrida por lotes no se quede trabada para siempre en un caso patológico. Es una red de seguridad.

¿Por qué 1500 y no menos? Porque los casos N=25 con mecanismo completo tardan de verdad varios minutos, y un límite muy bajo los mataría sin necesidad. La historia real: el primer intento puso el límite en 560 s y mató un caso que en realidad necesitaba ~345-430 s de cálculo más la carga; subir a 1500 s lo resolvió. (Manual, sección 13.4-c.)

Pero el timeout también es **información legítima**: si un caso *no entra* en 1500 s, eso dice algo real sobre el límite de la estrategia en este hardware, y se reporta como "excede el tiempo viable" en vez de forzarlo. En el log de llenado de 25A se registraron **3 casos con `timeout 1500s`** (`review/sprint4/llenado_nocturno.log`): esos quedan documentados como fuera del tiempo viable, no escondidos.

### C.4 Qué pasaría con 8 GB o con 32 GB de RAM

- **Con 8 GB**: N=25 **no entraría**. Un solo caso necesita ~5,9 GB, y entre Windows y cualquier otro programa ya no quedarían esos 5,9 GB libres y contiguos → MemoryError o un *swapping* (uso de disco como memoria) tan lento que sería inviable. El techo práctico bajaría a algo como N=22-23. (Las proyecciones de `diag_tpm.json` lo respaldan: la TPM N=25 sola en float32 ya son 3,2 GB, y todo lo demás no entra en 8 GB con el SO encima.)
- **Con 32 GB**: N=25 correría **con holgura** (sobrarían ~20 GB), y se podrían correr **varios casos en paralelo** (cada uno en su proceso, ~5,9 GB), aprovechando los 12 hilos del procesador que hoy están casi ociosos (CPU al 8%). El cuello de botella se mudaría de la RAM a la CPU, y ahí sí el paralelismo daría una mejora real de tiempo total. También permitiría intentar N=26 (un solo caso a la vez).

### C.5 Curva de costo por caso (tiempos reales del log de llenado de 25A)

Fuente: `review/sprint4/llenado_nocturno.log`. De los casos de 25A con tiempo registrado, la distribución es marcadamente **bimodal**:

| Tipo de caso | Cuántos | Tiempo |
|---|---|---|
| Rápidos (mecanismo muy reducido) | 121 | < 1 s |
| Medios | 37 | 1 – 10 s |
| Lentos (mecanismo grande/completo) | 51 | ≥ 10 s, hasta ~929 s |
| Excedieron el límite | 3 | timeout 1500 s (celda vacía) |

La lectura: **el costo de un caso N=25 depende casi por completo de cuántas variables quedan activas en el mecanismo**, no del número de la red. Un caso de 25 variables con mecanismo casi vacío se resuelve en centésimas de segundo (el subsistema real es chico); uno con mecanismo completo recorre el hipercubo entero y tarda cientos de segundos. Los lentos medidos suben así (segundos): 10 · 13 · 17 · 21 · 33 · 53 · 79 · 123 · 181 · 218 · 343 · 359 · 387 · 429 · 474 · 627 · 657 · 779 · 880 · 929 (`llenado_nocturno.log`). Por encima de eso, el timeout corta.

Esto explica por qué el total del llenado de 25A es de horas: la mayoría de los casos son rápidos, pero el puñado de casos con mecanismo grande domina el tiempo de pared. (Comparación útil: el caso N=25 con mecanismo completo, medido aislado en el Sprint 2, dio **395,6 s** de cálculo más **29,1 s** de carga de la TPM; `review/sprint2/optimizado_n25.json`.)

---

## Parte D — Los cinco desafíos, con honestidad

### D.1 La memoria exponencial

El desafío madre. El trabajo y la memoria crecen como 2^n, y en N=25 eso choca contra los 15,7 GB del equipo. La versión vieja directamente *no corría* N=25 (MemoryError). No se pudo eliminar la exponencialidad (está demostrado que es inherente, A.5), pero sí se atacó todo lo demás: marginalización perezosa (A.8), float32 (A.9), y procesamiento en streaming que nunca guarda el hipercubo entero. Resultado honesto: N=25 ahora **corre**, pero al límite del hardware, con casos que tardan minutos y algunos que no entran en el tiempo viable. No es "rápido"; es "posible donde antes era imposible". (Manual, secciones 1, 4.6, 8.2.)

### D.2 El bug N1 silencioso

El desafío más traicionero, porque no se quejaba: el código corría y devolvía números *equivocados* cuando las máscaras no eran triviales, por mezclar posiciones con etiquetas (A.15). Lo honesto del caso: se encontró **leyendo el código en la auditoría**, no porque algo fallara — un test que solo hubiera usado máscaras completas nunca lo habría detectado. La lección es que "el programa corre y da un número" no significa "el número está bien". Se corrigió de raíz reescribiendo todo por etiqueta global. (Manual, secciones 5.1 y 9.5.)

### D.3 Las convenciones de los dos subproyectos

El repositorio tiene dos ramas (GeoMIP y QNodes) con **convenciones de interfaz distintas**: distinto orden de argumentos, distintos nombres de funciones, distinta forma de cargar la TPM, distinto criterio para la marginal (una guarda la probabilidad de "apagado", la otra de "prendido"). El riesgo era "arreglar" código de una rama mezclándole convenciones de la otra y romper todo sutilmente. La regla que se siguió (regla cero del proyecto): identificar a qué rama pertenece cada archivo *antes* de tocarlo y respetar su convención. GeometricSIA y KGeometricSIA son de GeoMIP y se mantuvieron en esa convención. (Manual, sección 7.2.)

### D.4 La reformulación de costos: dos rutas fallidas y una cota inferior

El desafío intelectualmente más exigente. La consigna era "eliminá la exponencialidad". Se intentaron las dos rutas obvias y **las dos se demostraron inviables**: recortar estados (no se puede, el método los usa todos) y truncar la recursión (no se puede, el error es tan grande como la señal). Y en vez de seguir intentando en vano, se **demostró una cota inferior**: *ningún* algoritmo fiel al método puede evitar leer del orden de 2^n datos (A.5). Lo honesto: el objetivo literal ("eliminar la exponencialidad") era **imposible**, y se demostró que lo era, en vez de fingir que se logró. Lo que sí se logró —y es mucho— fue eliminar todo el desperdicio alrededor, con resultado bit a bit idéntico al original. La diferencia entre "no se pudo y acá está la prueba de por qué" y "no se pudo" es la diferencia entre un resultado científico y una excusa. (Manual, secciones 4.5 y 4.6.)

### D.5 Los detalles operativos

El llenado del Excel real destapó problemas que no son de algoritmo sino de *ingeniería de la corrida*, y vale narrarlos porque son parte honesta del trabajo:

- **Conteo de casos**: dos inspecciones tempranas contaron mal el número de casos por hoja (35, luego 40); el número real es 49 (hoja 10A) o 50 (las demás), verificado contra el lado QNodes ya lleno. La regla definitiva quedó: iterar hasta la primera fila vacía, no confiar en un tope fijo. (Manual, sección 13.3.)
- **El apagón**: la corrida nocturna se interrumpió por un apagado del equipo. Gracias al guardado atómico y la reanudabilidad (A.14), **no se perdió ni se corrompió nada**: el libro abrió bien, lo ya calculado estaba intacto, y la corrida retomó desde donde iba. Lo único que dejó fue un archivo de candado huérfano que se limpió a mano antes de relanzar.
- **El candado de escritor único**: se descubrió que dos llenados simultáneos se pisarían las celdas (cada uno guarda su copia entera del libro). Se agregó un *lockfile* para que solo un proceso escriba a la vez.
- **El memmap que no servía**: el primer intento de cargar la TPM "perezosamente" desde disco (memmap) resultó *más lento*, porque el sistema la consume por columnas y el archivo está por filas → lecturas dispersas de 3,3 GB por columna, hasta provocar timeouts. Se volvió a cargar la TPM completa de una (~10 s) y se documentó que, si algún día se quiere memmap de verdad, hay que guardar la TPM por columnas. (Manual, sección 13.4-e.)

Ninguno de estos era un problema "de paper", pero todos podían arruinar la entrega. Documentarlos es parte de la honestidad del proyecto.

---

## Parte E — Glosario

- **phi (φ)**: la pérdida de información al partir el sistema; cuánto se desvía el sistema partido del entero. Menos es mejor (corte más limpio).
- **MIP** (Minimum Information Partition): la partición de mínima pérdida, el "mejor corte" que el proyecto busca.
- **k-MIP**: la MIP cuando se permite cortar en `k` grupos en vez de 2.
- **IIT** (Integrated Information Theory): el marco teórico que mide cuán integrado (indivisible) es un sistema causal.
- **TPM** (Transition Probability Matrix): la tabla que define la dinámica; fila = estado presente, columna = probabilidad de que un nodo esté prendido en el instante siguiente.
- **n-cubo**: la columna de la TPM reorganizada como tensor n-dimensional (un eje por variable), para poder marginalizar colapsando ejes.
- **vértice**: un par (tiempo, variable); el presente `a` y el futuro `A` son vértices distintos. La partición se hace sobre vértices.
- **EMD** (Earth Mover's Distance): la distancia entre dos distribuciones; acá se reduce a una suma de diferencias absolutas gracias a la independencia condicional.
- **Hamming (distancia de)**: cantidad de bits distintos entre dos estados; la métrica del hipercubo.
- **2^−d**: factor de decaimiento por distancia de Hamming `d`; relaciones lejanas pesan exponencialmente menos.
- **marginalización**: promediar las dos caras de un eje de un cubo, colapsando esa variable.
- **marginalización perezosa**: hacer eso sobre el arreglo aplanado, con vistas y sin materializar el cubo entero; evita el MemoryError.
- **greedy (top-down)**: ir cortando de a un grupo, eligiendo en cada paso el corte localmente mejor; rápido pero puede ser miope (genera el gap).
- **poda (Branch & Bound)**: descartar movimientos/ramas sin calcularlos del todo cuando se puede probar que no van a mejorar.
- **oráculo**: la versión original y confiable del algoritmo (`geometric_oracle.py`), usada como juez de correctitud de las versiones nuevas.
- **fuerza bruta**: enumerar todas las particiones y elegir la mejor; da el óptimo exacto pero solo es viable en sistemas chicos.
- **monotonía causal**: propiedad de que φ no baja al aumentar k (φ₂ ≤ φ₃ ≤ φ₄ ≤ φ₅).
- **invariancia dimensional**: propiedad de que renombrar/reordenar las variables no cambia el resultado salvo por ese renombre.
- **memmap**: mapear un archivo de disco como si fuera memoria, para no cargarlo entero; útil solo si el patrón de acceso es secuencial (acá no lo era por filas/columnas).
- **float32 / float64**: números de precisión simple (4 bytes) / doble (8 bytes); el proyecto usa float32 para ocupar la mitad de RAM, sin perder exactitud relevante.
- **TPM `.npy`**: el caché binario de la TPM (formato numpy), que carga mucho más rápido que el CSV de texto.
- **guardado atómico**: escribir a un temporal y reemplazar de un saque, para que un corte no deje el archivo corrupto.
- **streaming (por niveles)**: procesar el retículo nivel por nivel, descartando lo viejo, para no tener todo en memoria a la vez.

---

*Documento de estudio. La fuente formal y las demostraciones están en `MANUAL_TECNICO_KGEOMIP.md`. Los números provienen de los archivos en `GeoMIP/src/Method2_Dynamic_Programming_Reformulation/review/` (sprints 2, 3 y 4) y de las secciones citadas del manual.*
