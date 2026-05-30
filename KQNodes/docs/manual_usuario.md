## 1 ¿Qué es KQNodes y para qué sirve?

### 1.1 El problema que resuelve
KQNodes encuentra k grupos de nodos que actúan lo más "independientes" posible entre sí. Es decir, divide una red en k subgrupos cuya interacción mutua minimiza la pérdida de información al separarlos. Analogía: imagina una orquesta; KQNodes busca agrupar instrumentos que suenan más coherentes entre sí, de modo que separar los grupos reduce lo mínimo posible la armonía general.

### 1.2 Cuándo usar KQNodes vs QNodes
| Situación | Herramienta recomendada |
|---|---|
| Necesitas una bipartición (k=2) rápida y ya probada | `QNodes` |
| Requieres particionar en k>2 grupos o comparar múltiples particiones | `KQNodes` |
| Quieres experimentar con tablas de costos externas (GeoMIP) | `KQNodes` (usa T de GeoMIP) |

### 1.3 Requisitos y cómo instalar
- Requisitos: Python 3.10+, `uv` (gestor de entorno como en `QNodes/`), `pyphi`, `numpy`, `pyemd`.
- Para sincronizar el entorno (desde la raíz de `KQNodes/`):

```bash
cd KQNodes
uv sync
```

Esto instalará las dependencias definidas en `pyproject.toml` del paquete KQNodes.

Si usas Windows PowerShell, ejecuta los mismos comandos en una terminal con permisos adecuados.

---

Tono: claro y directo. Para más detalles técnicos consulta `docs/manual_tecnico.md` y `KQNodes_Diagramas.md`.

## 3 Interpretar y Ajustar Resultados

### 3.1 Diagnóstico rápido: tabla de síntomas
| Síntoma | Posible causa | Qué hacer |
|---|---|---|
| Pérdida = 0 | TPM casi determinista o red trivial (n < 3) | Verifica el CSV; si es esperado, resultado correcto |
| Pérdida muy alta (>0.9) | Red muy acoplada; pocos buenos cortes independientes | Prueba con k mayor; red requiere múltiples particiones |
| Pérdida igual para k y k+1 | Partición saturada; no hay mejor división con más partes | Aumentar k no mejora; usar k actual |
| Ejecución lenta (>10s) | n > 15 o k=n; Queyranne O(k·n³) es costoso | Reducir k o usar refinar=False para prototipado |

### 3.2 Parámetros de ajuste
**refinar=True vs False:**
- `refinar=True` (default): ejecuta hill climbing tras Queyranne. Más tiempo (x1.5) pero mejor pérdida (~5-10% mejora típica).
- `refinar=False`: solo Queyranne. Rápido; válido para prototipos o n>20.

**verbose=True:**
Imprime en consola:
- Cada iteración de Queyranne (`[iter=i] S_opt, pérdida=...`)
- Cada intercambio mejorante en refinamiento (` movimiento: x de parte_a a parte_b`)
- Convergencia (`[intercambio_local] convergencia en iteración ...`)

Úsalo para auditar comportamiento o depurar particiones inesperadas.

### 3.3 Comparación lado a lado: KQNodes vs QNodes
```python
from src.strategies.kqnodes import KQNodes
from src.strategies.q_nodes import QNodes
from src.controllers.manager import Manager

# Cargar CSV
gestor = Manager(estado_inicial="1000")
tpm = gestor.cargar_red()

# QNodes (k=2)
qnodes = QNodes(tpm)
sol_qnodes = qnodes.aplicar_estrategia(...)
print(f"QNodes k=2 pérdida: {sol_qnodes.perdida:.6f}, tiempo: {sol_qnodes.tiempo_total:.3f}s")

# KQNodes (k=3)
kqnodes = KQNodes(tpm, k=3, refinar=True, verbose=False)
sol_kqnodes = kqnodes.aplicar_estrategia()
print(f"KQNodes k=3 pérdida: {sol_kqnodes.perdida:.6f}, tiempo: {sol_kqnodes.tiempo_total:.3f}s")

# Comparación
mejora = (sol_qnodes.perdida - sol_kqnodes.perdida) / sol_qnodes.perdida * 100
print(f"Mejora: {mejora:.1f}% con k=3 respecto a QNodes k=2")
```
Esperado: KQNodes k=3 mejora pérdida ~15-30% vs QNodes k=2 en redes acopladas.

## 4 Preguntas Frecuentes y Ejemplos

### 4.1 FAQ
- ¿Puedo usar `k=1`? → No. El algoritmo busca particiones y requiere al menos `k=2`.
- ¿Garantiza el óptimo para `k>=3`? → No. La extracción iterativa de Queyranne es una heurística basada en biparticiones sucesivas; no hay garantía teórica de óptimo global para k≥3 debido a la combinatoria exponencial del espacio de particiones.
- ¿Cuánto tarda para `n=15, k=4`? → Depende del hardware y de `refinar`. Complejidad teórica O(k·n³); en máquinas modernas suele tomar desde unos segundos hasta minutos (por ejemplo 5–60s según la carga).
- ¿Qué significa que dos nodos estén en la misma parte? → Significa que el algoritmo considera su comportamiento interno más coherente entre sí que con nodos de otras partes; separarlos aumenta la pérdida de información entre grupos.
- ¿Dónde pongo mis propios CSV? → Colócalos en `QNodes/src/.samples/` para reutilizar fixtures, o crea `KQNodes/src/data/` y ajusta la ruta en el fixture de tests.

### 4.2 Ejemplo (diagrama ASCII)
Partición de `{A,B,C,D}`:

k = 2
```
 {A,B} | {C,D}
```

k = 3
```
 {A} | {B,C} | {D}
```

### 4.3 Enlaces útiles
- Documento de formalización: `../KQNodes_Formalizacion.docx`
- Diagramas de diseño: `../KQNodes_Diagramas.md`

Tono amigable: si tienes dudas prácticas sobre un CSV concreto, pégalo en el canal y te ayudo a interpretarlo.
