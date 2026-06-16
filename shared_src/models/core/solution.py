from colorama import init, Fore, Style
try:
    import pyttsx3
    from pyttsx3.engine import Engine
    from pyttsx3.voice import Voice
except Exception:  # pragma: no cover - optional voice support
    pyttsx3 = None
    Engine = object
    Voice = object
import numpy as np
from threading import Thread
from typing import Optional

from shared_src.constants.models import PYPHI_LABEL
from shared_src.constants.base import FLOAT_ZERO, INT_ZERO, WHITESPACE
from shared_src.models.base.application import aplicacion

init()


class Solution:
    def __init__(
        self,
        estrategia: str,
        perdida: float,
        distribucion_subsistema: np.ndarray,
        distribucion_particion: np.ndarray,
        particion: str,
        tiempo_total: float = FLOAT_ZERO,
        quiere_hablar: bool = True,
        voz: Optional[str] = None,
    ) -> None:
        self.estrategia = estrategia
        self.perdida = perdida
        self.distribucion_subsistema = distribucion_subsistema
        self.distribucion_particion = distribucion_particion
        self.particion = particion
        self.tiempo_ejecucion = tiempo_total
        self.id_voz = voz
        self.hablar = quiere_hablar

    def __obtener_voz_espanol(self, motor: Engine) -> Optional[str]:
        voces: list[Voice] = motor.getProperty("voices")

        prioridades = [
            ("sabina", "méxico"),
            ("helena", "españa"),
            ("spanish", None),
            ("español", None),
            ("es-", None),
        ]

        for nombre_buscado, region in prioridades:
            for voz in voces:
                nombre_voz = voz.name.lower()
                id_voz = voz.id.lower()

                if nombre_buscado in nombre_voz or nombre_buscado in id_voz:
                    if region is None or region in nombre_voz:
                        return voz.id

        return voces[INT_ZERO].id if voces else None

    def __anunciar_solucion(self) -> None:
        try:
            motor = pyttsx3.init()

            id_voz = self.id_voz or self.__obtener_voz_espanol(motor)
            if id_voz:
                motor.setProperty("voice", id_voz)

            motor.setProperty("rate", 150)
            motor.setProperty("volume", 0.9)

            mensaje = f"Solución encontrada con {self.estrategia}." + (
                f"El valor de fi es de {self.perdida:.2f}"
                if self.perdida > FLOAT_ZERO
                else "No hubo pérdida."
            )
            motor.say(mensaje)
            motor.runAndWait()
        except Exception as e:
            print(f"Error al inicializar el motor de voz: {e}")

    def __str__(self) -> str:
        espaciado = 64
        bilinea = "═" * espaciado
        trilinea = "≡" * espaciado

        def formatear_distribucion(
            distribucion: np.ndarray,
            evitar_desbordamiento=True,
        ):
            rango = distribucion.size
            mensaje_desborde = ""
            if evitar_desbordamiento:
                LIMITE = espaciado
                excedente = rango - LIMITE
                if excedente > FLOAT_ZERO:
                    mensaje_desborde = f" {excedente} valores más.."
                    rango = LIMITE

            datos = WHITESPACE.join(
                f"{Fore.WHITE}{distribucion[idx]:.4f}"
                if distribucion[idx] > FLOAT_ZERO
                else f"{Fore.LIGHTBLACK_EX}0.    "
                for idx in range(rango)
            )
            return f"[ {datos}{mensaje_desborde} {Fore.WHITE}]"

        if self.hablar:
            voz = Thread(target=self.__anunciar_solucion)
            voz.start()

        es_pyphi = self.estrategia == PYPHI_LABEL
        tipo_distribucion = "tensorial" if es_pyphi else "marginal"

        tiempo_hrs, tiempo_min, tiempo_seg = (
            f"{self.tiempo_ejecucion / 3600:.2f}",
            f"{self.tiempo_ejecucion / 60:.1f}",
            f"{self.tiempo_ejecucion:.4f}",
        )

        # Formateo especial para QNodes / KQNodes: bloque visual compacto
        def _index_to_letter(idx: int) -> str:
            # 0 -> A, 1 -> B, ... 25 -> Z, then wrap to lowercase if beyond
            if idx < 26:
                return chr(ord("A") + idx)
            else:
                return chr(ord("a") + (idx - 26) % 26)

        def _format_partition_block(particion) -> str:
            def join_letters(s, upper=True):
                items = sorted(list(s))
                if not items:
                    return "∅"
                letters = [_index_to_letter(int(i)) for i in items]
                joined = ",".join(letters)
                return joined if upper else ",".join(l.lower() for l in letters)

            try:
                parts = [particion[i] for i in range(len(particion))]
            except Exception:
                return f"{particion}"

            tops = [join_letters(p, upper=True) for p in parts]
            bots = [join_letters(p, upper=False) for p in parts]
            block_top = "".join(f"⎛ {t} ⎞" for t in tops)
            block_bot = "".join(f"⎝ {b} ⎠" for b in bots)
            return f"{block_top}\n{block_bot}"

        _prefijos_k = {1: "Uni", 2: "Bi", 3: "Tri", 4: "Cuatri", 5: "Quinti"}
        _k_partes = len(self.particion) if hasattr(self.particion, "__len__") else 2
        _label_particion = f"Mejor {_prefijos_k.get(_k_partes, str(_k_partes))}-Partición"

        if self.estrategia in {"QNodes", "KQNodes"}:
            particion_str = _format_partition_block(self.particion)
        else:
            particion_str = str(self.particion)

        return f"""{Fore.CYAN}{bilinea}

{Fore.RED}{self.estrategia} fue la estrategia de solucion.

{Fore.BLUE}Distancia métrica utilizada:
{Fore.WHITE}{aplicacion.distancia_metrica}
{Fore.BLUE}Notación utilizada en indexación:
{Fore.WHITE}{aplicacion.notacion_indexado}

{Fore.YELLOW}Distribucion {tipo_distribucion} del Subsistema:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_subsistema)}
{Fore.YELLOW}Distribucion {tipo_distribucion} de la Partición:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_particion)}

{Fore.YELLOW}{_label_particion}:
{Fore.MAGENTA}{particion_str}
{Fore.GREEN}Perdida mínima ( φ ) = {self.perdida:.4f}

{Fore.BLUE}Tiempos de ejecución:
{Fore.WHITE}Horas: {tiempo_hrs} = Minutos: {tiempo_min} = Segundos: {tiempo_seg}

{Fore.CYAN}{trilinea}{Style.RESET_ALL}"""

    def __repr__(self) -> str:
        return self.__str__()
