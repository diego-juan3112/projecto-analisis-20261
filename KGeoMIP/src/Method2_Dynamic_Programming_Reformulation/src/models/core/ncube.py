from dataclasses import dataclass, field
from numpy.typing import NDArray
import numpy as np


@dataclass(frozen=True)
class NCube:
    """
    N-cubo hace referencia a un cubo n-dimensional, donde estarán indexados según la posición de precedencia de los datos, permitiendo el rápido acceso y operación en memoria.
    - `indice`: índice original del n-cubo asociado con un literal (0:A, 1:B, 2:C, ...) que permita representabilidad en su alcance o tiempo futuro.
    - `dims`: dimensiones activas actuales del n-cubo, es aquí donde se conoce la dimensionalidad según su cantidad de elementos, de forma tal que si este en el tiempo es condicionado o marginalizado tendrá una dimensionalidad menor o igual a la original a pesar que haya una alta dimensión específica.
    - `data`: arreglo numpy con los datos indexados según la notación de origen, de ser necesario se aplica una transformación sobre estos que los reindexe si se desea otra notación particular.
    """

    indice: int
    dims: NDArray[np.int8]
    data: np.ndarray
    memo: dict[tuple, tuple[np.ndarray, NDArray[np.int8]]] = field(
        default_factory=dict, compare=False, repr=False
    )

    def __post_init__(self):
        """Validación de tamaño y dimensionalidad tras inicialización.

        Raises:
            ValueError: Se valida que hayan dimensiones y cumpla con las dimensiones de un cubo n-dimensional.
        """
        if self.dims.size and self.data.shape != (2,) * self.dims.size:
            raise ValueError(
                f"Forma inválida {self.data.shape} para dimensiones {self.dims}"
            )

    def condicionar(
        self,
        indices_condicionados: NDArray[np.int8],
        estado_inicial: NDArray[np.int8],
    ) -> "NCube":
        """
        Aplicar condiciones de fondo sobre un n-cubo. En estas lo que se hace es seleccionar una serie de caras sobre el n-cubo según las dimensiones escogidas y su estado inicial específico asociado, descartandose así todas las demás que no pertenezcan al indice condicionado.
        En la selección de las dimensiones es importante saber cómo la dimensión más externa es la más significativa, de forma que la selección debe hacerse de afuera hacia adentro.
        Debe tenerse claro también la localidad de las dimensiones puesto aunque se tengan dimensiones muy superiores no hay correspondencia con el total de dimensiones del cubo (dimensiones locales).

        Args:
        ----------
            indices_condicionados (NDArray[np.int8]): Dimensiones o ejes en los cuales se aplicará el condicinamiento.
            estado_inicial (NDArray[np.int8]): El estado inicial asociado al sistema.

        Returns:
        -------

            NCube: El n-cubo seleccionado en todos los ejes, pero se definen para dar selección los cuales se hayan enviado como parámetros.

        Example:
        -------
        El n-cubo original está asociado con el estado inicial

        >>> estado_inicial = np.array([1,0,0])
        >>> mi_ncubo
            NCube(index=(1,)):
                dims=(0, 1, 2)
                shape=(2, 2, 2)
                data=
                    [[[0.1  0.3 ]
                    [0.5  0.7 ]]
                    [[0.9  0.11]
                    [0.13 0.15]]]
        >>> dimensiones = np.array([2])
        >>> mi_ncubo.condicionar(dimensiones, estado_incial)
            NCube(index=(1,)):
                dims=(0, 1)
                shape=(2, 2)
                data=
                    [[0.1 0.3]
                    [0.5 0.7]]
        """
        numero_dims = self.dims.size
        seleccion = [slice(None)] * numero_dims
        for condicion in indices_condicionados:
            level_arr = numero_dims - (condicion + 1)
            seleccion[level_arr] = estado_inicial[condicion]

        nuevas_dims = np.array(
            [dim for dim in self.dims if dim not in indices_condicionados],
            dtype=np.int8,
        )
        return NCube(
            data=self.data[tuple(seleccion)],
            dims=nuevas_dims,
            indice=self.indice,
        )

    @staticmethod
    def _mean_axis_flat(data: np.ndarray, n_dims: int, eje_local: int) -> np.ndarray:
        """
        Promedia el eje `eje_local` operando sobre el arreglo PLANO mediante vistas,
        sin materializar nunca un buffer del tamano completo del hipercubo.

        Con la convencion little-endian del proyecto, la variable en la posicion
        local `pos` tiene paso (stride) `2^pos` sobre el arreglo plano; aqui llega
        como `eje_local = n_dims - 1 - pos`, de modo que `stride = 2^pos`. El plano
        se ve como bloques `(n_bloques, 2, stride)` (reshape = vista, sin copia):
        la cara 0 y la cara 1 del eje se suman directamente sobre el buffer de
        salida de tamano `2^(n_dims-1)`, unico arreglo nuevo que se crea.
        Es la version vectorizada del patron por bloques: identica aritmetica,
        sin bucle Python sobre los `n // (2*stride)` bloques.
        """
        stride = 1 << (n_dims - 1 - eje_local)
        n = data.size
        vista = data.reshape(n // (2 * stride), 2, stride)
        resultado = np.empty(n // 2, dtype=np.float32)
        salida = resultado.reshape(n // (2 * stride), stride)
        np.add(vista[:, 0, :], vista[:, 1, :], out=salida)
        resultado *= np.float32(0.5)
        return resultado

    def marginalizar(self, ejes: NDArray[np.int8]) -> "NCube":
        """
        Marginalizar a nivel del n-cubo permite acoplar o colapsar una o más dimensiones manteniendo la probabilidad condicional.
        La operación se realiza de forma perezosa sobre la representación PLANA del n-cubo, eje por eje (equivale a `np.mean` sobre la tupla de ejes por conmutatividad del promedio), evitando los buffers intermedios del tamaño completo que materializa `np.mean(axis=tupla)`.
        El resultado se memoiza por tupla de ejes solicitada, de forma que biparticiones o mediciones repetidas sobre el mismo cubo no recalculen la reducción.

        Args:
        ----
            ejes (NDArray[np.int8]): Arreglo con las dimensiones a marginalizar o eliminar. Se valida que los ejes o dimensiones dadas estén y finalmente alineamos nuevamente con las dimensiones locales, donde con numpy debemos hacer uso de la dimensión complementaria para alinear la dimensión externa a la más interna.

        Returns:
        -------
            NCube: El n-cubo marginalizado en las dimensiones dadas. Donde es equivalente el marginalizar sobre (a, b,) que primero en (a,) y luego en (b,) o viceversa.

        Example:
        -------
            >>> dimensiones = np.array([2, 3])
            >>> mi_ncubo
            NCube(index=0):
            dims=[0 1 2]
            shape=(2, 2, 2)
            data=
                [[[0. 0.]
                [1. 1.]],
                [[1. 1.]
                [1. 1.]]]

            >>> mi_ncubo.marginalizar(dimensiones)
            NCube(index=0):
                dims=[0]
                shape=(2,)
                data=
                    [0.75 0.75]

            Se han agrupado los valores del n-cubo por promedio, dejando los remanentes en la dimension 0.
        """
        clave = tuple(int(e) for e in np.asarray(ejes).ravel())
        if clave not in self.memo:
            marginable_axis = np.intersect1d(ejes, self.dims)
            if not marginable_axis.size:
                return self

            # Representacion plana contigua en float32; ravel copia solo si la
            # data era una vista no contigua (p. ej. tras condicionar).
            data_plana = np.ascontiguousarray(
                self.data.ravel().astype(np.float32, copy=False)
            )
            dims_actuales = self.dims.copy()

            for axis_global in marginable_axis:
                pos_local = np.nonzero(dims_actuales == axis_global)[0]
                if not pos_local.size:
                    continue
                n_dims = dims_actuales.size
                # Inversion local little-endian: eje_local = (n_dims - 1) - pos
                eje_local = n_dims - 1 - int(pos_local[0])
                data_plana = NCube._mean_axis_flat(data_plana, n_dims, eje_local)
                dims_actuales = np.array(
                    [d for d in dims_actuales if d != axis_global],
                    dtype=np.int8,
                )

            # reshape(()) deja un arreglo 0-dimensional cuando no quedan dims
            forma_final = (2,) * dims_actuales.size
            self.memo[clave] = (
                data_plana.reshape(forma_final),
                dims_actuales,
            )

        data_memo, dims_memo = self.memo[clave]
        return NCube(
            data=data_memo,
            dims=dims_memo,
            indice=self.indice,
        )

    def __str__(self) -> str:
        dims_str = f"dims={self.dims}"
        forma_str = f"shape={self.data.shape}"
        datos_str = str(self.data).replace("\n", "\n" + " " * 8)
        return (
            f"NCube(index={self.indice}):\n"
            f"    {dims_str}\n"
            f"    {forma_str}\n"
            f"    data=\n        {datos_str}"
        )
