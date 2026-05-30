from src.controllers.manager import Manager

# 👇 Importación de estrategias 👇 #
from src.strategies.force import BruteForce
from src.strategies.q_nodes import QNodes


def iniciar():
    """Punto de entrada"""
    # "1111111111"
    # "1111111110"
    # "0111111111"
    # "0111111110"
    # "1101101101"
    # "1010101010"
    # "0101010101"

    # ABCD #
    estado_inicial = "1000000000"
    condiciones =    "1111111111"
    alcance =        "0101010101"
    mecanismo =      "0101010101"

    gestor_redes = Manager(estado_inicial)
    mpt = gestor_redes.cargar_red()

    ### Ejemplo de solución mediante módulo de fuerza bruta ###
    # analizador_bf = BruteForce(mpt)
    analizador_bf = QNodes(mpt)

    sia_cero = analizador_bf.aplicar_estrategia(
        estado_inicial,
        condiciones,
        alcance,
        mecanismo,
    )
    print(sia_cero)
