# SubCube-Factor: formalización (docx) vs implementación (HFSkMIP)

## Documento fuente

- **Formalización completa:** `HFSkMIP/docs/SubCubeFactor_Formalizacion.docx` (SubCube-Factor, k-MIP, fases 1–4).

## Documentación general del curso / proyecto

En la raíz del repositorio, `docs/` contiene materiales previos del proyecto (por ejemplo guía ADAV, GeoMIP en PDF, manuales). **No** sustituyen la formalización de SubCube-Factor; sirven de contexto MIP/IIT y del framework GeoMIP/QNodes.

## Qué describe el docx (objetivo de diseño)

1. **Fase 1:** Descomposición del hipercubo en subcubos disjuntos \(\mathcal{C}(d)\) con \(|F| = n-d\) coordenadas fijas y \(d\) libres; en la guía de implementación, *corte por índice* fija \(F = \{d+1,\ldots,n\}\) (1-based), es decir las últimas \(n-d\) dimensiones.
2. **Costo local:** BFS tipo GeoMIP **restringido** a cada subcubo \(C\), tabla \(T_{\mathrm{loc}}^{X_i}(C)\).
3. **Fase 2:** Matriz de afinidad \(A(i,j)\) por correlación (Pearson) entre tablas locales vectorizadas, promediada sobre subcubos.
4. **Fase 3:** Clustering espectral + k-means para **k partes** (k-MIP).
5. **Fase 4:** Refinamiento local (hill climbing) y evaluación de \(\delta_k\) con EMD.

## Qué hace hoy el código (`hfskmip/subcube_factor.py`)

- **Bipartición (k = 2)** acoplada al mismo pipeline que GeoMIP Method2: `SIA`, `bipartir`, EMD-efecto, `Solution`.
- **Agregación simplificada:** para cada subcubo considerado, se obtiene el vector de costos por variable futura en la arista local inicial→final (recurrencia análoga a GeoMIP) y se **promedia** ese vector entre subcubos (no hay aún matriz \(A\) ni correlaciones).
- **Selección de partición:** candidatos estilo GeoMIP (*leave one future out*), reordenados por el vector agregado; se evalúa EMD real sobre los `top_k` mejores.
- **Modos de descomposición** (ver docstring y parámetros de `SubcubeFactorSIA`):
  - `index_partition`: recorre (o muestrea) la cubierta disjunta del doc con corte por índice; es la línea base alineada con la sección 4.2.2 del docx.
  - `sample_faces`: muestrea combinaciones de \(k\) dimensiones activas (útil como variante experimental; no es la cubierta \(\mathcal{C}(d)\) completa).

## Trabajo pendiente respecto al docx

| Elemento del docx                         | Estado en código                          |
|-------------------------------------------|-------------------------------------------|
| Cubierta \(\mathcal{C}(d)\) corte índice  | Implementado en modo `index_partition`    |
| Matriz de afinidad + correlación          | No implementado                           |
| Clustering espectral, k > 2               | No implementado                           |
| Refinamiento local Fase 4                 | No implementado                           |
| Default \(d = \lfloor n/2 \rfloor\)       | Usado cuando `subcube_dim` es `None`      |

La sección 11 del docx indica que 4.3–4.4 pueden refinarse con la experimentación; la tabla anterior sirve como checklist para futuras iteraciones.

## Cómo ejecutar

Desde `HFSkMIP/` (con `uv sync` si aplica):

```bash
uv run exec.py
```

Variables de entorno útiles (ver `hfskmip/main.py`): `HFS_ESTADO_INICIAL`, `HFS_TPM_PATH`, `HFS_SUBCUBE_DIM`, `HFS_MAX_SUBCUBES`, `HFS_TOP_K`, `HFS_DECOMPOSITION` (`index_partition` | `sample_faces`).
