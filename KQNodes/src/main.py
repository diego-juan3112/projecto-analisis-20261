from src.strategies.kqnodes import KQNodesStrategy


def iniciar():
    """Punto de entrada de KQNodes."""

    estado_inicial = "1000"
    condiciones = "1110"
    alcance = "1110"
    mecanismo = "1110"

    analizador = KQNodesStrategy(estado_inicial)
    resultado = analizador.aplicar_estrategia(
        estado_inicial,
        condiciones,
        alcance,
        mecanismo,
    )

    print(resultado)
